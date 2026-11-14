"""Unit tests for the loader; a fake connection records SQL instead of calling Snowflake."""

from __future__ import annotations

from pathlib import Path

import pytest

from streampulse_loader.load import Batch, copy_statement, discover, load, put_statement
from streampulse_loader.settings import load_settings

ENVIRONMENT = {
    "SNOWFLAKE_ACCOUNT": "myorg-myaccount",
    "SNOWFLAKE_USER": "SVC_DEPLOYER_DEV",
    "SNOWFLAKE_PRIVATE_KEY_PATH": "~/.snowflake/keys/svc_deployer_dev.p8",
}


class FakeCursor:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.description: list[tuple] | None = None
        self._rows: list[tuple] = []

    def execute(self, sql: str) -> None:
        self.statements.append(sql)
        if sql.startswith("copy into raw.customers"):
            self.description = [("file",), ("status",), ("rows_parsed",), ("rows_loaded",)]
            self._rows = [("a.parquet", "LOADED", 10, 10), ("b.parquet", "LOADED", 5, 5)]
        else:
            self.description = [("status",)]
            self._rows = [("Copy executed with 0 files processed.",)]

    def fetchall(self) -> list[tuple]:
        return self._rows


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_ = FakeCursor()

    def cursor(self) -> FakeCursor:
        return self.cursor_


@pytest.fixture
def data_root(tmp_path: Path) -> Path:
    for table, day in [
        ("customers", "2025-01-01"),
        ("customers", "2025-01-02"),
        ("plans", "2025-01-02"),
    ]:
        folder = tmp_path / table / f"load_date={day}"
        folder.mkdir(parents=True)
        (folder / "data.parquet").write_bytes(b"")
    (tmp_path / "plans" / "load_date=2025-01-03").mkdir()  # empty batch folder
    return tmp_path


def test_discover_finds_batches_with_files(data_root):
    batches = discover(data_root)
    assert [(b.table, b.load_date) for b in batches] == [
        ("customers", "2025-01-01"),
        ("customers", "2025-01-02"),
        ("plans", "2025-01-02"),
    ]
    assert [b.table for b in discover(data_root, ["plans"])] == ["plans"]


def test_discover_needs_a_data_folder(tmp_path):
    with pytest.raises(SystemExit, match="generate backfill"):
        discover(tmp_path / "missing")


def test_discover_rejects_unexpected_folder_names(tmp_path):
    (tmp_path / "bad;name" / "load_date=2025-01-01").mkdir(parents=True)
    with pytest.raises(SystemExit, match="Unexpected table folder"):
        discover(tmp_path)


def test_put_keeps_the_batch_layout_and_never_overwrites(tmp_path):
    statement = put_statement(Batch("customers", "2025-01-01", tmp_path))
    assert statement.startswith("put 'file://")
    assert "/*.parquet' @raw.landing/customers/load_date=2025-01-01/" in statement
    assert "overwrite = false" in statement


def test_copy_matches_columns_by_name_and_records_metadata():
    statement = copy_statement("viewing_sessions")
    assert statement.startswith(
        "copy into raw.viewing_sessions from @raw.landing/viewing_sessions/"
    )
    assert "match_by_column_name = case_insensitive" in statement
    assert "_file_name = metadata$filename" in statement
    with pytest.raises(ValueError):
        copy_statement("customers; drop table x")


def test_load_puts_every_batch_and_copies_each_table_once(data_root):
    connection = FakeConnection()
    loaded = load(connection, discover(data_root))
    statements = connection.cursor_.statements
    assert sum(s.startswith("put ") for s in statements) == 3
    assert [s.split()[2] for s in statements if s.startswith("copy ")] == [
        "raw.customers",
        "raw.plans",
    ]
    assert loaded == {"customers": 15, "plans": 0}


def test_settings_use_dev_names():
    settings = load_settings("dev", ENVIRONMENT, Path("missing.env"))
    assert settings.database == "STREAMPULSE_DEV"
    assert settings.role("loader") == "LOADER_DEV"
    assert settings.warehouse("load") == "WH_LOAD_DEV"
    assert settings.private_key_path.name == "svc_deployer_dev.p8"


@pytest.mark.parametrize("env", ["test", "prod"])
def test_settings_refuse_other_environments_locally(env):
    with pytest.raises(SystemExit, match="only by the CD workflow"):
        load_settings(env, ENVIRONMENT, Path("missing.env"))


def test_settings_name_missing_values():
    with pytest.raises(SystemExit, match="SNOWFLAKE_ACCOUNT"):
        load_settings("dev", {}, Path("missing.env"))
