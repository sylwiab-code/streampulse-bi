"""The Snowflake-to-model comparison queries in semantic/powerbi/reconciliation.json (ADR-011).

They run by hand until Phase 7 automates them, so these tests keep them in the format that
`powerbi validate` reads and pointing at measures and schemas that exist.
"""

from __future__ import annotations

import re
from pathlib import Path

from streampulse_powerbi.validate import load_checks

SEMANTIC = Path(__file__).resolve().parents[2] / "semantic" / "powerbi"
TABLES = SEMANTIC / "StreamPulse.SemanticModel" / "definition" / "tables"
CHECKS = load_checks(SEMANTIC / "reconciliation.json")


def model_measures() -> set[str]:
    names = set()
    for path in TABLES.glob("*.tmdl"):
        for match in re.finditer(
            r"^\tmeasure ('(?:[^']|'')+'|[^ =]+)", path.read_text("utf-8"), re.MULTILINE
        ):
            name = match.group(1)
            names.add(name[1:-1].replace("''", "'") if name.startswith("'") else name)
    return names


def test_checks_load_and_have_unique_names():
    names = [check.name for check in CHECKS]
    assert len(names) >= 10
    assert len(set(names)) == len(names)


def test_dax_queries_use_existing_measures():
    measures = model_measures()
    for check in CHECKS:
        assert check.dax.startswith("EVALUATE"), check.name
        used = set(re.findall(r"(?<!')\[([^\]]+)\]", check.dax))
        assert used, check.name
        assert used <= measures, (check.name, used - measures)


def test_sql_reads_only_the_reporting_schemas():
    for check in CHECKS:
        schemas = set(re.findall(r"\b(?:from|join)\s+(\w+)\.", check.sql, re.IGNORECASE))
        assert schemas, check.name
        assert schemas <= {"kpi", "marts"}, (check.name, schemas)
