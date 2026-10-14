# Changelog

All notable changes to this project are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[SemVer](https://semver.org/). A push to `main` whose version is not yet on
PyPI publishes that version (see `docs/RELEASING.md`).

## [Unreleased]

### Added

- `svar` command: block-exogenous SVAR (Cushman and Zha 1997) estimated block by block, recursive identification, bootstrap impulse-response bands that keep the restriction in every draw, FEVD, historical decomposition, Sims-corrected LR and lag-augmented Wald tests of the restriction, and a `run.json` audit record (#2, change 0002).
- `screen` command: grades every theory-admissible foreign/domestic split on theory and on statistics separately (unit roots, Johansen rank, bootstrap Toda-Yamamoto block Wald with Holm correction, weak exogeneity, instantaneous causality, Clark-West, DirectLiNGAM ordering), ranks them, and checks headline impulse responses for robustness (#2, change 0004).
- `fetch` command: FRED and IMF SDMX series from a TOML recipe into one aligned CSV with a sources sidecar (change 0004).
- `init` command: stores a FRED API key in the OS keychain or a `0600` file; `FRED_API_KEY` takes precedence (change 0004).
- Nicaragua example (`examples/nicaragua/`) and report (`reports/nicaragua/report.md`, Word version, estimation-sample and candidate CSVs).

### Changed

- PR gates exempt bot authors (Dependabot) from the OpenSpec, CHANGELOG, title and issue gates; the version gate still applies. Dependabot commits now use `build(deps)` / `ci(deps)` prefixes. The Claude review and conformance jobs skip bot PRs and, when `ANTHROPIC_API_KEY` is unset, warn and pass instead of failing (#10).

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
