"""Print the CHANGELOG.md section for one version (used as release notes).

Usage: python changelog_section.py 1.2.3 > notes.md
Exits 1 if the section is missing, so a release never ships with empty notes.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parents[2] / "CHANGELOG.md"


def section(version: str, text: str) -> str | None:
    pattern = re.compile(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)",
        re.M | re.S,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: changelog_section.py <version>", file=sys.stderr)
        return 2
    body = section(sys.argv[1], CHANGELOG.read_text())
    if not body:
        print(f"::error::CHANGELOG.md has no section for {sys.argv[1]}", file=sys.stderr)
        return 1
    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
