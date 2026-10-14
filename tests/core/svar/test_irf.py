"""Impulse responses and variance decompositions."""

from __future__ import annotations

import numpy as np

from csuf_fullerton.core.svar.data import deterministic
from csuf_fullerton.core.svar.estimate import fit_block_var, fit_var
from csuf_fullerton.core.svar.irf import fevd, historical_decomposition, irf, ma_coefficients
from tests.core.svar.sim import block_dgp


def test_foreign_irf_to_domestic_shock_is_zero() -> None:
    d = block_dgp(n=300, seed=1)
    theta = irf(fit_block_var(d.values, 2, deterministic(300), 2), 24)
    assert np.all(theta[:, :2, 2:] == 0.0)


def test_recursive_a0_block_triangular() -> None:
    d = block_dgp(n=300, seed=2)
    theta = irf(fit_block_var(d.values, 1, deterministic(300), 2), 0)
    assert np.allclose(np.triu(theta[0], 1), 0.0)


def test_fevd_rows_sum_to_one() -> None:
    d = block_dgp(n=300, seed=3)
    share = fevd(irf(fit_var(d.values, 2, deterministic(300)), 12))
    np.testing.assert_allclose(share.sum(axis=2), 1.0)


def test_ma_coefficients_var1_powers() -> None:
    a = np.array([[[0.5, 0.1], [0.0, 0.3]]])
    phi = ma_coefficients(a, 3)
    np.testing.assert_allclose(phi[3], np.linalg.matrix_power(a[0], 3))


def test_historical_decomposition_adds_up_to_shock_driven_part() -> None:
    d = block_dgp(n=200, seed=4)
    fit = fit_var(d.values, 1, deterministic(200))
    hd = historical_decomposition(fit)
    # with zero initial deviation the shock contributions rebuild y_t minus its baseline:
    # the first row is just the impact of the first residual
    np.testing.assert_allclose(hd[0].sum(axis=1), fit.resid[0], atol=1e-10)
