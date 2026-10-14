# Time-varying SVAR for a small open economy whose main trading partner changes

Builds on [0002-block-exogenous-svar](../0002-block-exogenous-svar/proposal.md) (estimator)
and [0004-exogeneity-screening](../0004-exogeneity-screening/proposal.md) (`fetch` adapters,
runtime `statsmodels`), both merged in PR #14. Feature issue:
[#16](https://github.com/espin086/csuf-fullerton/issues/16). Planning sub-issue:
[#17](https://github.com/espin086/csuf-fullerton/issues/17).
This is a planning-only change; code starts after the planning PR merges.

## Outcome

```
csuf-fullerton fetch examples/brazil/data.toml --out data/brazil.csv
csuf-fullerton tvsvar data/brazil.csv \
  --partners us,cn,ea --partner-vars gdp,rate \
  --weights data/brazil_trade_weights.csv --weight-window 3 \
  --global commodity --domestic br_gdp,br_cpi,br_selic,br_reer \
  --model interacted --lags 2 --frozen-weights 1995,2005,2023 \
  --horizon 20 --bands bootstrap --draws 1000 --out results/brazil/
csuf-fullerton replicate --suite fast          # minutes, runs in `make check`
csuf-fullerton replicate --suite full --out results/replication/
```

`tvsvar` answers one question: how did the response of Brazil's output, prices, policy rate
and real exchange rate to a U.S. shock and to a China shock change as China replaced the
United States as Brazil's largest trading partner (2009)? It writes impulse responses at each
frozen weight year, the time path of the transmission coefficients, tests of whether the time
variation is real, and a `run.json` audit record.

`replicate` runs the evaluation pipeline: every estimator in this change must reproduce known
answers on simulated data, match a reference implementation, and reproduce the headline
result of a published paper before its output is trusted. The pipeline writes a scorecard,
and any case outside tolerance fails the command (and CI for the fast suite).

## Why

Change 0002 estimates one set of coefficients for the whole sample. For Brazil that averages
two different economies: one where the United States is the dominant export market, and one
where China is. The constant-coefficient answer to "what does a China GDP shock do to Brazil"
is then a sample-weighted blend that describes neither period.

The literature already measures this shift, with two different tools:

- **Trade-weighted foreign variables.** Cesa-Bianchi, Pesaran, Rebucci and Xu (2012) estimate
  a GVAR whose foreign variables use three-year moving-average trade weights, then compute
  impulse responses under fixed 1985, 1995, 2005 and 2009 weights. The long-run effect of a
  China GDP shock on a typical Latin American economy is about three times larger with 2009
  weights than with 1995 weights; the U.S. effect roughly halves.
- **Drifting coefficients.** Primiceri (2005), Cogley and Sargent (2005), and for open
  economies Liu, Mumtaz and Theophilopoulou (2014), let every VAR coefficient follow a random
  walk. That captures change of any origin but does not say the change came from trade.

Neither is available as accessible code for a single small open economy with a block-exogenous
foreign sector. Change 0002's users (ECON 505 students and M.A. thesis writers, per Dr. Rokon
Bhuiyan, 2026-10-02) would need MATLAB code from several papers to do it. This change gives
them a ladder of three models, each tested against the one below, plus the evaluation suite
that proves each rung works.

## What changes

- **Trade-weight construction** (`core/tvsvar/weights.py`): bilateral exports plus imports,
  shares over the declared partner set plus rest of world, k-year moving average with the
  Cesa-Bianchi et al. timing, annual-to-quarterly mapping, and a lagged option so the weights
  are predetermined.
- **Model M1, trade-weighted block-exogenous SVAR** (`interacted` and `star` variants). Partner
  variables enter the foreign block (block exogenous, as in 0002). Domestic equations load on
  partner variables through their trade weights: the `star` variant imposes GVAR-style
  loading `beta * w_jt * x_jt`; the `interacted` variant (Towbin and Weber 2013) allows
  `(beta_j + gamma_j * w_jt) * x_jt`. Both are estimated by OLS; impulse responses are computed
  conditional on weights frozen at chosen years.
- **Model M2, kernel time-varying block SVAR** (Giraitis, Kapetanios and Yates 2014; Kapetanios,
  Marcellino and Venditti 2019). Kernel-weighted least squares at every date, per block, so the
  block restriction holds at every date. Agnostic about why coefficients move; used to check
  that the M1 trade-weight story matches the drift the data shows.
- **Model M3, Bayesian TVP-VAR with stochastic volatility** (Primiceri 2005 with the Del Negro
  and Primiceri 2015 corrected sampler order), with block exogeneity imposed in the coefficient
  state vector. Precision-based simulation smoother (Chan and Jeliazkov 2009) in numpy/scipy;
  stochastic volatility by the Kim, Shephard and Chib (1998) mixture sampler.
- **Tests of time variation:** constant vs. M1 by LR (weights explain the change), M1 `star`
  vs. `interacted` by LR, split-sample Chow-type LR at a user break date, and the M2 path
  compared with the weight path.
- **Evaluation pipeline** (`core/replication/`, `replicate` command, `replication/` case
  registry with checked-in fixtures): simulation recovery, software parity, and published-result
  replication for every model, with a JSON scorecard and Markdown report.
- **Worked Brazil example** under `examples/brazil/` (data recipe, theory file, report).
- CHANGELOG lines, `docs/tvsvar.md`, and a `QUICKSTART.md` covering the Nicaragua and Brazil
  reports end to end.
- **Secret scanning on every path:** gitleaks in pre-commit and CI (already present), a
  `make secrets` target, GitHub secret scanning with push protection, and a rule that fetched
  data and fixtures never carry API keys.

## Does statsmodels handle this?

Short answer: not as a model. It supplies parts.

| Need | statsmodels 0.14 | Plan |
|---|---|---|
| Constant VAR, SVAR (A/B) | `tsa.api.VAR`, `tsa.vector_ar.svar_model.SVAR` | Already used as a reference in 0002 |
| Block exogeneity (zero lag blocks) | Not supported by `VAR` or `SVAR` | 0002 estimator, numpy |
| Trade-weighted / interacted VAR | No class; it is OLS with constructed regressors | numpy, reuses 0002 code |
| Kernel TVP-VAR | No class | numpy weighted least squares |
| TVP-VAR, random-walk coefficients | No class. `MLEModel` plus `simulation_smoother(method="cfa")` lets you build one; the official example notebook does, homoskedastic only | Hand-written precision sampler in numpy/scipy; the statsmodels notebook is a parity test |
| Stochastic volatility | No multivariate SV sampler | numpy, KSC mixture |
| Markov-switching VAR | `MarkovAutoregression` is univariate | Out of scope |

So core estimation goes into numpy and scipy (`scipy.linalg.cholesky_banded`,
`scipy.stats.invwishart`, `invgamma`). statsmodels stays where it is strong: a known-answer
oracle in the replication suite and the unit-root tests 0004 already uses. A full rationale
and the literature review live in
[context-lake/2026-10-14-time-varying-var-literature.md](../../../context-lake/2026-10-14-time-varying-var-literature.md).

## Sources

- Cesa-Bianchi, A., Pesaran, M. H., Rebucci, A. and Xu, T. (2012), "China's emergence in the
  world economy and business cycles in Latin America," *Economía* 12(2), 2012 (journal pages
  not verified). Working paper used here: IZA DP 5889, https://docs.iza.org/dp5889.pdf
  (also IDB WP 4732, https://doi.org/10.18235/0011334)
- Primiceri, G. E. (2005), "Time varying structural vector autoregressions and monetary
  policy," *Review of Economic Studies* 72(3): 821-852.
  https://doi.org/10.1111/j.1467-937X.2005.00353.x
- Del Negro, M. and Primiceri, G. E. (2015), "Time varying structural vector autoregressions
  and monetary policy: a corrigendum," *Review of Economic Studies* 82(4): 1342-1345.
  https://doi.org/10.1093/restud/rdv024
- Cogley, T. and Sargent, T. J. (2005), "Drifts and volatilities: monetary policies and
  outcomes in the post WWII US," *Review of Economic Dynamics* 8(2): 262-302.
  https://doi.org/10.1016/j.red.2004.10.009
- Liu, P., Mumtaz, H. and Theophilopoulou, A. (2014), "The transmission of international
  shocks to the UK. Estimates based on a time-varying factor augmented VAR," *Journal of
  International Money and Finance* 46: 1-15. https://doi.org/10.1016/j.jimonfin.2014.03.004
- Towbin, P. and Weber, S. (2013), "Limits of floating exchange rates: the role of foreign
  currency debt and import structure," *Journal of Development Economics* 101: 179-194.
  https://doi.org/10.1016/j.jdeveco.2012.10.007
- Giraitis, L., Kapetanios, G. and Yates, T. (2014), "Inference on stochastic time-varying
  coefficient models," *Journal of Econometrics* 179(1): 46-65.
  https://doi.org/10.1016/j.jeconom.2013.10.009
- Kapetanios, G., Marcellino, M. and Venditti, F. (2019), "Large time-varying parameter VARs:
  a nonparametric approach," *Journal of Applied Econometrics* 34(7): 1027-1049.
  https://doi.org/10.1002/jae.2722
- Chan, J. C. C. and Jeliazkov, I. (2009), "Efficient simulation and integrated likelihood
  estimation in state space models," *International Journal of Mathematical Modelling and
  Numerical Optimisation* 1(1/2): 101-120. https://doi.org/10.1504/IJMMNO.2009.030090
- Kim, S., Shephard, N. and Chib, S. (1998), "Stochastic volatility: likelihood inference and
  comparison with ARCH models," *Review of Economic Studies* 65(3): 361-393.
  https://doi.org/10.1111/1467-937X.00050
- Cushman, D. O. and Zha, T. (1997), block exogeneity, as cited in 0002.
- statsmodels, "TVP-VAR, MCMC, and sparse simulation smoothing" example notebook.
  https://www.statsmodels.org/devel/examples/notebooks/generated/statespace_tvpvar_mcmc_cfa.html
- Krueger, F., `bvarsv` R package (Primiceri model with the 2015 corrigendum).
  https://cran.r-project.org/package=bvarsv
- Prior changes: [0001-pr-issue-link](../0001-pr-issue-link/proposal.md),
  [0002-block-exogenous-svar](../0002-block-exogenous-svar/proposal.md),
  [0004-exogeneity-screening](../0004-exogeneity-screening/proposal.md).

Every other DOI above was resolved against doi.org on 2026-10-14 and matched title, volume and pages.

## Non-goals

- A full multi-country GVAR. M1 borrows GVAR trade weighting for one small open economy only.
- Markov-switching SVARs (Sims and Zha 2006) and smooth-transition VARs. Listed as later
  extensions.
- Time-varying identification schemes (sign restrictions that change by date). Identification
  stays recursive within blocks, as in 0002.
- Factor-augmented models (Liu, Mumtaz and Theophilopoulou 2014 style).
- New data sources beyond what 0004's adapters fetch; trade weights come from a CSV the user
  supplies or from the IMF adapter if 0004 covers Direction of Trade Statistics.
- Exact numerical replication of the Cesa-Bianchi et al. GVAR. The published-result case
  checks the direction and rough size of their headline ratio, not their numbers.
