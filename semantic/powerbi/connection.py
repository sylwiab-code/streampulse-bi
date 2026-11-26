"""Keep the Snowflake account host out of Git (ADR-011).

The repository stores a placeholder in the SnowflakeServer parameter. Locally, before opening
the model in Power BI Desktop:

    uv run python semantic/powerbi/connection.py set     # host from SNOWFLAKE_ACCOUNT (.env)

Before committing, the pre-commit hook runs `connection.py reset`, which restores the
placeholder and fails once so that the restored file is staged instead. Standard library only
(the hook runs in its own environment).
"""

from __future__ import annotations

import argparse
import os
import re
from collections.abc import Sequence
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPRESSIONS = HERE / "StreamPulse.SemanticModel" / "definition" / "expressions.tmdl"
ENV_FILE = HERE.parents[1] / ".env"
PLACEHOLDER = "ACCOUNT.snowflakecomputing.com"
SERVER = re.compile(r'^(expression SnowflakeServer = ")([^"]*)(")', re.MULTILINE)


def read_server(text: str) -> str:
    match = SERVER.search(text)
    if not match:
        raise SystemExit(f"No SnowflakeServer parameter in {EXPRESSIONS}.")
    return match.group(2)


def with_server(text: str, server: str) -> str:
    read_server(text)
    return SERVER.sub(lambda m: f"{m.group(1)}{server}{m.group(3)}", text, count=1)


def account_host(environ: dict[str, str]) -> str:
    account = environ.get("SNOWFLAKE_ACCOUNT", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", account):
        raise SystemExit("SNOWFLAKE_ACCOUNT is missing or invalid (see .env.example).")
    return f"{account.lower()}.snowflakecomputing.com"


def env_values(path: Path) -> dict[str, str]:
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip("'\"")
    return {**values, **os.environ}


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="connection", description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["set", "reset"])
    args = parser.parse_args(argv)
    text = EXPRESSIONS.read_text(encoding="utf-8")
    if args.command == "set":
        write(EXPRESSIONS, with_server(text, account_host(env_values(ENV_FILE))))
        print("SnowflakeServer set from SNOWFLAKE_ACCOUNT. Run `connection.py reset` to undo.")
        return 0
    if read_server(text) == PLACEHOLDER:
        return 0
    write(EXPRESSIONS, with_server(text, PLACEHOLDER))
    print(f"Restored the SnowflakeServer placeholder in {EXPRESSIONS.name}; stage it again.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
