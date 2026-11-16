"""Post-refresh validation: each check compares one number from Snowflake with one from Power BI.

Checks live in checks.json next to this module as a list of {"name", "sql", "dax",
"tolerance"}. Each query returns one value. The list is empty until the semantic model exists
(Phase 5).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    name: str
    sql: str
    dax: str
    tolerance: float = 0.005  # relative difference allowed


@dataclass(frozen=True)
class Result:
    check: Check
    snowflake_value: float
    power_bi_value: float

    @property
    def passed(self) -> bool:
        reference = max(abs(self.snowflake_value), 1e-9)
        return abs(self.power_bi_value - self.snowflake_value) / reference <= self.check.tolerance


def load_checks(path: Path) -> list[Check]:
    return [Check(**item) for item in json.loads(path.read_text(encoding="utf-8"))]


def run_checks(
    checks: list[Check],
    query_snowflake: Callable[[str], float],
    query_power_bi: Callable[[str], float],
) -> list[Result]:
    return [Result(c, float(query_snowflake(c.sql)), float(query_power_bi(c.dax))) for c in checks]
