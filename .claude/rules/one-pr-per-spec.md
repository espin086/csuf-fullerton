---
name: one-pr-per-spec
status: active
---

# One local session, one PR per spec

There is no PR size limit. When told to work a spec, an OpenSpec change, or any large
body of work, do all of it locally and open **one pull request at the end**.

1. **Issues first, still.** Confirm a GitHub issue exists for the work before coding
   (`pr-issue-link.md`). The work may be split into sub-issues and OpenSpec tasks. That is
   for planning and tracking. It does not mean one PR per piece.
2. **Work on one branch.** Check off OpenSpec tasks as they pass their proving tests.
3. **Verify locally, not in CI.** Run targeted tests while working. Before the push run
   the full offline suite, lint, format and type checks once. Do not push mid-work to see
   CI, and do not wait on or poll CI between tasks.
4. **Open one PR at the end.** Its body has one `Closes #N` line for the parent issue and
   for every sub-issue it delivers. CI runs once, on that PR.
5. **A stack of PRs is opt-in.** Only when the owner asks for one, or when a later piece
   needs an earlier one merged and deployed first. Never split by size.

## Why

Many small PRs mean many CI runs, each spending GitHub Actions budget, and a long session
stalls on every wait. The owner reviews one PR per spec, not a chain. Sub-issues and
OpenSpec tasks keep the tracking granular without the review and CI cost.

## Does not change

Branch then PR, never commit to `main`. Every PR closes an issue. A red required check is
never merged around. When CI fails, re-run and fix only the failing test.
