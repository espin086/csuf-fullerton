# project-template

## What this is

A template for a Python CLI/library repo. Made from `Use this template` on GitHub, then
`python scripts/rename.py <name>`.

## Where things live

| Thing | Path |
|---|---|
| Specs and changes for this repo | `openspec/` |
| Agent harness (hooks, agents, skills, rules) | `AGENTS.md`, linked `.agents/` skills/rules, Claude-specific runtime in `.claude/` |
| Package | `src/project_template/` (`core/` pure, `cli/` adapter) |
| Gates | `.github/workflows/{ci,pr-gates,claude-review,codeql}.yml` |
| Release | `.github/workflows/release.yml`, `docs/RELEASING.md` |

## The one architectural rule

Logic in `core/` is pure and tested against known answers. Adapters hold no logic.
`tests/architecture/test_layering.py` enforces it.

Contribution sequence: GitHub issue → OpenSpec planning PR merged by maintainer → small
implementation PRs. See CONTRIBUTING.md. The PR gate is path-based: it checks that a change
folder exists and is referenced, not that the diff matches the spec.
