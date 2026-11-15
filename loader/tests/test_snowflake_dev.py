"""Integration tests against the live DEV environment (Phase 2 Definition of Done).

Opt in with STREAMPULSE_SNOWFLAKE_TESTS=1 after Liquibase has built DEV and the loader has
loaded data. Queries return counts only, never PII values (CLAUDE.md).
"""

from __future__ import annotations

import os
from datetime import date
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


def test_transformer_hash_links_repeat_trial_emails(settings):
    """The normalized email hash drops +tags, so repeat-trial sign-ups share a hash."""
    (shared_hashes,) = query(
        settings,
        "transformer",
        "transform",
        "select count(*) from (select email from raw.customers "
        "group by email having count(distinct customer_id) > 1)",
    )
    assert shared_hashes > 0


@pytest.mark.parametrize("function", ["reporter", "ai_readonly"])
def test_reporting_roles_read_marts_and_kpis(settings, function):
    customers, subscriber_days = query(
        settings,
        function,
        "report",
        "select (select count(*) from marts.dim_customer), "
        "(select count(*) from kpi.kpi_subscribers_daily)",
    )
    assert customers > 0
    assert subscriber_days > 0


def test_reporter_cannot_read_staging(settings):
    from snowflake.connector.errors import ProgrammingError

    with pytest.raises(ProgrammingError):
        query(
            settings,
            "reporter",
            "report",
            "select count(*) from staging.stg_streampulse__customers",
        )


def test_timestamps_and_dates_load_correctly(settings):
    """Parquet logical types must be honored; otherwise timestamps land in the far future."""
    since, until = date(2024, 11, 1), date.today()
    created_from, created_to, rate_from, rate_to = query(
        settings,
        "ai_readonly",
        "report",
        "select min(created_at)::date, max(created_at)::date, min(rate_date), max(rate_date) "
        "from raw.customers, raw.fx_rates",
    )
    assert since <= created_from <= created_to <= until
    assert since <= rate_from <= rate_to <= until


def test_viewing_sessions_schema_versions_split_on_the_change_date(settings):
    old_after_change, new_before_change = query(
        settings,
        "ai_readonly",
        "report",
        "select count_if(device is not null and started_at >= '2026-01-01'), "
        "count_if(device_type is not null and started_at < '2026-01-01') "
        "from raw.viewing_sessions",
    )
    assert (old_after_change, new_before_change) == (0, 0)


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
