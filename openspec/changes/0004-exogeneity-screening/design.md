# Design: exogeneity screening and specification comparison

## 1. What "exogenous" has to mean here

Engle, Hendry and Richard (1983) separate three claims. A block-exogenous SVAR for a small open
economy makes two of them about the foreign block `x_t` relative to the domestic block `z_t`:

| Claim | In the VAR | Testable from the data? |
|---|---|---|
| **Lagged exogeneity** (Granger non-causality, `z` does not help predict `x`) | upper-right block of `A1..Ap` is zero | Yes. Block Wald and LR tests, lag-augmented when series are integrated |
| **Contemporaneous exogeneity** (predeterminedness, `x_t` does not respond within the period to domestic shocks) | upper-right block of `A0` is zero | Not from second moments. The instantaneous causality test is symmetric; it shows residual correlation exists, not its direction (Lütkepohl 2005, 3.6.3). Partial evidence only from non-Gaussianity |
| **Weak exogeneity for long-run parameters** (Johansen 1992) | foreign rows of the loading matrix `alpha` are zero when the system is cointegrated | Yes, when a cointegrating rank is found |

Strong exogeneity is weak exogeneity plus Granger non-causality. The screen reports every row of
this table separately and never sums them into one number that hides which claim failed.

## 2. What researchers do, and what the screen copies

- **Theory first.** Cushman and Zha (1997), Kim and Roubini (2000), Zha (1999) and Maćkowiak
  (2007) fix the foreign block by the small-open-economy argument: the domestic economy is too
  small to move U.S. policy, U.S. activity or world prices. The theory file records this
  argument per variable, with a citation, so it is reviewable.
- **Test the lag restriction.** Block exogeneity LR with Sims' small-sample correction against
  the unrestricted VAR (Cushman and Zha 1997, Zha 1999). In levels with unit roots, use
  Toda-Yamamoto (1995) / Dolado-Lütkepohl (1996): estimate with `p + d_max` lags, test only the
  first `p`. The resulting Wald statistic is asymptotically chi-square whatever the integration
  and cointegration properties.
- **GVAR practice for weak exogeneity.** Pesaran, Schuermann and Weiner (2004) and the GVAR
  papers that follow test whether the foreign ("star") variables load on the domestic error
  correction terms. The screen runs the same F-test when Johansen finds `0 < rank < k`. Cointegration among
  foreign variables alone is allowed: the test conditions on the foreign-only error-correction
  terms and asks whether the full-system terms (which involve domestic variables) add anything.
- **Report orderings and alternatives as robustness.** Kilian and Lütkepohl (2017, ch. 8)
  and the monetary SVAR literature report results across orderings and variable sets. Recursive
  orderings inside a block are observationally equivalent (same likelihood), so the data cannot
  rank them; the screen says so and only checks whether headline responses keep their sign.
- **Data-driven direction where it is possible.** Swanson and Granger (1997) and Demiralp and
  Hoover (2003) use residual conditional independence; LiNGAM-type methods (Hyvärinen and
  Smith 2013; Lanne, Meitz and Saikkonen 2017) use non-Gaussianity. The screen computes the
  Hyvärinen-Smith pairwise measure between every foreign and domestic residual, reports it only
  when Jarque-Bera rejects normality for both residuals, and labels it advisory.
- **Guard against pretesting.** Many candidates means many tests. Block-exogeneity p-values are
  Holm-adjusted across the candidate family. The screen ranks; it does not select and then
  pretend the selected model was known in advance (Leeb and Pötscher 2005).

## 3. Inputs

### Data CSV
A `date` column plus numeric columns, already transformed (logs etc.). `fetch` produces it.

### Theory file (TOML)

```toml
[meta]
country = "Nicaragua"
frequency = "M"
deterministic = { trend = true, seasonal = true }

[[variable]]
name = "ffr"
prior = "exogenous"        # exogenous | candidate | endogenous
rationale = "U.S. policy rate; Nicaragua is far too small to affect FOMC decisions."
source = "Cushman and Zha (1997); Maćkowiak (2007)"

[[variable]]
name = "commodity"
prior = "candidate"
rationale = "World price index; Nicaragua is a price taker but coffee and gold weights matter."
source = "Kim and Roubini (2000)"

[candidates]
min_foreign = 1            # smallest foreign block to enumerate
max_foreign = 4

[[ordering]]               # optional alternative within-block orderings (robustness only)
domestic = ["ni_er", "ni_ip", "ni_cpi", "ni_m2"]

[[headline]]               # responses the robustness check tracks
response = "ni_ip"
shock = "ffr"
```

Rules:
- `endogenous` variables are never placed in the foreign block.
- Candidate foreign blocks are every subset of `exogenous ∪ candidate` variables with size in
  `[min_foreign, max_foreign]`, foreign order as listed in the file.
- The domestic block is every other variable, in file order.
- Explicit `[[spec]]` tables (`name`, `foreign`, `domestic`) are added on top of the
  enumeration, for splits a researcher wants to see that the rules would not generate.

## 4. Stages

**Stage 1. Integration and cointegration (whole system).**
ADF (constant and trend, lag by AIC) and KPSS (trend) per series. Order `d_i = 0` when ADF
rejects at 5% and KPSS does not; `d_i = 1` otherwise, flagged "conflict" when both reject or
neither does. The differenced series gets the same check, so a series can be graded `d = 2`.
`d_max = max d_i`, capped at 2. Johansen trace test (trend case matching the theory file) for
the rank, with the Reinsel and Ahn (1992) small-sample scaling `(T - k p) / T`. Seasonal
dummies are partialled out first because the Johansen routine has no seasonal option.

**Stage 2. Lag order.** AIC, BIC and HQ on the unrestricted VAR in levels with the
deterministic terms, `p` from 1 to `max_lags`. The screen uses BIC's choice by default (the
most conservative with many parameters per equation) and reports all three; `--lags` overrides.

**Stage 3. Pairwise evidence (whole system, not per candidate).**
- Lag-augmented Granger matrix: for every ordered pair `(j -> i)`, Wald test of the first `p`
  lags of `j` in equation `i` of the `p + d_max` levels VAR with all variables. Holm-adjusted
  across all `k(k-1)` pairs.
- Instantaneous causality per pair from the unrestricted residual correlation (`T r^2`, chi-square 1).
- Non-Gaussian direction measure per pair (Hyvärinen-Smith `R`, positive means row variable
  causes column variable contemporaneously), with the Jarque-Bera gate.

**Stage 4. Per-candidate battery.** For each candidate split `(F, D)`:

| Test | Statistic | Null | Reading |
|---|---|---|---|
| Block exogeneity LR (Sims correction) | `(T - c)(ln|S_r| - ln|S_u|)`, df `k_F k_D p` | `D` does not Granger-cause `F` | the 0002 test |
| Block exogeneity, lag-augmented Wald | TY Wald, df `k_F k_D p`, residual-bootstrap p under the null (Hacker and Hatemi-J 2006) | same, robust to unit roots | **primary verdict** |
| Block instantaneous causality | `T(ln|S_FF| + ln|S_DD| - ln|S|)`, df `k_F k_D` | residual blocks uncorrelated | rejection is normal; recursive identification orders it |
| Weak exogeneity (when rank >= 1) | F-test of ECT loadings in `Δx` equations | `F` does not adjust to domestic disequilibrium | rejection breaks long-run exogeneity |
| Pseudo out-of-sample, h = 1 | Clark-West MSPE-adjusted, foreign equations, expanding window over the last 25% | domestic lags do not improve foreign forecasts | enters the verdict only when `d_max = 0`; Clark-West asymptotics assume stationarity |
| Information criteria | AIC, BIC, HQ of the restricted system | | fewer parameters, comparable likelihood across candidates on the same sample |
| Residual checks | adjusted portmanteau (h = 12), max companion root | | flags, not grades |
| Theory direction | DirectLiNGAM causal order of the residuals (Shimizu et al. 2011): share of foreign-domestic pairs ordered foreign first, with a bootstrap 5th percentile | | advisory |

All candidates use the same sample (the longest common one after lags), so likelihoods and
criteria are comparable.

**Stage 5. Grade and rank.**

Theory grade:
- **A** foreign block is exactly the `exogenous` variables plus any subset of `candidate`s, and
  every `exogenous` variable is in it.
- **B** every foreign variable is `exogenous` or `candidate`, but at least one `exogenous`
  variable is placed in the domestic block (it then responds to domestic shocks, which theory
  says it should not).
- **X** inadmissible: an `endogenous` variable in the foreign block. Reported, never ranked.

Statistical verdict, primary test = the bootstrap lag-augmented Wald, Holm-adjusted across
candidates at `alpha` (default 0.05). The bootstrap uses at least `4 m / alpha` draws for a
family of `m` candidates, because the smallest attainable p-value `1 / (B + 1)` must sit below
`alpha / m` for Holm to be able to reject at all:
- **supported** adjusted p >= alpha, and weak exogeneity not rejected (or not applicable).
- **mixed** adjusted p >= alpha but weak exogeneity rejected (Holm within the block), or
  unadjusted p < alpha only, or (stationary data only) Clark-West rejects.
- **rejected** adjusted p < alpha.

Rank: theory grade (A before B), then verdict (supported, mixed, rejected), then BIC, then the
Clark-West statistic. The recommendation is the top candidate; the report always shows the
full table and names the runner-up and what would have to change for it to win.

**Stage 6. Robustness.** For every candidate graded A or B and not rejected, plus every listed
alternative ordering of the recommended split: point IRFs of each `headline` pair at horizons
0 to `H`. The report states, per headline, the share of specifications with the same sign at
the peak response, and plots them together.

## 5. Code layout

```
src/csuf_fullerton/core/svar/
  data.py         align columns, drop missing rows, lag matrices, deterministic terms
  blocks.py       BlockSpec
  estimate.py     unrestricted VAR, two-block restricted VAR, reduced-form mapping
  identify.py     recursive identification
  irf.py          MA coefficients, IRF, FEVD, historical decomposition
  tests.py        LR, Wald, lag-augmented Wald, instantaneous causality, criteria, portmanteau
  bootstrap.py    residual bootstrap keeping the restriction
  unitroot.py     ADF/KPSS order, Johansen rank (statsmodels)
  direction.py    Hyvärinen-Smith pairwise measure, Jarque-Bera gate
  forecast.py     recursive pseudo out-of-sample forecasts, Clark-West
  theory.py       TheorySpec parsing (from a dict) and candidate enumeration
  screening.py    stages 1 to 6, ScreenResult
  report.py       ScreenResult and SvarResult to Markdown text (pure string building)
src/csuf_fullerton/core/recipe.py    data recipe parsing, transforms, monthly alignment
src/csuf_fullerton/core/svar/model.py one SVAR run (estimate, tests, bands, FEVD)
src/csuf_fullerton/data/
  credentials.py  FRED key lookup: env, keyring, 0600 file
  adapters/fred.py  FRED API (key) or fredgraph CSV (no key)
  adapters/imf.py   IMF SDMX 3.0 CSV
src/csuf_fullerton/cli/
  main.py         Typer app: init, fetch, screen, svar
  plots.py        matplotlib figures
```

Key lookup order: `FRED_API_KEY` env var, then keyring service `csuf-fullerton` user
`fred_api_key`, then `~/.config/csuf-fullerton/credentials.toml` (mode `0600`). `init` writes
to keyring and only falls back to the file when no keyring backend is available, and says
which it used. The key is never written to `run.json`, logs or output files.

## 6. Validation

1. Simulated block-exogenous DGP: the true split is graded supported and ranked first; a split
   that moves a truly domestic variable into the foreign block is rejected.
2. Simulated I(1) DGP with no feedback: lag-augmented Wald has size between 2% and 10% over
   300 draws of 300 observations. Measured during the build at T = 150: plain Wald 37%, LR
   34%, asymptotic lag-augmented Wald 10.7%, bootstrap lag-augmented Wald 6%.
3. Theory enumeration: counts, ordering, and the X grade for endogenous variables.
4. Hyvärinen-Smith measure recovers the direction on a simulated non-Gaussian pair.
5. Clark-West equals the textbook formula on a fixed example.
6. `init` stores and reads back a key with a fake keyring, and never prints it.
