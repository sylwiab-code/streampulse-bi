"""Checks the dbt conventions from CLAUDE.md and docs/standards on the parsed manifest.

`dbt parse` needs no warehouse connection; the profile gets placeholder values. The tests are
skipped when the dbt packages are not installed (run `uv run python transform/run_dbt.py deps`).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[2] / "transform" / "dbt"
LAYER_PREFIXES = {
    "staging": r"^stg_[a-z0-9]+__[a-z0-9_]+$",
    "intermediate": r"^int_[a-z0-9_]+_[a-z]+ed$",
    "marts": r"^(dim|fct)_[a-z0-9_]+$",
    "kpi": r"^kpi_[a-z0-9_]+$",
}
KPI_META_KEYS = {"owner", "definition", "grain", "formula", "scope"}
# Bare SQL keywords are not used as column names (docs/standards/naming.md).
KEYWORD_COLUMN_NAMES = {
    "comment",
    "current_date",
    "date",
    "group",
    "name",
    "order",
    "role",
    "table",
    "timestamp",
    "type",
    "user",
    "value",
}


@pytest.fixture(scope="module")
def manifest(tmp_path_factory: pytest.TempPathFactory) -> dict:
    if not (PROJECT_DIR / "dbt_packages").is_dir():
        pytest.skip("dbt packages missing; run `uv run python transform/run_dbt.py deps`")
    target = tmp_path_factory.mktemp("dbt_target")
    environment = {
        **os.environ,
        "DBT_PROFILES_DIR": str(PROJECT_DIR),
        "SNOWFLAKE_ACCOUNT": "offline",
        "SNOWFLAKE_USER": "offline",
        "SNOWFLAKE_PRIVATE_KEY_PATH": "offline",
    }
    subprocess.run(
        ["dbt", "parse", "--target-path", str(target), "--quiet"],
        cwd=PROJECT_DIR,
        env=environment,
        check=True,
    )
    return json.loads((target / "manifest.json").read_text(encoding="utf-8"))


def _models(manifest: dict) -> list[dict]:
    return [
        node
        for node in manifest["nodes"].values()
        if node["resource_type"] == "model" and node["package_name"] == "streampulse"
    ]


def _layer(model: dict) -> str:
    return Path(model["original_file_path"]).parts[1]


def _tests_by_model(manifest: dict) -> dict[str, list[dict]]:
    tests: dict[str, list[dict]] = {}
    for node in manifest["nodes"].values():
        if node["resource_type"] == "test" and node.get("attached_node"):
            tests.setdefault(node["attached_node"], []).append(node)
    return tests


def test_every_model_is_documented(manifest):
    missing = [m["name"] for m in _models(manifest) if not m["description"].strip()]
    assert missing == []


def test_model_names_follow_layer_prefixes(manifest):
    wrong = [
        m["name"] for m in _models(manifest) if not re.match(LAYER_PREFIXES[_layer(m)], m["name"])
    ]
    assert wrong == []


def test_marts_enforce_contracts(manifest):
    marts = [m for m in _models(manifest) if _layer(m) == "marts"]
    assert marts
    assert [m["name"] for m in marts if not m["config"]["contract"]["enforced"]] == []


def test_kpi_models_carry_their_definition(manifest):
    kpis = [m for m in _models(manifest) if _layer(m) == "kpi"]
    assert kpis
    for model in kpis:
        meta = model["config"]["meta"]
        assert meta.keys() >= KPI_META_KEYS, model["name"]
        assert meta["scope"] in {"global", "local"}, model["name"]


def test_marts_and_kpis_test_their_grain(manifest):
    tests = _tests_by_model(manifest)
    grain_tests = {"unique", "unique_combination_of_columns"}
    untested = [
        m["name"]
        for m in _models(manifest)
        if _layer(m) in {"marts", "kpi"}
        and not any(
            t.get("test_metadata", {}).get("name") in grain_tests
            for t in tests.get(m["unique_id"], [])
        )
    ]
    assert untested == []


def test_columns_avoid_sql_keyword_names(manifest):
    offending = [
        f"{m['name']}.{column}"
        for m in _models(manifest)
        for column in m["columns"]
        if column.lower() in KEYWORD_COLUMN_NAMES
    ]
    assert offending == []


def test_sources_check_freshness(manifest):
    sources = [s for s in manifest["sources"].values() if s["package_name"] == "streampulse"]
    assert sources
    assert [s["name"] for s in sources if not s.get("freshness", {}).get("error_after")] == []
