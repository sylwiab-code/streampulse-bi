"""Tests for semantic/powerbi/connection.py (Snowflake host placeholder guard)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "semantic" / "powerbi" / "connection.py"
spec = importlib.util.spec_from_file_location("powerbi_connection", SCRIPT)
connection = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = connection
spec.loader.exec_module(connection)

TEXT = (
    '/// Host.\nexpression SnowflakeServer = "ACCOUNT.snowflakecomputing.com" meta '
    '[IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n\n'
    'expression SnowflakeRole = "REPORTER_DEV" meta [IsParameterQuery=true]\n'
)


@pytest.fixture
def expressions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "expressions.tmdl"
    path.write_text(TEXT, encoding="utf-8")
    monkeypatch.setattr(connection, "EXPRESSIONS", path)
    monkeypatch.setattr(connection, "ENV_FILE", tmp_path / ".env")
    return path


def test_set_writes_the_host_from_the_account(expressions, monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "ORG-ACCT1")
    assert connection.main(["set"]) == 0
    text = expressions.read_text(encoding="utf-8")
    assert connection.read_server(text) == "org-acct1.snowflakecomputing.com"
    assert 'SnowflakeRole = "REPORTER_DEV"' in text


def test_reset_restores_the_placeholder_and_fails_once(expressions, monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "ORG-ACCT1")
    connection.main(["set"])
    assert connection.main(["reset"]) == 1
    assert expressions.read_text(encoding="utf-8") == TEXT
    assert connection.main(["reset"]) == 0


def test_set_reads_the_account_from_the_env_file(expressions, monkeypatch, tmp_path):
    monkeypatch.delenv("SNOWFLAKE_ACCOUNT", raising=False)
    (tmp_path / ".env").write_text("# local\nSNOWFLAKE_ACCOUNT=ORG-ACCT2\n", encoding="utf-8")
    connection.main(["set"])
    assert connection.read_server(expressions.read_text(encoding="utf-8")).startswith("org-acct2.")


@pytest.mark.parametrize("account", ["", "acct; drop", 'a"b'])
def test_invalid_accounts_are_refused(account):
    with pytest.raises(SystemExit, match="SNOWFLAKE_ACCOUNT"):
        connection.account_host({"SNOWFLAKE_ACCOUNT": account})
