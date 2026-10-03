# The Claude Code harness

Goal: an agent working in this repo gets the right context at the right moment and cannot
make the expensive mistakes, while the always-loaded text stays small. Agent, skill and
`CLAUDE.md` text total under 200 lines. Detail lives in `docs/` and is read on demand.

## Always loaded (small)

- `CLAUDE.md`: read order, commands, six hard rules.
- `.claude/rules/*.md`: five rules, each under 40 lines. `layering.md`, `testing.md` and
  `openspec-gate.md` are path-scoped (`paths:` frontmatter) so they load only when matching
  files are touched.

## Hooks (`.claude/settings.json`)

| Event | Script | Does |
|---|---|---|
| SessionStart | `session-context.sh` | Branch, active OpenSpec changes, skill list. Three lines. |
| PreToolUse Edit/Write/Bash | `guard-main-branch.sh` | Blocks edits and commits on `main` (exit 2). |
| PreToolUse Edit/Write | `openspec-gate.sh` | Reminds when a major path is edited with no active change. |
| Stop | `stop-checklist.sh` | Reminds about CHANGELOG and tasks.md if `src/` changed. |

`permissions.deny` blocks force push, push to main, pushing images, uploading to PyPI,
creating releases, merging PRs, and reading `.env*`, key files, `~/.ssh`, `~/.aws`.

## Agents (`.claude/agents/`)

| Agent | Tools | Job |
|---|---|---|
| `implementer` | rw | One task from `tasks.md`, test first, inside layering. |
| `reviewer` | read-only | Diff vs spec vs rules. `VERDICT:` + `path:line` findings. |
| `security-reviewer` | read-only | OWASP, secrets, subprocess, deps, Dockerfile, workflow perms. |
| `spec-author` | rw | Issue or plan to a validated OpenSpec change. |
| `release-manager` | rw | Version bump + CHANGELOG section + release PR. Never publishes. |

## Skills (`.claude/skills/`)

`/propose`, `/ship`, `/review-pr` (with `references/checklist.md` loaded only at
step 4), `/release`. Each is a numbered procedure under 20 lines. `/review-pr` is also the
prompt behind the CI conformance review, so local and CI reviews are the same procedure.
The `opsx:*` commands under `.claude/commands/` come from `openspec init`.

## CI reviews (`.github/workflows/claude-review.yml`)

1. Bug hunt: Anthropic `code-review` plugin, inline comments.
2. Conformance: follows `/review-pr`, one comment with a verdict.
3. `@claude` in any comment for on-demand work.

Needs `ANTHROPIC_API_KEY` in repo or org secrets; the `claude` GitHub App is installed
org-wide.

## Growing it

Add a rule only when a mistake has happened twice. Put facts in `docs/`, procedures in
skills, guard rails in hooks. If `CLAUDE.md` passes 80 lines, move something out.
