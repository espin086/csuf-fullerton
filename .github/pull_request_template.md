## Outcome and scope

<!-- State the concrete problem and resulting behavior. List non-goals. -->

## Workflow stage and traceability

- Stage: <!-- planning | implementation | maintenance -->
- Closes #<!-- the issue this PR closes: the Plan sub-issue for a planning PR, the task
  sub-issue for an intermediate PR, the feature issue for the final one. Refs does not link. -->
- OpenSpec change: <!-- openspec/changes/<slug>/ -->
- Merged planning PR and merge commit: <!-- required for implementation; N/A + reason otherwise -->
- Task IDs covered: <!-- one small capability, usually 1–3 tasks -->
- Context decisions: <!-- page paths, or unavailable + local evidence used -->

## Review size

- Task → commit mapping: <!-- commit SHA and task per line; include tests with implementation -->
- Size exception: <!-- explain atomicity if >~300 hand-written changed lines or >3 tasks; otherwise N/A -->
- Dependencies / merge order: <!-- especially stacked PRs -->

## Validation and hands-on review

<!-- Exact commands, outcomes, and steps the maintainer can reproduce. Name skipped checks and why. -->

## Risks and rollback

<!-- Migrations, compatibility, operational risk and recovery; N/A + reason for simple docs. -->

## Checklist

- [ ] The body says `Closes #<issue>`, and that issue defines the problem and acceptance criteria
- [ ] Planning PR contains no application feature implementation
- [ ] For implementation: plan already merged into default branch; scope and task IDs match
- [ ] Each completed task has a coherent commit with relevant tests and changelog
- [ ] Required checks passed; unchecked/skipped validation is explained above
- [ ] Python edits formatted with Black and isort, line length 100 (or no Python edits)
- [ ] No secrets, private content, or unsupported product claims in public artifacts
- [ ] Release/version or maintenance exception fields are explicitly explained when applicable
