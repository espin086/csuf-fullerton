# Changelog

All notable changes to this project are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[SemVer](https://semver.org/). A push to `main` whose version is not yet on
PyPI publishes that version (see `docs/RELEASING.md`).

## [Unreleased]

### Changed

- Every pull request closes a GitHub issue. PR gate 5 checks GitHub's `closingIssuesReferences`, and a `pr-issue-link` hook stops Claude Code and Codex from opening an unlinked PR. Planning PRs close a `Plan:` sub-issue (#7).

## [0.1.0] - 2026-09-16

### Added

- Template scaffolding: `src/` layout with pure `core/` and thin `cli/`, architecture tests,
  CI (ruff, mypy, pytest matrix, build smoke, Docker build + Trivy, pip-audit, CodeQL),
  version-gated release to PyPI, Docker Hub and GHCR, PR gates (OpenSpec, CHANGELOG,
  SemVer, Conventional Commits), Claude PR review, the shared Claude/Codex harness under
  `.claude/` and `.agents/`, and a `context-lake/` folder for non-code project context.

[Unreleased]: https://github.com/espin086/template-python-cli/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/espin086/template-python-cli/releases/tag/v0.1.0
