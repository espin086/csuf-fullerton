"""M3 TVP-VAR with stochastic volatility and the precision sampler (spec: time-varying-svar)."""

from __future__ import annotations

import numpy as np
import pytest

from csuf_fullerton.core.replication.run import m3_parity_kalman
from csuf_fullerton.core.tvsvar import m3
from csuf_fullerton.core.tvsvar.precision import draw_states
from csuf_fullerton.core.tvsvar.simulate import tvp_dgp


@pytest.fixture(scope="module")
def fit() -> tuple[m3.TvpResult, object]:
    d = tvp_dgp(150, 2, 0.003, 0.05)
    return m3.gibbs(d.y, 1, m3.TvpSettings(p=1, draws=600, burn=200, thin=2, seed=3)), d


def test_precision_mean_equals_kalman_smoother() -> None:
    assert m3_parity_kalman({}, {"n": 80}, 1)["max_abs_diff"] < 1e-8


def test_precision_draw_has_posterior_covariance() -> None:
    rng = np.random.default_rng(0)
    n, d = 3, 1
    obs = np.ones((n, d, d))
    lin = np.zeros((n, d))
    draws = np.array(
        [draw_states(obs, lin, np.eye(d), np.zeros(d), np.eye(d), rng)[1] for _ in range(4000)]
    )
    a = np.diag([3.0, 3.0, 2.0]) + np.diag([-1.0, -1.0], 1) + np.diag([-1.0, -1.0], -1)
    assert np.allclose(np.cov(draws.reshape(4000, 3).T), np.linalg.inv(a), atol=0.03)


def test_block_zero_every_draw(fit: tuple[m3.TvpResult, object]) -> None:
    res, _ = fit
    assert res.layout.cols[0] == (0,)  # foreign equation: own lag only
    for t in (0, 75, 148):
        resp = m3.irf_at(res, t, 6)
        assert np.all(resp[:, :, 0, 1] == 0.0)


def test_mcmc_diagnostics_are_reported(fit: tuple[m3.TvpResult, object]) -> None:
    res, _ = fit
    diag = m3.diagnostics(res)
    assert set(diag) == {"beta", "a", "log_var", "q_diag"}
    assert all(v["median_inefficiency"] > 0 for v in diag.values())
    assert res.accepted_draws == 200


def test_recovers_volatility_level(fit: tuple[m3.TvpResult, object]) -> None:
    res, d = fit
    med = np.median(res.g, axis=0)
    assert np.abs(med.mean(axis=0) - d.log_var[1:].mean(axis=0)).max() < 0.4


def test_settings_errors() -> None:
    y = tvp_dgp(60, 1).y
    with pytest.raises(ValueError, match="training"):
        m3.gibbs(y, 1, m3.TvpSettings(p=1, draws=10, burn=5, training=5))
    with pytest.raises(ValueError, match="burn"):
        m3.gibbs(y, 1, m3.TvpSettings(p=1, draws=5, burn=5))


def test_inefficiency_and_geweke() -> None:
    rng = np.random.default_rng(0)
    x = rng.standard_normal(2000)
    assert 0.5 < m3.inefficiency(x) < 1.5
    assert abs(m3.geweke_z(x)) < 3
    assert m3.inefficiency(np.ones(10)) == 1.0
    assert m3.geweke_z(np.ones(100)) == 0.0
