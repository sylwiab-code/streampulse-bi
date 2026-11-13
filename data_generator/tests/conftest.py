"""Shared fixtures: a small configuration that runs in seconds but covers every feature."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl
import pytest
from streampulse_generator.batches import apply_defects
from streampulse_generator.config import GeneratorConfig
from streampulse_generator.simulation import simulate

# Covers the price increase (2025-09-01) and a schema change inside the window.
SMALL_CONFIG = GeneratorConfig(
    start_date=date(2025, 6, 1),
    daily_signups=30.0,
    catalog_size=500,
    schema_change_date=date(2025, 10, 1),
)


@pytest.fixture(scope="session")
def cfg() -> GeneratorConfig:
    return SMALL_CONFIG


@pytest.fixture(scope="session")
def end_date() -> date:
    return date(2025, 11, 30)


@pytest.fixture(scope="session")
def tables(cfg: GeneratorConfig, end_date: date) -> dict[str, pl.DataFrame]:
    return simulate(cfg, end_date)


@pytest.fixture(scope="session")
def prepared(cfg: GeneratorConfig, tables: dict[str, pl.DataFrame]) -> dict[str, pl.DataFrame]:
    return apply_defects(cfg, tables)


def read_table(root: Path, table: str) -> pl.DataFrame:
    """Read every batch of a table, including files with an older schema version."""
    files = sorted((root / table).glob("load_date=*/*.parquet"))
    return pl.concat([pl.read_parquet(f) for f in files], how="diagonal_relaxed")


@pytest.fixture(scope="session")
def read() -> object:
    return read_table
