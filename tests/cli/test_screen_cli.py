"""End-to-end CLI runs on a simulated CSV."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from csuf_fullerton.cli.main import app
from tests.core.svar.sim import block_dgp

runner = CliRunner()

THEORY = """
[meta]
country = "Sim"
deterministic = { trend = false, seasonal = true }

[[variable]]
name = "f1"
prior = "exogenous"
[[variable]]
name = "f2"
prior = "candidate"
[[variable]]
name = "d1"
prior = "endogenous"
[[variable]]
name = "d2"
prior = "endogenous"
[[variable]]
name = "d3"
prior = "endogenous"

[[headline]]
response = "d1"
shock = "f1"
"""


def _csv(tmp_path: Path) -> Path:
    d = block_dgp(n=240, seed=0)
    df = pd.DataFrame(d.values, columns=list(d.names))
    df.insert(0, "date", pd.date_range("2000-01-01", periods=240, freq="MS").strftime("%Y-%m"))
    path = tmp_path / "sim.csv"
    df.to_csv(path, index=False)
    return path


def test_screen_end_to_end(tmp_path: Path) -> None:
    data = _csv(tmp_path)
    theory = tmp_path / "theory.toml"
    theory.write_text(THEORY)
    out = tmp_path / "screen"
    result = runner.invoke(
        app, ["screen", str(data), str(theory), "--out", str(out), "--max-lags", "2"]
    )
    assert result.exit_code == 0, result.stdout
    assert "Recommended foreign block: f1, f2" in result.stdout
    for name in ("screen.md", "candidates.csv", "run.json", "granger.png", "robust_d1_f1.png"):
        assert (out / name).is_file()
    run = json.loads((out / "run.json").read_text())
    assert run["recommended"]["foreign"] == ["f1", "f2"] and len(run["data_sha256"]) == 64


def test_end_to_end_on_fixture_csv(tmp_path: Path) -> None:
    data = _csv(tmp_path)
    out = tmp_path / "svar"
    args = [
        "svar",
        str(data),
        "--foreign",
        "f1,f2",
        "--domestic",
        "d1,d2,d3",
        "--lags",
        "1",
        "--no-trend",
        "--draws",
        "50",
        "--out",
        str(out),
    ]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.stdout
    irf = pd.read_csv(out / "irf.csv")
    foreign_to_domestic = irf[irf.response.isin(["f1", "f2"]) & irf.shock.isin(["d1", "d2", "d3"])]
    assert (foreign_to_domestic.irf == 0).all()
    first = json.loads((out / "run.json").read_text())
    runner.invoke(app, args)
    second = json.loads((out / "run.json").read_text())
    assert first["tests"] == second["tests"]
    assert pd.read_csv(out / "irf.csv").equals(irf)


def test_svar_unknown_column_is_usage_error(tmp_path: Path) -> None:
    data = _csv(tmp_path)
    result = runner.invoke(
        app,
        ["svar", str(data), "--foreign", "zz", "--domestic", "d1", "--out", str(tmp_path / "o")],
    )
    assert result.exit_code == 2


def test_restriction_rejected_warns(tmp_path: Path) -> None:
    d = block_dgp(n=400, seed=1, feedback=0.4)
    df = pd.DataFrame(d.values, columns=list(d.names))
    df.insert(0, "date", pd.date_range("1990-01-01", periods=400, freq="MS").strftime("%Y-%m"))
    data = tmp_path / "fb.csv"
    df.to_csv(data, index=False)
    args = [
        "svar",
        str(data),
        "--foreign",
        "f1,f2",
        "--domestic",
        "d1,d2,d3",
        "--lags",
        "1",
        "--no-trend",
        "--draws",
        "20",
        "--out",
        str(tmp_path / "o"),
    ]
    result = runner.invoke(app, args)
    assert result.exit_code == 0
    assert "block exogeneity rejected" in result.stdout and "LR p" in result.stdout
    assert "still imposed" in (tmp_path / "o" / "svar.md").read_text()
