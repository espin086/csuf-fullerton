---
name: ship
description: Take the current branch from working tree to an open pull request that passes the gates. Runs make check, updates CHANGELOG, pushes, opens the PR with the template.
allowed-tools: Read, Edit, Bash(make:*), Bash(git:*), Bash(gh pr:*), Bash(openspec:*)
---

Apply the workflow in `CONTRIBUTING.md` before these steps. For implementation, verify
the linked issue and planning PR merged into the default branch. Work in small task commits;
use the standard PR template. An active change folder alone is insufficient authorization.

# /ship

1. Refuse on `main`. Identify the stage and verify the issue/merged-plan requirements in CONTRIBUTING.
2. `make check`. Fix until green. `openspec validate --all`.
3. `CHANGELOG.md` `[Unreleased]` has a line per user-visible change. `tasks.md` boxes ticked.
4. Confirm each completed task has its coherent commit; commit outstanding fixes separately.
   `git push -u origin <branch>`.
5. Fill `.github/pull_request_template.md` in a body file and use `gh pr create --body-file`.
   Include issue, stage, merged planning PR where required, task-to-commit mapping and validation.
6. `gh pr checks --watch`. Report the URL and any red check. Do not merge.
