# csuf-fullerton

Block-exogenous structural VARs for small open economies, with a screen that decides which
variables can be treated as exogenous before the SVAR is estimated.

Built for ECON 505 research papers and M.A. VAR theses at CSUF. Standard and recursive SVARs are
easy in EViews or Stata; block-exogenous SVARs (Cushman and Zha 1997) are not, and neither tool
helps you justify the split between foreign and domestic variables. This package does both.

First application: [Nicaragua report](reports/nicaragua/report.md).

## What it does

| Command | What it answers |
|---|---|
| `csuf-fullerton init` | Stores your FRED API key securely (OS keychain, or a `0600` file) |
| `csuf-fullerton fetch` | Downloads FRED and IMF series from a recipe into one aligned CSV |
| `csuf-fullerton screen` | Which variables are exogenous to the domestic economy, judged by theory and by the data, across every candidate split |
| `csuf-fullerton svar` | Impulse responses, variance decompositions and the block-exogeneity tests for the split you choose |

### The screen, in one paragraph

You write a theory file that gives each variable a prior (`exogenous`, `candidate`,
`endogenous`) with a reason and a citation. The screen enumerates every foreign block that
theory allows, then for each one runs the tests applied researchers use: Toda-Yamamoto
lag-augmented Granger tests (valid when series have unit roots) with a bootstrap p-value and a
Holm correction across candidates, the Sims-corrected LR test, instantaneous causality, weak
exogeneity of the foreign block when the system is cointegrated, a Clark-West out-of-sample
test, information criteria, residual and stability checks, and a DirectLiNGAM causal ordering
of the residuals as advisory evidence on contemporaneous direction. Each candidate gets a
theory grade and a statistical verdict, kept separate, and a rank. The report names a
recommendation and a runner-up and shows whether the headline impulse responses keep their
sign across every surviving specification and alternative ordering. It recommends; you choose.

Why separate grades: Granger tests only speak to lags. Whether the foreign block reacts to
domestic shocks within the month is an identifying assumption that the data cannot test
without non-Gaussianity, so the report says which claims rest on data and which on theory.
Design and sources: `openspec/changes/0004-exogeneity-screening/design.md`.

## Quick start

```
make install                  # venv + editable install + dev tools
.venv/bin/csuf-fullerton init # optional; paste a key from https://fred.stlouisfed.org/docs/api/api_key.html

csuf-fullerton fetch examples/nicaragua/data.toml --out data/nicaragua.csv
csuf-fullerton screen data/nicaragua.csv examples/nicaragua/theory.toml --out results/screen
csuf-fullerton svar data/nicaragua.csv \
  --foreign ffr,us_ip,commodity,ni_er --domestic ni_ip,ni_cpi,ni_m2 \
  --lags 4 --seasonal --dmax 2 --draws 1000 --bands hall --out results/svar
```

`screen` writes `screen.md`, `candidates.csv`, figures and `run.json`. `svar` writes `svar.md`,
`irf.csv` (responses, bands and FEVD in long form), `irf.png` and `run.json`. Every `run.json`
records the input file's SHA-256, every setting and the package version, so a run can be
repeated exactly.

## FRED API key

The key is looked up in this order:

1. `FRED_API_KEY` environment variable
2. OS keychain (service `csuf-fullerton`), written by `csuf-fullerton init`
3. `~/.config/csuf-fullerton/credentials.toml`, mode `0600`, written by `init --file` or when
   no keychain is available

`init` reads the key with a hidden prompt and never prints it; `init --check` makes one FRED
request to verify it. Without a key, `fetch` falls back to FRED's public CSV download. The key is
never written to outputs, logs or `run.json`.

## Another country

Copy `examples/nicaragua/`, then edit:

- `data.toml`: one `[[series]]` per variable. `source = "fred"` takes an `id`; `source = "imf"`
  takes a `dataflow` and `filters` on the IMF SDMX dimensions. `transform` is `level`, `log` or
  `log100`. FRED holds mostly annual data for small economies, so monthly domestic series
  usually come from the IMF.
- `theory.toml`: priors with reasons, candidate size bounds, alternative orderings of the
  domestic block, and the `[[headline]]` responses you want checked for robustness.

## Layout

```
src/csuf_fullerton/core/svar/  estimator, tests, screening, report text (pure, no I/O)
src/csuf_fullerton/core/recipe.py  data recipe parsing and alignment
src/csuf_fullerton/data/       FRED and IMF drivers, credential storage
src/csuf_fullerton/cli/        Typer commands and matplotlib figures
examples/nicaragua/            data recipe and theory file
reports/nicaragua/             report and committed outputs
openspec/changes/              0002 (estimator) and 0004 (screening) specs
```

## Contributing

Spec-driven (OpenSpec): issue, planning change, then implementation. `make check` runs ruff,
mypy, the offline test suite and `openspec validate`. See `CONTRIBUTING.md` and
`docs/AGENT-HARNESS.md`. The repository started from a Python CLI template; release and hosting
docs are in `docs/RELEASING.md` and `docs/HOSTING-PROFILES.md`.
