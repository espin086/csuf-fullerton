"""PR policy gates. Exit 1 with ``::error::`` lines on any failure.

Env: BASE_SHA, HEAD_SHA, PR_TITLE, PR_LABELS (comma-separated), PR_BODY, PR_AUTHOR,
LINKED_ISSUES (GitHub's closingIssuesReferences count; empty when unavailable).

Gates
-----
1. openspec: a PR that touches "major" paths (src/, Dockerfile, .github/,
   pyproject.toml, .claude/) must also touch openspec/changes/** unless it
   carries the ``skip-openspec`` label.
2. changelog: a PR that touches src/ must touch CHANGELOG.md unless labelled
   ``skip-changelog``.
3. version: if src/<pkg>/__about__.py changed, CHANGELOG.md must contain a
   ``## [<new version>]`` heading.
4. title: Conventional Commits, ``type(scope)?: summary``.
5. issue: the PR closes a GitHub issue. GitHub's closingIssuesReferences count wins when
   present (it includes issues linked from the PR sidebar and only counts issues that
   exist); otherwise the body needs a closing keyword such as ``Closes #12``. ``Refs #12``
   does not link. No label bypasses it; see .claude/rules/pr-issue-link.md.

Bot authors (``*[bot]``, e.g. Dependabot) are exempt from gates 1, 2, 4 and 5: they cannot
write OpenSpec changes, CHANGELOG lines or issues, and their titles come from dependabot.yml.
The version gate still applies to them.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ABOUT = Path("src/csuf_fullerton/__about__.py")

MAJOR_PREFIXES = ("src/", ".github/", ".claude/", "Dockerfile", "pyproject.toml", "compose.yaml")
TITLE_RE = re.compile(
    r"^(feat|fix|docs|chore|refactor|test|ci|build|perf|spec|release)(\([\w./-]+\))?!?: .+"
)
VERSION_RE = re.compile(r'^__version__\s*=\s*"([^"]+)"', re.M)
CLOSING_RE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b:?\s+"
    r"(?:[\w.-]+/[\w.-]+#\d+|#\d+|https://github\.com/[\w.-]+/[\w.-]+/issues/\d+)",
    re.IGNORECASE,
)


def changed_files(base: str, head: str) -> list[str]:
    out = subprocess.run(  # noqa: S603
        ["git", "diff", "--name-only", f"{base}...{head}"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    ).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def version_at(ref: str) -> str | None:
    result = subprocess.run(  # noqa: S603
        ["git", "show", f"{ref}:{ABOUT.as_posix()}"],  # noqa: S607
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        return None
    match = VERSION_RE.search(result.stdout)
    return match.group(1) if match else None


def is_bot(author: str) -> bool:
    return author.endswith("[bot]")


def issue_link_error(body: str, author: str, linked: str) -> str | None:
    """Gate 5: the failure message, or None when the PR closes an issue or is exempt."""
    if is_bot(author):
        return None
    if linked.strip():
        if int(linked) > 0:
            return None
    elif CLOSING_RE.search(body):
        return None
    return (
        "issue gate: this PR closes no GitHub issue. Every PR, fixes and releases included, "
        "closes the issue it resolves. Find one with `gh issue list --search <keywords>` or "
        "create it with `gh issue create`, then add `Closes #<n>` to the PR body (or link it "
        "from the PR sidebar). A planning PR closes its plan sub-issue. `Refs #<n>` does not "
        "link. See .claude/rules/pr-issue-link.md."
    )


def main() -> int:
    base = os.environ["BASE_SHA"]
    head = os.environ["HEAD_SHA"]
    title = os.environ.get("PR_TITLE", "")
    labels = {
        label.strip() for label in os.environ.get("PR_LABELS", "").split(",") if label.strip()
    }

    author = os.environ.get("PR_AUTHOR", "")
    bot = is_bot(author)

    files = changed_files(base, head)
    errors: list[str] = []

    touches_major = any(f.startswith(MAJOR_PREFIXES) for f in files)
    touches_spec = any(f.startswith("openspec/changes/") for f in files)
    touches_src = any(f.startswith("src/") for f in files)
    touches_changelog = "CHANGELOG.md" in files

    if touches_major and not touches_spec and "skip-openspec" not in labels and not bot:
        errors.append(
            "openspec gate: this PR changes src/, .github/, .claude/, Dockerfile or pyproject.toml "
            "but adds no openspec/changes/<name>/ folder. Run `openspec new change <slug>` "
            "(or /opsx:propose) and commit it, or add the `skip-openspec` label with a reason."
        )

    if touches_src and not touches_changelog and "skip-changelog" not in labels and not bot:
        errors.append(
            "changelog gate: src/ changed but CHANGELOG.md did not. Add a line under "
            "## [Unreleased] or add the `skip-changelog` label with a reason."
        )

    old_version, new_version = version_at(base), version_at(head)
    if new_version and new_version != old_version:
        changelog = (REPO_ROOT / "CHANGELOG.md").read_text()
        if f"## [{new_version}]" not in changelog:
            errors.append(
                f"version gate: __about__.py now says {new_version} but CHANGELOG.md has no "
                f"`## [{new_version}]` section. Move the [Unreleased] notes under that heading."
            )
        if not re.match(r"^\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?(?:\.dev\d+)?$", new_version):
            errors.append(f"version gate: {new_version} is not SemVer (see check_release.py).")

    if not bot and not TITLE_RE.match(title):
        errors.append(
            f"title gate: '{title}' is not Conventional Commits. Use `type(scope): summary` with "
            "type in feat|fix|docs|chore|refactor|test|ci|build|perf|spec|release."
        )

    issue_error = issue_link_error(
        os.environ.get("PR_BODY", ""),
        author,
        os.environ.get("LINKED_ISSUES", ""),
    )
    if issue_error:
        errors.append(issue_error)

    for err in errors:
        print(f"::error::{err}")
    if errors:
        return 1
    print(f"All PR gates passed ({len(files)} files changed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
