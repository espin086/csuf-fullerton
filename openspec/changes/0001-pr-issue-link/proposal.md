# Every pull request closes a GitHub issue

## Why

Issue #7: pull requests could merge with no linked issue. The reason for a change then
lives only in the PR and commit text, the issue list drifts from real work, and merged fixes
close nothing. Planning PRs used `Refs #N`, which GitHub does not link at all.

## What changes

- PR gate 5 in `.github/scripts/check_pr_gates.py` fails a PR whose GitHub
  `closingIssuesReferences` count is zero, falling back to a closing keyword in the body when
  the API step cannot run. Bots are exempt. No label bypasses it.
- `.claude/hooks/pr-issue-link.sh` denies `gh pr create` and the GitHub MCP
  `create_pull_request` without a closing keyword, for Claude Code (`.claude/settings.json`)
  and Codex (`.codex/hooks.json`).
- `.claude/rules/pr-issue-link.md` states the rule and why it applies to fixes.
- The contribution flow keeps plan → implementation: the planning PR closes a `Plan:` sub-issue,
  intermediate PRs close task sub-issues, the final PR closes the feature issue.

## Non-goals

Merged-plan and ancestry verification (the rest of the stronger gate planned elsewhere) and
changing branch protection from code.
