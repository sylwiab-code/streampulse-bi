"""Deliberate data-quality defects and Parquet batches in the raw landing layout (ADR-009).

Layout: <output>/<table>/load_date=YYYY-MM-DD/*.parquet. A backfill writes one batch with every
row that arrived by the end date; a daily run writes one batch per day with the rows that
arrived on that day. Reference tables are written as full snapshots in every batch.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl

from .config import GeneratorConfig
from .randomness import hash_uniform

ARRIVAL = "_arrival_date"


@dataclass(frozen=True)
class TableSpec:
    name: str
    event_column: str | None = None  # None: reference table, written as a snapshot
    snapshot_column: str | None = None  # snapshot rows exist once this date has passed
    id_column: str | None = None
    duplicates: bool = False
    late: bool = False
    nullable_key: str | None = None


TABLES = (
    TableSpec("markets"),
    TableSpec("currencies"),
    TableSpec("plans"),
    TableSpec("plan_prices", snapshot_column="valid_from"),
    TableSpec("content_catalog", snapshot_column="added_date"),
    TableSpec("campaigns", snapshot_column="start_date"),
    TableSpec("fx_rates", event_column="rate_date"),
    TableSpec("campaign_spend", event_column="spend_date"),
    TableSpec("customers", "created_at", id_column="customer_id", duplicates=True),
    TableSpec("acquisition_attribution", "attributed_at"),
    TableSpec("subscriptions", "created_at"),
    TableSpec("subscription_events", "event_at", id_column="event_id", duplicates=True, late=True),
    TableSpec(
        "payments",
        "attempted_at",
        id_column="payment_id",
        duplicates=True,
        late=True,
        nullable_key="customer_id",
    ),
    TableSpec(
        "viewing_sessions",
        "started_at",
        id_column="session_id",
        duplicates=True,
        late=True,
        nullable_key="customer_id",
    ),
)


def apply_defects(cfg: GeneratorConfig, tables: dict[str, pl.DataFrame]) -> dict[str, pl.DataFrame]:
    """Add the arrival date to event tables and inject late rows, missing keys, and duplicates.

    Every decision is a hash of the row id, so a row gets the same defects in every run.
    """
    result = dict(tables)
    for spec in TABLES:
        if spec.event_column is None:
            continue
        frame = tables[spec.name]
        lag = np.zeros(frame.height, dtype=np.int64)
        missing = np.zeros(frame.height, dtype=bool)
        duplicate = np.zeros(frame.height, dtype=bool)
        if spec.id_column is not None:
            ids = frame[spec.id_column].to_numpy()
            if spec.late:
                late = _roll(cfg, spec.name, ids, "late") < cfg.late_rate
                delay = 1 + np.floor(_roll(cfg, spec.name, ids, "lag") * cfg.late_max_days)
                lag = np.where(late, delay, 0).astype(np.int64)
            if spec.nullable_key:
                missing = _roll(cfg, spec.name, ids, "null_key") < cfg.null_key_rate
            if spec.duplicates:
                duplicate = _roll(cfg, spec.name, ids, "duplicate") < cfg.duplicate_rate
        frame = frame.with_columns(
            pl.Series("_lag", lag), pl.Series("_missing", missing), pl.Series("_dup", duplicate)
        ).with_columns(
            (pl.col(spec.event_column).cast(pl.Date) + pl.duration(days=pl.col("_lag"))).alias(
                ARRIVAL
            )
        )
        if spec.nullable_key:
            key = pl.col(spec.nullable_key)
            frame = frame.with_columns(
                pl.when(pl.col("_missing")).then(None).otherwise(key).alias(spec.nullable_key)
            )
        frame = pl.concat([frame, frame.filter(pl.col("_dup"))])
        result[spec.name] = frame.drop("_lag", "_missing", "_dup")
    return result


def _roll(cfg: GeneratorConfig, table: str, ids: np.ndarray, purpose: str) -> np.ndarray:
    return hash_uniform(ids, cfg.seed, table, purpose)


def _snapshot(spec: TableSpec, frame: pl.DataFrame, as_of: date) -> pl.DataFrame:
    if spec.snapshot_column is None:
        return frame
    frame = frame.filter(pl.col(spec.snapshot_column) <= as_of)
    if spec.name == "plan_prices":  # a future end of validity is not known yet
        frame = frame.with_columns(
            pl.when(pl.col("valid_to") < as_of).then(pl.col("valid_to")).alias("valid_to")
        )
    return frame


def select_batch(
    cfg: GeneratorConfig, prepared: dict[str, pl.DataFrame], load_date: date, *, backfill: bool
) -> dict[str, pl.DataFrame]:
    batch = {}
    for spec in TABLES:
        frame = prepared[spec.name]
        if spec.event_column is None:
            batch[spec.name] = _snapshot(spec, frame, load_date)
            continue
        arrived = pl.col(ARRIVAL) <= load_date if backfill else pl.col(ARRIVAL) == load_date
        batch[spec.name] = frame.filter(arrived).drop(ARRIVAL)
    return batch


def _viewing_schema_versions(cfg: GeneratorConfig, frame: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """Sessions from the new app version have device_type and app_version instead of device."""
    changed = pl.col("started_at") >= pl.lit(cfg.schema_change_date).cast(pl.Datetime("us"))
    old = frame.filter(~changed)
    new = frame.filter(changed).rename({"device": "device_type"})
    new = new.with_columns(pl.format("6.0.{}", pl.col("session_id") % 5).alias("app_version"))
    return {"data_schema_v1.parquet": old, "data_schema_v2.parquet": new}


def write_batch(
    cfg: GeneratorConfig, batch: dict[str, pl.DataFrame], output: Path, load_date: date
) -> dict[str, int]:
    """Write one batch, replacing any earlier files for the same load date; return row counts."""
    counts = {}
    for name, frame in batch.items():
        folder = output / name / f"load_date={load_date.isoformat()}"
        if folder.exists():
            for old_file in folder.glob("*.parquet"):
                old_file.unlink()
        counts[name] = frame.height
        if frame.height == 0:
            continue
        folder.mkdir(parents=True, exist_ok=True)
        files = {"data.parquet": frame}
        if name == "viewing_sessions":
            files = _viewing_schema_versions(cfg, frame)
        for file_name, part in files.items():
            if part.height:
                part.write_parquet(folder / file_name)
    return counts


def write_batches(
    cfg: GeneratorConfig,
    prepared: dict[str, pl.DataFrame],
    output: Path,
    load_dates: Iterable[date],
    *,
    backfill: bool,
) -> dict[date, dict[str, int]]:
    return {
        load_date: write_batch(
            cfg, select_batch(cfg, prepared, load_date, backfill=backfill), output, load_date
        )
        for load_date in load_dates
    }
