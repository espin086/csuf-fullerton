---
paths: ["src/**", "tests/**"]
---
# Testing

Write the failing test first. Tests live by what they prove: `tests/core`, `tests/cli`,
`tests/architecture`, `tests/test_packaging.py`. Known-answer fixtures for logic; `CliRunner`
for adapters; `@pytest.mark.network` for anything that leaves the machine (excluded in CI).
Coverage floor 85% (`make test`). A scenario in `openspec/specs` with no test is a bug.
