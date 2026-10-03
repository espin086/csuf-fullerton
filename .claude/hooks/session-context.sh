#!/usr/bin/env bash
# SessionStart: inject the smallest useful orientation. Index only, never page bodies.
set -u
root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root" || exit 0
branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
active=""
if [ -d openspec/changes ]; then
  active="$(ls -1 openspec/changes 2>/dev/null | grep -v '^archive$' | tr '\n' ' ')"
fi
cat <<MSG
[project-template harness] branch=${branch}. Active OpenSpec changes: ${active:-none}.
Procedures are skills: /propose /ship /review-pr /release. Hard rules: CLAUDE.md.
MSG
exit 0
