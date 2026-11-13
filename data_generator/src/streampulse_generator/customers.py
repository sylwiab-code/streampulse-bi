"""Daily sign-ups: customers with PII, acquisition attribution, and each customer's lifecycle."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

import numpy as np
from faker import Faker

from .config import GeneratorConfig
from .lifecycle import LifecycleRows, Signup, simulate_customer
from .randomness import numpy_rng, python_rng, stable_seed
from .reference import campaign_id, date_range

_TRANSLITERATION = str.maketrans(
    {"ł": "l", "Ł": "L", "ø": "o", "Ø": "O", "æ": "ae", "Æ": "Ae", "ß": "ss"}
)


def email_local_part(first_name: str, last_name: str) -> str:
    """ASCII 'first.last' as an email address would use it."""
    parts = []
    for name in (first_name, last_name):
        ascii_name = unicodedata.normalize("NFKD", name.translate(_TRANSLITERATION))
        parts.append(re.sub(r"[^a-z]", "", ascii_name.encode("ascii", "ignore").decode().lower()))
    return ".".join(parts)


@dataclass(frozen=True)
class Identity:
    first_name: str
    last_name: str
    email: str
    market_index: int


@dataclass
class SignupRows(LifecycleRows):
    customers: list[tuple] = field(default_factory=list)
    attribution: list[tuple] = field(default_factory=list)


class _Names:
    """Seeded, localized fake names and email addresses."""

    def __init__(self, cfg: GeneratorConfig) -> None:
        self.cfg = cfg
        self.fakers = [Faker(m.faker_locale) for m in cfg.markets]

    def identity(self, customer_id: int, market_index: int) -> Identity:
        faker = self.fakers[market_index]
        faker.seed_instance(stable_seed(self.cfg.seed, "name", customer_id))
        first, last = faker.first_name(), faker.last_name()
        rnd = python_rng(self.cfg.seed, "email", customer_id)
        local = email_local_part(first, last)
        if rnd.random() < 0.5:
            local += str(1 + int(rnd.random() * 99))
        domains = self.cfg.markets[market_index].email_domains
        domain = domains[int(rnd.random() * len(domains))]
        return Identity(first, last, f"{local}@{domain}", market_index)


def simulate_signups(cfg: GeneratorConfig, end_date: date) -> SignupRows:
    """Generate sign-ups day by day and simulate each customer's lifecycle up to end_date."""
    rows = SignupRows()
    names = _Names(cfg)
    end = datetime.combine(end_date, time.max)
    market_shares = np.array([m.signup_share for m in cfg.markets])
    channel_shares = np.array([c.signup_share for c in cfg.channels])
    # Identities whose first trial expired without conversion, in expiry order.
    expired: list[tuple[datetime, Identity]] = []
    window_start = 0
    next_customer_id = 1

    for day_index, day in enumerate(date_range(cfg.start_date, end_date)):
        rng = numpy_rng(cfg.seed, "signups", day_index)
        count = int(rng.poisson(cfg.daily_signups * cfg.signup_seasonality[day.month - 1]))
        markets = rng.choice(len(cfg.markets), count, p=market_shares / market_shares.sum())
        channels = rng.choice(len(cfg.channels), count, p=channel_shares / channel_shares.sum())
        tiers = rng.choice(len(cfg.tier_shares), count, p=np.array(cfg.tier_shares))
        annual = rng.random(count) < cfg.annual_share
        trial = rng.random(count) < cfg.trial_share
        seconds = np.sort(rng.integers(0, 86_400, count))
        abuse_roll, abuse_pick = rng.random(count), rng.random(count)

        day_start = datetime.combine(day, time.min)
        window = day_start - timedelta(days=cfg.trial_abuse_window_days)
        while window_start < len(expired) and expired[window_start][0] < window:
            window_start += 1
        window_end = window_start
        while window_end < len(expired) and expired[window_end][0] < day_start:
            window_end += 1

        for i in range(count):
            customer_id = next_customer_id
            next_customer_id += 1
            created_at = day_start + timedelta(seconds=int(seconds[i]))
            candidates = window_end - window_start
            if abuse_roll[i] < cfg.trial_abuse_share and candidates > 0:
                original = expired[window_start + int(abuse_pick[i] * candidates)][1]
                local, domain = original.email.split("@")
                variant = 2 + int(abuse_pick[i] * 1000) % 8
                identity = Identity(
                    original.first_name,
                    original.last_name,
                    f"{local}+{variant}@{domain}",
                    original.market_index,
                )
                is_trial = True
            else:
                identity = names.identity(customer_id, int(markets[i]))
                is_trial = bool(trial[i])

            market = cfg.markets[identity.market_index]
            channel_index = int(channels[i])
            channel = cfg.channels[channel_index]
            rows.customers.append(
                (
                    customer_id,
                    identity.first_name,
                    identity.last_name,
                    identity.email,
                    market.code,
                    created_at,
                )
            )
            campaign = None
            if channel.is_paid:
                campaign = campaign_id(cfg, day, identity.market_index, channel_index)
            rows.attribution.append((customer_id, channel.name, campaign, created_at))

            signup = Signup(
                customer_id,
                market,
                channel,
                created_at,
                int(tiers[i]),
                bool(annual[i]),
                is_trial,
            )
            expired_at = simulate_customer(cfg, signup, end, rows)
            if expired_at is not None:
                expired.append((expired_at, identity))
    return rows
