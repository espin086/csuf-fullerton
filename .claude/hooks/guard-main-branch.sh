#!/usr/bin/env bash
# PreToolUse (Edit/Write/Bash): block file edits and git commits while on main.
set -u
input="$(cat)"
root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
branch="$(git -C "$root" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
[ "$branch" = "main" ] || [ "$branch" = "master" ] || exit 0
tool="$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_name",""))' 2>/dev/null)"
if [ "$tool" = "Bash" ]; then
  cmd="$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null)"
  case "$cmd" in
    *"git commit"*|*"git push"*|*"git merge"*|*"git rebase"*) ;;
    *) exit 0 ;;
  esac
fi
echo "Blocked: you are on '$branch'. Create a branch first: git switch -c <type>/<slug>. See .claude/rules/branch-and-pr.md" >&2
exit 2
