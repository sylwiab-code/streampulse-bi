"""Tests for the Liquibase runner in database/liquibase/run.py (no Docker or Snowflake needed)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

RUN_PATH = Path(__file__).resolve().parents[2] / "database" / "liquibase" / "run.py"
_spec = importlib.util.spec_from_file_location("liquibase_run", RUN_PATH)
assert _spec is not None and _spec.loader is not None
run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run)

SETTINGS = {
    "SNOWFLAKE_ACCOUNT": "myorg-myaccount",
    "SNOWFLAKE_USER": "SVC_DEPLOYER_DEV",
    "SNOWFLAKE_PRIVATE_KEY_PATH": "/home/me/.snowflake/keys/svc_deployer_dev.p8",
}


@pytest.mark.parametrize("env", ["test", "prod"])
def test_only_dev_runs_locally(env):
    with pytest.raises(SystemExit, match="only by the CD workflow"):
        run.check_environment(env, {})


@pytest.mark.parametrize("env", ["test", "prod"])
def test_other_environments_run_in_github_actions(env):
    run.check_environment(env, {"GITHUB_ACTIONS": "true"})


def test_dev_runs_locally():
    run.check_environment("dev", {})


def test_settings_come_from_env_file_and_environment(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\nSNOWFLAKE_ACCOUNT=from-file\nSNOWFLAKE_USER='SVC_DEPLOYER_DEV'\n"
        "SNOWFLAKE_PRIVATE_KEY_PATH=/keys/a.p8\n"
    )
    values = run.load_settings({"SNOWFLAKE_ACCOUNT": "from-environment"}, env_file)
    assert values["SNOWFLAKE_ACCOUNT"] == "from-environment"
    assert values["SNOWFLAKE_USER"] == "SVC_DEPLOYER_DEV"


def test_missing_settings_are_named(tmp_path):
    with pytest.raises(SystemExit, match="SNOWFLAKE_USER, SNOWFLAKE_PRIVATE_KEY_PATH"):
        run.load_settings({"SNOWFLAKE_ACCOUNT": "x"}, tmp_path / "missing.env")


def test_jdbc_url_uses_the_environment_deployer():
    url = run.jdbc_url(SETTINGS["SNOWFLAKE_ACCOUNT"], "dev")
    assert url.startswith("jdbc:snowflake://myorg-myaccount.snowflakecomputing.com/")
    assert "role=DEPLOYER_DEV" in url
    assert "authenticator=SNOWFLAKE_JWT" in url
    assert f"private_key_file={run.CONTAINER_KEY}" in url


def test_docker_command_mounts_read_only_and_keeps_values_off_the_command_line():
    key = Path(SETTINGS["SNOWFLAKE_PRIVATE_KEY_PATH"])
    command = run.docker_command("dev", key, ["update-sql"])
    assert command[-1] == "update-sql"
    assert "--defaults-file=env/dev.properties" in command
    assert f"{key}:{run.CONTAINER_KEY}:ro" in command
    assert all(SETTINGS["SNOWFLAKE_ACCOUNT"] not in part for part in command)
    assert "LIQUIBASE_COMMAND_URL" in command


@pytest.mark.parametrize("env", run.ENVIRONMENTS)
def test_every_environment_has_a_properties_file(env):
    properties = (run.LIQUIBASE_DIR / "env" / f"{env}.properties").read_text()
    assert f"parameter.env={env.upper()}" in properties
    assert f"databaseChangeLogTableName=DATABASECHANGELOG_{env.upper()}" in properties
    assert f"contexts={env}" in properties


def test_changelog_includes_every_sql_file():
    changelog = (run.LIQUIBASE_DIR / "changelog.yaml").read_text()
    for sql_file in sorted((run.LIQUIBASE_DIR / "changelogs").glob("*.sql")):
        assert f"changelogs/{sql_file.name}" in changelog


def test_changesets_have_rollbacks():
    for sql_file in (run.LIQUIBASE_DIR / "changelogs").glob("*.sql"):
        changesets = sql_file.read_text().split("-- changeset ")[1:]
        for changeset in changesets:
            assert "-- rollback " in changeset, f"{sql_file.name}: {changeset.splitlines()[0]}"
