# StreamPulse Power BI client

Standard-library client for the Power BI REST API, used by the Airflow `transform_pipeline` DAG ([ADR-010](../docs/adr/010-orchestration-with-airflow.md)):

```bash
uv run powerbi refresh
```

```bash
uv run powerbi wait --timeout 3600
```

```bash
uv run powerbi validate
```

- `refresh` starts a refresh of the semantic model; `wait` polls the latest refresh until it finishes and fails unless it completed.
- `validate` runs the checks in [`checks.json`](src/streampulse_powerbi/checks.json): each compares one number from Snowflake (as `REPORTER`) with one DAX result, within a relative tolerance. The list is empty until the semantic model exists (Phase 5).

Authentication uses a service principal (client credentials). Settings come from environment variables: `POWERBI_TENANT_ID`, `POWERBI_CLIENT_ID`, `POWERBI_CLIENT_SECRET`, `POWERBI_WORKSPACE_ID`, `POWERBI_DATASET_ID`. The workspace and service principal arrive with Phase 5 ([ADR-008](../docs/adr/008-power-bi-and-fabric-licensing.md)); until then the Airflow tasks are switched off (`POWERBI_ENABLED`), and the client is tested against a simulated API.
