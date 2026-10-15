"""The FRED key never reaches fetched data, source records or run records (secret scanning)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from typer.testing import CliRunner

from csuf_fullerton.cli.main import app

KEY = "zq" * 16  # fake 32-character key, built at runtime so secret scanners skip it


def test_key_not_written_to_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from csuf_fullerton.data.adapters import fred, imf

    monkeypatch.setenv("FRED_API_KEY", KEY)
    seen: list[str | None] = []

    def fake_fred(
        series_id: str, api_key: str | None, frequency: str | None = None
    ) -> dict[str, float]:
        seen.append(api_key)
        return {"2000-01-01": math.e, "2000-02-01": 1.0, "2000-03-01": 2.0}

    monkeypatch.setattr(fred, "fetch_series", fake_fred)
    monkeypatch.setattr(imf, "fetch_series", lambda *a, **k: {"2000-01-01": 5.0})
    recipe = tmp_path / "r.toml"
    recipe.write_text(
        '[meta]\nfrequency = "M"\nstart = "2000-01"\nend = "2000-03"\n'
        '[[series]]\nname = "a"\nsource = "fred"\nid = "A"\n'
        '[[series]]\nname = "b"\nsource = "imf"\ndataflow = "CPI"\nfilters = { COUNTRY = "NIC" }\n'
    )
    out = tmp_path / "d.csv"
    res = CliRunner().invoke(app, ["fetch", str(recipe), "--out", str(out)])
    assert res.exit_code == 0, res.stdout
    assert seen == [KEY]  # the key was used
    for f in tmp_path.iterdir():
        assert KEY not in f.read_text(errors="ignore"), f.name
    assert KEY not in res.stdout
