---
paths: ["src/**"]
---
# Layering

- `core/`: pure functions over plain data. No I/O, no logging, no `os.environ`, no `typer`,
  no `rich`. Docstrings cite the formula or rule they implement.
- `cli/`: parse arguments, call `core`, format output. Every command supports `--format`
  when it prints data. Exit codes: 1 internal, 2 usage, 3 config, 4 provider, 5 insufficient data.
- Anything swappable (storage, providers) sits behind a `Protocol` in `data/` with a shared
  conformance test. Drivers only in `data/adapters/`.
- Enforced by `tests/architecture/test_layering.py`. Extend `FORBIDDEN_IN_CORE` as needed.
