# StreamPulse Airflow image (ADR-010): Astro Runtime 3.3 (Airflow 3.3.2) on Python 3.12.
FROM astrocrpublic.azurecr.io/runtime:3.3-12-python-3.12@sha256:94016df1a2ab893f4590b85ad2fe6ce40352e40eca1da433ea03572cd6bfeae9

# dbt and the StreamPulse command-line tools run in their own virtual environments, so their
# pinned dependencies never clash with Airflow's. build/ is prepared by run_astro.py from the
# repository's uv.lock (hashes) and wheels.
COPY --chown=astro:0 build/ /tmp/streampulse-build/
RUN python -m venv /usr/local/airflow/dbt_venv \
    && /usr/local/airflow/dbt_venv/bin/pip install --no-cache-dir \
        -r /tmp/streampulse-build/requirements-dbt.txt \
    && python -m venv /usr/local/airflow/streampulse_venv \
    && /usr/local/airflow/streampulse_venv/bin/pip install --no-cache-dir \
        -r /tmp/streampulse-build/requirements-streampulse.txt \
    && /usr/local/airflow/streampulse_venv/bin/pip install --no-cache-dir --no-deps \
        /tmp/streampulse-build/wheels/*.whl
