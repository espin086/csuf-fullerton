"""Packaging invariants: version format and pyproject coherence."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from csuf_fullerton import __version__

REPO_ROOT = Path(__file__).resolve().parents[1]

# Must match VERSION_RE in .github/scripts/check_release.py.
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?(?:\.dev\d+)?$")


def test_version_is_semver() -> None:
    assert VERSION_RE.match(__version__), __version__


def test_version_regex_matches_release_script() -> None:
    script = (REPO_ROOT / ".github" / "scripts" / "check_release.py").read_text()
    assert VERSION_RE.pattern in script


def test_pyproject_points_at_about() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    assert data["tool"]["hatch"]["version"]["path"] == "src/csuf_fullerton/__about__.py"
    assert data["project"]["name"] == "csuf-fullerton"


def test_changelog_mentions_current_version() -> None:
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text()
    assert f"## [{__version__}]" in changelog, (
        f"CHANGELOG.md has no section for {__version__}; add one before releasing"
    )
