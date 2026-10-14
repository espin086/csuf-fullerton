"""End-to-end tvsvar, trade-weights and replicate commands on simulated data."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from csuf_fullerton.cli.main import app
from csuf_fullerton.core.tvsvar.simulate import tw_dgp, tw_weights

runner = CliRunner()
NAMES = ["g", "us", "cn", "d1", "d2"]
BLOCKS = ["--foreign", "g,us,cn", "--domestic", "d1,d2"]


@pytest.fixture(scope="module")
def files(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    d = tmp_path_factory.mktemp("tv")
    y, _ = tw_dgp(240, 5)
    dates = pd.period_range("2001-01", periods=240, freq="M").astype(str)
    df = pd.DataFrame(y, columns=NAMES)
    df.insert(0, "date", dates)
    data = d / "sim.csv"
    df.to_csv(data, index=False)
    w = tw_weights(25)
    rows = []
    for i, yr in enumerate(range(1998, 2023)):
        rows += [
            {"year": yr, "partner": "world", "value": 100.0},
            {"year": yr, "partner": "us", "value": 100 * w[i, 0]},
            {"year": yr, "partner": "cn", "value": 100 * w[i, 1]},
        ]
    trade = d / "trade.csv"
    pd.DataFrame(rows).to_csv(trade, index=False)
    return data, trade


def _run(args: list[str]) -> None:
    res = runner.invoke(app, args)
    assert res.exit_code == 0, res.stdout


def test_end_to_end_on_fixture_csv(files: tuple[Path, Path], tmp_path: Path) -> None:
    data, trade = files
    common = [str(data), *BLOCKS, "--lags", "1", "--headline", "d1:cn,d1:us", "--draws", "20"]
    _run(
        [
            "tvsvar",
            *common,
            "--model",
            "m1",
            "--trade",
            str(trade),
            "--partners",
            "us=us,cn=cn",
            "--frozen-years",
            "2002,2020",
            "--lr-draws",
            "9",
            "--out",
            str(tmp_path / "m1"),
        ]
    )
    rec = json.loads((tmp_path / "m1" / "run.json").read_text())
    assert rec["trade_sha256"] and "frozen_weights" in rec
    assert (tmp_path / "m1" / "frozen_irf.png").exists()
    irf = pd.read_csv(tmp_path / "m1" / "irf.csv")
    assert {"irf_2002", "diff_2020_2002"} <= set(irf.columns)
    assert irf[(irf.response == "g") & (irf.shock == "d1")]["irf_2020"].abs().max() == 0.0
    _run(
        [
            "tvsvar",
            *common,
            "--model",
            "m0",
            "--break",
            "2010-01",
            "--break-draws",
            "9",
            "--out",
            str(tmp_path / "m0"),
        ]
    )
    assert "Parameter stability" in (tmp_path / "m0" / "m0.md").read_text()
    _run(
        [
            "tvsvar",
            *common,
            "--model",
            "m2",
            "--trade",
            str(trade),
            "--partners",
            "us=us,cn=cn",
            "--bandwidth-exp",
            "0.8",
            "--kernel-step",
            "20",
            "--out",
            str(tmp_path / "m2"),
        ]
    )
    assert (tmp_path / "m2" / "kernel_path.csv").exists()
    _run(
        [
            "tvsvar",
            str(data),
            *BLOCKS,
            "--model",
            "m3",
            "--m3-vars",
            "cn,d1",
            "--m3-lags",
            "1",
            "--m3-yoy",
            "d1",
            "--mcmc-draws",
            "120",
            "--burn",
            "40",
            "--thin",
            "2",
            "--headline",
            "d1:cn",
            "--irf-dates",
            "2010-06",
            "--out",
            str(tmp_path / "m3"),
        ]
    )
    assert "MCMC diagnostics" in (tmp_path / "m3" / "m3.md").read_text()


def test_rerun_from_run_json(files: tuple[Path, Path], tmp_path: Path) -> None:
    data, trade = files
    args = [
        str(data),
        *BLOCKS,
        "--lags",
        "1",
        "--model",
        "m1",
        "--trade",
        str(trade),
        "--partners",
        "us=us,cn=cn",
        "--frozen-years",
        "2002,2020",
        "--draws",
        "15",
        "--lr-draws",
        "0",
        "--headline",
        "d1:cn",
    ]
    _run(["tvsvar", *args, "--out", str(tmp_path / "a")])
    _run(["tvsvar", *args, "--out", str(tmp_path / "b")])
    a, b = pd.read_csv(tmp_path / "a" / "irf.csv"), pd.read_csv(tmp_path / "b" / "irf.csv")
    pd.testing.assert_frame_equal(a, b)


def test_cli_errors(files: tuple[Path, Path], tmp_path: Path) -> None:
    data, trade = files
    assert runner.invoke(app, ["tvsvar", str(data), *BLOCKS, "--model", "m9"]).exit_code == 2
    assert runner.invoke(app, ["tvsvar", str(data), *BLOCKS, "--model", "m1"]).exit_code == 2
    r = runner.invoke(
        app,
        [
            "tvsvar",
            str(data),
            *BLOCKS,
            "--model",
            "m1",
            "--trade",
            str(trade),
            "--partners",
            "us=us,cn=cn",
            "--frozen-years",
            "1990,2020",
            "--lags",
            "1",
        ],
    )
    assert r.exit_code == 5 and "1990" in r.stdout
    assert runner.invoke(app, ["tvsvar", str(data), *BLOCKS, "--partners", "oops"]).exit_code == 2
    assert runner.invoke(app, ["tvsvar", str(data), *BLOCKS, "--headline", "x"]).exit_code == 2


def test_hash_mismatch_fails(tmp_path: Path) -> None:
    cases = tmp_path / "cases"
    cases.mkdir()
    (tmp_path / "f.csv").write_text("date,a\n2000-01,1\n")
    (cases / "a.toml").write_text(
        'id = "a"\nmodel = "m0"\nkind = "parity"\nsuite = "fast"\nfunction = "m3_parity_kalman"\n'
        'source = "t"\n[[data]]\nname = "d"\npath = "f.csv"\nsha256 = "' + "0" * 64 + '"\n'
        '[settings]\nn = 40\n[[metric]]\nname = "max_abs_diff"\nop = "<="\ntarget = 1e-8\n'
    )
    for m in ("m1", "m2", "m3"):
        for kind in ("simulation", "parity", "published"):
            (cases / f"{m}{kind}.toml").write_text(
                f'id = "{m}{kind}"\nmodel = "{m}"\nkind = "{kind}"\nsuite = "full"\n'
                'function = "m3_parity_kalman"\nsource = "t"\n[settings]\nn = 40\n'
                '[[metric]]\nname = "max_abs_diff"\nop = "<="\ntarget = 1e-8\n'
            )
    (cases / "m0sim.toml").write_text(
        (cases / "m1simulation.toml")
        .read_text()
        .replace('"m1simulation"', '"m0sim"')
        .replace('model = "m1"', 'model = "m0"')
    )
    (cases / "m0pub.toml").write_text(
        (cases / "m1published.toml")
        .read_text()
        .replace('"m1published"', '"m0pub"')
        .replace('model = "m1"', 'model = "m0"')
    )
    r = runner.invoke(
        app,
        ["replicate", "--cases", str(cases), "--root", str(tmp_path), "--out", str(tmp_path / "o")],
    )
    assert r.exit_code == 1 and "hash mismatch" in r.stdout
    card = json.loads((tmp_path / "o" / "scorecard.json").read_text())
    assert card["passed"] is False and card["cases"][0]["error"].startswith("fixture hash")
    assert "FAIL" in (tmp_path / "o" / "replication.md").read_text()
    ok = runner.invoke(
        app,
        [
            "replicate",
            "--cases",
            str(cases),
            "--suite",
            "full",
            "--case",
            "m1parity",
            "--root",
            str(tmp_path),
            "--out",
            str(tmp_path / "o2"),
        ],
    )
    assert ok.exit_code == 0, ok.stdout
    assert runner.invoke(app, ["replicate", "--cases", str(cases), "--list"]).exit_code == 0
    (cases / "m3published.toml").unlink()
    assert runner.invoke(app, ["replicate", "--cases", str(cases), "--list"]).exit_code == 1


def test_trade_weights_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from csuf_fullerton.data.adapters import imf

    rows = []
    for yr in ("2000", "2001"):
        for code, v in (("USA", 10.0), ("CHN", 5.0), ("G001", 100.0)):
            for ind in ("XG_FOB_USD", "MG_CIF_USD", "TBG_USD"):
                rows.append(
                    {
                        "INDICATOR": ind,
                        "COUNTERPART_COUNTRY": code,
                        "TIME_PERIOD": yr,
                        "OBS_VALUE": str(v),
                    }
                )
    rows.append(
        {
            "INDICATOR": "XG_FOB_USD",
            "COUNTERPART_COUNTRY": "ARG",
            "TIME_PERIOD": "2000",
            "OBS_VALUE": "1",
        }
    )
    monkeypatch.setattr(imf, "fetch_rows", lambda *a, **k: rows)
    out = tmp_path / "t.csv"
    _run(["trade-weights", "--country", "BRA", "--partners", "us=USA,cn=CHN", "--out", str(out)])
    df = pd.read_csv(out)
    assert set(df.partner) == {"us", "cn", "world"} and np.allclose(
        df[df.partner == "us"].value, 20.0
    )
    assert json.loads(out.with_suffix(".sources.json").read_text())["partners"] == {
        "us": "USA",
        "cn": "CHN",
    }
    monkeypatch.setattr(imf, "fetch_rows", lambda *a, **k: [])
    assert (
        runner.invoke(
            app, ["trade-weights", "--country", "BRA", "--partners", "us=USA", "--out", str(out)]
        ).exit_code
        == 4
    )
