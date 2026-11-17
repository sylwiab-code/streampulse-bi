"""Transformation and reporting refresh, started whenever RAW changes (ADR-010).

dbt build runs through Cosmos with one task per model (run, then its tests). The Power BI
refresh, status polling, and validation follow; they are switched off until the workspace
exists (POWERBI_ENABLED, ADR-008). A Slack message reports the outcome.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.python import PythonOperator, ShortCircuitOperator
from airflow.sdk import DAG
from common.alerts import notify_success
from common.settings import BIN, DBT_EXECUTABLE, DBT_PROJECT_DIR, DEFAULT_ARGS, RAW_ASSET
from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import LoadMode


def power_bi_enabled() -> bool:
    return os.environ.get("POWERBI_ENABLED", "false").lower() == "true"


with DAG(
    dag_id="transform_pipeline",
    description="dbt build, Power BI refresh and validation after each RAW load",
    schedule=[RAW_ASSET],
    start_date=datetime(2026, 11, 16, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["streampulse", "transform"],
):
    dbt_build = DbtTaskGroup(
        group_id="dbt_build",
        project_config=ProjectConfig(
            dbt_project_path=DBT_PROJECT_DIR,
            manifest_path=DBT_PROJECT_DIR / "target" / "manifest.json",
            install_dbt_deps=False,
        ),
        profile_config=ProfileConfig(
            profile_name="streampulse",
            target_name="dev",
            profiles_yml_filepath=DBT_PROJECT_DIR / "profiles.yml",
        ),
        execution_config=ExecutionConfig(dbt_executable_path=DBT_EXECUTABLE),
        # Tests that read several models (relationships, the MRR bridge) get their own task
        # after all of those models, as in `dbt build`; otherwise they run against stale data.
        render_config=RenderConfig(
            load_method=LoadMode.DBT_MANIFEST, should_detach_multiple_parents_tests=True
        ),
        default_args=DEFAULT_ARGS,
    )
    check_power_bi = ShortCircuitOperator(
        task_id="power_bi_enabled",
        python_callable=power_bi_enabled,
        ignore_downstream_trigger_rules=False,
    )
    refresh_power_bi = BashOperator(
        task_id="refresh_power_bi", bash_command=f"{BIN}/powerbi refresh"
    )
    wait_for_refresh = BashOperator(
        task_id="wait_for_power_bi_refresh", bash_command=f"{BIN}/powerbi wait --timeout 3600"
    )
    validate_power_bi = BashOperator(
        task_id="validate_power_bi", bash_command=f"{BIN}/powerbi validate"
    )
    notify = PythonOperator(
        task_id="notify_success",
        python_callable=notify_success,
        op_kwargs={"dag_id": "{{ dag.dag_id }}", "run_id": "{{ run_id }}"},
        trigger_rule="none_failed",
    )

    dbt_build >> check_power_bi >> refresh_power_bi >> wait_for_refresh >> validate_power_bi
    validate_power_bi >> notify
