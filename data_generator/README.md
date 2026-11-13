# StreamPulse data generator

Generates synthetic data for StreamPulse, a fictional streaming service in Germany, Poland, Sweden, and Norway, as Parquet batches for the Snowflake raw layer. Design decisions are in [ADR-009](../docs/adr/009-synthetic-data-generator-design.md).

## Usage

From the repository root:

```bash
uv run generate backfill
```

```bash
uv run generate daily --days 1
```

- `backfill` writes all history up to the end date as one batch.
- `daily --days N` writes one batch for each of the last N days, containing the rows that arrived that day.
- Options for both: `--end-date YYYY-MM-DD` (default: yesterday), `--seed` (default 42), `--scale` (multiplies the sign-up volume), `--output` (default `data/raw`, gitignored).

The output depends only on the seed, the settings, and the end date. Rerunning a batch replaces it with identical rows, and a backfill followed by daily batches holds the same rows as a later backfill. A full backfill (about 50,000 customers and 5 million viewing sessions since 2024-11-01) takes about half a minute.

## Output

`data/raw/<table>/load_date=YYYY-MM-DD/data.parquet`

| Table | Grain | Notes |
|---|---|---|
| `markets` | market | Snapshot in every batch |
| `currencies` | currency | Snapshot |
| `plans` | plan (tier and billing period) | Snapshot |
| `plan_prices` | market, plan, validity period | Snapshot; price increase on 2025-09-01 |
| `content_catalog` | title | Snapshot of titles added by the load date |
| `campaigns` | quarterly campaign per market and paid channel | Snapshot |
| `fx_rates` | currency and day | Units of currency per EUR |
| `campaign_spend` | campaign and day | Local currency |
| `customers` | customer | **PII:** `first_name`, `last_name`, `email` |
| `acquisition_attribution` | customer | Channel; campaign for paid channels |
| `subscriptions` | subscription | A reactivation starts a new subscription |
| `subscription_events` | event | `trial_started`, `trial_converted`, `trial_expired`, `subscription_started`, `plan_upgraded`, `plan_downgraded`, `price_increased`, `cancelled` (voluntary or involuntary, with `effective_date`), `reactivated` |
| `payments` | payment attempt | Up to three attempts per billing period |
| `viewing_sessions` | session | Two schema versions, see below |

## Patterns and defects

All assumptions are in [`config.py`](src/streampulse_generator/config.py). They are invented but plausible:

- **Sign-ups:** seasonal, with a holiday peak.
- **Markets:** 40% DE, 30% PL, 15% SE, 15% NO, each with its own prices, churn, and payment failure.
- **Trials:** 60% of sign-ups take a 7-day trial; 55% of trials convert, depending on the channel.
- **Voluntary churn:** about 4% per month, higher in the first three months and doubled in the month after the price increase.
- **Payments:** 5% of first attempts fail; retries happen after 3 and 7 days, and about half of failed payments recover. Payments that never succeed cancel the subscription (involuntary churn).
- **Plan changes and reactivation:** 2% of subscribers upgrade and 1% downgrade per month; 15% of churned customers come back within six months.
- **Trial abuse:** 2% of sign-ups reuse the name and email (with a `+N` suffix) of a customer whose trial expired.

Deliberate defects for the dbt layer to handle:

| Defect | Tables | Rate |
|---|---|---|
| Exact duplicate rows | `customers`, `subscription_events`, `payments`, `viewing_sessions` | 0.5% |
| Late arrival (1–5 days after the event) | `subscription_events`, `payments`, `viewing_sessions` | 1% |
| Missing `customer_id` | `payments`, `viewing_sessions` | 0.1% |
| Schema change | `viewing_sessions` from 2026-01-01: `device` becomes `device_type`, and `app_version` is added (`data_schema_v1.parquet` / `data_schema_v2.parquet`) | |

## Tests

```bash
uv run pytest data_generator/tests
```
