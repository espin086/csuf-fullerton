# Contribution workflow

## ADDED Requirements

### Requirement: Every pull request closes an issue

A pull request SHALL close at least one GitHub issue, so the reason for every change is
recorded and closes on merge.

#### Scenario: Unlinked pull request is rejected
- **WHEN** a PR's GitHub `closingIssuesReferences` count is zero, or the count is unavailable
  and the body has no closing keyword
- **THEN** PR gate 5 SHALL fail with the steps to find or create the issue, whatever the labels

#### Scenario: Agents are stopped before opening one
- **WHEN** Claude Code or Codex runs `gh pr create`, or calls MCP `create_pull_request`, with a
  body that has no closing keyword
- **THEN** the `pr-issue-link` hook SHALL deny the call and say how to link an issue

#### Scenario: Bots are exempt
- **WHEN** the PR author is a bot account (`*[bot]`)
- **THEN** gate 5 SHALL pass
