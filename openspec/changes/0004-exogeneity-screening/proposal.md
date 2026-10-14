# Exogeneity screening and specification comparison before the SVAR

Builds on [0002-block-exogenous-svar](../0002-block-exogenous-svar/proposal.md). Feature issue:
[#2](https://github.com/espin086/csuf-fullerton/issues/2). Agent workflow it feeds:
[#5](https://github.com/espin086/csuf-fullerton/issues/5) (change 0003).

## Outcome

```
csuf-fullerton init                                   # store a FRED API key in the OS keychain
csuf-fullerton fetch examples/nicaragua/data.toml --out data/nicaragua.csv
csuf-fullerton screen data/nicaragua.csv examples/nicaragua/theory.toml --out results/screen/
csuf-fullerton svar data/nicaragua.csv --foreign ffr,us_ip,commodity \
  --domestic ni_ip,ni_cpi,ni_m2,ni_er --lags 2 --trend --seasonal --out results/svar/
```

`screen` answers one question before any structural estimate is reported: which variables can
be treated as exogenous to the domestic economy, and how strongly do theory and the data each
support that choice? It enumerates the candidate block assignments that theory allows, runs a
fixed battery of tests on every candidate, grades each on theory and on statistics separately,
and writes a ranked report with a recommendation and the robustness of the headline impulse
responses across every specification that survives.

## Why

Change 0002 imposes the block restriction and tests it once, on the one split the researcher
typed. That leaves three gaps a referee or thesis committee will ask about:

1. **The split is chosen by assertion.** The block-exogeneity LR test only checks the split it
   is given. Nothing shows that the alternatives (commodity prices domestic, U.S. output
   dropped from the foreign block, a two-variable foreign block) were considered and are worse.
2. **The tests that are run are the wrong ones for the data.** Macro series in levels are
   usually I(1). Wald Granger tests in a levels VAR then have non-standard limits (Sims, Stock
   and Watson 1990; Toda and Phillips 1993). The lag-augmented test of Toda and Yamamoto (1995)
   fixes this and is the standard in applied work.
3. **Lagged and contemporaneous exogeneity are different claims.** Granger non-causality only
   covers lags. The zero restriction in the impact matrix is an identifying assumption that
   second moments cannot test (Lütkepohl 2005, section 3.6.3). The report must say which claims
   are tested, which are only partially informed by the data (non-Gaussian direction measures),
   and which rest on theory alone.

JJ asked on 2026-10-14 for a more robust, theory-plus-statistics way to decide the exogenous
set before the full SVAR, with multiple specifications tested and assessed. The Nicaragua
report is the first use.

## What changes

- `core/svar/` gains the estimator of change 0002 (tasks 2 to 8 there), which the screen calls.
- New `core/svar/screening.py`: integration order (ADF and KPSS), Johansen rank, lag-augmented
  Granger matrix with Holm correction, block-exogeneity LR and Wald tests per candidate,
  instantaneous causality, weak exogeneity of the foreign block when cointegration is found,
  non-Gaussian pairwise direction measures, pseudo out-of-sample comparison against the
  unrestricted VAR (Clark and West 2007), and the grading and ranking rules in `design.md`.
- New `core/svar/theory.py`: a theory file (TOML) that declares each variable's prior role with
  a written rationale and citation, the candidate pool, and alternative orderings.
- New `fetch` command and `adapters/` package: FRED (API key or keyless CSV fallback) and the
  IMF SDMX 3.0 API, driven by a TOML recipe, with transforms (log, scale) recorded in the output.
- New `init` command: prompts for a FRED API key with hidden input and stores it in the OS
  keychain through `keyring`, falling back to a `0600` file under the user config directory.
  `FRED_API_KEY` in the environment always wins.
- `svar` and `screen` CLI commands, Markdown plus CSV/PNG outputs, `run.json` audit record.
- Worked Nicaragua example under `examples/nicaragua/` and the report under
  `reports/nicaragua/`.
- `statsmodels` moves from test-only to a runtime dependency (unit-root and Johansen critical
  values); `keyring` added. This amends the dependency line in 0002's design.

## Sources

- Engle, R. F., Hendry, D. F. and Richard, J.-F. (1983), "Exogeneity," *Econometrica* 51(2):
  277-304. https://doi.org/10.2307/1911990
- Granger, C. W. J. (1969), "Investigating causal relations by econometric models and
  cross-spectral methods," *Econometrica* 37(3): 424-438. https://doi.org/10.2307/1912791
- Sims, C. A., Stock, J. H. and Watson, M. W. (1990), "Inference in linear time series models
  with some unit roots," *Econometrica* 58(1): 113-144. https://doi.org/10.2307/2938337
- Toda, H. Y. and Yamamoto, T. (1995), "Statistical inference in vector autoregressions with
  possibly integrated processes," *Journal of Econometrics* 66: 225-250.
  https://doi.org/10.1016/0304-4076(94)01616-8
- Dolado, J. J. and Lütkepohl, H. (1996), "Making Wald tests work for cointegrated VAR
  systems," *Econometric Reviews* 15(4): 369-386. https://doi.org/10.1080/07474939608800362
- Johansen, S. (1992), "Cointegration in partial systems and the efficiency of single-equation
  analysis," *Journal of Econometrics* 52(3): 389-402. https://doi.org/10.1016/0304-4076(92)90019-N
- Pesaran, M. H., Schuermann, T. and Weiner, S. M. (2004), "Modeling regional
  interdependencies using a global error-correcting macroeconometric model," *Journal of
  Business and Economic Statistics* 22(2): 129-162. https://doi.org/10.1198/073500104000000019
- Cushman, D. O. and Zha, T. (1997), *Journal of Monetary Economics* 39(3): 433-448.
  https://doi.org/10.1016/S0304-3932(97)00029-9
- Kim, S. and Roubini, N. (2000), "Exchange rate anomalies in the industrial countries: A
  solution with a structural VAR approach," *Journal of Monetary Economics* 45(3): 561-586.
  https://doi.org/10.1016/S0304-3932(00)00010-6
- Maćkowiak, B. (2007), "External shocks, U.S. monetary policy and macroeconomic fluctuations
  in emerging markets," *Journal of Monetary Economics* 54(8): 2512-2520.
  https://doi.org/10.1016/j.jmoneco.2007.06.021
- Lütkepohl, H. (2005), *New Introduction to Multiple Time Series Analysis*, Springer.
  https://doi.org/10.1007/978-3-540-27752-1
- Kilian, L. and Lütkepohl, H. (2017), *Structural Vector Autoregressive Analysis*, Cambridge
  University Press. https://doi.org/10.1017/9781108164818
- Swanson, N. R. and Granger, C. W. J. (1997), "Impulse response functions based on a causal
  approach to residual orthogonalization in vector autoregressions," *JASA* 92(437): 357-367.
  https://doi.org/10.1080/01621459.1997.10473634
- Hyvärinen, A. and Smith, S. M. (2013), "Pairwise likelihood ratios for estimation of
  non-Gaussian structural equation models," *JMLR* 14: 111-152.
  https://jmlr.org/papers/v14/hyvarinen13a.html
- Lanne, M., Meitz, M. and Saikkonen, P. (2017), "Identification and estimation of non-Gaussian
  structural vector autoregressions," *Journal of Econometrics* 196(2): 288-304.
  https://doi.org/10.1016/j.jeconom.2016.06.002
- Clark, T. E. and West, K. D. (2007), "Approximately normal tests for equal predictive
  accuracy in nested models," *Journal of Econometrics* 138(1): 291-311.
  https://doi.org/10.1016/j.jeconom.2006.05.023
- Holm, S. (1979), "A simple sequentially rejective multiple test procedure," *Scandinavian
  Journal of Statistics* 6(2): 65-70. https://www.jstor.org/stable/4615733
- Leeb, H. and Pötscher, B. M. (2005), "Model selection and inference: Facts and fiction,"
  *Econometric Theory* 21(1): 21-59. https://doi.org/10.1017/S0266466605050036

## Non-goals

- The screen never changes the model on its own. It ranks and recommends; the researcher names
  the split passed to `svar`. Automatic selection followed by inference as if the model were
  known is the pretest problem Leeb and Pötscher (2005) describe.
- Full non-Gaussian SVAR estimation (Lanne, Meitz and Saikkonen 2017) and identification
  through heteroskedasticity (Rigobon 2003). The pairwise direction measure is advisory only.
- VECM estimation of the structural model. Johansen output informs the screen; the SVAR stays
  in levels (or differences, the researcher's choice), as in 0002.
- A0 non-recursive ML identification (0002 task 9) and the Stata cross-check (0002 task 10)
  stay open in 0002.
- Scraping sources that block automated access. The Banco Central de Nicaragua site sits behind
  a CAPTCHA; the IMF API is used instead.
