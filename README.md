# csuf-fullerton

[Project home page](site/index.html) · [Contribution workflow](CONTRIBUTING.md) · [Claude/Codex harness](docs/AGENT-HARNESS.md) · [Hosting profiles](docs/HOSTING-PROFILES.md)

Template for a Python CLI + library repo. Spec-driven (OpenSpec), Claude Code and Codex
harness, and a release pipeline that ships to PyPI, Docker Hub, GHCR and GitHub Releases
from a version bump.

## Start a project

```
gh repo create <owner>/<name> --template <owner>/template-python-cli --private --clone
cd <name>
python scripts/rename.py <name>            # renames package, dist, image
make install                               # uv venv, editable install, pre-commit
make check                                 # ruff, mypy, pytest, openspec validate
```

Then follow `docs/RELEASING.md` one-time setup (PyPI trusted publisher, `ANTHROPIC_API_KEY`,
`scripts/apply-ruleset.sh`, `RELEASE_ENABLED`).

## How work flows

| Step | Tool | Enforced by |
|---|---|---|
| Spec | `openspec new change <slug>` (`/propose`) | `pr-gates.yml` fails PRs without a change folder |
| Build | test first, `core/` pure, `cli/` thin | `tests/architecture/`, `mypy --strict`, ruff |
| Ship | branch, `make check`, PR (`/ship`) | ruleset: PR required, `All checks passed` + `PR gates` |
| Review | two Claude passes + `@claude` on demand | `claude-review.yml` |
| Release | bump `__about__.py` + CHANGELOG (`/release`) | `release.yml`, version-gated |
| Evolve | weekly `template-sync.yml` PR | `.templatesyncignore` protects project files |

## Layout

```
src/csuf_fullerton/   core/ (pure logic)  cli/ (Typer adapter)  __about__.py (version)
tests/                  core, cli, architecture, packaging, release-script and gate contracts
openspec/               config.yaml, project.md, changes/, specs/
.claude/                settings.json, hooks/, agents/, skills/, rules/  (see docs/HARNESS.md)
.github/                workflows/{ci,pr-gates,claude-review,release,codeql,labeler,template-sync}.yml
Dockerfile compose.yaml Makefile .pre-commit-config.yaml
```

## Docs

- `CONTRIBUTING.md` the loop from idea to merged PR
- `docs/RELEASING.md` release flow and one-time setup
- `docs/HARNESS.md` what each hook, agent, skill and rule does and why it is small
- `SECURITY.md` what every PR is checked for
