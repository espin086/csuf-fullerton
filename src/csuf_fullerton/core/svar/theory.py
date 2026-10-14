"""Theory file: prior role of each variable, candidate enumeration and theory grades.

Grades (design.md section 4, stage 5):

* ``A`` every ``exogenous`` variable is foreign, the rest of the foreign block is ``candidate``.
* ``B`` foreign block is admissible but leaves at least one ``exogenous`` variable domestic.
* ``X`` an ``endogenous`` variable is in the foreign block. Reported, never ranked.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

PRIORS = ("exogenous", "candidate", "endogenous")


@dataclass(frozen=True)
class Variable:
    name: str
    prior: str
    rationale: str = ""
    source: str = ""


@dataclass(frozen=True)
class Spec:
    name: str
    foreign: tuple[str, ...]
    domestic: tuple[str, ...]
    explicit: bool = False


@dataclass(frozen=True)
class Headline:
    response: str
    shock: str


@dataclass(frozen=True)
class Theory:
    country: str
    variables: tuple[Variable, ...]
    min_foreign: int = 1
    max_foreign: int = 4
    trend: bool = True
    seasonal: bool = False
    orderings: tuple[tuple[str, ...], ...] = ()
    headlines: tuple[Headline, ...] = ()
    explicit: tuple[Spec, ...] = field(default_factory=tuple)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(v.name for v in self.variables)

    def prior(self, name: str) -> str:
        return next(v.prior for v in self.variables if v.name == name)


def parse_theory(doc: Mapping[str, Any]) -> Theory:
    """Build a Theory from the parsed TOML mapping (see design.md section 3)."""
    meta = doc.get("meta", {})
    det = meta.get("deterministic", {})
    variables = []
    for v in doc.get("variable", []):
        if v.get("prior") not in PRIORS:
            raise ValueError(f"variable {v.get('name')!r}: prior must be one of {PRIORS}")
        variables.append(
            Variable(v["name"], v["prior"], v.get("rationale", ""), v.get("source", ""))
        )
    names = [v.name for v in variables]
    if len(set(names)) != len(names) or len(names) < 2:
        raise ValueError("theory file needs at least two uniquely named variables")
    cand = doc.get("candidates", {})
    explicit = []
    for s in doc.get("spec", []):
        foreign = tuple(s["foreign"])
        domestic = tuple(s.get("domestic", [n for n in names if n not in foreign]))
        if set(foreign) | set(domestic) != set(names) or set(foreign) & set(domestic):
            raise ValueError(f"spec {s.get('name')!r} must split every variable exactly once")
        explicit.append(Spec(s.get("name", "+".join(foreign)), foreign, domestic, True))
    orderings = tuple(tuple(o["domestic"]) for o in doc.get("ordering", []))
    heads = tuple(Headline(h["response"], h["shock"]) for h in doc.get("headline", []))
    for h in heads:
        if h.response not in names or h.shock not in names:
            raise ValueError(f"headline {h} names an unknown variable")
    return Theory(
        meta.get("country", ""),
        tuple(variables),
        int(cand.get("min_foreign", 1)),
        int(cand.get("max_foreign", 4)),
        bool(det.get("trend", True)),
        bool(det.get("seasonal", False)),
        orderings,
        heads,
        tuple(explicit),
    )


def enumerate_specs(theory: Theory) -> list[Spec]:
    """Every subset of foreign-eligible variables within the size bounds, plus explicit specs.
    Foreign and domestic blocks keep the file order."""
    eligible = [v.name for v in theory.variables if v.prior != "endogenous"]
    specs: list[Spec] = []
    upper = min(theory.max_foreign, len(eligible), len(theory.variables) - 1)
    for size in range(theory.min_foreign, upper + 1):
        for combo in combinations(eligible, size):
            dom = tuple(n for n in theory.names if n not in combo)
            specs.append(Spec("+".join(combo), combo, dom))
    seen = {s.foreign for s in specs}
    specs.extend(s for s in theory.explicit if s.foreign not in seen)
    return specs


def theory_grade(theory: Theory, spec: Spec) -> tuple[str, str]:
    """Return (grade, reason)."""
    endo = [n for n in spec.foreign if theory.prior(n) == "endogenous"]
    if endo:
        return "X", f"endogenous by theory but placed foreign: {', '.join(endo)}"
    missing = [n for n in spec.domestic if theory.prior(n) == "exogenous"]
    if missing:
        return "B", f"exogenous by theory but placed domestic: {', '.join(missing)}"
    extra = [n for n in spec.foreign if theory.prior(n) == "candidate"]
    if extra:
        return "A", f"all exogenous variables foreign; candidates added: {', '.join(extra)}"
    return "A", "foreign block is exactly the exogenous-by-theory set"
