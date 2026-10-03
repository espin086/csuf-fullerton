#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
test -f AGENTS.md
grep -qx '@AGENTS.md' CLAUDE.md
test -L .agents/rules
test "$(readlink .agents/rules)" = '../.claude/rules'
count=0
for skill in .claude/skills/*; do
  test -f "$skill/SKILL.md"
  name=${skill##*/}
  test -L ".agents/skills/$name"
  test "$(readlink ".agents/skills/$name")" = "../../.claude/skills/$name"
  cmp "$skill/SKILL.md" ".agents/skills/$name/SKILL.md"
  count=$((count + 1))
done
for skill in .agents/skills/*; do test -f "$skill/SKILL.md"; done
printf 'Shared entry, rules and %s linked skills verified.\n' "$count"
