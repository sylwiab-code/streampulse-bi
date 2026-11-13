"""Viewing sessions, generated in bulk from the periods in which subscribers have access.

Access periods are processed in order of their start time, and every column has its own random
stream. Extending the end date only appends periods, so earlier sessions and their ids are
unchanged (see randomness.py).
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import polars as pl

from .config import GeneratorConfig
from .randomness import numpy_rng
from .reference import Catalog

_SECONDS_PER_DAY = 86_400


def generate_sessions(
    cfg: GeneratorConfig, access: list[tuple], catalog: Catalog, end_date: date
) -> pl.DataFrame:
    if not access:
        return _frame(*(np.array([], dtype=dtype) for dtype in _EMPTY_DTYPES), cfg=cfg)
    starts = np.array([row[0] for row in access], dtype="datetime64[s]")
    ends = np.array([row[1] for row in access], dtype="datetime64[s]")
    subscription_ids = np.array([row[2] for row in access], dtype=np.int64)
    customer_ids = np.array([row[3] for row in access], dtype=np.int64)
    tiers = np.array([row[4] for row in access], dtype=np.int64)

    order = np.lexsort((subscription_ids, starts))
    starts, ends = starts[order], ends[order]
    customer_ids, tiers = customer_ids[order], tiers[order]

    def rng(stream: str) -> np.random.Generator:
        return numpy_rng(cfg.seed, "viewing", stream)

    duration_days = (ends - starts).astype(np.int64) / _SECONDS_PER_DAY
    multipliers = np.array(cfg.tier_viewing_multipliers)[tiers]
    counts = rng("counts").poisson(cfg.sessions_per_active_day * multipliers * duration_days)
    period = np.repeat(np.arange(len(starts)), counts)
    total = len(period)

    span_days = np.ceil(duration_days).astype(np.int64)
    day_offset = np.floor(rng("day").random(total) * span_days[period]).astype(np.int64)
    hour_weights = np.array(cfg.hourly_viewing_weights)
    hour = rng("hour").choice(24, total, p=hour_weights / hour_weights.sum())
    second = rng("second").integers(0, 3600, total)
    started_at = starts.astype("datetime64[D]")[period].astype("datetime64[s]") + (
        day_offset * _SECONDS_PER_DAY + hour * 3600 + second
    ).astype("timedelta64[s]")

    title = rng("title").choice(len(catalog.popularity), total, p=catalog.popularity)
    fallback = rng("fallback").choice(catalog.launch_titles, total)
    device_shares = np.array([share for _, share in cfg.devices])
    device = rng("device").choice(len(cfg.devices), total, p=device_shares / device_shares.sum())
    completion = rng("completion").beta(2.0, 1.2, total)
    session_id = np.arange(1, total + 1, dtype=np.int64)

    # A title can only be watched after it was added to the catalog.
    not_yet_added = catalog.added_date[title] > started_at.astype("datetime64[D]")
    title = np.where(not_yet_added, fallback, title)
    watch_minutes = np.maximum(1, np.round(catalog.runtime_minutes[title] * completion))

    end_limit = np.datetime64(end_date + timedelta(days=1), "s")
    keep = (started_at >= starts[period]) & (started_at < ends[period]) & (started_at < end_limit)
    return _frame(
        session_id[keep],
        customer_ids[period][keep],
        (title[keep] + 1),
        started_at[keep],
        watch_minutes[keep],
        device[keep],
        cfg=cfg,
    )


_EMPTY_DTYPES = (np.int64, np.int64, np.int64, "datetime64[s]", np.float64, np.int64)


def _frame(
    session_id: np.ndarray,
    customer_id: np.ndarray,
    title_id: np.ndarray,
    started_at: np.ndarray,
    watch_minutes: np.ndarray,
    device: np.ndarray,
    *,
    cfg: GeneratorConfig,
) -> pl.DataFrame:
    device_names = np.array([name for name, _ in cfg.devices])
    return pl.DataFrame(
        {
            "session_id": session_id,
            "customer_id": customer_id,
            "title_id": title_id.astype(np.int32),
            "started_at": started_at.astype("datetime64[us]"),
            "watch_minutes": watch_minutes.astype(np.int32),
            "device": device_names[device] if len(device) else np.array([], dtype=str),
        }
    )
