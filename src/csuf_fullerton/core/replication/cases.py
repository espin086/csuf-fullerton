"""Replication cases: what is run, on which pinned data, and what counts as a pass.

A case is a TOML document (``replication/cases/*.toml``)::

    id = "m1-parity-constant"
    model = "m1"                 # m0 | m1 | m2 | m3
    kind = "parity"              # simulation | parity | published | regression
    suite = "fast"               # fast | full
    function = "m1_parity_constant"
    source = "Change 0002 estimator"
    seed = 1
    [[data]]
    name = "brazil"
    path = "data/brazil.csv"
    sha256 = "..."
    [settings]
    lags = 2
    [[metric]]
    name = "max_abs_diff"
    op = "<="                    # <=, >=, between
    target = 1e-10               # or [lo, hi] for between
    golden = 3.4e-16             # optional pinned value
    golden_tol = 1e-12           # absolute tolerance around the pin
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

MODELS = ("m0", "m1", "m2", "m3")
KINDS = ("simulation", "parity", "published", "regression")
SUITES = ("fast", "full")
OPS = ("<=", ">=", "between")


@dataclass(frozen=True)
class DataRef:
    name: str
    path: str
    sha256: str


@dataclass(frozen=True)
class Metric:
    name: str
    op: str
    target: float | tuple[float, float]
    golden: float | None = None
    golden_tol: float | None = None


@dataclass(frozen=True)
class Case:
    id: str
    model: str
    kind: str
    suite: str
    function: str
    source: str
    seed: int
    data: tuple[DataRef, ...]
    settings: Mapping[str, Any]
    metrics: tuple[Metric, ...]
    qualitative: bool = False
    notes: str = ""


def parse_case(doc: Mapping[str, Any]) -> Case:
    for key in ("id", "model", "kind", "suite", "function", "source"):
        if not doc.get(key):
            raise ValueError(f"case needs '{key}'")
    if doc["model"] not in MODELS:
        raise ValueError(f"{doc['id']}: model must be one of {MODELS}")
    if doc["kind"] not in KINDS:
        raise ValueError(f"{doc['id']}: kind must be one of {KINDS}")
    if doc["suite"] not in SUITES:
        raise ValueError(f"{doc['id']}: suite must be one of {SUITES}")
    metrics = []
    for m in doc.get("metric", []):
        if m.get("op") not in OPS:
            raise ValueError(f"{doc['id']}: metric op must be one of {OPS}")
        tgt = m["target"]
        if m["op"] == "between":
            if not isinstance(tgt, list) or len(tgt) != 2:
                raise ValueError(f"{doc['id']}: 'between' needs a [lo, hi] target")
            target: float | tuple[float, float] = (float(tgt[0]), float(tgt[1]))
        else:
            target = float(tgt)
        metrics.append(
            Metric(
                m["name"],
                m["op"],
                target,
                None if m.get("golden") is None else float(m["golden"]),
                None if m.get("golden_tol") is None else float(m["golden_tol"]),
            )
        )
    if not metrics:
        raise ValueError(f"{doc['id']}: case needs at least one metric")
    data = tuple(DataRef(d["name"], d["path"], d["sha256"]) for d in doc.get("data", []))
    return Case(
        doc["id"],
        doc["model"],
        doc["kind"],
        doc["suite"],
        doc["function"],
        doc["source"],
        int(doc.get("seed", 0)),
        data,
        dict(doc.get("settings", {})),
        tuple(metrics),
        bool(doc.get("qualitative", False)),
        str(doc.get("notes", "")),
    )


def registry_gaps(cases: Iterable[Case]) -> dict[str, list[str]]:
    """Kinds each model is missing. Every model needs a simulation case, a parity case and a
    published-result or regression case."""
    have: dict[str, set[str]] = {m: set() for m in MODELS}
    for c in cases:
        have[c.model].add("published" if c.kind == "regression" else c.kind)
    need = ("simulation", "parity", "published")
    return {
        m: [k for k in need if k not in got]
        for m, got in have.items()
        if any(k not in got for k in need)
    }


@dataclass(frozen=True)
class MetricResult:
    metric: Metric
    observed: float
    passed: bool
    golden_passed: bool | None
    message: str


@dataclass(frozen=True)
class CaseResult:
    case: Case
    metrics: tuple[MetricResult, ...] = field(default_factory=tuple)
    error: str = ""
    seconds: float = 0.0

    @property
    def passed(self) -> bool:
        return not self.error and all(
            m.passed and m.golden_passed is not False for m in self.metrics
        )


def check_metric(m: Metric, observed: float) -> MetricResult:
    tgt = m.target
    if isinstance(tgt, tuple):
        lo, hi = tgt
        ok = lo <= observed <= hi
        rule = f"in [{lo:g}, {hi:g}]"
    elif m.op == "<=":
        ok = observed <= tgt
        rule = f"<= {tgt:g}"
    else:
        ok = observed >= tgt
        rule = f">= {tgt:g}"
    golden_ok = None
    msg = f"{m.name} = {observed:.6g}, needs {rule}"
    if m.golden is not None:
        tol = m.golden_tol if m.golden_tol is not None else 0.0
        golden_ok = abs(observed - m.golden) <= tol
        msg += f"; pinned {m.golden:.6g} +/- {tol:g}"
    return MetricResult(m, float(observed), bool(ok), golden_ok, msg)


def evaluate(case: Case, observed: Mapping[str, float], seconds: float = 0.0) -> CaseResult:
    out: list[MetricResult] = []
    for m in case.metrics:
        if m.name not in observed:
            return CaseResult(case, tuple(out), f"case function did not return '{m.name}'", seconds)
        out.append(check_metric(m, observed[m.name]))
    return CaseResult(case, tuple(out), "", seconds)
