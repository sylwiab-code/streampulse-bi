"""Integration tests against the live DEV environment (Phase 2 Definition of Done).

Opt in with STREAMPULSE_SNOWFLAKE_TESTS=1 after Liquibase has built DEV and the loader has
loaded data. Queries return counts only, never PII values (CLAUDE.md).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from streampulse_loader.settings import Settings, connect, load_settings

pytestmark = pytest.mark.skipif(
    os.environ.get("STREAMPULSE_SNOWFLAKE_TESTS") != "1",
    reason="set STREAMPULSE_SNOWFLAKE_TESTS=1 to run against Snowflake DEV",
)

PII_COLUMNS = ("first_name", "last_name", "email")


@pytest.fixture(scope="module")
def settings() -> Settings:
    return load_settings("dev")


def query(settings: Settings, function: str, warehouse: str, sql: str) -> tuple:
    connection = connect(settings, settings.role(function), settings.warehouse(warehouse))
    try:
        return connection.cursor().execute(sql).fetchone()
    finally:
        connection.close()


def count_where(settings: Settings, function: str, warehouse: str, condition: str) -> tuple:
    """Return (rows, rows matching the condition for every PII column)."""
    checks = ", ".join(f"count_if({condition.format(column=c)})" for c in PII_COLUMNS)
    return query(settings, function, warehouse, f"select count(*), {checks} from raw.customers")


def test_pii_reader_sees_clear_text(settings):
    total, *matches = count_where(
        settings, "pii_reader", "report", "{column} <> '***MASKED***' and len({column}) < 64"
    )
    assert total > 0
    assert matches == [total] * len(PII_COLUMNS)


def test_transformer_sees_sha256_hashes(settings):
    total, *matches = count_where(
        settings, "transformer", "transform", "regexp_like({column}, '[0-9a-f]{{64}}')"
    )
    assert total > 0
    assert matches == [total] * len(PII_COLUMNS)


def test_ai_readonly_sees_masked_values(settings):
    total, *matches = count_where(settings, "ai_readonly", "report", "{column} = '***MASKED***'")
    assert total > 0
    assert matches == [total] * len(PII_COLUMNS)


@pytest.mark.parametrize(("function", "warehouse"), [("reporter", "report"), ("loader", "load")])
def test_roles_without_read_access_cannot_query_raw(settings, function, warehouse):
    from snowflake.connector.errors import ProgrammingError

    with pytest.raises(ProgrammingError):
        query(settings, function, warehouse, "select count(*) from raw.customers")


def test_every_local_file_was_loaded(settings):
    root = Path("data/raw")
    if not root.is_dir():
        pytest.skip("no local data/raw folder")
    for table_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        local_files = len(list(table_dir.glob("load_date=*/*.parquet")))
        (loaded_files,) = query(
            settings,
            "ai_readonly",
            "report",
            f"select count(distinct _file_name) from raw.{table_dir.name}",
        )
        assert loaded_files == local_files, table_dir.name
