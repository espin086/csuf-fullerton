---
paths: ["src/**", "tests/**", ".github/**", ".claude/**", ".agents/**", ".codex/**", "site/**", "Dockerfile", "pyproject.toml"]
---
# Issue and merged plan before implementation

Follow `CONTRIBUTING.md`. Identify the issue and merged planning PR before implementing a
capability. An active change folder or approval comment alone does not authorize coding.
New acceptance criteria require a merged planning amendment first. Planning PRs contain
specs, tasks and design; implementation PRs reference the merged plan and its task IDs.

Current `pr-gates.yml` checks changed paths only; maintainers must verify the sequence until
change 0002's stronger gate is implemented after plan merge. A bypass label alone is not
permission to ignore this workflow. Design decisions belong in the proposal itself, with
their sources linked.
