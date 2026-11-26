"""Summarize VertiPaq Analyzer exports (.vpax) as Markdown for docs/performance (ADR-011).

Export a .vpax with DAX Studio (Advanced > Export Metrics) or its command line:

    dscmd vpax baseline.vpax -s localhost:<port> -d <database>

Then, from the repository root:

    uv run python semantic/powerbi/vpax_summary.py baseline.vpax [optimized.vpax]

With two files the tables show before, after, and the change. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

AUTO_DATE_TABLES = ("LocalDateTable_", "DateTableTemplate_")
AUTO_DATE_LABEL = "(auto date/time tables)"


@dataclass(frozen=True)
class Metrics:
    tables: dict[str, int]  # bytes per table; auto date/time tables grouped
    rows: dict[str, int]
    columns: dict[str, int]  # bytes per 'Table'[Column], row-number columns excluded
    column_count: int

    @property
    def total(self) -> int:
        return sum(self.tables.values())


def load(path: Path) -> Metrics:
    with zipfile.ZipFile(path) as archive:
        view = json.loads(archive.read("DaxVpaView.json").decode("utf-8-sig"))
    tables: dict[str, int] = {}
    rows: dict[str, int] = {}
    for table in view["Tables"]:
        name = table["TableName"]
        if name.startswith(AUTO_DATE_TABLES):
            name = AUTO_DATE_LABEL
        tables[name] = tables.get(name, 0) + int(table["TableSize"])
        rows[name] = rows.get(name, 0) + int(table["RowsCount"])
    columns = {
        column["FullColumnName"]: int(column["TotalSize"])
        for column in view["Columns"]
        if not column.get("IsRowNumber") and not column["TableName"].startswith(AUTO_DATE_TABLES)
    }
    return Metrics(tables, rows, columns, len(columns))


def megabytes(size: int | None) -> str:
    return "-" if size is None else f"{size / 1_000_000:,.2f}"


def change(before: int | None, after: int | None) -> str:
    if not before or after is None:
        return "-"
    return f"{(after - before) / before:+.0%}"


def table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def summary(before: Metrics, after: Metrics | None = None, top: int = 10) -> str:
    out = []
    if after is None:
        out.append(f"Model size: {megabytes(before.total)} MB, {before.column_count} columns.\n")
        ranked = sorted(before.tables.items(), key=lambda item: -item[1])
        out.append(
            table(
                ["Table", "Rows", "Size (MB)"],
                [[name, f"{before.rows[name]:,}", megabytes(size)] for name, size in ranked],
            )
        )
        largest = sorted(before.columns.items(), key=lambda item: -item[1])[:top]
        out.append(f"\nLargest {top} columns:\n")
        out.append(table(["Column", "Size (MB)"], [[n, megabytes(s)] for n, s in largest]))
        return "\n".join(out)

    out.append(
        table(
            ["Measure", "Before", "After", "Change"],
            [
                [
                    "Model size (MB)",
                    megabytes(before.total),
                    megabytes(after.total),
                    change(before.total, after.total),
                ],
                ["Columns", str(before.column_count), str(after.column_count), "-"],
            ],
        )
    )
    names = sorted(set(before.tables) | set(after.tables), key=lambda n: -before.tables.get(n, 0))
    out.append("\nSize per table (MB):\n")
    out.append(
        table(
            ["Table", "Before", "After", "Change"],
            [
                [
                    name,
                    megabytes(before.tables.get(name)),
                    megabytes(after.tables.get(name)),
                    change(before.tables.get(name), after.tables.get(name)),
                ]
                for name in names
            ],
        )
    )
    largest = sorted(before.columns.items(), key=lambda item: -item[1])[:top]
    out.append(f"\nLargest {top} columns before (MB):\n")
    out.append(
        table(
            ["Column", "Before", "After"],
            [[n, megabytes(s), megabytes(after.columns.get(n))] for n, s in largest],
        )
    )
    return "\n".join(out)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vpax_summary", description=__doc__.split("\n")[0])
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path, nargs="?")
    parser.add_argument("--top", type=int, default=10, help="largest columns to list")
    args = parser.parse_args(argv)
    print(summary(load(args.before), load(args.after) if args.after else None, args.top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
