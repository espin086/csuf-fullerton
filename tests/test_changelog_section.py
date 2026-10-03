"""changelog_section.py extracts exactly one version's notes."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "changelog_section.py"
spec = importlib.util.spec_from_file_location("changelog_section", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

TEXT = """# Changelog

## [Unreleased]

- pending

## [1.2.0] - 2026-02-01

### Added
- feature

## [1.1.0] - 2026-01-01

- old
"""


def test_extracts_middle_section() -> None:
    assert mod.section("1.2.0", TEXT) == "### Added\n- feature"


def test_extracts_last_section() -> None:
    assert mod.section("1.1.0", TEXT) == "- old"


def test_missing_is_none() -> None:
    assert mod.section("9.9.9", TEXT) is None
