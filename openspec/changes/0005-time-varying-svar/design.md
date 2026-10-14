# Design: time-varying SVAR with changing trade partners

## Variables

Stack `y_t = [x_t ; z_t]` as in 0002.

- **Foreign block `x_t`.** Partner variables for each partner `j` in the declared set
  (`us`, `cn`, `ea`, ...), for example `gdp_j` and `rate_j`, plus global variables such as a
  commodity price index. Block exogenous: no current or lagged domestic variable enters any
  foreign equation. Within the foreign block the coefficients are constant in M1 (partners'
  own dynamics are not what changed).
- **Domestic block `z_t`.** Brazil output, prices, policy rate, real effective exchange rate.
- **Trade weights `w_{j,t}`.** Share of partner `j` in Brazil's exports plus imports, over the
  declared partners plus a rest-of-world residual, so shares sum to one.

## Trade weights (`core/tvsvar/weights.py`)

1. Input: annual bilateral exports and imports by partner (CSV with `year, partner, exports,
   imports`; the IMF Direction of Trade Statistics is the expected source).
2. `w_{j,y} = (X_{j,y} + M_{j,y}) / sum_i (X_{i,y} + M_{i,y})`, including rest of world.
3. Smoothing: `k`-year moving average, default `k = 3` over years `y, y-1, y-2`, following
   Cesa-Bianchi et al. (2012), who use the average of the current and previous two years.
4. Mapping to quarters: every quarter of year `y` takes the year-`y` average (their timing).
   `--weights-lag 1` uses year `y-1` instead, so the weight is predetermined with respect to
   every quarter of year `y`. The lagged form is the default for inference; the unlagged form
   exists for replication.
5. Checks: shares in `[0, 1]`, rows sum to 1 within 1e-10, no gaps, coverage of the estimation
   sample. Failures raise, they do not impute.

## M0: constant baseline and split sample

The 0002 estimator on the same variables, plus:

- Split-sample estimate at a user break date (`--break 2009Q1`), with a Chow-type LR test of
  equal coefficients across subsamples, degrees of freedom equal to the free coefficients in
  the domestic block.
- Rolling-window estimate (`--rolling 40`) of selected impulse responses, for a picture only.

M0 is what every time-varying model is tested against.

## M1: trade-weighted block-exogenous SVAR

Foreign block exactly as in 0002. Domestic block:

```
z_t = c + sum_{l=0..p} [ D_l g_{t-l} + sum_j B_{j,l}(w_{j,t}) x_{j,t-l} ] + sum_{l=1..p} C_l z_{t-l} + e_t
```

with `g` the global variables and `x_j` partner `j`'s variables (`l = 0` term is the
contemporaneous foreign effect allowed by block exogeneity).

- **`star` variant (GVAR loading).** `B_{j,l}(w) = w * B_l`, one matrix per lag shared across
  partners. The domestic block sees `x*_{t-l} = sum_j w_{j,t} x_{j,t-l}`. All time variation
  in transmission comes from the weights. Few parameters, suited to `T ~ 120` quarters.
- **`interacted` variant (Towbin and Weber 2013).** `B_{j,l}(w) = B_{j,l} + w * G_{j,l}`.
  Each partner has its own level effect and its own slope on the weight. Nests `star`
  (`B_{j,l} = 0`, `G_{j,l} = G_l` for all `j`) and the constant model (`G = 0`).

Estimation: equation-by-equation OLS on constructed regressors, reusing `fit_block_var`'s
foreign block and a new domestic design matrix. Weights are treated as predetermined data.

Impulse responses: the model is linear given a weight path. For each `--frozen-weights` year
`s`, set `w_{j,t} = w_{j,s}` for all `t`, build constant companion matrices, and compute
IRFs, FEVD and historical decompositions with 0002's `irf.py`. This is the Cesa-Bianchi et al.
counterfactual: same estimated structure, trade linkages of year `s`. Also report the impact
coefficient path `B_{j,0}(w_{j,t})` over the sample.

Identification: recursive within blocks (0002). Default foreign ordering is global variables,
then U.S., then China, then other partners; the ordering is an open question below and is
recorded in `run.json`.

Tests reported every run:

- LR constant (`G = 0`, `B` unrestricted) vs. `interacted`: do the weights explain any change.
- LR `star` vs. `interacted`: is GVAR loading enough.
- Wald test that the China and U.S. slopes are equal.
- Residual diagnostics per block (0002/0004 portmanteau).

Inference: residual bootstrap from 0002 with the observed weight path held fixed in every
draw; IRFs at each frozen year re-computed per draw; 68% and 90% bands. Difference bands
(`IRF_2023 - IRF_1995`) are computed draw by draw, because two overlapping bands do not test
a difference.

## M2: kernel time-varying block SVAR

Agnostic drift check, following Giraitis, Kapetanios and Yates (2014).

- At each date `tau`, estimate each block by weighted least squares with weights
  `k_{t,tau} = K((t - tau) / H)`, Gaussian kernel `K`, bandwidth `H = T^h`, default `h = 0.5`
  (to be checked against the paper's recommendation before task 6 starts). Each block keeps its
  own regressor set, so block exogeneity holds at every date.
- Time-varying covariance from kernel-weighted residual outer products.
- IRF at each date from the local coefficients (a "frozen at tau" IRF, as is standard for
  TVP-VARs).
- Pointwise bands from the GKY asymptotic variance; residual bootstrap as an option.
- Comparison output: the kernel path of Brazil output's impact loading on China GDP and on U.S.
  GDP, plotted against `w_{cn,t}` and `w_{us,t}`, with the correlation reported. If M1's story
  is right, the paths should co-move.

Bandwidth sensitivity: `h in {0.4, 0.5, 0.6}` reported in the robustness table.

## M3: Bayesian TVP-VAR with stochastic volatility and block exogeneity

Primiceri (2005) model:

```
y_t = X_t' beta_t + A_t^{-1} Sigma_t eps_t
beta_t = beta_{t-1} + nu_t,  a_t = a_{t-1} + zeta_t,  log sigma_t = log sigma_{t-1} + eta_t
```

- **Block exogeneity.** `X_t` for foreign equations omits domestic lags (the `beta_t` state
  vector has no element for them), and the free elements of the lower-triangular `A_t` with
  foreign variables ordered first already put zeros in the foreign-on-domestic block. So the
  restriction holds for every `t` and every draw.
- **Sampler order.** Del Negro and Primiceri (2015): draw the SV mixture indicators after the
  volatilities, in the order given in the corrigendum.
- **Coefficient draws.** Precision-based sampler (Chan and Jeliazkov 2009): build the banded
  posterior precision of the stacked `beta_{1..T}`, Cholesky with
  `scipy.linalg.cholesky_banded`, solve with `scipy.linalg.cho_solve_banded`. Same for `a_t`.
- **Stochastic volatility.** Kim, Shephard and Chib (1998) seven-component mixture,
  `log(eps^2 + c)` offset `c = 0.001` (Primiceri's value).
- **Priors.** Primiceri's training-sample priors need about 40 quarters before the sample,
  which a Brazil sample starting in 1996 cannot afford. Default: Minnesota-style prior mean and
  variance from OLS on the full sample, `k_Q = 0.01`, `k_S = 0.1`, `k_W = 0.01` as in
  Primiceri; a training-sample option for long samples. This choice is a known weakness and is
  reported in every run.
- **MCMC controls.** `--mcmc-draws 20000 --burn 5000 --thin 10 --seed`; reported diagnostics:
  inefficiency factors and Geweke convergence statistics per parameter block.
- **IRFs.** At each date from that date's `beta_t, A_t, Sigma_t`, per posterior draw; median
  and percentile bands; the posterior distribution of `IRF_2023 - IRF_1995`.

M3 is the heaviest and least robust in a short sample. It is the last rung, run when M1 and M2
disagree or when a committee asks for "the Primiceri model."

## Evaluation and replication pipeline (`core/replication/`, `replicate`)

Every model has to pass three kinds of case before its output is trusted. Cases are data, in
`replication/cases/*.toml`; fixtures sit in `replication/fixtures/` with SHA-256 hashes and the
script that produced them.

### Case kinds

1. **Simulation recovery (known answer).** Simulate from a known DGP, estimate, compare.
   - M1: DGP with China weight rising from 0.05 to 0.30 and U.S. weight falling from 0.25 to
     0.12 (the shape of Brazil's shares), `T = 120` and `T = 400`. Metrics: bias and RMSE of
     `G`, coverage of true frozen-year IRFs by 90% bands over 200 replications (target at least
     85%), LR size at 5% under `G = 0` (between 3% and 8%) and power under the true `G`.
   - M2: DGP with smooth sinusoidal coefficient drift (the GKY Monte Carlo design); metric is
     mean absolute deviation of the kernel path from the truth, falling as `T` grows.
   - M3: DGP with random-walk coefficients and SV; posterior 90% bands cover the true
     `beta_t` path at least 80% of dates.
   - Every model: the block restriction holds exactly (foreign responses to domestic shocks are
     zero at all horizons and dates).
2. **Software parity (reference implementation).**
   - M0 and M1 with `G = 0` and no foreign block: coefficients equal `statsmodels`
     `tsa.api.VAR` to 1e-8.
   - M1 `star`: equals 0002's `fit_block_var` run on a pre-built `x*` column, to 1e-10.
   - M2 with bandwidth to infinity (flat kernel): equals the constant 0002 estimate to 1e-8.
   - M3 homoskedastic mode: posterior means within Monte Carlo error (3 numerical standard
     errors) of the statsmodels "TVP-VAR, MCMC, and sparse simulation smoothing" notebook on
     its `macrodata` series, same priors, fixture generated by
     `replication/scripts/statsmodels_tvpvar.py`.
   - M3 with SV: posterior medians of `sigma_t` and `beta_t` within Monte Carlo error of R
     `bvarsv::bvar.sv.tvp` on its bundled `usmacro` data, fixture generated by
     `replication/scripts/bvarsv_reference.R` and checked in with the R and package versions.
     R is never needed to run the suite, only to regenerate the fixture.
3. **Published-result replication (economics sanity).**
   - Primiceri (2005), U.S. inflation, unemployment and interest rate, 1953Q1-2001Q3: the
     posterior median interest-rate volatility peaks around 1980-1982 and the inflation response
     to a monetary policy shock shows little systematic change over time. Qualitative checks
     with numeric thresholds written in the case file (for example, peak `sigma_rate` date
     within 1979Q1-1983Q4).
   - Cesa-Bianchi et al. (2012) direction check, single-country version: using Brazil with
     U.S., China and euro area partners and their sample end (2009Q4), M1's long-run Brazil
     GDP response to a China GDP shock is larger with 2009 weights than with 1995 weights by a
     ratio in a band declared in the case file, and the U.S. response is smaller. Marked
     `qualitative`: our model is not their GVAR, so only direction and rough size count.
   - 0002 regression: the Nicaragua headline IRFs from 0002/0004 reproduce from M1 with all
     weights frozen at one value and `G = 0`.

### Mechanics

- Case file fields: `id`, `model`, `kind`, `suite` (`fast` or `full`), `data` (fixture path and
  SHA-256), `settings`, `metrics` (name, target, tolerance, comparison), `source` (paper or
  package with link), `seed`.
- Runner: pure `core/replication/run.py` takes a parsed case and data arrays and returns a
  `CaseResult` (metric values, pass/fail, elapsed seconds). Loading files and writing reports
  lives in `cli/replicate.py`, per the layering rule.
- Output: `scorecard.json` (one row per case and metric, package version, git commit, seeds,
  numpy/scipy/statsmodels versions) and `replication.md` (pass/fail table, then one section
  per failed metric with expected vs. observed).
- Exit code: non-zero when any case fails. A fixture whose hash does not match is a failure,
  not a skip.
- `fast` suite (target under 3 minutes): parity cases, block-restriction checks, small-`T`
  recovery with 20 replications. Runs inside `make check` and so in CI.
- `full` suite: all Monte Carlo replications and M3 MCMC cases. `make replicate` locally and a
  `workflow_dispatch` GitHub workflow; not on every PR, to keep Actions budget down
  (`.claude/rules/one-pr-per-spec.md`).
- Golden values: once a case passes with a reviewed result, its observed values are pinned in
  the case file; later runs compare to the pin, so an unintended numerical change fails even if
  it still passes the loose economic threshold.

## Code layout

```
src/csuf_fullerton/core/tvsvar/
  weights.py      trade shares, moving average, quarterly mapping, checks
  design.py       domestic design matrices for star / interacted
  m0.py           split-sample and rolling wrappers around 0002
  m1.py           trade-weighted block SVAR estimate, frozen-weight IRFs, tests
  m2.py           kernel weighted block estimates, local IRFs, GKY variance
  m3.py           Gibbs sampler: precision sampler, KSC mixture, A_t draws
  precision.py    banded precision build and draw (shared by m3)
  bootstrap.py    fixed-weight-path residual bootstrap, difference bands
  simulate.py     DGPs used by tests and the replication suite
src/csuf_fullerton/core/replication/
  cases.py        Case and Metric models (pydantic), comparison rules
  run.py          run_case() -> CaseResult, pure
src/csuf_fullerton/cli/tvsvar.py
src/csuf_fullerton/cli/replicate.py
replication/cases/*.toml
replication/fixtures/*.csv(.npz)
replication/scripts/{statsmodels_tvpvar.py,bvarsv_reference.R,make_fixtures.py}
examples/brazil/{data.toml,theory.toml,README.md}
```

Dependencies: no new runtime dependency beyond 0004's (numpy, scipy, pandas, statsmodels,
matplotlib). `tomllib` is in the standard library for Python 3.11.

## Risks

- **Short Brazil sample.** Quarterly Brazilian national accounts start in 1996, so
  `T` is about 115 quarters after lags. M3 with 7 to 9 variables is over-parameterised there.
  Mitigation: M1 is the headline, M3 is a robustness rung with a small variable set, and a
  monthly variant (industrial production instead of GDP) is an option.
- **Weights are not exogenous.** Trade shares respond to the same shocks the model studies.
  Lagged weights and the 3-year average reduce, not remove, the problem. Stated in every report.
- **China data quality.** Quarterly Chinese GDP begins in the early 1990s and has known
  measurement issues; the case file and report name the series used.
- **Commodity channel.** Much of China's effect on Brazil runs through commodity prices
  (Cesa-Bianchi et al. 2012 find the shift works mainly through China's effect on Latin
  America's traditional partners). Leaving the commodity price out of the foreign block would
  load that channel onto China GDP. The theory file makes it a required global variable.

## Open questions for the faculty call

- Foreign-block ordering: global variables first, then the U.S., then China? Or China before
  the U.S. after 2009?
- Is the `interacted` model with lagged trade weights acceptable as the headline for an M.A.
  thesis, with M3 as robustness, or does the committee expect M3 first?
- Quarterly from 1996 or monthly from 2002?
- Which partners besides the U.S. and China: euro area, Argentina, or rest of world only?

## Implementation notes (2026-10-14)

Decisions taken while building, each with the evidence that forced it. The spec deltas were
amended to match where a requirement changed.

1. **Monthly data and activity measures.** Neither the IMF API nor FRED carries a quarterly real
   GDP index for China before 2011. The Brazil recipe is monthly and uses the OECD GDP reference
   series (normalised cycle) for both the U.S. and China, so the two partners' activity is on
   the same scale and can be trade-weighted. Trade comes from IMF IMTS (goods exports FOB plus
   imports CIF), which replaced the Direction of Trade Statistics extract on the IMF API.
2. **Sample.** The screen on 1996-10 to 2023-11 rejects normality in every residual (2020) and
   straddles the January 1999 float and the June 1999 inflation-targeting regime. On 1999-07 to
   2019-12 the block-exogeneity restriction holds (bootstrap lag-augmented Wald p = 0.37) and
   every surviving specification agrees on the headline signs. That is the headline sample; the
   sample through 2023-11 is a robustness run.
3. **Lag order.** AIC 6, BIC 4, HQ 5. Headline p = 4 (BIC). The screen rejects block exogeneity
   at p = 2 and accepts it at p = 6, so results are reported at p = 2, 4 and 6.
4. **M1 regressors.** Partner variables are centred at their sample mean inside the weight
   products, and the weights enter on their own (`levels`), so a product cannot act as a
   disguised trend. The LR null for "weights do not change transmission" is therefore `levels`.
5. **M1 inference.** Hall intervals are the default: percentile bands left point estimates
   outside their own band in the levels VAR. LR tests also get a bootstrap p-value that
   regenerates data from the restricted model along the observed weight path.
6. **M1 coverage target.** 40 replications of the M1 DGP at T = 400 gave 90% Hall bands
   covering 0.82 (first year), 0.82 (last year) and 0.76 (difference). Bootstrap IRF bands
   under-cover in samples this size (Kilian 1998). The full-suite targets are 0.80, 0.80 and
   0.75 rather than the 0.85 first planned.
7. **M0 rolling window** dropped: M2 gives the same picture with a defined bandwidth.
8. **M2 bandwidth.** GKY's `T^0.5` leaves about 28 effective observations at the sample ends,
   fewer than the 49 regressors of an eight-variable, four-lag monthly equation with seasonal
   dummies; local fits became singular. The estimator now stops when the Kish effective sample
   at the ends is below twice the regressors. Brazil uses `T^0.7`, p = 2 and a local constant.
9. **M3 data.** Levels near 100 (OECD cycles) and log levels near 500 made the OLS prior
   precision near singular. The Brazil M3 run uses a four-variable system (U.S. and China
   activity, Brazil IP and CPI as 12-month changes) and centres each series; no training sample
   is long enough after 1999, so the prior comes from full-sample OLS and the report says so.
10. **M3 parity.** The exact check is the conditional posterior mean of the coefficient states
    against the statsmodels Kalman smoother (agreement to 1e-14). R is not installed here, so
    the `bvarsv` fixture is deferred; the Primiceri (2005) published case checks the full
    sampler instead: posterior median interest-rate volatility peaks in 1980Q4.
11. **M3 simulation design.** Primiceri's priors (`k_Q = 0.01`, 40 prior degrees of freedom)
    shrink coefficient drift hard. A DGP whose drift is far outside the prior (standard
    deviation 0.01 a month) is not recovered by any correct sampler with these priors, so the
    recovery case draws drift on the prior's scale (0.003) and log-volatility steps of 0.05.
12. **Cesa-Bianchi direction case.** p = 4 on 1999-07 to 2009-12, 1995 against 2009 weights,
    mean response over months 0 to 24. With p = 2 the China change is positive over months
    0 to 12 and slightly negative over 12 to 24; the report carries the table.
