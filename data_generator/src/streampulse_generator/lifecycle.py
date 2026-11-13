"""Subscription lifecycle of one customer: trials, payments, plan changes, churn, reactivation.

Each customer has an own random stream, consumed one billing period at a time, so the history up
to any date does not depend on how far the simulation runs (see randomness.py).
"""

from __future__ import annotations

import calendar
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .config import TIERS, Channel, GeneratorConfig, Market
from .randomness import python_rng
from .reference import plan_id, price

FAILURE_REASONS = ("insufficient_funds", "card_expired", "do_not_honor")


@dataclass(frozen=True)
class Signup:
    customer_id: int
    market: Market
    channel: Channel
    created_at: datetime
    tier: int
    annual: bool
    trial: bool


@dataclass
class LifecycleRows:
    """Row collectors for the tables the lifecycle produces."""

    subscriptions: list[tuple] = field(default_factory=list)
    events: list[tuple] = field(default_factory=list)
    payments: list[tuple] = field(default_factory=list)
    # Periods with access to the service: (start, end, subscription_id, customer_id, tier)
    access: list[tuple] = field(default_factory=list)


def add_months(moment: datetime, months: int) -> datetime:
    """Same day and time a number of months later, clipped to the end of shorter months."""
    month_index = moment.month - 1 + months
    year, month = moment.year + month_index // 12, month_index % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


class _Subscription:
    def __init__(
        self,
        cfg: GeneratorConfig,
        signup: Signup,
        subscription_id: int,
        rows: LifecycleRows,
        rnd: random.Random,
    ) -> None:
        self.cfg, self.signup, self.id, self.rows, self.rnd = (
            cfg,
            signup,
            subscription_id,
            rows,
            rnd,
        )
        self.event_count = 0
        self.payment_count = 0

    def event(self, kind: str, at: datetime, plan: str, **extra: object) -> None:
        self.event_count += 1
        self.rows.events.append(
            (
                self.id * 1000 + self.event_count,
                self.id,
                self.signup.customer_id,
                kind,
                at,
                plan,
                extra.get("previous_plan_id"),
                extra.get("cancellation_type"),
                extra.get("effective_date"),
            )
        )

    def collect_payment(self, plan: str, amount: float, period_start: datetime) -> datetime | None:
        """Charge for one billing period with retries; return the time of the successful attempt."""
        cfg, market = self.cfg, self.signup.market
        first_failure = cfg.payment_failure_rate * market.payment_failure_multiplier
        for attempt, offset in enumerate((0, *cfg.payment_retry_days), start=1):
            at = period_start + timedelta(days=offset)
            failure_chance = first_failure if attempt == 1 else 1 - cfg.retry_success_rate
            failed = self.rnd.random() < failure_chance
            reason = None
            if failed:
                reason = FAILURE_REASONS[int(self.rnd.random() * len(FAILURE_REASONS))]
            self.payment_count += 1
            self.rows.payments.append(
                (
                    self.id * 1000 + self.payment_count,
                    self.id,
                    self.signup.customer_id,
                    plan,
                    period_start.date(),
                    attempt,
                    at,
                    amount,
                    market.currency,
                    "failed" if failed else "succeeded",
                    reason,
                )
            )
            if not failed:
                return at
        return None

    def churn_chance(self, annual: bool, tenure_months: int, period_start: datetime) -> float:
        cfg = self.cfg
        if annual:
            chance = cfg.annual_renewal_churn
        else:
            chance = cfg.monthly_churn
            if tenure_months < cfg.early_tenure_months:
                chance *= cfg.early_tenure_churn_multiplier
        days_since_increase = (period_start.date() - cfg.price_increase_date).days
        if 0 <= days_since_increase < cfg.price_increase_churn_days:
            chance *= cfg.price_increase_churn_multiplier
        return chance * self.signup.market.churn_multiplier

    def run(
        self,
        start: datetime,
        tier: int,
        annual: bool,
        trial: bool,
        reactivation: bool,
        end: datetime,
    ) -> tuple[datetime | None, str]:
        """Simulate until the subscription ends or the next period starts after `end`.

        Returns the end time (None while still active) and the reason.
        """
        cfg, signup, rows = self.cfg, self.signup, self.rows
        plan = plan_id(tier, annual)
        rows.subscriptions.append(
            (self.id, signup.customer_id, signup.market.code, plan, start, trial, reactivation)
        )
        if trial:
            self.event("trial_started", start, plan)
            trial_end = start + timedelta(days=cfg.trial_days)
            rows.access.append((start, trial_end, self.id, signup.customer_id, tier))
            conversion = cfg.trial_conversion * signup.channel.trial_conversion_multiplier
            if self.rnd.random() >= conversion:
                self.event("trial_expired", trial_end, plan)
                return trial_end, "trial_expired"
            self.event("trial_converted", trial_end, plan)
            period_start = trial_end
        else:
            self.event("reactivated" if reactivation else "subscription_started", start, plan)
            period_start = start

        tenure_months = 0
        price_announced = start.date() >= cfg.price_increase_date
        while period_start <= end:
            if tenure_months > 0 and not annual:
                roll = self.rnd.random()
                previous = plan
                if roll < cfg.upgrade_rate and tier < len(TIERS) - 1:
                    tier += 1
                    plan = plan_id(tier, annual)
                    self.event("plan_upgraded", period_start, plan, previous_plan_id=previous)
                elif roll < cfg.upgrade_rate + cfg.downgrade_rate and tier > 0:
                    tier -= 1
                    plan = plan_id(tier, annual)
                    self.event("plan_downgraded", period_start, plan, previous_plan_id=previous)
            if not price_announced and period_start.date() >= cfg.price_increase_date:
                price_announced = True
                self.event("price_increased", period_start, plan)

            amount = price(cfg, signup.market, tier, annual, period_start.date())
            paid_at = self.collect_payment(plan, amount, period_start)
            if paid_at is None:
                last_attempt = period_start + timedelta(days=cfg.payment_retry_days[-1])
                self.event(
                    "cancelled",
                    last_attempt,
                    plan,
                    cancellation_type="involuntary",
                    effective_date=last_attempt.date(),
                )
                rows.access.append((period_start, last_attempt, self.id, signup.customer_id, tier))
                return last_attempt, "involuntary"

            period_end = add_months(period_start, 12 if annual else 1)
            rows.access.append((period_start, period_end, self.id, signup.customer_id, tier))
            if self.rnd.random() < self.churn_chance(annual, tenure_months, period_start):
                requested_at = period_start + (period_end - period_start) * self.rnd.random()
                self.event(
                    "cancelled",
                    requested_at,
                    plan,
                    cancellation_type="voluntary",
                    effective_date=period_end.date(),
                )
                return period_end, "voluntary"
            period_start = period_end
            tenure_months += 12 if annual else 1
        return None, "active"


def simulate_customer(
    cfg: GeneratorConfig, signup: Signup, end: datetime, rows: LifecycleRows
) -> datetime | None:
    """Simulate all subscriptions of a customer up to `end`.

    Returns when the first trial expired without conversion, or None.
    """
    rnd = python_rng(cfg.seed, "life", signup.customer_id)
    start, tier, annual, trial = signup.created_at, signup.tier, signup.annual, signup.trial
    trial_expired_at = None
    for sequence in range(100):
        subscription = _Subscription(cfg, signup, signup.customer_id * 100 + sequence, rows, rnd)
        ended_at, reason = subscription.run(start, tier, annual, trial, sequence > 0, end)
        if reason == "trial_expired" and sequence == 0:
            trial_expired_at = ended_at
        if ended_at is None or reason == "trial_expired":
            break
        if rnd.random() >= cfg.reactivation_rate:
            break
        span = cfg.reactivation_max_days - cfg.reactivation_min_days
        start = ended_at + timedelta(days=cfg.reactivation_min_days + span * rnd.random())
        if start > end:
            break
        annual, trial = False, False
    return trial_expired_at
