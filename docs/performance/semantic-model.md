# Semantic Model Optimization (Phase 5)

The first complete version of the StreamPulse semantic model ([ADR-011](../adr/011-power-bi-semantic-model.md)) was measured, optimized, and measured again on 2026-11-19. Memory dropped from **396.5 MB to 46.8 MB (-88%)**; query times did not change, because they were already short.

## Setup

- Power BI Desktop with the PBIP open, Import mode, DEV data: 5.2 million viewing sessions, 293,000 payment attempts, 254,000 MRR movement rows, and 50,000 customers (two years from November 2024).
- **Memory:** VertiPaq Analyzer export from DAX Studio's command line (`dscmd vpax`), summarized with [`semantic/powerbi/vpax_summary.py`](../../semantic/powerbi/vpax_summary.py).
- **Queries:** `dscmd benchmark` with 5 cold-cache and 5 warm-cache runs per query. The four queries in [`queries/`](queries/) stand for typical report visuals. The tables show the median total duration; DAX Studio did not capture server timings for some runs, so their averages are not used.

How to repeat the measurement: [semantic/powerbi/README.md](../../semantic/powerbi/README.md#measure-performance).

## Changes

| Change | Why |
|---|---|
| Auto date/time off; its 10 hidden date tables removed | The model has its own Date table; the hidden tables cost memory and add relationships |
| `Viewing Sessions`: `started_at`, `session_id`, `watch_hours`, `loaded_at` removed | `started_at` (a unique timestamp per row) took 232 MB alone. It still filters the incremental-refresh range in the source query, before the columns are selected; `started_date` is enough for the model |
| `Payments`: ids, `attempted_at`, `billing_period_start`, `market_code`, `currency_code` removed | No measure or relationship uses them; the market comes through Customer |
| `completion_rate` stored as a fixed decimal | Fewer distinct values than a double |
| `IsAvailableInMdx = false` on 59 hidden non-attribute columns | No attribute hierarchy is built for keys and measure inputs; this removed about 1 MB from each small table |

## Memory

| Measure | Before | After | Change |
|---|---|---|---|
| Model size (MB) | 396.53 | 46.84 | -88% |
| Columns | 118 | 108 | - |

| Table | Rows | Before (MB) | After (MB) | Change |
|---|---|---|---|---|
| Viewing Sessions | 5,245,683 | 320.46 | 35.46 | -89% |
| Payments | 293,348 | 37.70 | 4.47 | -88% |
| Market | 4 | 4.26 | 0.07 | -98% |
| Customer | 50,168 | 4.09 | 1.59 | -61% |
| Content | 2,000 | 3.33 | 0.19 | -94% |
| Subscribers Daily | 17,895 | 3.32 | 0.97 | -71% |
| Plan | 6 | 3.22 | 0.07 | -98% |
| MRR Movements | 253,762 | 1.68 | 1.38 | -18% |
| Date | 1,461 | 1.18 | 0.13 | -89% |
| Auto date/time tables | - | 1.12 | - | - |
| KPI Selector, Dimension Selector | 6, 5 | 2.16 | 2.16 | 0% |
| Nine other tables | 4-4,476 | 14.01 | 0.34 | -98% |

Largest columns before the pass:

| Column | Before (MB) | After (MB) |
|---|---|---|
| `'Viewing Sessions'[started_at]` | 232.49 | removed |
| `'Viewing Sessions'[session_id]` | 41.97 | removed |
| `'Payments'[attempted_at]` | 14.03 | removed |
| `'Payments'[payment_id]` | 13.95 | removed |
| `'Viewing Sessions'[customer_id]` | 12.14 | 11.74 |
| `'Viewing Sessions'[completion_rate]` | 8.67 | 8.55 |
| `'Viewing Sessions'[started_date]` | 6.99 | 6.99 |

The two field parameter tables stay at about 1 MB each: calculated tables keep their attribute hierarchies, and BPA's rules for them have documented exceptions. The after export was taken before the Campaign RLS fix, which removed one more 180-row column (about 0.02 MB).

## Queries

| Query | Rows | Cold before | Cold after | Warm before | Warm after |
|---|---|---|---|---|---|
| [01 Executive monthly](queries/01-executive-monthly.dax): subscribers, MRR, ARPU per month and market | 100 | 13 ms | 14 ms | 11 ms | 12 ms |
| [02 Time intelligence](queries/02-time-intelligence.dax): MRR and viewers, current, PY, YoY % per month | 63 | 857 ms | 817 ms | 53 ms | 50 ms |
| [03 Top titles](queries/03-top-titles.dax): top 20 titles of 2026 by watch hours | 20 | 357 ms | 340 ms | 8 ms | 8 ms |
| [04 Engagement by genre](queries/04-engagement-by-genre.dax): viewers and watch hours per subscriber by quarter, genre, device | 360 | 504 ms | 505 ms | 23 ms | 13 ms |

The pass did not change query times beyond the noise, which was expected: the columns it removed were not read by these queries. All warm-cache results are below 55 ms.

**Query 02 cold.** About 800 ms with a cold cache, with 93-96 storage engine queries. Almost all of the time goes to `[Viewers]`, a distinct count of customers over 5.2 million sessions, evaluated per month for the current and the previous year. The same query with MRR only takes 27 ms. This is the normal cost of a distinct count at session grain.

## Refresh in the Service

| Refresh | Trigger | Duration |
|---|---|---|
| First refresh after publishing (creates the incremental-refresh partitions) | Service, on demand | 68 s |
| Next refresh (last 7 days of viewing sessions, all other tables) | Service principal, REST API (`powerbi refresh`) | 18 s |

## Follow-ups

- If report pages with viewers over time become slow, add a monthly viewers table to dbt (distinct viewers per month, market, and genre) and use it for those visuals. Not needed at the current volume.
- Measure again with the Phase 6 reports, using Performance Analyzer in Desktop.
