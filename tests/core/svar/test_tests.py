"""Hypothesis tests: size, power, criteria and Holm."""

from __future__ import annotations

import numpy as np
import pytest

from csuf_fullerton.core.svar.data import deterministic
from csuf_fullerton.core.svar.estimate import fit_var
from csuf_fullerton.core.svar.tests import (
    bootstrap_block_wald,
    holm,
    instantaneous_block,
    lag_augmented_wald,
    lr_block_exogeneity,
    portmanteau,
    select_lags,
)
from tests.core.svar.sim import block_dgp


def test_lr_size_under_true_restriction() -> None:
    rej = [
        lr_block_exogeneity(block_dgp(n=400, seed=s).values, 1, deterministic(400), 2).pvalue < 0.05
        for s in range(150)
    ]
    assert 0.0 <= np.mean(rej) <= 0.12


def test_lr_rejects_false_restriction() -> None:
    rej = [
        lr_block_exogeneity(
            block_dgp(n=400, seed=s, feedback=0.3).values, 1, deterministic(400), 2
        ).pvalue
        < 0.05
        for s in range(30)
    ]
    assert np.mean(rej) >= 0.9


def test_lag_augmented_matches_lr_on_stationary_data() -> None:
    d = block_dgp(n=400, seed=7, feedback=0.2)
    det = deterministic(400)
    la = lag_augmented_wald(d.values, 1, 1, det, [2, 3, 4], [0, 1])
    assert la.pvalue < 0.05 and la.df == 6


def test_bootstrap_block_wald_p_in_unit_interval() -> None:
    d = block_dgp(n=150, seed=8, unit_root=True)
    res = bootstrap_block_wald(
        d.values, 2, 1, deterministic(150, True), [0, 1], 49, np.random.default_rng(0)
    )
    assert 0.0 < res.pvalue <= 1.0 and res.df == 12


def test_instantaneous_block_detects_correlation() -> None:
    d = block_dgp(n=400, seed=9)
    fit = fit_var(d.values, 1, deterministic(400))
    assert instantaneous_block(fit.resid, 2).pvalue < 0.01


def test_select_lags_finds_var1() -> None:
    d = block_dgp(n=600, seed=10)
    assert select_lags(d.values, 4, deterministic(600))["bic"] == 1


def test_portmanteau_does_not_reject_white_residuals() -> None:
    d = block_dgp(n=600, seed=11)
    assert portmanteau(fit_var(d.values, 1, deterministic(600))).pvalue > 0.01


def test_holm_known_answer() -> None:
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
