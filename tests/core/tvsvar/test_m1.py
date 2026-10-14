"""M1 trade-weighted SVAR (spec: time-varying-svar)."""

from __future__ import annotations

import numpy as np
import pytest

from csuf_fullerton.core.svar.data import deterministic
from csuf_fullerton.core.svar.estimate import fit_block_var
from csuf_fullerton.core.svar.irf import irf
from csuf_fullerton.core.tvsvar import m1
from csuf_fullerton.core.tvsvar.simulate import TW_G, tw_dgp, tw_true_irf

SPEC = m1.TwSpec(3, 5, ("us", "cn"), ((1,), (2,)), 1, "interacted")


@pytest.fixture(scope="module")
def sim() -> tuple[np.ndarray, np.ndarray]:
    return tw_dgp(600, 3)


def test_constant_weights_reduce_to_constant_model(sim: tuple[np.ndarray, np.ndarray]) -> None:
    y, w = sim
    det = deterministic(len(y), True)
    for p in (1, 2):
        fit = m1.fit_tw(
            SPEC.with_variant("constant")
            if p == 1
            else m1.TwSpec(3, 5, ("us", "cn"), ((1,), (2,)), 2, "constant"),
            y,
            det,
            w,
        )
        ref = fit_block_var(y, p, det, 3)
        assert np.abs(m1.frozen_irf(fit, w[0], 12) - irf(ref, 12)).max() < 1e-10


def test_foreign_variables_never_respond_to_domestic_shocks(
    sim: tuple[np.ndarray, np.ndarray],
) -> None:
    y, w = sim
    det = np.ones((len(y), 1))
    for v in m1.VARIANTS:
        fit = m1.fit_tw(SPEC.with_variant(v), y, det, w)
        for wt in (w[0], w[-1]):
            assert np.all(m1.frozen_irf(fit, wt, 24)[:, :3, 3:] == 0.0)


def test_interacted_recovers_true_irfs(sim: tuple[np.ndarray, np.ndarray]) -> None:
    y, w = sim
    fit = m1.fit_tw(SPEC, y, np.ones((len(y), 1)), w)
    for wt in (w[0], w[-1]):
        assert np.abs(m1.frozen_irf(fit, wt, 6) - tw_true_irf(wt, 6)).max() < 0.15


def test_frozen_weights_change_the_response(sim: tuple[np.ndarray, np.ndarray]) -> None:
    y, w = sim
    det = np.ones((len(y), 1))
    fit = m1.fit_tw(SPEC, y, det, w)
    b = m1.bootstrap_frozen(
        fit, y, det, w, [(1995, w[0]), (2023, w[-1])], 8, 30, np.random.default_rng(0)
    )
    assert b.point.shape == (2, 9, 5, 5) and b.diff_point.shape == (1, 9, 5, 5)
    assert np.allclose(b.diff_point[0], b.point[1] - b.point[0])
    assert b.diff_lower[0, 0, 3, 2] > 0  # China weight rises, so its impact on d1 rises
    pct = m1.bootstrap_frozen(
        fit,
        y,
        det,
        w,
        [(1, w[0]), (2, w[-1])],
        4,
        10,
        np.random.default_rng(0),
        method="percentile",
    )
    assert np.all(pct.lower <= pct.upper)
    with pytest.raises(ValueError, match="method"):
        m1.bootstrap_frozen(fit, y, det, w, [(1, w[0])], 4, 2, np.random.default_rng(0), method="x")


def test_weights_do_not_matter(sim: tuple[np.ndarray, np.ndarray]) -> None:
    """Scenario: under G = 0 the LR test does not reject; under the true G it does."""
    det = np.ones((600, 1))
    y0, w0 = tw_dgp(600, 9, 0 * TW_G)
    fi = m1.fit_tw(SPEC, y0, det, w0)
    fl = m1.fit_tw(SPEC.with_variant("levels"), y0, det, w0, fi.center)
    assert m1.lr_nested(fl, fi, "x").pvalue > 0.05
    y, w = sim
    fi = m1.fit_tw(SPEC, y, det, w)
    fl = m1.fit_tw(SPEC.with_variant("levels"), y, det, w, fi.center)
    assert m1.lr_nested(fl, fi, "x").pvalue < 0.01
    assert m1.bootstrap_lr(fl, "interacted", y, det, w, 19, np.random.default_rng(0)) <= 0.1


def test_wald_equal_slopes(sim: tuple[np.ndarray, np.ndarray]) -> None:
    y, w = sim
    fit = m1.fit_tw(SPEC, y, np.ones((len(y), 1)), w)
    assert m1.wald_equal_slopes(fit).pvalue < 0.05  # true slopes 0.8 vs 2.0
    with pytest.raises(ValueError):
        m1.wald_equal_slopes(m1.fit_tw(SPEC.with_variant("star"), y, np.ones((len(y), 1)), w))


def test_star_reduces_to_prebuilt_star_column(sim: tuple[np.ndarray, np.ndarray]) -> None:
    y, w = sim
    det = np.ones((len(y), 1))
    star = m1.fit_tw(SPEC.with_variant("star"), y, det, w)
    # the star regressor equals sum_j w_j (x_j - mean) at every lag
    xs = star.x_d
    c = star.center
    expected = w[1:, 0] * (y[1:, 1] - c[1]) + w[1:, 1] * (y[1:, 2] - c[2])
    assert np.allclose(xs[:, 1 + 1], expected)


def test_loading_path_tracks_weights(sim: tuple[np.ndarray, np.ndarray]) -> None:
    y, w = sim
    fit = m1.fit_tw(SPEC, y, np.ones((len(y), 1)), w)
    path = m1.loading_path(fit, w, 0, 2)
    assert np.corrcoef(path, w[:, 1])[0, 1] > 0.99


def test_spec_validation() -> None:
    with pytest.raises(ValueError, match="variant"):
        m1.TwSpec(3, 5, (), (), 1, "bad")
    with pytest.raises(ValueError, match="foreign"):
        m1.TwSpec(0, 5, (), (), 1)
    with pytest.raises(ValueError, match="lag"):
        m1.TwSpec(3, 5, (), (), 0)
    with pytest.raises(ValueError, match="one column"):
        m1.TwSpec(3, 5, ("a",), (), 1)
    with pytest.raises(ValueError, match="same variable"):
        m1.TwSpec(3, 5, ("a", "b"), ((0,), (1, 2)), 1)
    with pytest.raises(ValueError, match="distinct"):
        m1.TwSpec(3, 5, ("a", "b"), ((1,), (1,)), 1)
    with pytest.raises(ValueError, match="share rows"):
        m1.fit_tw(SPEC, np.zeros((10, 5)), np.ones((9, 1)), np.zeros((10, 2)))
