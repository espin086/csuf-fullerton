"""Simulated processes with known answers, shared by the SVAR tests."""

from __future__ import annotations

import numpy as np

from csuf_fullerton.core.svar.data import Dataset

NAMES = ("f1", "f2", "d1", "d2", "d3")


A_TRUE = np.array(
    [
        [0.5, 0.1, 0.0, 0.0, 0.0],
        [0.0, 0.4, 0.0, 0.0, 0.0],
        [0.3, 0.0, 0.5, 0.1, 0.0],
        [0.0, 0.2, 0.1, 0.4, 0.0],
        [0.1, 0.1, 0.0, 0.2, 0.3],
    ]
)
B0_TRUE = np.array(
    [
        [1.0, 0.0, 0.0, 0.0, 0.0],
        [0.3, 1.0, 0.0, 0.0, 0.0],
        [0.5, 0.2, 1.0, 0.0, 0.0],
        [0.0, 0.3, 0.4, 1.0, 0.0],
        [0.2, 0.0, 0.1, 0.3, 1.0],
    ]
)


def true_irf(horizon: int) -> np.ndarray:
    """Recursive IRFs of the no-feedback process: chol(B0 B0') = B0 (unit-variance shocks)."""
    return np.stack([np.linalg.matrix_power(A_TRUE, h) @ B0_TRUE for h in range(horizon + 1)])


def block_dgp(
    n: int = 300, seed: int = 0, feedback: float = 0.0, unit_root: bool = False
) -> Dataset:
    """VAR(1) with foreign block (f1, f2) exogenous unless ``feedback`` != 0, in which case
    d1 feeds f1 with that lag coefficient. Laplace shocks so residuals are non-Gaussian."""
    rng = np.random.default_rng(seed)
    a = A_TRUE.copy()
    a[0, 2] = feedback
    b0 = B0_TRUE
    e = rng.laplace(size=(n + 100, 5)) / np.sqrt(2)
    y = np.zeros((n + 100, 5))
    for t in range(1, n + 100):
        y[t] = a @ y[t - 1] + b0 @ e[t]
    if unit_root:
        y = np.cumsum(y, axis=0)
    y = y[100:]
    dates = tuple(f"t{i}" for i in range(n))
    return Dataset(NAMES, y, dates)


def theory_doc(trend: bool = False) -> dict[str, object]:
    return {
        "meta": {"country": "Sim", "deterministic": {"trend": trend, "seasonal": False}},
        "variable": [
            {"name": "f1", "prior": "exogenous"},
            {"name": "f2", "prior": "candidate"},
            {"name": "d1", "prior": "candidate"},
            {"name": "d2", "prior": "endogenous"},
            {"name": "d3", "prior": "endogenous"},
        ],
        "candidates": {"min_foreign": 1, "max_foreign": 3},
        "ordering": [{"domestic": ["d3", "d2", "d1"]}],
        "headline": [{"response": "d1", "shock": "f1"}],
    }
