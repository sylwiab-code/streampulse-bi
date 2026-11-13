"""Reference data: markets, currencies, plans, prices, exchange rates, catalog, campaigns."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import product

import numpy as np
import polars as pl

from .config import TIERS, GeneratorConfig, Market
from .randomness import numpy_rng

CURRENCY_NAMES = {
    "EUR": "Euro",
    "PLN": "Polish zloty",
    "SEK": "Swedish krona",
    "NOK": "Norwegian krone",
}

_ADJECTIVES = (
    "Silent", "Broken", "Hidden", "Last", "Northern", "Golden", "Crimson", "Lost", "Endless",
    "Frozen", "Wild", "Secret", "Distant", "Burning", "Quiet", "Dark", "Electric", "Little",
    "Midnight", "Hollow", "Bright", "Final", "Restless", "Velvet", "Iron", "Paper", "Glass",
    "Second", "Winter", "Fading",
)  # fmt: skip
_NOUNS = (
    "Harbor", "Kingdom", "Signal", "River", "Witness", "Garden", "Frontier", "Echo", "Station",
    "Empire", "Orchard", "Mirror", "Island", "Protocol", "Summer", "Archive", "Lighthouse",
    "Border", "Circus", "Forest", "Promise", "Machine", "Daughter", "Stranger", "Verdict",
    "Horizon", "Shelter", "Detective", "Season", "Bridge",
)  # fmt: skip
_PLACES = (
    "Berlin", "Krakow", "Oslo", "Malmo", "Gdansk", "Bergen", "Hamburg", "Uppsala", "Warsaw",
    "Munich", "Stockholm", "Tromso", "Leipzig", "Lodz", "Gothenburg", "Stavanger", "Bremen",
    "Wroclaw", "Lund", "Trondheim", "the North", "the Valley", "the Coast", "the Mountains",
    "the Sea", "Tomorrow", "Yesterday", "Nowhere", "the Lake", "the Night",
)  # fmt: skip


def date_range(start: date, end: date) -> list[date]:
    """All dates from start to end, inclusive."""
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def plan_id(tier: int, annual: bool) -> str:
    return f"{TIERS[tier]}_{'annual' if annual else 'monthly'}"


def price(cfg: GeneratorConfig, market: Market, tier: int, annual: bool, on: date) -> float:
    """List price in local currency for a billing period that starts on the given date."""
    monthly = market.monthly_prices[tier]
    if on >= cfg.price_increase_date:
        monthly += market.price_increase
    return round(monthly * (cfg.annual_price_months if annual else 1), 2)


def markets_frame(cfg: GeneratorConfig) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "market_code": [m.code for m in cfg.markets],
            "market_name": [m.name for m in cfg.markets],
            "currency_code": [m.currency for m in cfg.markets],
        }
    )


def currencies_frame(cfg: GeneratorConfig) -> pl.DataFrame:
    codes = ["EUR", *sorted({m.currency for m in cfg.markets} - {"EUR"})]
    return pl.DataFrame(
        {"currency_code": codes, "currency_name": [CURRENCY_NAMES[c] for c in codes]}
    )


def plans_frame() -> pl.DataFrame:
    rows = [
        (
            plan_id(tier, annual),
            f"{TIERS[tier].title()} ({'annual' if annual else 'monthly'})",
            TIERS[tier],
            tier + 1,
            "annual" if annual else "monthly",
            12 if annual else 1,
        )
        for tier, annual in product(range(len(TIERS)), (False, True))
    ]
    schema = {
        "plan_id": pl.String,
        "plan_name": pl.String,
        "tier": pl.String,
        "tier_rank": pl.Int8,
        "billing_period": pl.String,
        "billing_months": pl.Int8,
    }
    return pl.DataFrame(rows, schema=schema, orient="row")


def plan_prices_frame(cfg: GeneratorConfig) -> pl.DataFrame:
    rows = []
    before = cfg.price_increase_date - timedelta(days=1)
    for market, tier, annual in product(cfg.markets, range(len(TIERS)), (False, True)):
        for valid_from, valid_to in ((cfg.start_date, before), (cfg.price_increase_date, None)):
            rows.append(
                (
                    len(rows) + 1,
                    market.code,
                    plan_id(tier, annual),
                    market.currency,
                    price(cfg, market, tier, annual, valid_from),
                    valid_from,
                    valid_to,
                )
            )
    schema = {
        "price_id": pl.Int32,
        "market_code": pl.String,
        "plan_id": pl.String,
        "currency_code": pl.String,
        "price": pl.Float64,
        "valid_from": pl.Date,
        "valid_to": pl.Date,
    }
    return pl.DataFrame(rows, schema=schema, orient="row")


def fx_rates(cfg: GeneratorConfig, end_date: date) -> dict[str, np.ndarray]:
    """Daily units of each currency per EUR, indexed by days since the start date."""
    days = (end_date - cfg.start_date).days + 1
    rates = {"EUR": np.ones(days)}
    for market in cfg.markets:
        if market.currency in rates:
            continue
        shocks = numpy_rng(cfg.seed, "fx", market.currency).normal(
            0.0, cfg.fx_daily_volatility, days
        )
        base = math.log(market.eur_rate)
        log_rate = base
        series = np.empty(days)
        for day, shock in enumerate(shocks):
            log_rate += shock - 0.02 * (log_rate - base)  # random walk pulled back to the base
            series[day] = math.exp(log_rate)
        rates[market.currency] = series
    return rates


def fx_rates_frame(
    cfg: GeneratorConfig, rates: dict[str, np.ndarray], end_date: date
) -> pl.DataFrame:
    dates = date_range(cfg.start_date, end_date)
    frames = [
        pl.DataFrame(
            {
                "rate_date": dates,
                "currency_code": [currency] * len(dates),
                "units_per_eur": np.round(series, 4),
            }
        )
        for currency, series in rates.items()
    ]
    return pl.concat(frames)


@dataclass(frozen=True)
class Catalog:
    frame: pl.DataFrame
    runtime_minutes: np.ndarray  # by title index (title_id - 1)
    added_date: np.ndarray  # datetime64[D] by title index
    popularity: np.ndarray  # probability of being watched, by title index
    launch_titles: np.ndarray  # indexes of titles available before the start date


def build_catalog(cfg: GeneratorConfig) -> Catalog:
    rng = numpy_rng(cfg.seed, "catalog")
    size = cfg.catalog_size
    names = [f"The {a} {n}" for a, n in product(_ADJECTIVES, _NOUNS)]
    names += [f"{n} of {p}" for n, p in product(_NOUNS, _PLACES)]
    names += [f"{a} {p}" for a, p in product(_ADJECTIVES, _PLACES)]
    if size > len(names):
        raise ValueError(f"catalog_size must be at most {len(names)}")
    title_names = [names[i] for i in rng.permutation(len(names))[:size]]

    genre = rng.choice(len(cfg.genres), size)
    is_movie = rng.random(size) < 0.6
    runtime = np.where(is_movie, rng.integers(80, 161, size), rng.integers(22, 61, size))
    release_year = 2026 - np.minimum(40, np.floor(rng.exponential(6.0, size))).astype(int)
    launch = rng.random(size) < cfg.catalog_launch_share
    offsets = np.where(launch, -rng.integers(30, 1500, size), rng.integers(0, 730, size))
    added = np.datetime64(cfg.start_date, "D") + offsets.astype("timedelta64[D]")
    ranks = rng.permutation(size) + 1
    popularity = ranks.astype(float) ** -0.9
    popularity /= popularity.sum()

    frame = pl.DataFrame(
        {
            "title_id": np.arange(1, size + 1, dtype=np.int32),
            "title_name": title_names,
            "genre": [cfg.genres[g] for g in genre],
            "content_type": np.where(is_movie, "movie", "series"),
            "runtime_minutes": runtime.astype(np.int16),
            "release_year": release_year.astype(np.int16),
            "added_date": added,
        }
    )
    return Catalog(frame, runtime, added, popularity, np.flatnonzero(launch))


def _quarter_index(day: date) -> int:
    return day.year * 4 + (day.month - 1) // 3


def campaign_id(cfg: GeneratorConfig, day: date, market_index: int, channel_index: int) -> int:
    """Stable id of the quarterly campaign for a market and paid channel."""
    quarter = _quarter_index(day) - _quarter_index(cfg.start_date)
    return quarter * 100 + market_index * 10 + channel_index + 1


def campaigns_frame(cfg: GeneratorConfig, end_date: date) -> pl.DataFrame:
    rows = []
    for quarter in range(_quarter_index(end_date) - _quarter_index(cfg.start_date) + 1):
        absolute = _quarter_index(cfg.start_date) + quarter
        year, first_month = absolute // 4, (absolute % 4) * 3 + 1
        start = max(date(year, first_month, 1), cfg.start_date)
        next_quarter = date(year + first_month // 10, (first_month + 2) % 12 + 1, 1)
        end = next_quarter - timedelta(days=1)
        for (m, market), (c, channel) in product(enumerate(cfg.markets), enumerate(cfg.channels)):
            if not channel.is_paid:
                continue
            rows.append(
                (
                    campaign_id(cfg, start, m, c),
                    f"{market.code} {channel.name} {year} Q{absolute % 4 + 1}",
                    market.code,
                    channel.name,
                    start,
                    end,
                )
            )
    schema = {
        "campaign_id": pl.Int32,
        "campaign_name": pl.String,
        "market_code": pl.String,
        "channel": pl.String,
        "start_date": pl.Date,
        "end_date": pl.Date,
    }
    return pl.DataFrame(rows, schema=schema, orient="row")


def campaign_spend_frame(
    cfg: GeneratorConfig, campaigns: pl.DataFrame, rates: dict[str, np.ndarray], end_date: date
) -> pl.DataFrame:
    markets = {m.code: m for m in cfg.markets}
    channels = {c.name: c for c in cfg.channels}
    rows = []
    for row in campaigns.iter_rows(named=True):
        market, channel = markets[row["market_code"]], channels[row["channel"]]
        days = date_range(row["start_date"], row["end_date"])
        noise = numpy_rng(cfg.seed, "spend", row["campaign_id"]).lognormal(0.0, 0.25, len(days))
        for day, factor in zip(days, noise, strict=True):
            if day > end_date:
                break
            rate = rates[market.currency][(day - cfg.start_date).days]
            amount = channel.daily_spend_eur * market.signup_share * factor * rate
            rows.append((day, row["campaign_id"], market.currency, round(float(amount), 2)))
    schema = {
        "spend_date": pl.Date,
        "campaign_id": pl.Int32,
        "currency_code": pl.String,
        "amount": pl.Float64,
    }
    return pl.DataFrame(rows, schema=schema, orient="row")
