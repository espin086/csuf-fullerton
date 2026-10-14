"""Non-Gaussian direction measures."""

from __future__ import annotations

import numpy as np

from csuf_fullerton.core.svar.data import deterministic
from csuf_fullerton.core.svar.direction import direct_lingam, direction, order_agreement
from csuf_fullerton.core.svar.estimate import fit_var
from tests.core.svar.sim import block_dgp


def test_direction_recovered_on_non_gaussian_data() -> None:
    rng = np.random.default_rng(0)
    hits = 0
    for _ in range(40):
        x = rng.laplace(size=800)
        y = 0.8 * x + rng.laplace(size=800)
        d = direction("x", x, "y", y)
        hits += d.identified and d.verdict == "x -> y"
    assert hits >= 36


def test_gaussian_pair_is_not_identified() -> None:
    rng = np.random.default_rng(1)
    x = rng.normal(size=2000)
    y = 0.5 * x + rng.normal(size=2000)
    assert not direction("x", x, "y", y).identified


def test_direct_lingam_recovers_simulated_order() -> None:
    d = block_dgp(n=800, seed=2)
    fit = fit_var(d.values, 1, deterministic(800))
    order = direct_lingam(d.names, fit.resid).order
    assert order_agreement(order, ("f1", "f2")) == 1.0


def test_order_agreement_counts_pairs() -> None:
    assert order_agreement(("d", "f", "e"), ("f",)) == 0.5
