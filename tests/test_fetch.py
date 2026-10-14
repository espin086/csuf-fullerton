"""Recipe parsing, transforms and alignment (no network)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from typer.testing import CliRunner

from csuf_fullerton.cli.main import app
from csuf_fullerton.core.recipe import assemble, month_range, parse_recipe
from csuf_fullerton.data.adapters import imf

RECIPE = {
    "meta": {"frequency": "M", "start": "2000-01", "end": "2000-03"},
    "series": [
        {"name": "a", "source": "fred", "id": "A", "transform": "log"},
        {"name": "b", "source": "imf", "dataflow": "CPI", "filters": {"COUNTRY": "NIC"}},
    ],
}


def test_transforms_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from csuf_fullerton.data.adapters import fred

    monkeypatch.setenv("FRED_API_KEY", "")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr("csuf_fullerton.data.credentials._keyring_usable", lambda: False)
    monkeypatch.setattr(
        fred, "fetch_series", lambda *a, **k: {"2000-01-01": math.e, "2000-02-01": 1.0}
    )
    monkeypatch.setattr(imf, "fetch_series", lambda *a, **k: {"2000-01-01": 5.0, "2000-03-01": 7.0})
    recipe = tmp_path / "r.toml"
    recipe.write_text(
        '[meta]\nfrequency = "M"\nstart = "2000-01"\nend = "2000-03"\n'
        '[[series]]\nname = "a"\nsource = "fred"\nid = "A"\ntransform = "log"\n'
        '[[series]]\nname = "b"\nsource = "imf"\ndataflow = "CPI"\nfilters = { COUNTRY = "NIC" }\n'
    )
    out = tmp_path / "d.csv"
    result = CliRunner().invoke(app, ["fetch", str(recipe), "--out", str(out)])
    assert result.exit_code == 0, result.stdout
    lines = out.read_text().splitlines()
    assert lines[0] == "date,a,b"
    assert lines[1].startswith("2000-01,1.0,5.0")
    meta = json.loads(out.with_suffix(".sources.json").read_text())
    assert meta["series"][0]["transform"] == "log"
    assert meta["fred_access"] == "fredgraph"


def test_assemble_aligns_and_fills_missing() -> None:
    rec = parse_recipe(RECIPE)
    dates, rows = assemble(rec, {"a": {"2000-02-01": 1.0}, "b": {"2000-01-01": 2.0}})
    assert dates == ["2000-01", "2000-02", "2000-03"]
    assert math.isnan(rows[0][0]) and rows[1][0] == 0.0 and rows[0][1] == 2.0


def test_month_range_crosses_year() -> None:
    assert month_range("1999-11", "2000-02") == ["1999-11", "1999-12", "2000-01", "2000-02"]


def test_bad_transform() -> None:
    bad = {"meta": {}, "series": [{"name": "a", "source": "fred", "transform": "sqrt"}]}
    with pytest.raises(ValueError, match="transform"):
        parse_recipe(bad)


def test_imf_select_series_requires_unique_match() -> None:
    rows = [
        {"TIME_PERIOD": "2000-M01", "OBS_VALUE": "1", "COUNTRY": "NIC", "X": "a"},
        {"TIME_PERIOD": "2000-M01", "OBS_VALUE": "2", "COUNTRY": "NIC", "X": "b"},
    ]
    assert imf.select_series(rows, {"X": "b"}, "t") == {"2000-01-01": 2.0}
    with pytest.raises(ValueError, match="several series"):
        imf.select_series(rows, {"COUNTRY": "NIC"}, "t")


@pytest.mark.network
def test_live_fred_keyless() -> None:
    from csuf_fullerton.data.adapters import fred

    assert len(fred.fetch_series("FEDFUNDS", None)) > 500
