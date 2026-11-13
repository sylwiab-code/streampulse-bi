"""Generator settings: every synthetic-data assumption in one place (ADR-009).

The values are invented but plausible for a European streaming service. They are inputs for
synthetic data, not business rules; KPI definitions live in dbt.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

TIERS = ("basic", "standard", "premium")


@dataclass(frozen=True)
class Market:
    code: str
    name: str
    currency: str
    signup_share: float
    faker_locale: str
    email_domains: tuple[str, ...]
    monthly_prices: tuple[float, float, float]  # basic, standard, premium in local currency
    price_increase: float  # added to every monthly price on the price increase date
    eur_rate: float  # starting units of local currency per EUR
    churn_multiplier: float = 1.0
    payment_failure_multiplier: float = 1.0


@dataclass(frozen=True)
class Channel:
    name: str
    signup_share: float
    trial_conversion_multiplier: float
    daily_spend_eur: float = 0.0  # per campaign and day at a 100% market share; 0 = unpaid

    @property
    def is_paid(self) -> bool:
        return self.daily_spend_eur > 0


DEFAULT_MARKETS = (
    Market(
        code="DE",
        name="Germany",
        currency="EUR",
        signup_share=0.40,
        faker_locale="de_DE",
        email_domains=("gmail.com", "web.de", "gmx.de", "t-online.de"),
        monthly_prices=(7.99, 12.99, 17.99),
        price_increase=1.00,
        eur_rate=1.0,
    ),
    Market(
        code="PL",
        name="Poland",
        currency="PLN",
        signup_share=0.30,
        faker_locale="pl_PL",
        email_domains=("gmail.com", "wp.pl", "onet.pl", "o2.pl"),
        monthly_prices=(29.99, 43.99, 60.99),
        price_increase=5.00,
        eur_rate=4.30,
        churn_multiplier=1.2,
        payment_failure_multiplier=1.3,
    ),
    Market(
        code="SE",
        name="Sweden",
        currency="SEK",
        signup_share=0.15,
        faker_locale="sv_SE",
        email_domains=("gmail.com", "hotmail.se", "outlook.com"),
        monthly_prices=(99.0, 139.0, 179.0),
        price_increase=10.00,
        eur_rate=11.40,
        churn_multiplier=0.85,
        payment_failure_multiplier=0.8,
    ),
    Market(
        code="NO",
        name="Norway",
        currency="NOK",
        signup_share=0.15,
        faker_locale="no_NO",
        email_domains=("gmail.com", "online.no", "hotmail.no"),
        monthly_prices=(99.0, 139.0, 179.0),
        price_increase=10.00,
        eur_rate=11.70,
        churn_multiplier=0.8,
        payment_failure_multiplier=0.8,
    ),
)

DEFAULT_CHANNELS = (
    Channel("organic", 0.35, 1.05),
    Channel("paid_search", 0.20, 1.10, daily_spend_eur=900.0),
    Channel("paid_social", 0.20, 0.85, daily_spend_eur=800.0),
    Channel("display", 0.08, 0.80, daily_spend_eur=300.0),
    Channel("tv", 0.07, 1.00, daily_spend_eur=1500.0),
    Channel("affiliate", 0.05, 0.90, daily_spend_eur=200.0),
    Channel("referral", 0.05, 1.25),
)

DEFAULT_GENRES = (
    "drama",
    "comedy",
    "thriller",
    "crime",
    "documentary",
    "sci-fi",
    "romance",
    "animation",
    "horror",
    "action",
)

# Relative viewing activity per hour of day (00-23), with an evening peak.
DEFAULT_HOURLY_WEIGHTS = (
    0.30, 0.15, 0.10, 0.05, 0.05, 0.05, 0.10, 0.25, 0.30, 0.30, 0.35, 0.40,
    0.50, 0.50, 0.50, 0.60, 0.70, 0.90, 1.20, 1.60, 2.00, 2.00, 1.50, 0.80,
)  # fmt: skip

# Relative sign-up volume per calendar month (January first): peaks around the holidays.
DEFAULT_SEASONALITY = (1.15, 1.0, 0.95, 0.9, 0.85, 0.8, 0.8, 0.85, 1.0, 1.05, 1.2, 1.3)


@dataclass(frozen=True)
class GeneratorConfig:
    seed: int = 42
    start_date: date = date(2024, 11, 1)

    # Sign-ups and plans
    daily_signups: float = 68.0
    signup_seasonality: tuple[float, ...] = DEFAULT_SEASONALITY
    markets: tuple[Market, ...] = DEFAULT_MARKETS
    channels: tuple[Channel, ...] = DEFAULT_CHANNELS
    tier_shares: tuple[float, float, float] = (0.35, 0.45, 0.20)
    annual_share: float = 0.15
    annual_price_months: int = 10  # an annual plan costs this many monthly prices

    # Trials
    trial_share: float = 0.60
    trial_days: int = 7
    trial_conversion: float = 0.55
    trial_abuse_share: float = 0.02  # share of sign-ups reusing an identity whose trial expired
    trial_abuse_window_days: int = 30

    # Churn, payments, plan changes
    monthly_churn: float = 0.034  # about 4% overall once the higher early-tenure churn is added
    early_tenure_months: int = 3
    early_tenure_churn_multiplier: float = 1.4
    annual_renewal_churn: float = 0.25
    payment_failure_rate: float = 0.05
    payment_retry_days: tuple[int, ...] = (3, 7)
    retry_success_rate: float = 0.29  # with two retries, about half of failed payments recover
    upgrade_rate: float = 0.02
    downgrade_rate: float = 0.01
    reactivation_rate: float = 0.15
    reactivation_min_days: int = 7
    reactivation_max_days: int = 180

    # Price increase
    price_increase_date: date = date(2025, 9, 1)
    price_increase_churn_multiplier: float = 2.0
    price_increase_churn_days: int = 30

    # Content and viewing
    catalog_size: int = 2000
    catalog_launch_share: float = 0.8  # titles available before the start date
    genres: tuple[str, ...] = DEFAULT_GENRES
    sessions_per_active_day: float = 0.55
    tier_viewing_multipliers: tuple[float, float, float] = (0.8, 1.0, 1.3)
    devices: tuple[tuple[str, float], ...] = (
        ("tv", 0.45),
        ("mobile", 0.25),
        ("web", 0.15),
        ("tablet", 0.15),
    )
    hourly_viewing_weights: tuple[float, ...] = DEFAULT_HOURLY_WEIGHTS

    # Exchange rates
    fx_daily_volatility: float = 0.003

    # Deliberate data-quality defects
    duplicate_rate: float = 0.005
    late_rate: float = 0.01
    late_max_days: int = 5
    null_key_rate: float = 0.001
    schema_change_date: date = date(2026, 1, 1)  # viewing_sessions: device -> device_type
