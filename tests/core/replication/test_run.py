"""Replication registry, metric rules and fast case functions (spec: replication-eval)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from csuf_fullerton.core.replication.cases import (
    Case,
    check_metric,
    evaluate,
    parse_case,
    registry_gaps,
)
from csuf_fullerton.core.replication.run import FUNCTIONS, run_case

ROOT = Path(__file__).resolve().parents[3]
CASES = sorted((ROOT / "replication" / "cases").glob("*.toml"))


def _doc(**kw: object) -> dict[str, object]:
    base = {
        "id": "x",
        "model": "m1",
        "kind": "parity",
        "suite": "fast",
        "function": "m3_parity_kalman",
        "source": "test",
        "settings": {"n": 60},
        "metric": [{"name": "max_abs_diff", "op": "<=", "target": 1e-8}],
    }
    return base | kw


def test_registry_completeness() -> None:
    cases = [parse_case(tomllib.loads(p.read_text())) for p in CASES]
    assert registry_gaps(cases) == {}
    assert all(c.function in FUNCTIONS for c in cases)
    partial = [c for c in cases if c.model != "m3"]
    assert registry_gaps(partial) == {"m3": ["simulation", "parity", "published"]}


def test_every_case_pins_fixture_hashes() -> None:
    for p in CASES:
        c = parse_case(tomllib.loads(p.read_text()))
        for d in c.data:
            assert len(d.sha256) == 64 and (ROOT / d.path).exists(), (c.id, d.path)


def test_parse_errors() -> None:
    for bad, msg in (
        ({"id": ""}, "needs 'id'"),
        ({"model": "m9"}, "model"),
        ({"kind": "vibes"}, "kind"),
        ({"suite": "slow"}, "suite"),
        ({"metric": []}, "at least one"),
        ({"metric": [{"name": "a", "op": "~", "target": 1}]}, "op"),
        ({"metric": [{"name": "a", "op": "between", "target": 1}]}, "between"),
    ):
        with pytest.raises(ValueError, match=msg):
            parse_case(_doc(**bad))


def test_metric_rules_and_golden() -> None:
    c = parse_case(
        _doc(
            metric=[
                {"name": "a", "op": "between", "target": [0, 1], "golden": 0.5, "golden_tol": 1e-6},
                {"name": "b", "op": ">=", "target": 2},
            ]
        )
    )
    r = evaluate(c, {"a": 0.5, "b": 3})
    assert r.passed
    drift = evaluate(c, {"a": 0.6, "b": 3})  # inside the economic threshold, off the pin
    assert not drift.passed and drift.metrics[0].passed and drift.metrics[0].golden_passed is False
    assert "pinned 0.5" in drift.metrics[0].message
    assert not evaluate(c, {"a": 0.5}).passed
    assert not check_metric(c.metrics[1], 1.0).passed


def test_run_case_ok_and_errors() -> None:
    ok = run_case(parse_case(_doc()), {})
    assert ok.passed and ok.seconds >= 0
    unknown = run_case(parse_case(_doc(function="nope")), {})
    assert not unknown.passed and "unknown" in unknown.error
    broken = run_case(parse_case(_doc(settings={})), {})
    assert not broken.passed and "KeyError" in broken.error


@pytest.mark.parametrize(
    "case_id",
    [
        "m0-parity-statsmodels",
        "m0-nicaragua-regression",
        "m1-parity-constant",
        "m1-cesa-bianchi-2012-direction",
        "m2-parity-flat",
        "m2-brazil-regression",
    ],
)
def test_fast_data_cases_pass(case_id: str) -> None:
    import pandas as pd

    c: Case = parse_case(
        tomllib.loads((ROOT / "replication" / "cases" / f"{case_id}.toml").read_text())
    )
    tables = {d.name: pd.read_csv(ROOT / d.path) for d in c.data}
    r = run_case(c, tables)
    assert r.passed, [m.message for m in r.metrics] or r.error


def test_simulation_functions_small() -> None:
    from csuf_fullerton.core.replication import run

    assert (
        run.m0_sim_break({}, {"reps": 1, "n": 200, "draws": 9, "scale": 2.0}, 1)["rejection_rate"]
        >= 0
    )
    out = run.m1_sim_coverage({}, {"n": 200, "reps": 1, "draws": 9, "horizon": 4}, 1)
    assert set(out) == {"coverage_first", "coverage_last", "coverage_diff"}
    assert run.m1_sim_lr_size({}, {"n": 200, "reps": 2}, 1)["power"] >= 0.5
    assert (
        run.m2_sim_sinusoid({}, {"reps": 1, "n_small": 100, "n_large": 200}, 1)["mad_large"] < 0.2
    )
    m = run.m3_sim_coverage(
        {}, {"reps": 1, "n": 80, "beta_sd": 0.003, "lv_sd": 0.05, "draws": 300, "burn": 100}, 1
    )
    assert m["max_foreign_response_to_domestic"] == 0.0
