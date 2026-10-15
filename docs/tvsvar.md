# Time-varying SVARs: `tvsvar`, `trade-weights` and `replicate`

Change 0005. The design, with sources, is `openspec/changes/0005-time-varying-svar/design.md`.
For copy-paste runs of the Brazil and Nicaragua reports, see `QUICKSTART.md`.

## The question

A small open economy's response to a foreign shock depends on how much it trades with the
country the shock comes from. When the main trading partner changes (Brazil: the United States
to China, which passed the U.S. in 2009), a constant-coefficient SVAR averages two different
economies. `tvsvar` estimates the change four ways, each tested against the one before it.

| Model | What varies | Estimation | Use it for |
|---|---|---|---|
| `m0` | Nothing | 0002 block-exogenous OLS | Baseline, Chow and sup-LR stability tests |
| `m1` | Transmission, through trade weights | OLS with weight interactions | Headline: frozen-weight IRFs and their differences |
| `m2` | Every coefficient, smoothly | Kernel weighted least squares | Does the data's drift look like the weights? |
| `m3` | Coefficients, contemporaneous relations, volatilities | Gibbs sampler | Primiceri (2005) robustness on a small system |

Every model keeps the foreign block exogenous at every date and in every bootstrap or posterior
draw: foreign variables never respond to domestic shocks.

## Data

1. A monthly CSV with a `date` column (`YYYY-MM`), from `fetch` or your own.
2. For `m1` and the M2 weight comparison, an annual trade table:

```
csuf-fullerton trade-weights --country BRA --partners us=USA,cn=CHN --out data/brazil_trade.csv
```

This downloads goods exports (FOB) plus imports (CIF) by partner from the IMF IMTS dataflow,
with `G001` (world) as the total. The CSV is long: `year, partner, value`.

Weights are the partner's share of total trade averaged over `--weight-window` years (default
3, as in Cesa-Bianchi et al. 2012), lagged `--weights-lag` years (default 1, so the weight is
fixed before the year's shocks). A missing value in any year the sample needs stops the run.

## Before any VAR: screen

Run `screen` first (change 0004). It tests integration order, cointegration rank, lag-augmented
Granger causality from domestic to foreign, block exogeneity, weak exogeneity and the residual
causal order, for every admissible foreign block. Re-run it at more than one lag order: the
Brazil screen accepts block exogeneity at p = 4 and p = 6 and rejects it at p = 2, so the
conclusion depends on enough lags.

## `tvsvar` options

| Option | Models | Meaning |
|---|---|---|
| `--foreign`, `--domestic` | all | Blocks, in recursive order |
| `--trade`, `--partners us=us_act,cn=cn_act` | m1, m2 | Trade table and each partner's foreign columns (`+` joins several) |
| `--variant` | m1 | `interacted` (default), `star`, `levels`, `constant` |
| `--frozen-years 2000,2009,2019` | m1 | IRFs with weights held at each year; differences are against the first |
| `--headline br_ip:cn_act,...` | m1, m2, m3 | Pairs tabulated and plotted |
| `--draws`, `--level`, `--bands` | m0, m1 | Bootstrap draws, band coverage, `hall` (default) or `percentile` |
| `--lr-draws` | m1 | Bootstrap draws for the LR tests of time variation (0 skips) |
| `--break 2009-01`, `--break-draws` | m0 | Chow date and bootstrap draws for Chow and sup-LR |
| `--bandwidth-exp 0.7`, `--kernel-step` | m2 | Bandwidth `T^h`; the run stops if the window is too small for the regressors |
| `--m3-vars`, `--m3-yoy`, `--m3-lags` | m3 | Small system (foreign first), columns used as 12-month changes, lags |
| `--mcmc-draws`, `--burn`, `--thin`, `--training` | m3 | Gibbs controls; `--training n` takes the prior from the first n rows |
| `--irf-dates 2002-06,2019-06` | m3 | Dates at which posterior IRFs are reported |
| `--lags`, `--trend`, `--seasonal`, `--start`, `--end`, `--seed`, `--out` | all | As in `svar` |

Outputs: `<model>.md`, `irf.csv` (long form), model-specific CSVs (`loading_path.csv`,
`kernel_path.csv`, `m3_volatility.csv`), figures, and `run.json` with the data and trade file
hashes and every setting.

## Reading M1

- **Frozen weights.** IRFs at 2019 weights answer: with today's estimated structure and 2019's
  trade linkages, how does Brazil respond? Differences between years are bootstrapped draw by
  draw; a `*` marks a band that excludes zero.
- **Tests.** "weights do not change transmission" compares the `levels` model (weights enter, but
  not as interactions) with `interacted`. "GVAR star loading is enough" asks whether one shared
  slope per variable type explains it. Read the bootstrap p-values; the chi-square ones over-reject
  with persistent regressors.
- **Caveat.** Trade shares respond to the same shocks the model studies. Lagged, smoothed weights
  reduce the problem; they do not remove it.

## `replicate`

```
csuf-fullerton replicate --list                 # cases, and a check that every model has all three kinds
csuf-fullerton replicate --suite fast           # runs in make check and CI, about a minute
csuf-fullerton replicate --suite full           # adds the Monte Carlo and long MCMC cases
csuf-fullerton replicate --case m3-primiceri-2005
```

Each case in `replication/cases/*.toml` pins its data by SHA-256, names its source, and states
pass rules. Kinds: `simulation` (known DGP), `parity` (reference software), `published` (a paper's
headline result, marked `qualitative` when only direction and rough size can match), and
`regression` (a committed result that must not move). Pinned `golden` values catch numerical
drift that still passes the economic threshold. Output: `scorecard.json` and `replication.md`.

To rebuild fixtures and case files:

```
.venv/bin/python replication/scripts/make_primiceri_fixture.py
.venv/bin/python replication/scripts/make_cases.py
.venv/bin/python replication/scripts/make_cases.py --pin results/replication/scorecard.json
```
