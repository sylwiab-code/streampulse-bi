#!/usr/bin/env bash
# Container entrypoint (ADR-010): copy the mounted Snowflake key to a file only the astro user
# can read, then start Airflow. Docker Desktop on Windows shows bind-mounted files as writable
# by everyone, and the Snowflake connector refuses private keys with such permissions.
set -euo pipefail
if [[ -f /run/streampulse/snowflake_key.p8 ]]; then
    install -m 600 /run/streampulse/snowflake_key.p8 /usr/local/airflow/secrets/snowflake_key.p8
fi
exec /entrypoint "$@"
