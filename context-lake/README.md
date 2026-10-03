# Context lake

Project context that is not software lives here. This folder is the durable record of why
the code looks the way it does, kept next to the code but outside the package.

## What belongs here

- Meeting notes and decision logs
- Discussion topics, open questions, and the answers they reached
- ADRs (architecture decision records)
- PRDs and product briefs
- Research notes, benchmarks, vendor comparisons, cost models
- Diagrams and any other non-code project material

## What does not belong here

- Source code, tests, or configuration. Those live in `src/`, `tests/`, and the repo root.
- Specs and change proposals. Those live in `openspec/` and are gated by `pr-gates.yml`.
- Secrets, credentials, customer data, or anything else that should not be in Git.

## Conventions

One topic per file, Markdown, lowercase kebab-case names, dated when the content is
time-bound: `2026-09-16-storage-decision.md`. Link a page from the OpenSpec proposal that
relies on it rather than copying its text.

The folder ships empty on purpose. Add pages as the project produces them.
