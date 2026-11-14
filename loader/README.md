# StreamPulse loader

Loads the generator's Parquet batches (`data/raw/<table>/load_date=YYYY-MM-DD/`) into the Snowflake raw layer of one environment ([ADR-003](../docs/adr/003-snowflake-environments-and-liquibase-boundary.md)).

```bash
uv run load --env dev
```

1. **PUT** each batch folder to `@RAW.LANDING/<table>/load_date=YYYY-MM-DD/` (existing files are skipped).
2. **COPY INTO** each `RAW.<table>` with `MATCH_BY_COLUMN_NAME`, recording `_file_name`, `_file_row_number`, and `_loaded_at`. Files that were already loaded are skipped, so reruns are safe.

The loader connects with the `LOADER_<ENV>` role and the `WH_LOAD_<ENV>` warehouse, using key-pair authentication from `.env` (see [the setup guide](../docs/guides/snowflake-setup.md)). Options: `--path` (default `data/raw`) and `--table NAME` (repeatable). Locally only `--env dev` is allowed.

## Tests

```bash
uv run pytest loader/tests
```

Unit tests use a fake connection. The DEV integration tests (masking per role, access per role, every local file loaded) run only with `STREAMPULSE_SNOWFLAKE_TESTS=1`.
