"""Command line: `generate backfill` and `generate daily --days N`."""

from __future__ import annotations

import argparse
import dataclasses
import time
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path

from .batches import apply_defects, write_batches
from .config import GeneratorConfig
from .simulation import simulate


def _parse_date(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"not a date in YYYY-MM-DD format: {text}") from error


def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--seed", type=int, default=GeneratorConfig.seed, help="random seed")
    common.add_argument(
        "--scale", type=float, default=1.0, help="multiplier for the daily sign-up volume"
    )
    common.add_argument(
        "--end-date",
        type=_parse_date,
        default=date.today() - timedelta(days=1),
        help="last day of data (default: yesterday)",
    )
    common.add_argument(
        "--output", type=Path, default=Path("data/raw"), help="output folder (default: data/raw)"
    )
    parser = argparse.ArgumentParser(
        prog="generate", description="Generate synthetic StreamPulse data as Parquet batches."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "backfill", parents=[common], help="write all history up to the end date as one batch"
    )
    daily = commands.add_parser(
        "daily", parents=[common], help="write one batch per day for the last N days"
    )
    daily.add_argument("--days", type=int, default=1, help="number of daily batches (default: 1)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    cfg = GeneratorConfig()
    cfg = dataclasses.replace(cfg, seed=args.seed, daily_signups=cfg.daily_signups * args.scale)
    if args.command == "daily":
        if args.days < 1:
            raise SystemExit("--days must be at least 1")
        load_dates = [args.end_date - timedelta(days=n) for n in range(args.days - 1, -1, -1)]
    else:
        load_dates = [args.end_date]
    if load_dates[0] < cfg.start_date:
        raise SystemExit(f"the first load date must not be before {cfg.start_date}")

    started = time.perf_counter()
    prepared = apply_defects(cfg, simulate(cfg, args.end_date))
    written = write_batches(
        cfg, prepared, args.output, load_dates, backfill=args.command == "backfill"
    )
    for load_date, counts in written.items():
        print(f"{args.command} batch load_date={load_date} -> {args.output}")
        for table, rows in counts.items():
            print(f"  {table:<25} {rows:>10,}")
    print(f"Done in {time.perf_counter() - started:.1f} s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
