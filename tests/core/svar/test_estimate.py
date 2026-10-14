"""Estimator known answers: statsmodels equivalence and simulated block recovery."""

from __future__ import annotations

import numpy as np
from statsmodels.tsa.api import VAR

from csuf_fullerton.core.svar.data import deterministic, lag_matrix, make_dataset
from csuf_fullerton.core.svar.estimate import fit_block_var, fit_var, max_root
from tests.core.svar.sim import block_dgp


def test_unrestricted_matches_statsmodels() -> None:
    d = block_dgp(n=250, seed=3)
    fit = fit_var(d.values, 2, deterministic(250))
    ref = VAR(d.values).fit(2, trend="c")
    np.testing.assert_allclose(fit.coef, ref.params, atol=1e-8)
    np.testing.assert_allclose(fit.resid, ref.resid, atol=1e-8)


def test_recovers_simulated_block_dgp() -> None:
    d = block_dgp(n=4000, seed=4)
    fit = fit_block_var(d.values, 1, deterministic(4000), 2)
    assert np.all(fit.A[0][:2, 2:] == 0.0)
    assert abs(fit.A[0][2, 0] - 0.3) < 0.05
    assert abs(fit.A[0][0, 0] - 0.5) < 0.05
    assert max_root(fit) < 1


def test_restricted_equals_unrestricted_when_foreign_block_unrelated() -> None:
    """Domestic equations of the block fit keep every lag, so their residual variance can
    only be at least as small as the restricted foreign equations allow."""
    d = block_dgp(n=300, seed=5)
    det = deterministic(300)
    r = fit_block_var(d.values, 1, det, 2)
    u = fit_var(d.values, 1, det)
    assert np.linalg.det(r.sigma) >= np.linalg.det(u.sigma) - 1e-12


def test_make_dataset_keeps_last_complete_block() -> None:
    vals = np.array([[1.0, 2.0], [np.nan, 1.0], [3.0, 4.0], [5.0, 6.0]])
    ds = make_dataset(["a", "b"], vals, ["d0", "d1", "d2", "d3"], [1, 2, 3, 4])
    assert ds.dates == ("d2", "d3")
    assert ds.season is not None and list(ds.season) == [3, 4]


def test_lag_matrix_layout() -> None:
    y = np.arange(10.0).reshape(5, 2)
    x = lag_matrix(y, 2)
    np.testing.assert_array_equal(x[0], [2.0, 3.0, 0.0, 1.0])


def test_seasonal_dummies_are_centred() -> None:
    season = np.array([1 + (t % 12) for t in range(24)])
    det = deterministic(24, trend=True, season=season, period=12)
    assert det.shape == (24, 13)
    np.testing.assert_allclose(det[:, 2:].sum(axis=0), 0.0, atol=1e-12)
