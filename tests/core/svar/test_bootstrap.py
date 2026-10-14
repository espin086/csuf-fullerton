"""Bootstrap bands keep the restriction."""

from __future__ import annotations

import numpy as np

from csuf_fullerton.core.svar.bootstrap import bootstrap_irf, refit, simulate
from csuf_fullerton.core.svar.data import deterministic
from csuf_fullerton.core.svar.estimate import fit_block_var
from csuf_fullerton.core.svar.irf import irf
from tests.core.svar.sim import block_dgp, true_irf


def test_every_draw_keeps_zero_block() -> None:
    d = block_dgp(n=200, seed=1)
    det = deterministic(200)
    fit = fit_block_var(d.values, 2, det, 2)
    rng = np.random.default_rng(0)
    u = fit.resid
    for _ in range(20):
        yb = simulate(fit, d.values[:2], det, u[rng.integers(0, len(u), len(u))])
        theta = irf(refit(fit, yb, det), 12)
        assert np.all(theta[:, :2, 2:] == 0.0)


def test_bands_bracket_point_and_keep_zeros() -> None:
    d = block_dgp(n=200, seed=2)
    det = deterministic(200)
    fit = fit_block_var(d.values, 1, det, 2)
    bands = bootstrap_irf(fit, d.values, det, 12, 100, np.random.default_rng(1), 0.9, "hall")
    assert np.all(bands.lower[:, :2, 2:] == 0.0) and np.all(bands.upper[:, :2, 2:] == 0.0)
    assert np.all(bands.lower <= bands.upper + 1e-12)


def test_band_coverage_simulated() -> None:
    """True recursive IRFs fall inside 95% bands at least 85% of the time (40 replications,
    so the 90% target of the 0002 spec is checked with sampling slack)."""
    truth = true_irf(4)
    hits = []
    for s in range(40):
        d = block_dgp(n=400, seed=100 + s)
        det = deterministic(400)
        fit = fit_block_var(d.values, 1, det, 2)
        b = bootstrap_irf(fit, d.values, det, 4, 100, np.random.default_rng(s), 0.95)
        inside = (b.lower[:, 2:, :2] <= truth[:, 2:, :2]) & (truth[:, 2:, :2] <= b.upper[:, 2:, :2])
        hits.append(float(inside.mean()))
    assert np.mean(hits) >= 0.85
