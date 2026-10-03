"""Architecture rules as tests. Fails the build; never relies on review.

Rule: ``core/`` is pure. It may not import I/O, logging, network, env, or
adapter modules. Extend ``FORBIDDEN_IN_CORE`` as the project grows.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "project_template"
CORE = SRC / "core"

FORBIDDEN_IN_CORE = {
    "os",
    "sys",
    "io",
    "logging",
    "pathlib",
    "subprocess",
    "socket",
    "http",
    "urllib",
    "requests",
    "httpx",
    "typer",
    "rich",
    "project_template.cli",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.parametrize("path", sorted(CORE.rglob("*.py")), ids=lambda p: p.name)
def test_core_has_no_io_imports(path: Path) -> None:
    bad = {
        name
        for name in _imports(path)
        if name in FORBIDDEN_IN_CORE or name.split(".")[0] in FORBIDDEN_IN_CORE
    }
    assert not bad, f"{path.relative_to(SRC)} imports I/O into core: {sorted(bad)}"


def test_cli_does_not_define_business_logic() -> None:
    """Adapters may only call into core. A CLI module with no core import is
    a smell: it is probably computing something itself."""
    main = SRC / "cli" / "main.py"
    assert any(n.startswith("project_template.core") for n in _imports(main))
