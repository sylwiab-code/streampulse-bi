"""Daily ingestion: generate yesterday's batch and load it into RAW (ADR-010).

A successful load updates the RAW asset, which starts transform_pipeline (data-aware
scheduling). The DAG only orchestrates the generator and loader command-line tools.
"""

from __future__ import annotations

from datetime import UTC, datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG
from common.settings import BIN, DEFAULT_ARGS, ENVIRONMENT, RAW_ASSET, RAW_DIR

with DAG(
    dag_id="daily_pipeline",
    description="Generate the previous day's batch and load it into Snowflake RAW",
    schedule="0 5 * * *",
    start_date=datetime(2026, 11, 16, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["streampulse", "ingest"],
):
    generate_batch = BashOperator(
        task_id="generate_batch",
        bash_command=(
            f"{BIN}/generate daily --days 1 --end-date {{{{ macros.ds_add(ds, -1) }}}} "
            f"--output {RAW_DIR}"
        ),
    )
    load_raw = BashOperator(
        task_id="load_raw",
        bash_command=f"{BIN}/load --env {ENVIRONMENT} --path {RAW_DIR}",
        outlets=[RAW_ASSET],
    )

    generate_batch >> load_raw
