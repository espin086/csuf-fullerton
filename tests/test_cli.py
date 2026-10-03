"""CLI adapter tests. Behaviour lives in core; these check wiring only."""

from __future__ import annotations

from typer.testing import CliRunner

from project_template import __version__
from project_template.cli.main import app

runner = CliRunner()


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_hello_default() -> None:
    result = runner.invoke(app, ["hello"])
    assert result.exit_code == 0
    assert "Hello, world." in result.stdout


def test_hello_empty_name_is_usage_error() -> None:
    result = runner.invoke(app, ["hello", "   "])
    assert result.exit_code == 2
