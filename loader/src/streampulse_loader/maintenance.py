"""Maintenance for one environment: table statistics and cleanup of old CI schemas.

`maintain --env dev stats` prints row counts and sizes. `maintain --env dev ci-schemas` lists
CI schemas (CI_*, created per pull request from Phase 7) older than the threshold; it drops
them only with --execute. Runs as DEPLOYER_<ENV>, the owner of the environment's schemas.
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from .settings import ENVIRONMENTS, connect, load_settings

CI_SCHEMA = re.compile(r"^CI_[A-Z0-9_]+$")


def table_stats(connection: Any, database: str) -> list[tuple]:
    sql = (
        "select table_schema, table_name, row_count, bytes "
        f"from {database}.information_schema.tables "
        "where table_type = 'BASE TABLE' and table_schema <> 'INFORMATION_SCHEMA' "
        "order by bytes desc"
    )
    return connection.cursor().execute(sql).fetchall()


def old_ci_schemas(connection: Any, database: str, older_than_days: int) -> list[str]:
    cursor = connection.cursor()
    cursor.execute(f"show terse schemas like 'CI\\\\_%' in database {database}")
    columns = [column[0].lower() for column in cursor.description]
    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    names = []
    for row in cursor.fetchall():
        record = dict(zip(columns, row, strict=True))
        if record["created_on"] < cutoff and CI_SCHEMA.match(record["name"]):
            names.append(record["name"])
    return sorted(names)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="maintain", description="Environment maintenance.")
    parser.add_argument("--env", choices=ENVIRONMENTS, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("stats", help="row counts and sizes of all tables")
    ci = commands.add_parser("ci-schemas", help="list (and with --execute drop) old CI schemas")
    ci.add_argument("--older-than-days", type=int, default=7)
    ci.add_argument("--execute", action="store_true", help="drop the schemas (default: list)")
    args = parser.parse_args(argv)

    settings = load_settings(args.env)
    connection = connect(settings, settings.role("deployer"), "WH_DEPLOY")
    try:
        if args.command == "stats":
            for schema, table, rows, size in table_stats(connection, settings.database):
                print(f"{schema}.{table:<40} {rows or 0:>12,} rows {(size or 0) / 1e6:>10.1f} MB")
            return 0
        names = old_ci_schemas(connection, settings.database, args.older_than_days)
        if not names:
            print(f"No CI schemas older than {args.older_than_days} days.")
        for name in names:
            if args.execute:
                connection.cursor().execute(f"drop schema if exists {settings.database}.{name}")
                print(f"Dropped {settings.database}.{name}")
            else:
                print(f"Would drop {settings.database}.{name} (use --execute)")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
