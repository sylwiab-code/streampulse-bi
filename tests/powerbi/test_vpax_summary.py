"""Tests for semantic/powerbi/vpax_summary.py (VertiPaq Analyzer summary for docs/performance)."""

from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "semantic" / "powerbi" / "vpax_summary.py"
spec = importlib.util.spec_from_file_location("vpax_summary", SCRIPT)
vpax_summary = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = vpax_summary
spec.loader.exec_module(vpax_summary)


def write_vpax(path: Path, tables: dict[str, tuple[int, int]], columns: list[dict]) -> Path:
    view = {
        "Tables": [
            {"TableName": name, "TableSize": size, "RowsCount": rows}
            for name, (size, rows) in tables.items()
        ],
        "Columns": columns,
    }
    with zipfile.ZipFile(path, "w") as archive:
        # DAX Studio writes the JSON with a byte order mark.
        archive.writestr("DaxVpaView.json", "﻿" + json.dumps(view))
    return path


def column(table: str, name: str, size: int, row_number: bool = False) -> dict:
    return {
        "TableName": table,
        "FullColumnName": f"'{table}'[{name}]",
        "TotalSize": size,
        "IsRowNumber": row_number,
    }


def test_load_groups_auto_date_tables_and_skips_row_numbers(tmp_path):
    path = write_vpax(
        tmp_path / "before.vpax",
        {
            "Sessions": (3_000_000, 100),
            "LocalDateTable_1": (400_000, 10),
            "DateTableTemplate_2": (600_000, 20),
        },
        [
            column("Sessions", "started_at", 2_500_000),
            column("Sessions", "RowNumber-1", 10, row_number=True),
            column("LocalDateTable_1", "Date", 300_000),
        ],
    )
    metrics = vpax_summary.load(path)
    assert metrics.tables == {"Sessions": 3_000_000, vpax_summary.AUTO_DATE_LABEL: 1_000_000}
    assert metrics.rows[vpax_summary.AUTO_DATE_LABEL] == 30
    assert metrics.columns == {"'Sessions'[started_at]": 2_500_000}
    assert metrics.total == 4_000_000


def test_summary_of_one_export_lists_tables_and_largest_columns(tmp_path):
    path = write_vpax(
        tmp_path / "model.vpax",
        {"Sessions": (3_000_000, 1_234), "Date": (500_000, 7)},
        [column("Sessions", "started_at", 2_500_000), column("Date", "Date", 100_000)],
    )
    text = vpax_summary.summary(vpax_summary.load(path), top=1)
    assert "Model size: 3.50 MB, 2 columns." in text
    assert "| Sessions | 1,234 | 3.00 |" in text
    assert "| 'Sessions'[started_at] | 2.50 |" in text
    assert "'Date'[Date]" not in text


def test_summary_compares_before_and_after(tmp_path):
    before = write_vpax(
        tmp_path / "before.vpax",
        {"Sessions": (4_000_000, 100), "LocalDateTable_1": (1_000_000, 10)},
        [column("Sessions", "started_at", 3_000_000), column("Sessions", "title_id", 500_000)],
    )
    after = write_vpax(
        tmp_path / "after.vpax",
        {"Sessions": (1_000_000, 100)},
        [column("Sessions", "title_id", 400_000)],
    )
    text = vpax_summary.summary(vpax_summary.load(before), vpax_summary.load(after), top=2)
    assert "| Model size (MB) | 5.00 | 1.00 | -80% |" in text
    assert "| Sessions | 4.00 | 1.00 | -75% |" in text
    assert f"| {vpax_summary.AUTO_DATE_LABEL} | 1.00 | - | - |" in text
    assert "| 'Sessions'[started_at] | 3.00 | - |" in text
    assert "| 'Sessions'[title_id] | 0.50 | 0.40 |" in text


def test_main_prints_the_summary(tmp_path, capsys):
    path = write_vpax(tmp_path / "model.vpax", {"Sessions": (1_000_000, 5)}, [])
    assert vpax_summary.main([str(path)]) == 0
    assert "Model size: 1.00 MB" in capsys.readouterr().out
