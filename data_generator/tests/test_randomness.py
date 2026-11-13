"""Tests for seeded randomness and helpers whose output must never drift."""

from __future__ import annotations

from datetime import datetime

import numpy as np
from streampulse_generator.customers import email_local_part
from streampulse_generator.lifecycle import add_months
from streampulse_generator.randomness import hash_uniform, stable_seed


def test_stable_seed_is_fixed():
    # A change here changes every generated dataset; update only on purpose.
    assert stable_seed(42, "signups", 0) == stable_seed(42, "signups", 0)
    assert stable_seed(42, "signups", 0) != stable_seed(42, "signups", 1)
    assert stable_seed(42, "signups", 0) == STABLE_SEED_42_SIGNUPS_0


def test_hash_uniform_does_not_depend_on_other_ids():
    ids = np.arange(1, 10_001)
    values = hash_uniform(ids, 42, "test")
    subset = hash_uniform(ids[::7], 42, "test")
    assert np.array_equal(values[::7], subset)
    assert values.min() >= 0
    assert values.max() < 1
    assert abs(values.mean() - 0.5) < 0.01


def test_email_local_part_transliterates():
    assert email_local_part("Łukasz", "Søren-Øberg") == "lukasz.sorenoberg"
    assert email_local_part("Jürgen", "Groß") == "jurgen.gross"


def test_add_months_clips_to_month_end():
    assert add_months(datetime(2025, 1, 31, 10), 1) == datetime(2025, 2, 28, 10)
    assert add_months(datetime(2024, 11, 30), 3) == datetime(2025, 2, 28)
    assert add_months(datetime(2025, 3, 15), 12) == datetime(2026, 3, 15)


STABLE_SEED_42_SIGNUPS_0 = 17386994537118685050
