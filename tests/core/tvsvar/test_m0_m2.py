"""M0 stability tests and M2 kernel estimator (spec: time-varying-svar)."""

from __future__ import annotations

import numpy as np
import pytest

from csuf_fullerton.core.svar.data import deterministic
from csuf_fullerton.core.svar.estimate import fit_block_var
from csuf_fullerton.core.svar.irf import irf
from csuf_fullerton.core.tvsvar import m0, m2
from csuf_fullerton.core.tvsvar.simulate import TW_G, kernel_dgp, tw_dgp


def test_sup_lr_detects_drift_and_chow_reports_date() -> None:
    y, _ = tw_dgp(400, 1, 2 * TW_G)
    out = m0.stability_tests(y, 1, np.ones((400, 1)), 3, 200, np.random.default_rng(0), 19)
    assert [t.name.split()[0] for t in out] == ["Chow", "sup-LR"]
    assert out[1].bootstrap_p <= 0.1
    assert out[0].break_index == 200 and out[0].asymptotic_p is not None


def test_stability_errors() -> None:
    y, _ = tw_dgp(60, 1)
    with pytest.raises(ValueError, match="too few"):
        m0.stability_tests(y, 1, np.ones((60, 1)), 3, 3, np.random.default_rng(0), 2)
    with pytest.raises(ValueError, match="too short"):
        m0.stability_tests(y[:20], 1, np.ones((20, 1)), 3, None, np.random.default_rng(0), 2)


def test_split_fits() -> None:
    y, _ = tw_dgp(200, 2)
    a, b = m0.split_fits(y, 1, np.ones((200, 1)), 3, 100)
    assert a.nobs == 99 and b.nobs == 100


def test_flat_kernel_equals_constant() -> None:
    y, _ = tw_dgp(300, 4)
    det = deterministic(300, True)
    kp = m2.kernel_svar(y, 2, det, 3, 8, float("inf"), step=100)
    ref = irf(fit_block_var(y, 2, det, 3), 8)
    for x in kp.irf:
        assert np.abs(x - ref).max() < 1e-8


def test_kernel_tracks_sinusoid_and_keeps_block_zero() -> None:
    d = kernel_dgp(600, 1)
    kp = m2.kernel_svar(d.y, 1, np.ones((600, 1)), 1, 6)
    assert np.abs(kp.impact[:, 0, 0] - d.beta[1:]).mean() < 0.08
    assert np.all(kp.irf[:, :, 0, 1] == 0.0)
    assert np.all(kp.impact_se > 0)


def test_kernel_bandwidth_guard() -> None:
    y, _ = tw_dgp(100, 4)
    with pytest.raises(ValueError, match="effective observations"):
        m2.kernel_svar(y, 4, deterministic(100, True), 3, 2, 0.3)
    assert m2.effective_nobs(np.ones(10)) == 10
