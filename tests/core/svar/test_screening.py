"""Screening stages on simulated processes with a known answer."""

from __future__ import annotations

import numpy as np

from csuf_fullerton.core.svar.data import deterministic
from csuf_fullerton.core.svar.report import screen_markdown
from csuf_fullerton.core.svar.screening import ScreenConfig, screen
from csuf_fullerton.core.svar.tests import lag_augmented_wald
from csuf_fullerton.core.svar.theory import parse_theory
from tests.core.svar.sim import block_dgp, theory_doc

FAST = ScreenConfig(max_lags=3, wald_draws=49, lingam_draws=10)


def test_lag_augmented_wald_size_under_unit_roots() -> None:
    rej = []
    for s in range(300):
        d = block_dgp(n=300, seed=1000 + s, unit_root=True)
        res = lag_augmented_wald(d.values, 2, 1, deterministic(300, True), [2, 3, 4], [0, 1])
        rej.append(res.pvalue < 0.05)
    assert 0.02 <= np.mean(rej) <= 0.10


def test_true_split_ranks_first() -> None:
    r = screen(block_dgp(n=400, seed=0), parse_theory(theory_doc()), FAST)
    rec = r.recommended
    assert rec is not None
    assert rec.spec.foreign == ("f1", "f2")
    assert rec.verdict == "supported" and rec.grade == "A"


def test_false_split_is_rejected() -> None:
    r = screen(block_dgp(n=400, seed=0, feedback=0.3), parse_theory(theory_doc()), FAST)
    by = {c.spec.foreign: c for c in r.candidates}
    assert by[("f1", "f2")].verdict == "rejected"
    assert by[("f1",)].verdict == "rejected"


def test_robustness_summary() -> None:
    r = screen(block_dgp(n=400, seed=0), parse_theory(theory_doc()), FAST)
    row = r.robustness[0]
    # splits that move f1 into the domestic block cannot respond to it, so not every
    # surviving split agrees; every grade-A split and the alternative ordering must
    a_specs = {c.spec.name for c in r.candidates if c.grade == "A" and c.verdict != "rejected"}
    assert a_specs <= set(row.specs)
    assert row.same_sign >= len(a_specs) + 1
    assert "ordering d3 > d2 > d1" in row.specs
    text = screen_markdown(r)
    assert "same sign" in text and "## Recommendation" in text


def test_weak_exogeneity_runs_on_cointegrated_data() -> None:
    d = block_dgp(n=300, seed=5, unit_root=True)
    th = parse_theory(theory_doc(trend=True))
    r = screen(d, th, ScreenConfig(max_lags=3, lags=2, wald_draws=0, lingam_draws=5))
    assert r.dmax >= 1
    assert all(
        c.verdict in ("supported", "mixed", "rejected") for c in r.candidates if c.grade != "X"
    )
