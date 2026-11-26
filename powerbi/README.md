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
- `validate` runs the checks in [`checks.json`](src/streampulse_powerbi/checks.json): each compares one number from Snowflake (as `REPORTER`) with one DAX result, within a relative tolerance. The list stays empty until Phase 7: the Execute Queries API does not accept a service principal on a model with RLS ([ADR-011](../docs/adr/011-power-bi-semantic-model.md)). The comparison queries are kept in [`semantic/powerbi/reconciliation.json`](../semantic/powerbi/reconciliation.json), in the same format.

Authentication uses a service principal (client credentials). Settings come from environment variables: `POWERBI_TENANT_ID`, `POWERBI_CLIENT_ID`, `POWERBI_CLIENT_SECRET`, `POWERBI_WORKSPACE_ID`, `POWERBI_DATASET_ID`. The workspace is `StreamPulse DEV` ([ADR-008](../docs/adr/008-power-bi-and-fabric-licensing.md)); the semantic model's id comes from its first publish ([semantic/powerbi/README.md](../semantic/powerbi/README.md#publish)). The Airflow tasks run only when `POWERBI_ENABLED=true`. The client is tested against a simulated API. Outside Airflow, pass the settings with `uv run --env-file .env powerbi ...`.
