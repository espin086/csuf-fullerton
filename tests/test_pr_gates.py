"""Contract tests for .github/scripts/check_pr_gates.py against a throwaway git repo."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / ".github" / "scripts" / "check_pr_gates.py"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "r"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "user.email", "t@t")
    git(r, "config", "user.name", "t")
    (r / ".github" / "scripts").mkdir(parents=True)
    shutil.copy(SCRIPT, r / ".github" / "scripts" / "check_pr_gates.py")
    (r / "src" / "project_template").mkdir(parents=True)
    (r / "src" / "project_template" / "__about__.py").write_text('__version__ = "0.1.0"\n')
    (r / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n\n## [0.1.0] - 2026-01-01\n")
    (r / "openspec" / "changes").mkdir(parents=True)
    git(r, "add", "-A")
    git(r, "commit", "-qm", "init")
    return r


def run(
    repo: Path,
    base: str,
    head: str,
    title: str = "feat: x",
    labels: str = "",
    body: str = "Closes #1",
    author: str = "someone",
    linked: str = "",
) -> tuple[int, str]:
    env = {
        **os.environ,
        "BASE_SHA": base,
        "HEAD_SHA": head,
        "PR_TITLE": title,
        "PR_LABELS": labels,
        "PR_BODY": body,
        "PR_AUTHOR": author,
        "LINKED_ISSUES": linked,
    }
    p = subprocess.run(
        [sys.executable, str(repo / ".github/scripts/check_pr_gates.py")],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )
    return p.returncode, p.stdout + p.stderr


def commit(repo: Path, msg: str = "c") -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", msg)
    return git(repo, "rev-parse", "HEAD")


def test_src_change_without_spec_or_changelog_fails(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    (repo / "src" / "project_template" / "x.py").write_text("x = 1\n")
    head = commit(repo)
    code, out = run(repo, base, head)
    assert code == 1
    assert "openspec gate" in out
    assert "changelog gate" in out


def test_labels_bypass(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    (repo / "src" / "project_template" / "x.py").write_text("x = 1\n")
    head = commit(repo)
    code, out = run(repo, base, head, labels="skip-openspec,skip-changelog")
    assert code == 0, out


def test_spec_and_changelog_pass(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    (repo / "src" / "project_template" / "x.py").write_text("x = 1\n")
    (repo / "openspec" / "changes" / "0001-x").mkdir()
    (repo / "openspec" / "changes" / "0001-x" / "proposal.md").write_text("# x\n")
    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n- x\n\n## [0.1.0] - 2026-01-01\n"
    )
    head = commit(repo)
    code, out = run(repo, base, head)
    assert code == 0, out


def test_version_bump_needs_section(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    (repo / "src" / "project_template" / "__about__.py").write_text('__version__ = "0.2.0"\n')
    head = commit(repo)
    code, out = run(
        repo, base, head, title="release: v0.2.0", labels="skip-openspec,skip-changelog"
    )
    assert code == 1
    assert "version gate" in out


def test_bad_title_fails(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    (repo / "docs.md").write_text("hi\n")
    head = commit(repo)
    code, out = run(repo, base, head, title="Update stuff")
    assert code == 1
    assert "title gate" in out


def _docs_change(repo: Path) -> tuple[str, str]:
    base = git(repo, "rev-parse", "HEAD")
    (repo / "docs.md").write_text("hi\n")
    return base, commit(repo)


@pytest.mark.parametrize(
    "body",
    [
        "Closes #12",
        "fixes #3",
        "Resolves: #40",
        "Closes org/repo#8",
        "Fixes https://github.com/org/repo/issues/9",
    ],
)
def test_issue_gate_accepts_a_closing_keyword(repo: Path, body: str) -> None:
    base, head = _docs_change(repo)
    code, out = run(repo, base, head, title="docs: x", body=body)
    assert code == 0, out


@pytest.mark.parametrize("body", ["", "Refs #12", "Part of #12", "#12", "tidy up"])
def test_issue_gate_rejects_a_pr_that_closes_nothing(repo: Path, body: str) -> None:
    base, head = _docs_change(repo)
    code, out = run(repo, base, head, title="docs: x", body=body)
    assert code == 1
    assert "issue gate" in out and "gh issue create" in out


def test_issue_gate_trusts_githubs_count_over_the_body(repo: Path) -> None:
    base, head = _docs_change(repo)
    sidebar = run(repo, base, head, title="docs: x", body="no keyword", linked="1")
    assert sidebar[0] == 0, sidebar[1]
    missing = run(repo, base, head, title="docs: x", body="Closes #99999", linked="0")
    assert missing[0] == 1 and "issue gate" in missing[1]


def test_issue_gate_exempts_bots_and_ignores_labels(repo: Path) -> None:
    base, head = _docs_change(repo)
    bot = run(repo, base, head, title="docs: x", body="", author="dependabot[bot]", linked="0")
    assert bot[0] == 0, bot[1]
    labelled = run(
        repo, base, head, title="docs: x", body="", labels="skip-openspec,skip-changelog"
    )
    assert labelled[0] == 1 and "issue gate" in labelled[1]
