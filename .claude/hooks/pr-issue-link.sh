#!/usr/bin/env bash
# PreToolUse hook (Claude Code and Codex): a pull request must close a GitHub issue.
#
# Fires on `gh pr create` in a Bash call and on MCP create_pull_request tools. The PR
# body (inline, --body-file, or the commit messages --fill would use) must contain a
# closing keyword that links an issue: "Closes #12", "Fixes org/repo#12", or
# "Resolves https://github.com/org/repo/issues/12". Anything else is denied with the
# steps to find or create the issue. Rule: .claude/rules/pr-issue-link.md
# (global copy: ~/.claude/rules/pr-issue-link.md).
#
# Same input and output contract in both harnesses: JSON on stdin, a PreToolUse
# `permissionDecision: deny` object on stdout. Needs only bash, git and python3.
set -u
input="$(cat)"
# The program is Python in single quotes on purpose: nothing in it is shell-expanded.
# shellcheck disable=SC2016
printf '%s' "$input" | python3 -c '
import json, os, re, shlex, subprocess, sys

LINK = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b:?\s+"
    r"(?:[\w.-]+/[\w.-]+#\d+|#\d+|https://github\.com/[\w.-]+/[\w.-]+/issues/\d+)",
    re.IGNORECASE,
)
RULE = "Rule: .claude/rules/pr-issue-link.md (global copy: ~/.claude/rules/pr-issue-link.md)."

try:
    event = json.load(sys.stdin)
except ValueError:
    sys.exit(0)
tool = str(event.get("tool_name") or "")
args = event.get("tool_input") or {}
if not isinstance(args, dict):
    sys.exit(0)

def git(*a):
    r = subprocess.run(["git", *a], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""

texts = []
unreadable = []  # body files named with shell variables or created later in the same command
if tool == "Bash":
    command = str(args.get("command") or "")
    # Only `gh pr create` in command position counts, so text that merely mentions it
    # (an issue body, a commit message, an echo) is not mistaken for the command.
    if not re.search(r"(?:^|[;&|(\n]|\$\()\s*(?:\w+=\S*\s+)*gh\s+pr\s+create\b", command):
        sys.exit(0)
    texts.append(command)  # inline --body, heredocs and $(cat <<EOF) bodies
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        words = command.split()
    for i, w in enumerate(words):
        nxt = words[i + 1] if i + 1 < len(words) else ""
        path = nxt if w in ("--body-file", "-F") else w.split("=", 1)[1] if w.startswith("--body-file=") else ""
        if path and path != "-":
            try:
                with open(os.path.expandvars(os.path.expanduser(path)), encoding="utf-8") as fh:
                    texts.append(fh.read())
            except OSError:
                unreadable.append(path)
    if any(w.startswith("--fill") for w in words):
        base = ""
        if "--base" in words and words.index("--base") + 1 < len(words):
            base = "origin/" + words[words.index("--base") + 1]
        base = base or git("symbolic-ref", "--short", "refs/remotes/origin/HEAD").strip()
        if base:
            texts.append(git("log", "--format=%B", f"{base}..HEAD"))
elif tool.endswith("create_pull_request"):
    texts.append(str(args.get("body") or ""))
else:
    sys.exit(0)

if any(LINK.search(t) for t in texts):
    sys.exit(0)
if unreadable:
    # Cannot see the body, so do not guess: let it through and say what CI will check.
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": (
            "pr-issue-link: could not read the PR body file " + ", ".join(unreadable)
            + " before the command runs, so the issue link was not checked here. Make sure the "
            "body says Closes #<n>; the CI issue gate will fail the PR otherwise."
        ),
    }}))
    sys.exit(0)

reason = (
    "Blocked: this pull request does not close a GitHub issue. Every PR, fixes and "
    "releases included, must name the issue it resolves so the why, the discussion and "
    "the code stay linked. "
    "1) Look for one: gh issue list --state open --search \"<keywords>\". "
    "2) If none fits, create it: gh issue create --title \"<problem>\" --body \"<what is wrong or "
    "missing, why it matters, how we will know it is done>\". "
    "3) Put \"Closes #<n>\" (or Fixes/Resolves) in the PR body, then retry. "
    "For one slice of a larger issue, open a sub-issue for the slice and close that. "
    "Starting from the issue is simplest: gh issue develop <n> --checkout. " + RULE
)
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": reason,
}}))
'
exit 0
