"""Each .claude hook runs with fixture JSON and behaves as the harness spec says."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS = REPO_ROOT / ".claude" / "hooks"


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
    (r / "openspec" / "changes").mkdir(parents=True)
    (r / "src").mkdir()
    (r / "f").write_text("x")
    git(r, "add", "-A")
    git(r, "commit", "-qm", "init")
    return r


def run_hook(name: str, repo: Path, payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(HOOKS / name)],
        cwd=repo,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


def edit(path: str) -> dict[str, object]:
    return {"tool_name": "Edit", "tool_input": {"file_path": path}}


def bash(command: str) -> dict[str, object]:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def test_guard_blocks_edit_on_main(repo: Path) -> None:
    p = run_hook("guard-main-branch.sh", repo, edit("f"))
    assert p.returncode == 2
    assert "main" in p.stderr


def test_guard_allows_on_branch(repo: Path) -> None:
    git(repo, "switch", "-qc", "feat/x")
    assert run_hook("guard-main-branch.sh", repo, edit("f")).returncode == 0


def test_guard_allows_readonly_bash_on_main(repo: Path) -> None:
    assert run_hook("guard-main-branch.sh", repo, bash("git status")).returncode == 0


def test_guard_blocks_commit_on_main(repo: Path) -> None:
    assert run_hook("guard-main-branch.sh", repo, bash("git commit -m x")).returncode == 2


def test_openspec_gate_reminds_without_change(repo: Path) -> None:
    p = run_hook("openspec-gate.sh", repo, edit(str(repo / "src" / "a.py")))
    assert p.returncode == 0
    assert "OpenSpec" in p.stdout


def test_openspec_gate_silent_with_change(repo: Path) -> None:
    (repo / "openspec" / "changes" / "0001-x").mkdir()
    p = run_hook("openspec-gate.sh", repo, edit(str(repo / "src" / "a.py")))
    assert p.returncode == 0
    assert p.stdout == ""


def test_session_context_reports_branch_and_skills(repo: Path) -> None:
    p = run_hook("session-context.sh", repo, {})
    assert p.returncode == 0
    assert "branch=main" in p.stdout
    assert "/propose" in p.stdout


def test_stop_checklist_reminds(repo: Path) -> None:
    (repo / "src" / "a.py").write_text("x")
    p = run_hook("stop-checklist.sh", repo, {})
    assert "CHANGELOG" in p.stdout
    assert "openspec" in p.stdout


def _pr_denied(repo: Path, payload: dict[str, object]) -> bool:
    p = run_hook("pr-issue-link.sh", repo, payload)
    assert p.returncode == 0, p.stderr
    if not p.stdout.strip():
        return False
    return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.parametrize(
    ("command", "denied"),
    [
        ('gh pr create --title x --body "Closes #12"', False),
        ('gh pr create --title x --body "tidy"', True),
        ('gh pr create --title x --body "Refs #12"', True),
        ('cd r && gh pr create --body "tidy"', True),
        ("gh pr create --body \"$(cat <<'EOF'\nWhy\n\nFixes org/repo#4\nEOF\n)\"", False),
        ('gh issue create --title x --body "hooks deny `gh pr create` without a link"', False),
        ("gh pr list", False),
    ],
)
def test_pr_issue_link_hook(repo: Path, command: str, denied: bool) -> None:
    assert _pr_denied(repo, bash(command)) is denied


def test_pr_issue_link_hook_reads_body_files_and_mcp(repo: Path) -> None:
    (repo / "ok.md").write_text("Closes #7\n")
    (repo / "bad.md").write_text("Summary\n")
    assert not _pr_denied(repo, bash("gh pr create -t x -F ok.md"))
    assert _pr_denied(repo, bash("gh pr create -t x --body-file=bad.md"))
    mcp = "mcp__github__create_pull_request"
    assert _pr_denied(repo, {"tool_name": mcp, "tool_input": {"body": "tidy"}})
    assert not _pr_denied(repo, {"tool_name": mcp, "tool_input": {"body": "Closes #1"}})


def test_pr_issue_link_hook_runs_in_claude_and_codex() -> None:
    claude = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text())
    codex = json.loads((REPO_ROOT / ".codex" / "hooks.json").read_text())
    for config in (claude, codex):
        commands = [h["command"] for e in config["hooks"]["PreToolUse"] for h in e["hooks"]]
        assert any("pr-issue-link.sh" in c for c in commands)


def test_pr_issue_link_hook_leaves_an_unreadable_body_file_to_ci(repo: Path) -> None:
    p = run_hook("pr-issue-link.sh", repo, bash("gh pr create --body-file $UNSET_DIR/body.md"))
    decision = json.loads(p.stdout)["hookSpecificOutput"]
    assert "permissionDecision" not in decision
    assert "could not read the PR body file" in decision["additionalContext"]
