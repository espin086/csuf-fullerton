"""Rename the template package after `Use this template`.

    python scripts/rename.py my-project

Replaces `project-template` and `project_template`
across tracked files and moves `src/project_template/`. Idempotent; run once.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = (".git/", "scripts/rename.py")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    dist = sys.argv[1].lower()
    if not re.fullmatch(r"[a-z][a-z0-9-]*", dist):
        print("name must be lowercase kebab-case")
        return 2
    pkg = dist.replace("-", "_")
    files = subprocess.run(
        ["git", "ls-files"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout.splitlines()
    changed = 0
    for rel in files:
        if rel.startswith(SKIP) or not (ROOT / rel).is_file():
            continue
        path = ROOT / rel
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        new = text.replace("project_template", pkg).replace("project-template", dist)
        if new != text:
            path.write_text(new)
            changed += 1
    src = ROOT / "src" / "project_template"
    if src.exists():
        src.rename(ROOT / "src" / pkg)
    print(f"renamed to {dist} ({pkg}); {changed} files edited. Review `git diff`, then commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
