#!/usr/bin/env bash
# Apply the template's branch ruleset to a repo. Usage: scripts/apply-ruleset.sh OWNER/REPO
# Sole-developer policy: PRs required, zero approvals, required checks, no force push.
set -euo pipefail
repo="${1:?usage: apply-ruleset.sh OWNER/REPO}"
gh api --method POST "repos/${repo}/rulesets" --input - <<'JSON'
{
  "name": "main: PR + green checks",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_linear_history" },
    { "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": true,
        "allowed_merge_methods": ["squash"]
      } },
    { "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          { "context": "All checks passed" },
          { "context": "OpenSpec, CHANGELOG, version, title" }
        ]
      } }
  ]
}
JSON
echo "ruleset applied to ${repo}"
