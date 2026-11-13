"""Run the full simulation up to an end date and return clean tables (before defects)."""

from __future__ import annotations

from datetime import date, datetime, time

import polars as pl

from .config import GeneratorConfig
from .customers import simulate_signups
from .reference import (
    build_catalog,
    campaign_spend_frame,
    campaigns_frame,
    currencies_frame,
    fx_rates,
    fx_rates_frame,
    markets_frame,
    plan_prices_frame,
    plans_frame,
)
from .viewing import generate_sessions

_SCHEMAS: dict[str, dict[str, pl.DataType]] = {
    "customers": {
        "customer_id": pl.Int64,
        "first_name": pl.String,
        "last_name": pl.String,
        "email": pl.String,
        "market_code": pl.String,
        "created_at": pl.Datetime("us"),
    },
    "acquisition_attribution": {
        "customer_id": pl.Int64,
        "channel": pl.String,
        "campaign_id": pl.Int32,
        "attributed_at": pl.Datetime("us"),
    },
    "subscriptions": {
        "subscription_id": pl.Int64,
        "customer_id": pl.Int64,
        "market_code": pl.String,
        "plan_id": pl.String,
        "created_at": pl.Datetime("us"),
        "is_trial": pl.Boolean,
        "is_reactivation": pl.Boolean,
    },
    "subscription_events": {
        "event_id": pl.Int64,
        "subscription_id": pl.Int64,
        "customer_id": pl.Int64,
        "event_type": pl.String,
        "event_at": pl.Datetime("us"),
        "plan_id": pl.String,
        "previous_plan_id": pl.String,
        "cancellation_type": pl.String,
        "effective_date": pl.Date,
    },
    "payments": {
        "payment_id": pl.Int64,
        "subscription_id": pl.Int64,
        "customer_id": pl.Int64,
        "plan_id": pl.String,
        "billing_period_start": pl.Date,
        "attempt_number": pl.Int8,
        "attempted_at": pl.Datetime("us"),
        "amount": pl.Float64,
        "currency_code": pl.String,
        "status": pl.String,
        "failure_reason": pl.String,
    },
}

# Timestamp column that decides whether a row exists by the end date.
_EVENT_TIME = {
    "customers": "created_at",
    "acquisition_attribution": "attributed_at",
    "subscriptions": "created_at",
    "subscription_events": "event_at",
    "payments": "attempted_at",
}


def simulate(cfg: GeneratorConfig, end_date: date) -> dict[str, pl.DataFrame]:
    if end_date < cfg.start_date:
        raise ValueError(f"end date {end_date} is before the start date {cfg.start_date}")
    rates = fx_rates(cfg, end_date)
    catalog = build_catalog(cfg)
    campaigns = campaigns_frame(cfg, end_date)
    rows = simulate_signups(cfg, end_date)

    collected = {
        "customers": rows.customers,
        "acquisition_attribution": rows.attribution,
        "subscriptions": rows.subscriptions,
        "subscription_events": rows.events,
        "payments": rows.payments,
    }
    end = datetime.combine(end_date, time.max)
    tables = {
        "markets": markets_frame(cfg),
        "currencies": currencies_frame(cfg),
        "plans": plans_frame(),
        "plan_prices": plan_prices_frame(cfg),
        "fx_rates": fx_rates_frame(cfg, rates, end_date),
        "content_catalog": catalog.frame,
        "campaigns": campaigns,
        "campaign_spend": campaign_spend_frame(cfg, campaigns, rates, end_date),
    }
    for name, data in collected.items():
        frame = pl.DataFrame(data, schema=_SCHEMAS[name], orient="row")
        tables[name] = frame.filter(pl.col(_EVENT_TIME[name]) <= end)
    tables["viewing_sessions"] = generate_sessions(cfg, rows.access, catalog, end_date)
    return tables
