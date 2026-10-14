"""Core is tested against known answers, never live data."""

from __future__ import annotations

import pytest

from csuf_fullerton.core.greeting import greet


def test_greet_trims_and_formats() -> None:
    assert greet("  JJ ") == "Hello, JJ."


def test_greet_rejects_empty() -> None:
    with pytest.raises(ValueError, match="empty"):
        greet("")
