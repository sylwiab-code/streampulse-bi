"""Tests for defects, Parquet batches, and the command line."""

from __future__ import annotations

from datetime import timedelta

import polars as pl
import pytest
from polars.testing import assert_frame_equal
from streampulse_generator.batches import ARRIVAL, TABLES, apply_defects, write_batches
from streampulse_generator.cli import main
from streampulse_generator.simulation import simulate

EVENT_TABLES = [spec.name for spec in TABLES if spec.event_column is not None]


def test_duplicates_late_rows_and_missing_keys(cfg, tables, prepared):
    for name in ("customers", "subscription_events", "payments", "viewing_sessions"):
        extra = prepared[name].height - tables[name].height
        assert extra / tables[name].height == pytest.approx(cfg.duplicate_rate, abs=0.003)

    sessions = prepared["viewing_sessions"]
    lag = (sessions[ARRIVAL] - sessions["started_at"].dt.date()).dt.total_days()
    assert lag.min() == 0
    assert lag.max() == cfg.late_max_days
    assert (lag > 0).mean() == pytest.approx(cfg.late_rate, abs=0.003)

    for name in ("payments", "viewing_sessions"):
        missing = prepared[name]["customer_id"].null_count() / prepared[name].height
        assert missing == pytest.approx(cfg.null_key_rate, abs=0.001)
        assert tables[name]["customer_id"].null_count() == 0


def test_defects_are_deterministic(cfg, tables, prepared):
    again = apply_defects(cfg, tables)
    for name in EVENT_TABLES:
        assert_frame_equal(prepared[name], again[name])


def test_backfill_plus_daily_batches_equal_a_later_backfill(
    cfg, end_date, prepared, tmp_path, read
):
    """The daily load path delivers exactly the same rows as a fresh backfill."""
    earlier = end_date - timedelta(days=3)
    incremental, fresh = tmp_path / "incremental", tmp_path / "fresh"
    earlier_prepared = apply_defects(cfg, simulate(cfg, earlier))
    write_batches(cfg, earlier_prepared, incremental, [earlier], backfill=True)
    daily_dates = [earlier + timedelta(days=n) for n in (1, 2, 3)]
    write_batches(cfg, prepared, incremental, daily_dates, backfill=False)
    write_batches(cfg, prepared, fresh, [end_date], backfill=True)

    for name in EVENT_TABLES:
        a, b = read(incremental, name), read(fresh, name)
        assert_frame_equal(a.sort(a.columns), b.sort(a.columns).select(a.columns))


def test_viewing_sessions_change_schema(cfg, end_date, prepared, tmp_path):
    write_batches(cfg, prepared, tmp_path, [end_date], backfill=True)
    folder = tmp_path / "viewing_sessions" / f"load_date={end_date}"
    old = pl.read_parquet(folder / "data_schema_v1.parquet")
    new = pl.read_parquet(folder / "data_schema_v2.parquet")
    assert "device" in old.columns
    assert "device_type" not in old.columns
    assert {"device_type", "app_version"} <= set(new.columns)
    assert "device" not in new.columns
    change = pl.datetime(cfg.schema_change_date.year, cfg.schema_change_date.month, 1)
    assert old.filter(pl.col("started_at") >= change).height == 0


def test_snapshots_only_show_what_existed(cfg, prepared, tmp_path):
    before_increase = cfg.price_increase_date - timedelta(days=10)
    write_batches(cfg, prepared, tmp_path, [before_increase], backfill=False)
    prices = pl.read_parquet(tmp_path / "plan_prices" / f"load_date={before_increase}" / "*")
    assert (prices["valid_from"] <= before_increase).all()
    assert prices["valid_to"].null_count() == prices.height


def test_cli_daily_writes_one_batch_per_day(tmp_path, read, capsys):
    args = ["daily", "--days", "2", "--end-date", "2024-12-31", "--scale", "0.2"]
    assert main([*args, "--output", str(tmp_path)]) == 0
    folders = sorted(p.name for p in (tmp_path / "customers").iterdir())
    assert folders == ["load_date=2024-12-30", "load_date=2024-12-31"]
    first = read(tmp_path, "payments")

    assert main([*args, "--output", str(tmp_path)]) == 0  # a rerun replaces the batches
    assert_frame_equal(first, read(tmp_path, "payments"))
    assert "daily batch load_date=2024-12-31" in capsys.readouterr().out


def test_cli_backfill(tmp_path):
    args = ["backfill", "--end-date", "2024-11-30", "--scale", "0.2", "--output", str(tmp_path)]
    assert main(args) == 0
    for spec in TABLES:
        assert (tmp_path / spec.name / "load_date=2024-11-30").is_dir(), spec.name


@pytest.mark.parametrize(
    "args",
    [
        ["daily", "--days", "0", "--end-date", "2024-12-31"],
        ["backfill", "--end-date", "2024-01-01"],
    ],
)
def test_cli_rejects_invalid_ranges(args, tmp_path):
    with pytest.raises(SystemExit):
        main([*args, "--output", str(tmp_path)])


def test_cli_rejects_bad_dates(tmp_path):
    with pytest.raises(SystemExit):
        main(["backfill", "--end-date", "31.12.2024", "--output", str(tmp_path)])
