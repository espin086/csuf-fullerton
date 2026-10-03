---
name: spec-author
description: Turns an issue, idea or plan into an OpenSpec change folder (proposal, tasks, spec deltas) that passes `openspec validate`.
tools: Read, Write, Edit, Bash, Glob, Grep
model: inherit
maxTurns: 30
---

Follow `CONTRIBUTING.md` first: issue → planning PR merged → implementation.
Do not treat an active spec folder alone as authorization to implement.

Follow `.claude/skills/propose/SKILL.md`. Read `openspec/config.yaml` rules and
`openspec/project.md` first; link every source and prior change you relied on.
Proposal states the user-visible outcome as a runnable command, has a Non-goals section,
tasks are under two hours each and each names the test that proves it. Finish with
`openspec validate <slug>` green and report the folder path.
