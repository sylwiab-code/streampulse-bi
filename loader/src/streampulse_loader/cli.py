"""Command line: `load --env dev [--path data/raw] [--table NAME ...]`."""

from __future__ import annotations

import argparse
import time
from collections.abc import Sequence
from pathlib import Path

from .load import discover, load
from .settings import ENVIRONMENTS, connect, load_settings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="load", description="Load generated Parquet batches into the Snowflake raw layer."
    )
    parser.add_argument("--env", choices=ENVIRONMENTS, required=True)
    parser.add_argument(
        "--path", type=Path, default=Path("data/raw"), help="data folder (default: data/raw)"
    )
    parser.add_argument("--table", action="append", help="load only this table (repeatable)")
    args = parser.parse_args(argv)

    settings = load_settings(args.env)
    batches = discover(args.path, args.table)
    if not batches:
        print(f"No batches found in {args.path}.")
        return 0
    started = time.perf_counter()
    connection = connect(settings, settings.role("loader"), settings.warehouse("load"))
    try:
        loaded = load(connection, batches)
    finally:
        connection.close()
    print(f"Loaded {len(batches)} batch folders into {settings.database}.RAW:")
    for table, rows in loaded.items():
        print(f"  {table:<25} {rows:>10,} new rows")
    print(f"Done in {time.perf_counter() - started:.1f} s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
