#!/usr/bin/env bash
# Stop: if src/ changed but CHANGELOG.md or openspec/ did not, remind once.
set -u
root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$root" || exit 0
changed="$(git status --porcelain 2>/dev/null | awk '{print $2}')"
[ -n "$changed" ] || exit 0
src=$(printf '%s\n' "$changed" | grep -c '^src/' || true)
log=$(printf '%s\n' "$changed" | grep -c '^CHANGELOG.md$' || true)
spec=$(printf '%s\n' "$changed" | grep -c '^openspec/' || true)
msg=""
[ "$src" -gt 0 ] && [ "$log" -eq 0 ] && msg="$msg CHANGELOG.md [Unreleased] has no line for the src/ changes."
[ "$src" -gt 0 ] && [ "$spec" -eq 0 ] && msg="$msg openspec/ untouched: are tasks.md boxes checked and spec deltas written?"
[ -n "$msg" ] && echo "Before you stop:$msg"
exit 0
