"""Manual backfill: generate history (or several daily batches) and load it into RAW (ADR-010).

Parameters: mode "full" writes all history up to end_date as one batch; mode "daily" writes one
batch per day for the last `days` days. The load updates the RAW asset like the daily run.
"""

from __future__ import annotations

from datetime import UTC, datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG, Param
from common.settings import BIN, DEFAULT_ARGS, ENVIRONMENT, RAW_ASSET, RAW_DIR

with DAG(
    dag_id="backfill",
    description="Generate and load history or a range of daily batches",
    schedule=None,
    start_date=datetime(2026, 11, 16, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    params={
        "mode": Param("daily", enum=["daily", "full"], description="daily batches or full history"),
        "days": Param(1, type="integer", minimum=1, description="number of daily batches"),
        "end_date": Param(
            "", type="string", description="last day (YYYY-MM-DD); empty means yesterday"
        ),
    },
    tags=["streampulse", "ingest"],
):
    generate = BashOperator(
        task_id="generate",
        bash_command=(
            f"{BIN}/generate "
            "{{ 'backfill' if params.mode == 'full' else 'daily --days ' ~ params.days }} "
            "--end-date {{ params.end_date or macros.ds_add(ds, -1) }} "
            f"--output {RAW_DIR}"
        ),
    )
    load_raw = BashOperator(
        task_id="load_raw",
        bash_command=f"{BIN}/load --env {ENVIRONMENT} --path {RAW_DIR}",
        outlets=[RAW_ASSET],
    )

    generate >> load_raw
