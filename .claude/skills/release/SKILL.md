---
name: release
description: Prepare a release PR (version bump + CHANGELOG section). Publishing happens in release.yml on merge; this skill never publishes.
arguments: [version]
allowed-tools: Read, Edit, Bash(git:*), Bash(gh pr:*), Bash(pytest:*), Bash(python .github/scripts/changelog_section.py:*)
---

Apply the workflow in `CONTRIBUTING.md` before these steps. For implementation, verify
the linked issue and planning PR merged into the default branch. Work in small task commits;
use the standard PR template. An active change folder alone is insufficient authorization.

# /release <x.y.z>

1. On `main`, pulled. `git switch -c release/v$0`.
2. `src/project_template/__about__.py`: `__version__ = "$0"`.
3. `CHANGELOG.md`: rename `[Unreleased]` to `[$0] - <today>`, add an empty `[Unreleased]`
   above, update the two link refs at the bottom.
4. `pytest tests/test_packaging.py tests/test_release_script.py -q` and
   `python .github/scripts/changelog_section.py $0`.
5. Commit `release: v$0`, push, `gh pr create --title "release: v$0"`.
6. Tell the user: merging publishes to PyPI, Docker Hub, GHCR and creates the GitHub release
   only if `RELEASE_ENABLED=true` (see `docs/RELEASING.md`).
