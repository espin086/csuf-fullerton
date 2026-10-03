---
name: propose
description: Create an OpenSpec change folder for a feature, fix, or design change before any code. Required for edits to src/, .github/, .claude/, Dockerfile, pyproject.toml.
arguments: [slug]
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(openspec:*), Bash(git:*)
---

Before these steps, follow `CONTRIBUTING.md`: identify or create the GitHub issue, then
prepare a planning-only PR. Do not implement the capability until that PR is merged.

# /propose <slug>

1. `openspec new change $0` (falls back to `/opsx:propose` if installed).
2. Read `openspec/config.yaml` (the proposal and task rules) and `openspec/project.md`.
3. Write `proposal.md`: Outcome (as a command someone can run), Why, What changes,
   Non-goals, Risks. Link every source relied on. Write `tasks.md`: tasks under two hours,
   each naming its test. Write `specs/<capability>/spec.md` deltas with `#### Scenario:` blocks.
4. `openspec validate $0`. Fix until green. Commit on a `spec/$0` branch.
