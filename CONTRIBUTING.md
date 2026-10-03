# Contributing

Humans, Claude, and Codex use the same workflow. The maintainer merges PRs; agents do not.

## Issue → merged OpenSpec plan → implementation

1. **Issue first.** Open a feature/change or bug issue (or find the existing one). Describe
   the problem, desired behavior, acceptance criteria, and non-goals. Include reproduction
   and expected/actual results for bugs. Do not put secrets or private customer data in issues.
2. **Plan in its own PR.** Create `spec/<issue>-<slug>` from the default branch. Write
   `openspec/changes/<slug>/proposal.md`, `tasks.md`, and scenario deltas under `specs/`.
   Link the issue, relevant architecture decisions, risks, tests and rollback approach.
   Mark the PR **planning** using the standard PR template. Open a `Plan: <feature>`
   sub-issue of the feature issue and close it with this PR (`Closes #<plan>`), so the
   feature issue stays open. Investigation is allowed; feature code is not.
3. **Wait for merge.** The maintainer reviews and merges the planning PR into the default
   branch. Approval without merge is insufficient. Do not begin production implementation
   while the plan is open. Clarify scope through the issue and revise the plan as needed.
4. **Implement from the merged plan.** Start `feat/<issue>-<task>` or `fix/<issue>-<task>`
   from the updated default branch. Verify the plan's merge commit is an ancestor. Link
   issue, merged planning PR, change folder and task IDs. If acceptance criteria change,
   merge a separate planning amendment before implementing the affected change.
5. **Keep review units small.** One coherent commit per completed task, including its test
   and changelog entry. Aim for 1–3 related tasks per PR and about 300 changed hand-written
   lines (excluding lock/generated files). Split independent capabilities. Explain necessary
   exceptions such as an atomic migration; do not omit tests to hit the target. Preserve
   reviewed history; follow-up fixes are new commits. Plan tasks for roughly two hours or less.
6. **Verify and open the implementation PR.** Run `make check`, relevant integration/contract
   tests, and fill every applicable PR-template field. After any Python edit, run
   `black --line-length=100 <file>` and `isort --profile=black --line-length=100 <file>`.
   Existing Ruff checks still run; resolve disagreement in favor of the required formatters.
7. **Review, merge, close.** Fix findings and let the maintainer merge after required checks.
   Every PR closes an issue. Intermediate PRs close their task sub-issue; the PR that delivers
   the capability closes the feature issue (`Closes #N`). `Refs #N` alone never links a PR.
   Why this applies to one-line fixes too: `.claude/rules/pr-issue-link.md`.
   Archive the change after implementation merges and canonical specs reflect the behavior.

For documentation-only maintenance, use an issue and state the exact scope in the PR.
A maintainer may approve a narrowly scoped exception with a reason; a bypass label alone
is not approval to skip planning or start unrelated coding. Automated dependency updates
need maintainer triage; their existing labels do not authorize a feature implementation.

## What currently enforces this

AGENTS and linked procedures require this sequence. Main's active ruleset requires PRs and
checks, blocks force pushes/deletions, and has no bypass actors. It has zero required approving
reviews for the sole maintainer; it is not a second-human approval requirement.
PR gate 5 fails any PR that closes no issue, and the `pr-issue-link` hook stops Claude and
Codex before they open one. The OpenSpec checker only checks changed paths. It does **not**
validate a merged planning PR, ancestry, substantive exception reasons, or task-sized commits. These
remain maintainer review checks until the stronger gate in
[change 0002](openspec/changes/0002-review-workflow/proposal.md) is merged and implemented.
The pre-existing foundation PR is bootstrap work, not proof of retroactive compliance.

## Releasing and enterprise inquiries

Use [release setup](docs/RELEASING.md). Publishing credentials and switches must be configured
before merging a version bump can publish. Use the hosting inquiry issue form for non-sensitive
questions; an inquiry is not an accepted feature or contractual hosting commitment. See the
[home page](site/index.html) and [publication guide](docs/HOME-PAGE.md).
