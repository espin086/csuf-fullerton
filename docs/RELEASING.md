# Releasing

Releases are version-gated pushes to `main`. There is no release branch and no manual upload.

## Every release

1. Bump `__version__` in `src/csuf_fullerton/__about__.py` (SemVer: `1.2.3`, `1.2.3rc1`,
   `1.2.3.dev0`).
2. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [1.2.3] - YYYY-MM-DD`, add a fresh empty
   `[Unreleased]` above it, update the link refs at the bottom.
3. Open the PR with title `release: v1.2.3`. The PR gate checks the CHANGELOG section exists.
4. Merge. `release.yml` runs: `decide` (is 1.2.3 on PyPI?) then `verify` (full CI) then
   `build` then `publish-pypi` and `publish-image` then `github-release`.

Nothing publishes twice: PyPI versions are immutable, so the `decide` job is the idempotency key.

## One-time setup for a new repo made from this template

1. **PyPI Trusted Publishing.** On pypi.org add a pending publisher: project = your dist name,
   owner = your GitHub owner, repo = your repo, workflow `release.yml`, environment `pypi`.
   Repeat on test.pypi.org with environment `testpypi`.
2. **GitHub environments.** Settings > Environments: create `pypi` and `testpypi`. Add yourself
   as a required reviewer on `pypi` if you want a manual approval step.
3. **Docker Hub.** Add repo or org secrets `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN`, and set
   `IMAGE_NAME` in `release.yml`. GHCR needs nothing; it uses the workflow's own permission.
4. **Arm it.** Repo variable `RELEASE_ENABLED=true`. Until then pushes to `main` log "not armed"
   and publish nothing. `workflow_dispatch` to `testpypi` ignores the arm switch.
5. **Claude review.** Repo (or org) secret `ANTHROPIC_API_KEY`, and the `claude` GitHub App
   installed on the repo or owner.
6. **CodeQL (optional).** Private repos need GitHub Advanced Security for code scanning.
   The CodeQL workflow skips itself unless the repo is public or the repo variable
   `CODEQL_ENABLED=true`. gitleaks, pip-audit, Trivy and ruff `S` rules run regardless.
7. **Ruleset.** `scripts/apply-ruleset.sh` applies the same branch rules this template uses:
   PRs required on `main`, no approvals required, `All checks passed` + `PR gates` required,
   no force push, no deletion.

## Dry run

`Actions > Release > Run workflow > testpypi` publishes the current version to TestPyPI
without touching PyPI, Docker Hub or the GitHub release.

## Shipping past an unfixable advisory

`pip-audit` and Trivy block on known vulnerabilities. If a transitive advisory has no fix,
add `--ignore-vuln <ID>` (pip-audit) or a `.trivyignore` entry with a comment naming the
advisory and the date you will revisit it. Record the decision in an OpenSpec change.
