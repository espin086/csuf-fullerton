---
name: pr-issue-link
status: active
---

# Rule: every pull request closes a GitHub issue

## What this rule says

No pull request is opened without an issue it closes. The PR body carries a closing
keyword that GitHub turns into a link:

```
Closes #12
Fixes #12
Resolves AI-Solutions-Lab-LLC/other-repo#12
Closes https://github.com/org/repo/issues/12
```

`Refs #12`, `Part of #12` and a bare `#12` do not count. GitHub does not link them, so
merging the PR leaves the issue open and the two drift apart.

This holds for every PR: features, fixes, one-line typo fixes, hand-made dependency bumps,
release PRs and docs. Bots that cannot open issues (Dependabot, Renovate) are the only
exception.

## How to apply it

Before drafting the PR:

1. **Look for the issue.** `gh issue list --state open --search "<keywords>"`.
2. **If none fits, create one first.** `gh issue create --title "<the problem, not the fix>"`
   with a body that says what is wrong or missing, why it matters, and how we will know it is
   done. Two or three sentences is enough for a small fix.
3. **Link it.** Put `Closes #<n>` in the PR body. One PR may close several issues, one per line.
4. **A slice of a bigger issue:** open a sub-issue for the slice and close that. The parent
   stays open until its last slice lands. In this repo's issue → plan → implementation flow
   (`CONTRIBUTING.md`) that means: the planning PR closes a `Plan: <feature>` sub-issue,
   each intermediate implementation PR closes its task sub-issue, and the PR that delivers
   the capability closes the feature issue.

Starting from the issue is the shortest path. `gh issue develop <n> --checkout` creates a
branch linked to the issue, and the PR from that branch shows on the issue. The GitHub UI's
"Create a branch" button on an issue does the same.

## Why, even for a fix

- **The issue holds the why; the PR holds the how.** A diff shows what changed. The issue
  says what was broken, who saw it and what "done" means. Months later, `git blame` leads to
  the PR and the PR leads to the issue. Without the issue the trail stops at a commit message.
- **Closing is automatic and honest.** A closing keyword closes the issue on merge, so the
  open list is the real backlog. Unlinked fixes leave stale issues open, or no issue exists and
  the fix never shows up in planning.
- **Small fixes are where context gets lost.** A quick fix often hides a decision: why this
  default, why not the other approach. Two sentences in an issue put that decision where a
  reviewer can disagree before the code lands.
- **Agents need a target.** An issue with acceptance criteria gives Claude Code or Codex a
  definition of done to check against, instead of guessing from the diff.
- **Release notes and history read from it.** A PR with no issue is a gap in the changelog
  trail and in anything that reports on issues.

The cost is a minute per PR. The cost of skipping it is a history nobody can reconstruct.

## Enforcement

- `.claude/hooks/pr-issue-link.sh` runs before every Claude Code `Bash` call and every GitHub
  MCP `create_pull_request` call. It denies `gh pr create` when the body (inline, heredoc,
  `--body-file`, or the commit messages `--fill` uses) has no closing keyword, and says how to
  fix it.
- `.codex/hooks.json` runs the same script for Codex. Codex asks you to trust a project hook
  once.
- Gate 5 of `.github/scripts/check_pr_gates.py` (the `PR gates` workflow) fails any PR whose
  GitHub `closingIssuesReferences` is empty. No label bypasses it. That catches PRs opened
  from the browser or by hand, and counts issues linked from the PR sidebar too. Make that
  check required in branch protection.
