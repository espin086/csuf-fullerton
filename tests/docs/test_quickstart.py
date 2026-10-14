"""Every csuf-fullerton command in QUICKSTART.md parses against the real CLI (task 14)."""

from __future__ import annotations

import shlex
from pathlib import Path

import pytest
import typer

from csuf_fullerton.cli.main import app

ROOT = Path(__file__).resolve().parents[2]


def _commands() -> list[str]:
    text = (ROOT / "QUICKSTART.md").read_text()
    blocks = text.split("```")[1::2]
    return [
        ln.split("#")[0].strip()
        for b in blocks
        for ln in b.splitlines()
        if ln.strip().startswith("csuf-fullerton ")
    ]


def test_quickstart_has_commands() -> None:
    cmds = _commands()
    assert any(c.startswith("csuf-fullerton tvsvar") for c in cmds)
    assert any(c.startswith("csuf-fullerton svar") for c in cmds)
    assert any(c.startswith("csuf-fullerton replicate") for c in cmds)


@pytest.mark.parametrize("cmd", _commands())
def test_every_command_in_quickstart_parses(cmd: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    args = shlex.split(cmd)[1:]
    if args == ["--version"]:
        return
    commands = typer.main.get_command(app).commands  # type: ignore[attr-defined]
    sub = commands.get(args[0])
    assert sub is not None, f"unknown command {args[0]}"
    sub.make_context(args[0], args[1:])  # raises on an unknown option or a missing file


def test_reproduce_scripts_reference_real_options() -> None:
    commands = typer.main.get_command(app).commands  # type: ignore[attr-defined]
    known = {o for c in commands.values() for p in c.params for o in p.opts + p.secondary_opts}
    for script in ("reproduce_brazil.sh", "reproduce_nicaragua.sh"):
        text = (ROOT / "scripts" / script).read_text()
        flags = {
            tok
            for tok in shlex.split(text.replace("\\\n", " "), comments=True)
            if tok.startswith("--")
        }
        assert flags, script
        unknown = sorted(f for f in flags if f not in known)
        assert not unknown, f"{script}: unknown options {unknown}"
