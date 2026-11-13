"""Seeded randomness that keeps the output stable for every end date (ADR-009).

Each random stream is derived from the seed and a fixed label, never from the end date, and is
consumed in date order. Generating up to a later end date therefore only appends data: all rows
up to an earlier end date stay identical, so daily batches always match the backfill.
"""

from __future__ import annotations

import hashlib
import random

import numpy as np


def stable_seed(*parts: object) -> int:
    """Derive a 64-bit seed from the given parts, identical on every platform and run."""
    text = "|".join(str(part) for part in parts)
    return int.from_bytes(hashlib.blake2b(text.encode(), digest_size=8).digest(), "little")


def numpy_rng(*parts: object) -> np.random.Generator:
    return np.random.default_rng(stable_seed(*parts))


def python_rng(*parts: object) -> random.Random:
    """A fast scalar generator; only .random() is used, which is stable across Python versions."""
    return random.Random(stable_seed(*parts))


def hash_uniform(ids: np.ndarray, *parts: object) -> np.ndarray:
    """Return a uniform value in [0, 1) for each id that does not depend on the other ids.

    Uses the splitmix64 mixing function, so a row gets the same value in a backfill and in a
    daily batch.
    """
    x = ids.astype(np.uint64) ^ np.uint64(stable_seed(*parts))
    with np.errstate(over="ignore"):
        x = x + np.uint64(0x9E3779B97F4A7C15)
        x = (x ^ (x >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        x = (x ^ (x >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        x = x ^ (x >> np.uint64(31))
    return (x >> np.uint64(11)).astype(np.float64) / float(1 << 53)
