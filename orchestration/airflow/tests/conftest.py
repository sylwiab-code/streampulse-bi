"""Point the DAG settings at this repository so the DAGs parse outside the Astro container."""

from __future__ import annotations

import os
import sys
from pathlib import Path

AIRFLOW_PROJECT = Path(__file__).resolve().parents[1]
REPO = AIRFLOW_PROJECT.parents[1]

os.environ.setdefault("AIRFLOW__CORE__LOAD_EXAMPLES", "False")
if not Path("/usr/local/airflow/dbt/streampulse/target/manifest.json").is_file():
    os.environ.setdefault("STREAMPULSE_DBT_PROJECT_DIR", str(REPO / "transform" / "dbt"))
sys.path.insert(0, str(AIRFLOW_PROJECT / "dags"))
