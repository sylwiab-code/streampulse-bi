"""Conventions of the Power BI semantic model, checked on the TMDL text (ADR-011).

Runs offline in CI. Tabular Editor's Best Practice Analyzer (semantic/powerbi/run_bpa.py)
checks more, but needs Windows; these tests keep the rules that matter most on every pull
request: `///` only as an object's description, descriptions and format strings everywhere,
object-level security on financial columns, Polish translations, and no account host.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEFINITION = ROOT / "semantic" / "powerbi" / "StreamPulse.SemanticModel" / "definition"

# Objects that carry a description in TMDL (a /// line directly above the declaration).
DESCRIBED = {
    "table",
    "column",
    "measure",
    "calculationItem",
    "expression",
    "role",
    "perspective",
    "model",
    "hierarchy",
}
# Declarations whose properties sit one level deeper than the declaration; a multi-line
# expression of such an object is two levels deeper.
OBJECTS = {"table", "column", "measure", "calculationItem", "expression", "tablePermission"}
FINANCIAL = re.compile(r"(_eur|_local)$|^mrr_")


def indent(line: str) -> int:
    return len(line) - len(line.lstrip("\t"))


def unquote(name: str) -> str:
    name = name.strip()
    if name.startswith("'") and name.endswith("'"):
        return name[1:-1].replace("''", "'")
    return name


def declaration(line: str) -> tuple[str, str] | None:
    """(keyword, name) for an object declaration such as `measure 'MRR (EUR)' = ...`."""
    match = re.match(r"^\t*([a-zA-Z]+) (.+)$", line)
    if not match or match.group(1) not in DESCRIBED | OBJECTS | {"partition"}:
        return None
    rest = match.group(2)
    quoted = re.match(r"'(?:[^']|'')*'", rest)
    name = quoted.group(0) if quoted else rest.rstrip("= ").split(" = ", 1)[0]
    return match.group(1), unquote(name)


def code_lines(lines: list[str]) -> set[int]:
    """Indexes of lines inside multi-line DAX or M expressions."""
    inside: set[int] = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.endswith("=") or stripped.endswith("= ```"):
            found = declaration(line)
            threshold = indent(line) + 1 if found and found[0] in OBJECTS else indent(line)
            fenced = stripped.endswith("```")
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if fenced:
                    inside.add(j)
                    if nxt.strip() == "```":
                        break
                elif nxt.strip() and indent(nxt) <= threshold:
                    break
                else:
                    inside.add(j)
                j += 1
            i = j
            continue
        i += 1
    return inside


@dataclass
class Item:
    kind: str
    name: str
    description: str = ""
    properties: list[str] = field(default_factory=list)

    @property
    def hidden(self) -> bool:
        return "isHidden" in self.properties


@dataclass
class Table(Item):
    items: list[Item] = field(default_factory=list)


def parse_table(path: Path) -> Table:
    lines = path.read_text(encoding="utf-8").split("\n")
    code = code_lines(lines)
    table: Table | None = None
    current: Item | None = None
    pending: list[str] = []
    for n, line in enumerate(lines):
        if n in code or not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("///"):
            pending.append(stripped[3:].strip())
            continue
        found = declaration(line)
        level = indent(line)
        if found and level == 0 and found[0] == "table":
            table = Table("table", found[1], " ".join(pending))
            current = table
        elif found and table and found[0] in {"column", "measure", "calculationItem"}:
            current = Item(found[0], found[1], " ".join(pending))
            table.items.append(current)
        elif found and found[0] == "partition":
            current = None
        elif current is not None and table is not None:
            owner_level = 0 if current is table else (2 if current.kind == "calculationItem" else 1)
            if level == owner_level + 1:
                current.properties.append(stripped)
        pending = []
    assert table is not None, path
    return table


@pytest.fixture(scope="module")
def tables() -> dict[str, Table]:
    parsed = [parse_table(path) for path in sorted((DEFINITION / "tables").glob("*.tmdl"))]
    return {table.name: table for table in parsed}


def all_files() -> list[Path]:
    return sorted(DEFINITION.rglob("*.tmdl"))


def test_model_has_the_planned_tables(tables):
    assert {"Date", "Market", "Subscribers Daily", "Viewing Sessions", "Time Intelligence"} <= set(
        tables
    )
    assert len(tables) >= 20


def test_triple_slash_is_only_an_object_description_and_there_are_no_comments():
    problems = []
    for path in all_files():
        lines = [*path.read_text(encoding="utf-8").split("\n"), ""]
        code = code_lines(lines)
        for n, line in enumerate(lines[:-1]):
            stripped = line.strip()
            if n in code or not stripped.startswith("//"):
                continue
            where = f"{path.relative_to(DEFINITION)}:{n + 1}"
            following = lines[n + 1]
            if not stripped.startswith("///"):
                problems.append(f"{where}: comment outside an expression")
            elif not following.strip().startswith("///"):
                found = declaration(following)
                if not found or found[0] not in DESCRIBED:
                    problems.append(f"{where}: /// must sit directly above a described object")
    assert problems == []


def test_tables_columns_measures_and_calculation_items_are_described(tables):
    missing = [f"table {t.name}" for t in tables.values() if not t.description]
    missing += [
        f"{item.kind} {t.name}[{item.name}]"
        for t in tables.values()
        for item in t.items
        if not item.description
    ]
    assert missing == []


def test_measure_names_are_unique_and_differ_from_column_names(tables):
    # Power BI compares object names case-insensitively; Desktop refuses to load a measure
    # named like a column (for example Trialists and trialists).
    measures = [m.name.lower() for t in tables.values() for m in t.items if m.kind == "measure"]
    columns = {c.name.lower() for t in tables.values() for c in t.items if c.kind == "column"}
    assert sorted({m for m in measures if measures.count(m) > 1}) == []
    assert sorted(set(measures) & columns) == []


def test_columns_are_never_summarized_implicitly(tables):
    # Implicit measures are off (discourageImplicitMeasures). Power BI Desktop resets
    # summarizeBy to sum for numeric columns unless SummarizationSetBy is User.
    wrong = [
        f"{t.name}[{c.name}]"
        for t in tables.values()
        for c in t.items
        if c.kind == "column"
        and t.name != "Time Intelligence"
        and not (
            "summarizeBy: none" in c.properties
            and "annotation SummarizationSetBy = User" in c.properties
        )
    ]
    assert wrong == []


def test_measures_have_a_format_string(tables):
    missing = [
        f"{t.name}[{m.name}]"
        for t in tables.values()
        for m in t.items
        if m.kind == "measure"
        and not any(p.startswith(("formatString:", "formatStringDefinition")) for p in m.properties)
    ]
    assert missing == []


def test_visible_measures_have_a_display_folder(tables):
    missing = [
        f"{t.name}[{m.name}]"
        for t in tables.values()
        for m in t.items
        if m.kind == "measure"
        and not m.hidden
        and not any(p.startswith("displayFolder:") for p in m.properties)
    ]
    assert missing == []


def secured_columns() -> set[tuple[str, str]]:
    text = (DEFINITION / "roles" / "Content Analyst.tmdl").read_text(encoding="utf-8")
    secured, table = set(), None
    for line in text.split("\n"):
        if line.startswith("\ttablePermission "):
            table = unquote(line.split("tablePermission ", 1)[1].split(" = ")[0])
        elif line.startswith("\t\tcolumnPermission ") and line.endswith("= none"):
            secured.add((table, unquote(line.split("columnPermission ", 1)[1][: -len(" = none")])))
    return secured


def test_financial_columns_are_secured_for_content_analysts(tables):
    financial = {
        (t.name, c.name)
        for t in tables.values()
        for c in t.items
        if c.kind == "column" and FINANCIAL.search(c.name)
    }
    assert financial
    assert financial - secured_columns() == set()


def polish_captions() -> set[tuple[str, str]]:
    text = (DEFINITION / "cultures" / "pl-PL.tmdl").read_text(encoding="utf-8")
    captions, table, current = set(), None, None
    for line in text.split("\n"):
        stripped = line.strip()
        if indent(line) == 3 and stripped.startswith("table "):
            table = unquote(stripped[len("table ") :])
            current = (table, "")
        elif indent(line) == 4 and stripped.startswith(("column ", "measure ")):
            current = (table, unquote(stripped.split(" ", 1)[1]))
        elif stripped.startswith("caption:") and current:
            captions.add(current)
    return captions


def test_visible_objects_have_polish_captions(tables):
    visible = {(t.name, "") for t in tables.values() if not t.hidden}
    visible |= {
        (t.name, item.name)
        for t in tables.values()
        if not t.hidden
        for item in t.items
        if item.kind in {"column", "measure"} and not item.hidden
    }
    assert visible - polish_captions() == set()


def test_field_parameters_point_at_existing_objects(tables):
    names = {(t.name, item.name) for t in tables.values() for item in t.items}
    for parameter in ("KPI Selector", "Dimension Selector"):
        text = (DEFINITION / "tables" / f"{parameter}.tmdl").read_text(encoding="utf-8")
        refs = re.findall(r"NAMEOF \( ('(?:[^']|'')+'|\w+)\[([^\]]+)\] \)", text)
        assert refs, parameter
        assert [r for r in refs if (unquote(r[0]), r[1]) not in names] == []


def test_snowflake_host_is_a_placeholder():
    text = (DEFINITION / "expressions.tmdl").read_text(encoding="utf-8")
    hosts = re.findall(r'"([^"]*snowflakecomputing\.com)"', text)
    assert hosts == ["ACCOUNT.snowflakecomputing.com"]
