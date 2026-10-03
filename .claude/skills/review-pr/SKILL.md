---
name: review-pr
description: Review a PR or the current diff against its OpenSpec change and the repo rules. Used by the reviewer agent locally and by claude-review.yml in CI.
arguments: [pr]
allowed-tools: Read, Grep, Glob, Bash(gh pr:*), Bash(git diff:*), Bash(git log:*)
---

Apply the workflow in `CONTRIBUTING.md` before these steps. For implementation, verify
the linked issue and planning PR merged into the default branch. Work in small task commits;
use the standard PR template. An active change folder alone is insufficient authorization.

# /review-pr [number]

1. Diff: `gh pr diff $0` (or `git diff origin/main...HEAD`). Files list first.
2. Spec: find the change the PR body links under `openspec/changes/`. Read `proposal.md`,
   `tasks.md`, `specs/`. Map every behaviour change to a scenario and every scenario to a
   test. Unmapped = finding.
3. Rules: the `.claude/rules/` files relevant to touched modules. Any diff that contradicts
   a rule = finding with the rule path.
4. Correctness pass over the diff: `references/checklist.md`.
5. Hygiene: CHANGELOG line present; version bump has a section; layering intact.
6. Output: `VERDICT: PASS|WARN|BLOCK` then `path:line: severity: problem. fix.` lines,
   under 40. In CI post it with `gh pr comment`.
