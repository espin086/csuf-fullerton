"""Theory file parsing, candidate enumeration and grades."""

from __future__ import annotations

import pytest

from csuf_fullerton.core.svar.theory import enumerate_specs, parse_theory, theory_grade


def _doc() -> dict[str, object]:
    return {
        "meta": {"country": "X"},
        "variable": [
            {"name": "a", "prior": "exogenous"},
            {"name": "b", "prior": "exogenous"},
            {"name": "c", "prior": "candidate"},
            {"name": "d1", "prior": "endogenous"},
            {"name": "d2", "prior": "endogenous"},
            {"name": "d3", "prior": "endogenous"},
            {"name": "d4", "prior": "endogenous"},
        ],
        "candidates": {"min_foreign": 1, "max_foreign": 3},
    }


def test_enumeration_respects_priors_and_size_bounds() -> None:
    specs = enumerate_specs(parse_theory(_doc()))
    assert len(specs) == 7
    assert all(not {"d1", "d2", "d3", "d4"} & set(s.foreign) for s in specs)
    assert all(
        set(s.foreign) | set(s.domestic) == {"a", "b", "c", "d1", "d2", "d3", "d4"} for s in specs
    )


def test_explicit_endogenous_spec_is_inadmissible() -> None:
    doc = _doc() | {"spec": [{"name": "odd", "foreign": ["a", "b", "d1"]}]}
    theory = parse_theory(doc)
    odd = next(s for s in enumerate_specs(theory) if s.name == "odd")
    assert theory_grade(theory, odd)[0] == "X"


def test_grades() -> None:
    theory = parse_theory(_doc())
    by = {s.foreign: s for s in enumerate_specs(theory)}
    assert theory_grade(theory, by[("a", "b")])[0] == "A"
    assert theory_grade(theory, by[("a", "b", "c")])[0] == "A"
    assert theory_grade(theory, by[("a", "c")])[0] == "B"


def test_bad_prior_rejected() -> None:
    doc = _doc()
    doc["variable"] = [{"name": "a", "prior": "maybe"}, {"name": "b", "prior": "endogenous"}]
    with pytest.raises(ValueError, match="prior"):
        parse_theory(doc)


def test_spec_must_split_every_variable() -> None:
    doc = _doc() | {"spec": [{"foreign": ["a"], "domestic": ["b"]}]}
    with pytest.raises(ValueError, match="exactly once"):
        parse_theory(doc)
