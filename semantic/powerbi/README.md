# StreamPulse Semantic Model

Power BI project (PBIP) with the semantic model in TMDL and the report in PBIR. Import mode on the Snowflake `MARTS` and `KPI` schemas. Design decisions: [ADR-011](../../docs/adr/011-power-bi-semantic-model.md); conventions: [docs/standards/semantic-model.md](../../docs/standards/semantic-model.md).

| Path | Content |
|---|---|
| `StreamPulse.pbip` | Opens the project in Power BI Desktop |
| `StreamPulse.SemanticModel/definition/` | TMDL: tables, relationships, roles, perspectives, cultures, parameters |
| `StreamPulse.Report/` | PBIR report; the "Model check" page until Phase 6 |
| `connection.py` | Sets or resets the Snowflake host parameter |
| `bpa-rules.json`, `run_bpa.py` | Project rules for the Best Practice Analyzer, and the script that runs it |
| `reconciliation.json` | Snowflake-to-model comparison queries (automated in Phase 7) |
| `vpax_summary.py` | Summarizes VertiPaq Analyzer exports for [docs/performance](../../docs/performance/semantic-model.md) |

## Connection

The model connects as the service user `SVC_POWERBI_DEV` (role `REPORTER_DEV`, warehouse `WH_REPORT_DEV`) with a key pair. The private key is `~/.snowflake/keys/svc_powerbi_dev.p8`, outside the repository; the public key is attached to the user in Snowflake.

The repository keeps the host parameter as the placeholder `ACCOUNT.snowflakecomputing.com`. Before opening the model, write the real host from `SNOWFLAKE_ACCOUNT` in `.env`:

```bash
uv run python semantic/powerbi/connection.py set
```

The pre-commit hook restores the placeholder when `expressions.tmdl` is committed, and the commit stops so that you can stage the file again. To restore it yourself:

```bash
uv run python semantic/powerbi/connection.py reset
```

## Open and Edit

1. Open `StreamPulse.pbip` in Power BI Desktop and select **Refresh**.
2. The first time, Desktop asks for Snowflake credentials: **Key pair**, user `SVC_POWERBI_DEV`, the private key file's content, no passphrase.

Changes can be made in Desktop or in the TMDL files. After editing TMDL as text, open the project in Desktop and save it once: Desktop's format is the canonical one. If you change files while Desktop has the project open, close Desktop **without saving**, or it overwrites your changes. Git stores the files with LF line endings (`.gitattributes`); Desktop writes CRLF, which Git converts.

## Publish

1. In Desktop: **Home** > **Publish** > `StreamPulse DEV`.
2. In the service, open the semantic model's **Settings** > **Data source credentials** > **Edit credentials**: **Key pair**, user `SVC_POWERBI_DEV`, the private key, no passphrase, privacy level **Organizational**.
3. Leave scheduled refresh off: Airflow starts the refresh ([ADR-010](../../docs/adr/010-orchestration-with-airflow.md)).
4. Put the semantic model's id into `POWERBI_DATASET_ID` in `.env`.

The first refresh in the service creates the incremental-refresh partitions of `Viewing Sessions`. Publishing again from Desktop replaces them, so the next refresh loads all history again.

To refresh as the service principal ([powerbi/README.md](../../powerbi/README.md)):

```bash
uv run --env-file .env powerbi refresh
```

```bash
uv run --env-file .env powerbi wait
```

## Test Row-Level and Object-Level Security

Roles: `Market` (markets mapped to the user in the dbt seed `security_market_access`), `Global` (all markets), and `Content Analyst` (no financial columns). The seed uses fictional users, for example `de.analyst@streampulse.example` (DE) and `nordics.manager@streampulse.example` (SE and NO).

In Desktop: **Modeling** > **View as** > **Other user** with the user's address, plus the role `Market`. Compare a table of Market Code, Active Subscribers, and Sessions with Snowflake:

```sql
select c.market_code, count(*) as sessions
from marts.fct_viewing_sessions as s
inner join marts.dim_customer as c on s.customer_id = c.customer_id
group by c.market_code
order by c.market_code;
```

Also check a user without a mapping (no data) and the role `Content Analyst` alone (MRR and payment amount measures are unavailable; subscriber, churn, and engagement measures work). DAX Studio's `EffectiveUserName` does not work against Desktop's local engine, so per-user tests use "View as".

## Run the Best Practice Analyzer

```bash
uv run python semantic/powerbi/run_bpa.py
```

The script downloads Tabular Editor 2 and Microsoft's BPA rules into `%LOCALAPPDATA%\streampulse\tools` (versions pinned and checked by SHA-256), adds the rules in `bpa-rules.json`, and fails on any violation. An accepted exception is a `BestPracticeAnalyzer_IgnoreRules` annotation on the object, with the reason in the standard. Windows only.

The offline convention tests run in CI:

```bash
uv run pytest tests/powerbi
```

`test_snowflake_host_is_a_placeholder` fails while the real host is set locally; that is expected.

## Measure Performance

Use DAX Studio (or its command line, `dscmd`) against the model open in Desktop. Desktop's local port is in `%LOCALAPPDATA%\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces\<workspace>\Data\msmdsrv.port.txt`; DAX Studio shows the database id when it connects.

```bash
dscmd vpax before.vpax -s localhost:<port> -d <database>
```

```bash
dscmd benchmark 01.csv -s localhost:<port> -d <database> -f docs/performance/queries/01-executive-monthly.dax --cold 5 --warm 5
```

```bash
uv run python semantic/powerbi/vpax_summary.py before.vpax after.vpax --top 25
```

`dscmd` writes CSV files in the machine's locale (for example semicolons and decimal commas).

## DAX Notes

- `Content` is a reserved word: write `'Content'[Title]`, not `Content[Title]`.
- Measures that read secured columns are unavailable to `Content Analyst`; do not combine that role with `Market` for one user, because RLS and OLS from different roles raise an error.
