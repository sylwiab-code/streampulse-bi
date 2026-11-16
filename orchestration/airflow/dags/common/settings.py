"""Paths, assets, and default arguments shared by the StreamPulse DAGs (ADR-010).

Paths default to the Astro container layout and can be overridden through environment
variables, for example by the DAG tests.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from airflow.sdk import Asset

from common.alerts import notify_failure

AIRFLOW_HOME = Path(os.environ.get("AIRFLOW_HOME", "/usr/local/airflow"))
ENVIRONMENT = os.environ.get("STREAMPULSE_ENV", "dev")
BIN = Path(os.environ.get("STREAMPULSE_BIN_DIR", AIRFLOW_HOME / "streampulse_venv" / "bin"))
DATA_DIR = Path(os.environ.get("STREAMPULSE_DATA_DIR", AIRFLOW_HOME / "data"))
RAW_DIR = DATA_DIR / "raw"
DBT_PROJECT_DIR = Path(
    os.environ.get("STREAMPULSE_DBT_PROJECT_DIR", AIRFLOW_HOME / "dbt" / "streampulse")
)
DBT_EXECUTABLE = Path(
    os.environ.get("STREAMPULSE_DBT_EXECUTABLE", AIRFLOW_HOME / "dbt_venv" / "bin" / "dbt")
)

# Updated by every successful load into RAW; transform_pipeline runs when it changes.
RAW_ASSET = Asset(name=f"streampulse_raw_{ENVIRONMENT}", uri=f"streampulse://{ENVIRONMENT}/raw")

DEFAULT_ARGS = {
    "owner": "streampulse",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "on_failure_callback": notify_failure,
}
