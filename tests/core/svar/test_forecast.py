"""Clark-West out-of-sample test."""

from __future__ import annotations

import numpy as np
from scipy import stats

from csuf_fullerton.core.svar.data import deterministic
from csuf_fullerton.core.svar.forecast import clark_west, clark_west_stat
from tests.core.svar.sim import block_dgp


def test_clark_west_known_answer() -> None:
    e_r = np.array([1.0, -1.0, 2.0, 0.5])
    e_u = np.array([0.5, -0.5, 1.0, 0.5])
    f_r = np.array([0.0, 0.0, 0.0, 0.0])
    f_u = np.array([0.5, -0.5, 1.0, 0.0])
    f = e_r**2 - (e_u**2 - (f_r - f_u) ** 2)
    t_ref = f.mean() / (f.std(ddof=1) / 2.0)
    t, p = clark_west_stat(e_r, e_u, f_r, f_u)
    assert np.isclose(t, t_ref) and np.isclose(p, stats.norm.sf(t_ref))


def test_clark_west_detects_feedback() -> None:
    d = block_dgp(n=500, seed=3, feedback=0.4)
    res = clark_west(d.names, d.values, deterministic(500), 1, 2, 350)
    assert res[0].pvalue < 0.05 and res[0].mspe_ratio < 1
