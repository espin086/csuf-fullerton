# project-template

Python CLI + library. Pure logic in `src/project_template/core/`, thin adapters in `cli/`.
Spec-driven: no major change without an OpenSpec change folder.

## Read order (progressive disclosure)

1. `openspec/project.md` and the active change under `openspec/changes/` when implementing.
2. Read applicable `.agents/rules/` files (linked to `.claude/rules/`). Claude loads its
   rules automatically; Codex must read them explicitly, including path-scoped rules.
3. Skills (`propose`, `ship`, `review-pr`, `release`) carry the procedures.
   Claude uses `/name`; Codex can invoke `$name`. Commands/tools differ; procedures are shared.

## Commands

```
make install     # uv venv + editable install + pre-commit
make check       # ruff, mypy, pytest (offline), openspec validate  = the PR gate
make docker      # build image and smoke-test --version
openspec new change <slug>   # start a change (or /propose)
```

## Hard rules (details in the linked rules and CONTRIBUTING.md)

- Never commit on `main`. Branch, PR, green `All checks passed`, squash-merge.
- One local session, one PR per spec. No PR size limit: work a spec or large body of work locally on one branch, verify locally, open one PR at the end with one `Closes #N` per issue. Sub-issues and OpenSpec tasks track the pieces. No mid-work CI waits. Stacks are opt-in. Rule: `.claude/rules/one-pr-per-spec.md`.
- `core/` never imports I/O, logging, env, or `cli/`. `tests/architecture/` fails otherwise.
- Every scenario in a spec delta has a test that names it. Math and logic tested against known
  answers, never live data (`@pytest.mark.network` for the rest).
- `CHANGELOG.md` `[Unreleased]` gets a line for every user-visible change.
- Release = bump `src/project_template/__about__.py` + CHANGELOG section + merge. Nothing manual.
- Secrets never enter the repo or a prompt. Agent-specific settings are not universal controls.
- Every PR closes a GitHub issue: `Closes #<n>` in the body, fixes and releases included.
  No issue yet? Create it first (`gh issue create`). A planning PR closes its `Plan:`
  sub-issue. `.claude/hooks/pr-issue-link.sh` (Claude and `.codex/hooks.json`) and PR gate 5
  enforce it. Why: `.claude/rules/pr-issue-link.md`.
- Follow `CONTRIBUTING.md`: issue → planning PR → maintainer merges plan → implementation PR.
  An unmerged plan is not permission to code. Work one task per coherent commit.
- After every Python edit: `black --line-length=100 <file>` then
  `isort --profile=black --line-length=100 <file>`. Do not manually reorder imports.

## Code Review Rules

Check the linked issue, merged planning PR, accepted scope, task-to-commit mapping, and
`CONTRIBUTING.md` PR size target. Flag missing tests, secret exposure, adapter leaks and
unjustified scope changes. Agents open PRs and address findings; the maintainer merges.
