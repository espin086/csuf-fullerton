#!/usr/bin/env bash
# PreToolUse (Edit/Write): warn (not block) when editing a major path with no active change.
set -u
input="$(cat)"
root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
path="$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)"
rel="${path#"$root"/}"
case "$rel" in
  src/*|.github/*|.claude/*|Dockerfile|pyproject.toml|compose.yaml) ;;
  *) exit 0 ;;
esac
active="$(ls -1 "$root/openspec/changes" 2>/dev/null | grep -v '^archive$')"
[ -z "$active" ] || exit 0
echo "Reminder: editing $rel with no active OpenSpec change. pr-gates.yml will fail the PR. Run /propose first or plan to add the skip-openspec label with a reason."
exit 0
