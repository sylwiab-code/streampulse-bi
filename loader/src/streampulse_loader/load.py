"""Upload Parquet batches to the raw stage and copy them into the raw tables (ADR-003).

Both steps are idempotent: PUT skips files already on the stage, and COPY skips files it has
already loaded (Snowflake load history), so a rerun loads only new batches.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_LOAD_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class Batch:
    table: str
    load_date: str
    folder: Path


def discover(root: Path, tables: Iterable[str] | None = None) -> list[Batch]:
    """Find <root>/<table>/load_date=YYYY-MM-DD folders that contain Parquet files."""
    if not root.is_dir():
        raise SystemExit(f"No data folder at {root}; run `uv run generate backfill` first.")
    wanted = set(tables) if tables else None
    batches = []
    for table_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if wanted is not None and table_dir.name not in wanted:
            continue
        if not _NAME.match(table_dir.name):
            raise SystemExit(f"Unexpected table folder name: {table_dir.name}")
        for folder in sorted(table_dir.glob("load_date=*")):
            load_date = folder.name.split("=", 1)[1]
            if _LOAD_DATE.match(load_date) and any(folder.glob("*.parquet")):
                batches.append(Batch(table_dir.name, load_date, folder))
    return batches


def put_statement(batch: Batch) -> str:
    source = (batch.folder.resolve() / "*.parquet").as_posix()
    target = f"@raw.landing/{batch.table}/load_date={batch.load_date}/"
    return f"put 'file://{source}' {target} auto_compress = false overwrite = false"


def copy_statement(table: str) -> str:
    if not _NAME.match(table):
        raise ValueError(f"invalid table name: {table}")
    return (
        f"copy into raw.{table} from @raw.landing/{table}/ "
        "file_format = (format_name = raw.parquet_format) "
        "match_by_column_name = case_insensitive "
        "include_metadata = (_file_name = metadata$filename, "
        "_file_row_number = metadata$file_row_number, _loaded_at = metadata$start_scan_time) "
        "on_error = abort_statement"
    )


def _rows_loaded(cursor: Any) -> int:
    columns = [column[0].lower() for column in cursor.description or []]
    if "rows_loaded" not in columns:  # "Copy executed with 0 files processed."
        return 0
    index = columns.index("rows_loaded")
    return sum(int(row[index]) for row in cursor.fetchall())


def load(connection: Any, batches: Iterable[Batch]) -> dict[str, int]:
    """Upload and copy the batches; return the rows loaded per table in this run."""
    batches = list(batches)
    cursor = connection.cursor()
    for batch in batches:
        cursor.execute(put_statement(batch))
    loaded = {}
    for table in sorted({batch.table for batch in batches}):
        cursor.execute(copy_statement(table))
        loaded[table] = _rows_loaded(cursor)
    return loaded
