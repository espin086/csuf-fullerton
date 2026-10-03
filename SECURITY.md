# Security

Report a vulnerability privately to the repository owner. Do not open a public issue.
Expect an acknowledgement within 72 hours.

## What the repo enforces on every PR

- `pip-audit --strict` over the resolved dependency tree
- `ruff --select S` (bandit rules) over `src/`
- Trivy scan of the built image, CRITICAL and HIGH block
- `gitleaks` history scan in CI, plus `gitleaks` and `detect-private-key` in pre-commit
- CodeQL `security-and-quality` on push, PR, and weekly (public repos, or `CODEQL_ENABLED=true`)
- Dependabot weekly for pip and GitHub Actions
- The image runs as a non-root user; the sdist excludes `.claude/`
- Claude PR review checks secrets handling, input validation and dependency changes
