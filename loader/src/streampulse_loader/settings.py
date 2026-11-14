"""Snowflake connection settings for one StreamPulse environment (ADR-003).

Credentials come from environment variables or the gitignored .env file: SNOWFLAKE_ACCOUNT,
SNOWFLAKE_USER, and SNOWFLAKE_PRIVATE_KEY_PATH. The private key file is passed to the
Snowflake connector by path; this module never reads or prints it.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ENVIRONMENTS = ("dev", "test", "prod")
REQUIRED = ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PRIVATE_KEY_PATH")


@dataclass(frozen=True)
class Settings:
    env: str
    account: str
    user: str
    private_key_path: Path

    @property
    def database(self) -> str:
        return f"STREAMPULSE_{self.env.upper()}"

    def role(self, function: str) -> str:
        """Functional role name, for example role('loader') -> LOADER_DEV."""
        return f"{function.upper()}_{self.env.upper()}"

    def warehouse(self, workload: str) -> str:
        """Warehouse name, for example warehouse('load') -> WH_LOAD_DEV."""
        return f"WH_{workload.upper()}_{self.env.upper()}"


def read_env_file(path: Path) -> dict[str, str]:
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


def check_environment(env: str, environ: Mapping[str, str]) -> None:
    """Locally only DEV is allowed (CLAUDE.md); other environments run in GitHub Actions."""
    if env not in ENVIRONMENTS:
        raise SystemExit(f"Unknown environment {env!r}; use one of {', '.join(ENVIRONMENTS)}.")
    if env != "dev" and environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit(f"{env.upper()} is used only by the CD workflow; use --env dev.")


def load_settings(
    env: str, environ: Mapping[str, str] | None = None, env_file: Path = Path(".env")
) -> Settings:
    environ = os.environ if environ is None else environ
    check_environment(env, environ)
    values = {**read_env_file(env_file), **{k: v for k, v in environ.items() if v}}
    missing = [name for name in REQUIRED if not values.get(name)]
    if missing:
        raise SystemExit(f"Missing settings: {', '.join(missing)} (see .env.example).")
    return Settings(
        env=env,
        account=values["SNOWFLAKE_ACCOUNT"],
        user=values["SNOWFLAKE_USER"],
        private_key_path=Path(values["SNOWFLAKE_PRIVATE_KEY_PATH"]).expanduser(),
    )


def connect(settings: Settings, role: str, warehouse: str) -> Any:
    """Open a key-pair connection that acts with exactly one role (no secondary roles)."""
    import snowflake.connector  # imported lazily so unit tests need no connector setup

    connection = snowflake.connector.connect(
        account=settings.account,
        user=settings.user,
        authenticator="SNOWFLAKE_JWT",
        private_key_file=str(settings.private_key_path),
        role=role,
        warehouse=warehouse,
        database=settings.database,
        schema="RAW",
        session_parameters={"QUERY_TAG": "streampulse"},
        # No async queries: always log out on close (and silence the connector's warning).
        enable_server_session_keep_alive_auto_detection=False,
    )
    # Masking depends on the roles in the session; secondary roles would widen them.
    connection.cursor().execute("use secondary roles none")
    return connection
