"""Tests for the clean simulation: determinism, referential integrity, and business patterns."""

from __future__ import annotations

import dataclasses
from datetime import date, datetime, time

import polars as pl
import pytest
from polars.testing import assert_frame_equal
from streampulse_generator.config import GeneratorConfig
from streampulse_generator.simulation import simulate

EVENT_TIME = {
    "fx_rates": "rate_date",
    "campaign_spend": "spend_date",
    "customers": "created_at",
    "acquisition_attribution": "attributed_at",
    "subscriptions": "created_at",
    "subscription_events": "event_at",
    "payments": "attempted_at",
    "viewing_sessions": "started_at",
}


def _until(frame: pl.DataFrame, column: str, day: date) -> pl.DataFrame:
    limit = datetime.combine(day, time.max) if frame[column].dtype == pl.Datetime else day
    return frame.filter(pl.col(column) <= limit).sort(frame.columns)


# Determinism


def test_same_seed_gives_identical_tables(cfg, end_date, tables):
    again = simulate(cfg, end_date)
    for name, frame in tables.items():
        assert_frame_equal(frame, again[name], check_row_order=True)


def test_other_seed_gives_other_data(cfg, end_date, tables):
    other = simulate(dataclasses.replace(cfg, seed=cfg.seed + 1), end_date)
    assert not other["customers"].equals(tables["customers"])


def test_later_end_date_only_appends(cfg, tables):
    """Rows up to an earlier end date never change, so daily batches match the backfill."""
    earlier_end = date(2025, 9, 15)
    earlier = simulate(cfg, earlier_end)
    for name, column in EVENT_TIME.items():
        assert_frame_equal(
            _until(earlier[name], column, earlier_end), _until(tables[name], column, earlier_end)
        )


# Referential integrity


def _missing(child: pl.DataFrame, column: str, parent: pl.DataFrame, key: str) -> int:
    values = child[column].drop_nulls().unique()
    return values.filter(~values.is_in(parent[key].implode())).len()


@pytest.mark.parametrize(
    ("child", "column", "parent", "key"),
    [
        ("customers", "market_code", "markets", "market_code"),
        ("markets", "currency_code", "currencies", "currency_code"),
        ("fx_rates", "currency_code", "currencies", "currency_code"),
        ("plan_prices", "plan_id", "plans", "plan_id"),
        ("acquisition_attribution", "customer_id", "customers", "customer_id"),
        ("acquisition_attribution", "campaign_id", "campaigns", "campaign_id"),
        ("campaign_spend", "campaign_id", "campaigns", "campaign_id"),
        ("subscriptions", "customer_id", "customers", "customer_id"),
        ("subscriptions", "plan_id", "plans", "plan_id"),
        ("subscription_events", "subscription_id", "subscriptions", "subscription_id"),
        ("subscription_events", "plan_id", "plans", "plan_id"),
        ("payments", "subscription_id", "subscriptions", "subscription_id"),
        ("viewing_sessions", "customer_id", "customers", "customer_id"),
        ("viewing_sessions", "title_id", "content_catalog", "title_id"),
    ],
)
def test_foreign_keys_exist(tables, child, column, parent, key):
    assert _missing(tables[child], column, tables[parent], key) == 0


@pytest.mark.parametrize(
    ("table", "key"),
    [
        ("customers", "customer_id"),
        ("subscriptions", "subscription_id"),
        ("subscription_events", "event_id"),
        ("payments", "payment_id"),
        ("viewing_sessions", "session_id"),
        ("content_catalog", "title_id"),
        ("campaigns", "campaign_id"),
    ],
)
def test_primary_keys_are_unique(tables, table, key):
    assert tables[table][key].is_duplicated().sum() == 0
    assert tables[table][key].null_count() == 0


# Business patterns (tolerances are several standard errors wide)


def test_market_shares(cfg, tables):
    shares = tables["customers"]["market_code"].value_counts(normalize=True)
    actual = dict(zip(shares["market_code"], shares["proportion"], strict=True))
    for market in cfg.markets:
        assert actual[market.code] == pytest.approx(market.signup_share, abs=0.03)


def test_trial_share_and_conversion(cfg, tables):
    first = tables["subscriptions"].filter(~pl.col("is_reactivation"))
    assert first["is_trial"].mean() == pytest.approx(cfg.trial_share, abs=0.03)
    events = tables["subscription_events"]["event_type"]
    converted, expired = (events == "trial_converted").sum(), (events == "trial_expired").sum()
    assert converted / (converted + expired) == pytest.approx(cfg.trial_conversion, abs=0.04)


def test_churn_and_payment_failure_rates(tables):
    first_attempts = tables["payments"].filter(pl.col("attempt_number") == 1)
    assert (first_attempts["status"] == "failed").mean() == pytest.approx(0.05, abs=0.015)
    cancels = tables["subscription_events"].filter(pl.col("event_type") == "cancelled")
    voluntary = (cancels["cancellation_type"] == "voluntary").sum() / first_attempts.height
    involuntary = (cancels["cancellation_type"] == "involuntary").sum() / first_attempts.height
    assert 0.025 < voluntary < 0.06
    assert 0.012 < involuntary < 0.035


def test_price_increase_raises_churn(cfg, tables):
    cancels = tables["subscription_events"].filter(
        pl.col("event_type") == "cancelled", pl.col("cancellation_type") == "voluntary"
    )
    by_month = cancels.group_by(pl.col("event_at").dt.month().alias("month")).len()
    counts = dict(by_month.iter_rows())
    assert counts[9] > 1.3 * counts[8]


def test_payment_amounts_follow_the_price_history(tables):
    prices = tables["plan_prices"]
    payments = tables["payments"].join(
        tables["subscriptions"].select("subscription_id", "market_code"), on="subscription_id"
    )
    matched = payments.join(prices, on=["market_code", "plan_id"]).filter(
        pl.col("billing_period_start") >= pl.col("valid_from"),
        pl.col("valid_to").is_null() | (pl.col("billing_period_start") <= pl.col("valid_to")),
    )
    assert matched.height == payments.height
    assert (matched["amount"] == matched["price"]).all()
    assert (matched["currency_code"] == matched["currency_code_right"]).all()


def test_failed_payments_are_retried_then_churned(cfg, tables):
    attempts = (
        tables["payments"]
        .group_by("subscription_id", "billing_period_start")
        .agg(
            pl.col("attempt_number").max().alias("attempts"),
            (pl.col("status") == "succeeded").sum().alias("successes"),
        )
    )
    assert attempts["successes"].max() == 1
    assert attempts["attempts"].max() == 1 + len(cfg.payment_retry_days)
    exhausted = attempts.filter(pl.col("successes") == 0, pl.col("attempts") == 3)
    involuntary = tables["subscription_events"].filter(pl.col("cancellation_type") == "involuntary")
    assert set(exhausted["subscription_id"]) <= set(involuntary["subscription_id"])


def test_reactivations_and_plan_changes_happen(tables):
    events = set(tables["subscription_events"]["event_type"].unique())
    assert {"reactivated", "plan_upgraded", "plan_downgraded", "price_increased"} <= events
    assert tables["subscriptions"]["is_reactivation"].sum() > 0


def test_trial_abuse_reuses_identities(tables):
    variants = tables["customers"].filter(pl.col("email").str.contains(r"\+\d@"))
    assert variants.height > 0
    originals = variants.with_columns(pl.col("email").str.replace(r"\+\d@", "@"))
    assert _missing(originals, "email", tables["customers"], "email") == 0


def test_viewing_sessions_are_plausible(tables):
    sessions = tables["viewing_sessions"].join(
        tables["content_catalog"].select("title_id", "runtime_minutes", "added_date"),
        on="title_id",
    )
    assert (sessions["watch_minutes"] >= 1).all()
    assert (sessions["watch_minutes"] <= sessions["runtime_minutes"]).all()
    assert (sessions["started_at"].dt.date() >= sessions["added_date"]).all()
    evening = sessions["started_at"].dt.hour().is_between(18, 22).mean()
    assert evening > 0.4


def test_end_date_before_start_is_rejected(cfg):
    with pytest.raises(ValueError, match="before the start date"):
        simulate(cfg, date(2025, 1, 1))


def test_default_config_markets_add_up():
    cfg = GeneratorConfig()
    assert sum(m.signup_share for m in cfg.markets) == pytest.approx(1.0)
    assert sum(c.signup_share for c in cfg.channels) == pytest.approx(1.0)
    assert sum(cfg.tier_shares) == pytest.approx(1.0)
