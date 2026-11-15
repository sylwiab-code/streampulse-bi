"""Run dbt against the StreamPulse DEV environment (ADR-002).

From the repository root:

    uv run python transform/run_dbt.py deps
    uv run python transform/run_dbt.py build

Connection settings come from environment variables or the gitignored .env file, exactly as
for the loader (SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PRIVATE_KEY_PATH). dbt connects
as TRANSFORMER_DEV (transform/dbt/profiles.yml); TEST and PROD targets arrive with CD in
Phase 7. The private key is passed by path and never read here.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from streampulse_loader.settings import load_settings

PROJECT_DIR = Path(__file__).resolve().parent / "dbt"
REPO_ROOT = PROJECT_DIR.parents[1]


def dbt_environment(environ: dict[str, str] | None = None) -> dict[str, str]:
    settings = load_settings("dev", environ, REPO_ROOT / ".env")
    return {
        **os.environ,
        "SNOWFLAKE_ACCOUNT": settings.account,
        "SNOWFLAKE_USER": settings.user,
        "SNOWFLAKE_PRIVATE_KEY_PATH": str(settings.private_key_path.resolve()),
        "DBT_PROFILES_DIR": str(PROJECT_DIR),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        raise SystemExit("Give a dbt command, for example: build")
    environment = dbt_environment()
    return subprocess.run(["dbt", *args], cwd=PROJECT_DIR, env=environment, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
