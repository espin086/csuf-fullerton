# Quickstart: rebuild the Nicaragua and Brazil reports from code

Every number in `reports/nicaragua/report.md` and `reports/brazil/report.md` comes from the
commands below, run on data committed in `data/`. Each run writes a `run.json` with the input
file hashes, every setting, the seed and the package version, so a rerun gives the same numbers.

Contents: [1. Install](#1-install) · [2. Nicaragua](#2-nicaragua-block-exogenous-svar) ·
[3. Brazil](#3-brazil-time-varying-svar) · [4. Replication suite](#4-replication-suite) ·
[5. Secret scanning](#5-secret-scanning) · [6. Troubleshooting](#6-troubleshooting)

## 1. Install

Python 3.11 or later.

```
git clone https://github.com/espin086/csuf-fullerton.git
cd csuf-fullerton
make install                       # .venv, editable install, dev tools, pre-commit hooks
source .venv/bin/activate          # puts csuf-fullerton on PATH
csuf-fullerton --version
```

Without `make`: `python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"`.

A FRED API key is optional. Without one, `fetch` uses FRED's public CSV download. To add one
(stored in the OS keychain, never printed or written to outputs):

```
csuf-fullerton init
```

You only need network access to re-download data. Everything else runs offline on `data/`.

## 2. Nicaragua: block-exogenous SVAR

The question: which variables can be treated as exogenous to Nicaragua, and how do U.S. rates,
U.S. activity and commodity prices move Nicaraguan output and prices? Report:
`reports/nicaragua/report.md`. Sample 2002-03 to 2014-06, monthly.

**One command rebuilds every output and checks it against the committed ones:**

```
make nicaragua-check
```

That runs `scripts/reproduce_nicaragua.sh results/nicaragua` (about two minutes), then
`scripts/compare_outputs.py`, which compares every CSV and Markdown output numerically. Expect
`14 files compared, 0 differences.`

**Step by step**, if you want to see each stage:

```
csuf-fullerton fetch examples/nicaragua/data.toml --out data/nicaragua.csv
csuf-fullerton screen data/nicaragua.csv examples/nicaragua/theory.toml --max-lags 4 --out results/nicaragua/screen
csuf-fullerton screen data/nicaragua.csv examples/nicaragua/theory.toml --lags 4 --out results/nicaragua/screen_p4
csuf-fullerton svar data/nicaragua.csv --foreign ffr,us_ip,commodity,ni_er --domestic ni_ip,ni_cpi,ni_m2 --lags 4 --seasonal --dmax 2 --draws 1000 --bands hall --out results/nicaragua/svar_recommended_p4
csuf-fullerton svar data/nicaragua.csv --foreign ffr,us_ip,commodity --domestic ni_ip,ni_cpi,ni_m2,ni_er --lags 1 --seasonal --dmax 2 --draws 1000 --bands hall --out results/nicaragua/svar_thesis_p1
```

The `fetch` line re-downloads the data and is optional; the IMF revises series, so a fresh
download can move numbers slightly. Skip it to reproduce the report exactly.

What to look for:

- `screen/screen.md`: recommended foreign block {ffr, us_ip, commodity, ni_er}, verdict
  "mixed" (U.S. industrial production fails weak exogeneity). Bootstrap lag-augmented Wald
  p = 0.55 at p = 1.
- `svar_recommended_p4/svar.md`: impulse responses, FEVD, and the block-exogeneity tests.

## 3. Brazil: time-varying SVAR

The question: how did Brazil's response to U.S. and China shocks change as China replaced the
United States as Brazil's largest trading partner? China's share of Brazil's goods trade went
from 2% (2000) to 21% (2019); the U.S. share fell from 22% to 14% (three-year averages, IMF
IMTS). Report: `reports/brazil/report.md`. Headline sample 1999-07 to 2019-12, monthly
(inflation targeting, before COVID).

**One command rebuilds every output and checks it against the committed ones:**

```
make brazil-check
```

`QUICK=1 bash scripts/reproduce_brazil.sh results/brazil_quick` runs the same steps with fewer
bootstrap and MCMC draws in about five minutes; its bands will differ from the report's.

**Step by step.** The order matters: test exogeneity and the lag order before estimating.

```
# 0. Data (optional: the committed files reproduce the report exactly)
csuf-fullerton fetch examples/brazil/data.toml --out data/brazil.csv
csuf-fullerton trade-weights --country BRA --partners us=USA,cn=CHN --out data/brazil_trade.csv

# 1. Exogeneity and lag order: the screen, at the criteria's choice and at p = 2 and 6
csuf-fullerton screen data/brazil.csv examples/brazil/theory.toml --max-lags 6 --start 1999-07 --end 2019-12 --out results/brazil/screen_it
csuf-fullerton screen data/brazil.csv examples/brazil/theory.toml --lags 2 --start 1999-07 --end 2019-12 --out results/brazil/screen_it_p2
csuf-fullerton screen data/brazil.csv examples/brazil/theory.toml --lags 6 --start 1999-07 --end 2019-12 --out results/brazil/screen_it_p6

# 2. M0: constant baseline and parameter stability (Chow at 2009-01, sup-LR over all dates)
csuf-fullerton tvsvar data/brazil.csv --model m0 --foreign commodity,us_act,cn_act,ffr --domestic br_ip,br_cpi,br_selic,br_er --lags 4 --seasonal --start 1999-07 --end 2019-12 --break 2009-01 --out results/brazil/m0_p4

# 3. M1: trade-weighted SVAR, IRFs at 2000, 2009 and 2019 weights
csuf-fullerton tvsvar data/brazil.csv --model m1 --foreign commodity,us_act,cn_act,ffr --domestic br_ip,br_cpi,br_selic,br_er --trade data/brazil_trade.csv --partners us=us_act,cn=cn_act --headline br_ip:cn_act,br_ip:us_act,br_cpi:cn_act,br_er:cn_act --lags 4 --seasonal --start 1999-07 --end 2019-12 --frozen-years 2000,2009,2019 --draws 1000 --out results/brazil/m1_p4

# 4. M2: kernel drift check
csuf-fullerton tvsvar data/brazil.csv --model m2 --foreign commodity,us_act,cn_act,ffr --domestic br_ip,br_cpi,br_selic,br_er --trade data/brazil_trade.csv --partners us=us_act,cn=cn_act --headline br_ip:cn_act,br_ip:us_act --lags 2 --no-trend --seasonal --bandwidth-exp 0.7 --start 1999-07 --end 2019-12 --out results/brazil/m2_p2

# 5. M3: TVP-VAR with stochastic volatility on a four-variable system
csuf-fullerton tvsvar data/brazil.csv --model m3 --foreign commodity,us_act,cn_act,ffr --domestic br_ip,br_cpi,br_selic,br_er --m3-vars us_act,cn_act,br_ip,br_cpi --m3-yoy br_ip,br_cpi --m3-lags 2 --headline br_ip:cn_act,br_ip:us_act --irf-dates 2002-06,2009-06,2019-06 --start 1999-07 --end 2019-12 --out results/brazil/m3
```

`scripts/reproduce_brazil.sh` also runs M1 at p = 2 and 6, the `star` variant, and the sample
through 2023-11. Command options are explained in `docs/tvsvar.md`.

What to look for:

- `screen_it/screen.md`: foreign block {commodity, us_act, cn_act, ffr}, theory grade A.
  Compare with `screen_it_p2`, where too few lags make the restriction look rejected.
- `m1_p4/m1.md`: the "Is the time variation real?" table (read the bootstrap p column), the
  frozen-weight table, and `frozen_irf.png` / `frozen_diff.png`.
- `m2_p2/m2.md`: whether the kernel estimate of Brazil's loading on China activity moves with
  China's trade weight.
- `m3/m3.md`: MCMC diagnostics first, then volatilities and IRFs by date.

## 4. Replication suite

Before trusting any estimator, check it reproduces known answers.

```
csuf-fullerton replicate --list            # every case, and a check that each model has all three kinds
make replicate                             # fast suite, about a minute (also part of make check and CI)
make replicate-full                        # adds the Monte Carlo and long MCMC cases, about an hour
```

The scorecard is `results/replication/scorecard.json`; `replication.md` is the readable version.
What the fast suite proves, case by case:

| Case | Proves |
|---|---|
| `m0-parity-statsmodels` | The VAR estimator equals statsmodels to 1e-8 |
| `m0-nicaragua-regression` | The committed Nicaragua impulse responses still come out of the code |
| `m0-sim-break-power` | The sup-LR test detects drifting transmission in simulated data |
| `m1-parity-constant` | M1 without weights equals the change 0002 estimator to 1e-10 |
| `m1-sim-coverage-fast`, `m1-sim-lr-size-fast` | M1 bands cover the true IRFs; the LR test has size and power |
| `m1-cesa-bianchi-2012-direction` | China's effect on Brazil rises and the U.S. effect falls from 1995 to 2009 weights |
| `m2-parity-flat`, `m2-sim-sinusoid` | The kernel estimator reduces to OLS and tracks a known drift |
| `m3-parity-kalman` | The M3 coefficient sampler equals the statsmodels Kalman smoother to 1e-8 |
| `m3-primiceri-2005-fast` | U.S. interest-rate volatility peaks around 1980, as in Primiceri (2005) |
| `m3-sim-coverage-fast` | M3 recovers simulated coefficient and volatility paths |

Fixtures are pinned by SHA-256: if `data/brazil.csv` changes, the cases that use it fail until
you regenerate the case files (`replication/scripts/make_cases.py`) and review the new values.

## 5. Secret scanning

```
make secrets
```

runs gitleaks over the git history and over the working tree, including uncommitted `data/`
and `results/`. The same history scan runs in CI, pre-commit runs gitleaks on every commit,
and the GitHub repository has secret scanning and push protection turned on. The FRED key is
read from the environment, the keychain or a `0600` file, and a test checks it never reaches a
fetched CSV, a sources file or `run.json`.

## 6. Troubleshooting

- **`bandwidth ... leaves N effective observations`** (M2): the kernel window is too narrow for
  the number of regressors. Raise `--bandwidth-exp`, cut `--lags`, or drop `--trend`.
- **`leading minor not positive definite`** (M3): the prior is near singular. Use fewer
  variables, `--m3-yoy` for trending series, or a training sample (`--training 40`).
- **`no trade value for partner ...`**: the trade table has a gap in a year the sample needs;
  check the IMF download or shorten the sample.
- **A case fails with `fixture hash mismatch`**: a pinned data file changed. That is the point;
  regenerate the case files only after you have checked why the data changed.
