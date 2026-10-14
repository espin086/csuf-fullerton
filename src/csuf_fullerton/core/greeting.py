"""Example pure function. Delete once the project has real logic."""

from __future__ import annotations


def greet(name: str) -> str:
    """Return a greeting. Raises ``ValueError`` on an empty name."""
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("name must not be empty")
    return f"Hello, {cleaned}."
