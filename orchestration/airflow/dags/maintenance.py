"""Weekly maintenance: table statistics and cleanup of old CI schemas (ADR-010).

CI schemas are only listed unless the run is triggered with execute=true, because dropping
objects needs an explicit decision (CLAUDE.md).
"""

from __future__ import annotations

from datetime import UTC, datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG, Param
from common.settings import BIN, DEFAULT_ARGS, ENVIRONMENT

with DAG(
    dag_id="maintenance",
    description="Table statistics and cleanup of old CI schemas",
    schedule="0 6 * * 1",
    start_date=datetime(2026, 11, 16, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    params={
        "older_than_days": Param(7, type="integer", minimum=1),
        "execute": Param(False, type="boolean", description="drop the schemas instead of listing"),
    },
    tags=["streampulse", "maintenance"],
):
    table_stats = BashOperator(
        task_id="table_stats", bash_command=f"{BIN}/maintain --env {ENVIRONMENT} stats"
    )
    clean_ci_schemas = BashOperator(
        task_id="clean_ci_schemas",
        bash_command=(
            f"{BIN}/maintain --env {ENVIRONMENT} ci-schemas "
            "--older-than-days {{ params.older_than_days }} "
            "{{ '--execute' if params.execute else '' }}"
        ),
    )

    table_stats >> clean_ci_schemas
