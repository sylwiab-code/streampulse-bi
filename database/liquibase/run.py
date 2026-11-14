"""Run Liquibase in Docker against one StreamPulse environment (ADR-003).

From the repository root:

    uv run python database/liquibase/run.py --env dev update-sql   # preview
    uv run python database/liquibase/run.py --env dev update       # apply

Locally only DEV is allowed (CLAUDE.md). TEST and PROD are changed only by the CD workflow
(Phase 7). Connection settings come from environment variables or the gitignored .env file:
SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, and SNOWFLAKE_PRIVATE_KEY_PATH. The key file is mounted
read-only into the container; its content is never read or printed by this script.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

LIQUIBASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = LIQUIBASE_DIR.parents[1]
IMAGE = "streampulse-liquibase:5.0.4"
ENVIRONMENTS = ("dev", "test", "prod")
REQUIRED = ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PRIVATE_KEY_PATH")
CONTAINER_KEY = "/keys/deployer.p8"


def read_env_file(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE lines; comments and blank lines are ignored."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def load_settings(environ: Mapping[str, str], env_file: Path) -> dict[str, str]:
    """Environment variables override the .env file."""
    values = {**read_env_file(env_file), **{k: v for k, v in environ.items() if v}}
    missing = [name for name in REQUIRED if not values.get(name)]
    if missing:
        raise SystemExit(f"Missing settings: {', '.join(missing)} (see .env.example).")
    return values


def check_environment(env: str, environ: Mapping[str, str]) -> None:
    if env != "dev" and environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit(
            f"{env.upper()} is changed only by the CD workflow; use --env dev locally."
        )


def jdbc_url(account: str, env: str) -> str:
    return (
        f"jdbc:snowflake://{account}.snowflakecomputing.com/"
        f"?db=STREAMPULSE_ADMIN&schema=LIQUIBASE&warehouse=WH_DEPLOY&role=DEPLOYER_{env.upper()}"
        f"&authenticator=SNOWFLAKE_JWT&private_key_file={CONTAINER_KEY}"
    )


def docker_command(env: str, key_file: Path, liquibase_args: Sequence[str]) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        # Values are passed through the environment, not the command line.
        "--env",
        "LIQUIBASE_COMMAND_URL",
        "--env",
        "LIQUIBASE_COMMAND_USERNAME",
        "--env",
        "LIQUIBASE_ANALYTICS_ENABLED=false",
        "--volume",
        f"{LIQUIBASE_DIR}:/liquibase/changelog:ro",
        "--volume",
        f"{key_file}:{CONTAINER_KEY}:ro",
        "--workdir",
        "/liquibase/changelog",
        IMAGE,
        f"--defaults-file=env/{env}.properties",
        "--search-path=/liquibase/changelog",
        *liquibase_args,
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Liquibase in Docker for one environment.")
    parser.add_argument("--env", choices=ENVIRONMENTS, required=True)
    parser.add_argument("liquibase_args", nargs=argparse.REMAINDER, help="e.g. update-sql")
    args = parser.parse_args(argv)
    if not args.liquibase_args:
        parser.error("give a Liquibase command, for example update-sql")
    check_environment(args.env, os.environ)
    values = load_settings(os.environ, REPO_ROOT / ".env")
    key_file = Path(values["SNOWFLAKE_PRIVATE_KEY_PATH"]).expanduser().resolve()
    if not key_file.is_file():
        raise SystemExit("SNOWFLAKE_PRIVATE_KEY_PATH does not point to a file.")

    subprocess.run(
        ["docker", "build", "--quiet", "--tag", IMAGE, str(LIQUIBASE_DIR)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    environ = {
        **os.environ,
        "LIQUIBASE_COMMAND_URL": jdbc_url(values["SNOWFLAKE_ACCOUNT"], args.env),
        "LIQUIBASE_COMMAND_USERNAME": values["SNOWFLAKE_USER"],
    }
    command = docker_command(args.env, key_file, args.liquibase_args)
    return subprocess.run(command, env=environ, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
