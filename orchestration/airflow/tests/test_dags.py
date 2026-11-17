"""DAG tests (PLAN.md Phase 4): import integrity and structure.

Needs the dbt manifest (`dbt parse`), because Cosmos renders one task per model from it.
"""

from __future__ import annotations

import itertools
import json
import os
from pathlib import Path

import pytest
from airflow.models import DagBag
from common.settings import DBT_PROJECT_DIR

EXPECTED_DAGS = {"daily_pipeline", "backfill", "transform_pipeline", "maintenance"}
DAGS_FOLDER = Path(__file__).resolve().parents[1] / "dags"


@pytest.fixture(scope="module")
def dagbag() -> DagBag:
    manifest = DBT_PROJECT_DIR / "target" / "manifest.json"
    if not manifest.is_file():
        pytest.fail(f"dbt manifest missing at {manifest}; run `dbt parse` first")
    return DagBag(dag_folder=str(DAGS_FOLDER), include_examples=False)


def test_dags_import_without_errors(dagbag):
    assert dagbag.import_errors == {}


def test_expected_dags_exist(dagbag):
    assert set(dagbag.dag_ids) == EXPECTED_DAGS


def test_every_task_retries_and_alerts(dagbag):
    for dag in dagbag.dags.values():
        for task in dag.tasks:
            assert task.retries >= 1, f"{dag.dag_id}.{task.task_id}"
            assert task.on_failure_callback, f"{dag.dag_id}.{task.task_id}"


def test_every_dag_is_tagged_and_runs_one_at_a_time(dagbag):
    for dag in dagbag.dags.values():
        assert "streampulse" in dag.tags
        assert dag.max_active_runs == 1
        assert not dag.catchup


@pytest.mark.parametrize("dag_id", ["daily_pipeline", "backfill"])
def test_ingestion_loads_after_generating_and_updates_the_raw_asset(dagbag, dag_id):
    dag = dagbag.dags[dag_id]
    load_raw = dag.get_task("load_raw")
    assert {t.task_id for t in load_raw.upstream_list} == {
        "generate_batch" if dag_id == "daily_pipeline" else "generate"
    }
    assert [outlet.name for outlet in load_raw.outlets] == ["streampulse_raw_dev"]


def test_daily_pipeline_generates_the_previous_day(dagbag):
    command = dagbag.dags["daily_pipeline"].get_task("generate_batch").bash_command
    assert "macros.ds_add(ds, -1)" in command


def test_transform_runs_when_raw_changes(dagbag):
    dag = dagbag.dags["transform_pipeline"]
    assert "streampulse_raw_dev" in str(dag.timetable.asset_condition)


def test_transform_has_a_run_task_per_dbt_model(dagbag):
    manifest = json.loads((DBT_PROJECT_DIR / "target" / "manifest.json").read_text())
    models = {
        node["name"]
        for node in manifest["nodes"].values()
        if node["resource_type"] == "model" and node["package_name"] == "streampulse"
    }
    task_ids = set(dagbag.dags["transform_pipeline"].task_ids)
    missing = sorted(m for m in models if f"dbt_build.{m}.run" not in task_ids)
    assert missing == []


def test_tests_with_several_parents_run_after_all_of_them(dagbag):
    """The MRR bridge test reads two models; it must wait for both (detached test task)."""
    dag = dagbag.dags["transform_pipeline"]
    bridge = [t for t in dag.task_ids if "assert_mrr_bridge_reconciles" in t]
    assert len(bridge) == 1
    upstream = dag.get_task(bridge[0]).upstream_task_ids
    for model in ("int_customer_months_aggregated", "fct_mrr_movements"):
        assert any(task_id.startswith(f"dbt_build.{model}.") for task_id in upstream), model


def test_power_bi_steps_follow_dbt_and_success_is_reported_when_they_are_skipped(dagbag):
    dag = dagbag.dags["transform_pipeline"]
    chain = ["power_bi_enabled", "refresh_power_bi", "wait_for_power_bi_refresh"]
    chain += ["validate_power_bi", "notify_success"]
    for upstream, downstream in itertools.pairwise(chain):
        assert downstream in dag.get_task(upstream).downstream_task_ids
    assert any(
        t.startswith("dbt_build.") for t in dag.get_task("power_bi_enabled").upstream_task_ids
    )
    assert dag.get_task("notify_success").trigger_rule == "none_failed"


def test_power_bi_is_off_unless_enabled(monkeypatch, dagbag):
    callable_ = dagbag.dags["transform_pipeline"].get_task("power_bi_enabled").python_callable
    monkeypatch.delenv("POWERBI_ENABLED", raising=False)
    assert callable_() is False
    monkeypatch.setenv("POWERBI_ENABLED", "true")
    assert callable_() is True


def test_maintenance_only_lists_ci_schemas_by_default(dagbag):
    dag = dagbag.dags["maintenance"]
    assert dag.params["execute"] is False
    assert "--execute" in dag.get_task("clean_ci_schemas").bash_command  # rendered only if set


def test_alert_message_names_the_task(monkeypatch):
    from common import alerts

    class FakeTaskInstance:
        dag_id, task_id, run_id, try_number = "daily_pipeline", "load_raw", "manual__1", 3

    message = alerts.failure_message({"ti": FakeTaskInstance(), "exception": ValueError("boom")})
    assert "daily_pipeline.load_raw" in message
    assert "boom" in message
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    assert alerts.post("test") is False  # without a webhook the alert is only logged


def test_settings_paths_can_be_overridden():
    assert os.environ.get("STREAMPULSE_DBT_PROJECT_DIR", "/usr/local/airflow") in str(
        DBT_PROJECT_DIR
    )
