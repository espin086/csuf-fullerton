# Design: block-exogenous SVAR

## Model

Stack the variables as `y_t = [x_t ; z_t]`, foreign block `x_t` (k1 variables) first, domestic
block `z_t` (k2 variables) second. The structural form is

```
A0 y_t = c + A1 y_{t-1} + ... + Ap y_{t-p} + e_t,   e_t ~ N(0, I)
```

Block exogeneity (Cushman and Zha 1997) puts zeros in the upper-right k1 x k2 block of `A0` and
of every `Al`. The foreign equations contain no current or lagged domestic variable. Zha (1999)
shows that with this block-recursive `A0` the likelihood splits into one piece per block, so each
block can be estimated on its own.

## Estimation (two OLS blocks, then identification)

1. **Foreign block.** Regress `x_t` on a constant and `p` lags of `x` only. OLS per equation
   (same regressors in every equation of the block). Residuals `u_x`, covariance `S_x`.
2. **Domestic block.** Regress `z_t` on a constant, current `x_t`, and `p` lags of both `x` and
   `z`. Including current `x_t` is valid because the foreign structural shocks are orthogonal to
   the domestic ones under the restriction. Residuals `u_z`, covariance `S_z`.
3. **Identification within each block.** Default `recursive`: Cholesky of `S_x` and `S_z` in the
   column order the user gives. Option `--a0 file.csv`: a user zero pattern for the
   within-block contemporaneous matrix, estimated by maximum likelihood (scipy optimizer), with an
   LR overidentification test when the pattern has more zeros than needed.
4. **Recover the full system.** Map the two block estimates back to `A0, A1..Ap` for the stacked
   model, then compute the MA representation for IRFs, FEVD and historical decomposition.

Exogenous deterministic terms (`--trend`, `--dummies cols`) enter both blocks.

## Test of the restriction

Estimate the unrestricted reduced-form VAR on the same sample and lags. Report
`LR = (T - c)(log|S_restricted| - log|S_unrestricted|)` with Sims' small-sample correction
`c` (number of parameters per equation in the unrestricted system), degrees of freedom
`k1 * k2 * p`, and the p-value. This is the same hypothesis as the EViews "Granger causality /
block exogeneity Wald test", so we report the Wald form too for comparison. The tool never drops
the restriction on its own; a rejection is printed as a warning for the researcher.

## Inference

- Residual bootstrap (default 1000 draws): resample residual vectors jointly, regenerate data
  from the restricted model, re-estimate both blocks, recompute IRFs. Every draw keeps the
  zeros. Percentile and Hall intervals.
- Kilian (1998) bias-corrected bootstrap as an option.
- Delta-method bands as a fast option for class use.

## Lag choice

AIC, BIC and HQ computed on the restricted system (the log-determinant of the block-diagonal
structural covariance). All three are reported; `--lags` overrides. The Ljung-Box / LM residual
check is reported per block.

## Code layout

```
src/csuf_fullerton/core/svar/
  data.py        CSV load result (pure: takes a DataFrame), column checks, sample alignment
  blocks.py      BlockSpec: foreign/domestic columns, lags, deterministic terms
  estimate.py    estimate_blocks() -> BlockEstimates (OLS per block, unrestricted VAR)
  identify.py    recursive and A0-pattern ML identification
  irf.py         MA coefficients, IRF, FEVD, historical decomposition
  bootstrap.py   residual and Kilian bootstrap that preserve the restriction
  tests.py       LR and Wald block-exogeneity tests, lag criteria
src/csuf_fullerton/cli/svar.py   Typer command; reads CSV, writes outputs, run.json
```

Dependencies: numpy, pandas, scipy, matplotlib. statsmodels only in tests, as the unrestricted
VAR reference. Core stays pure per `tests/architecture/test_layering.py`.

## Validation plan

1. Simulated DGP with known block-exogenous `A0, A1, A2` (k1 = 3, k2 = 4, T = 400): estimates
   within tolerance, true IRFs inside 95% bands at least 90% of the time over 200 replications.
2. Restriction off: the unrestricted path matches `statsmodels.tsa.api.VAR` coefficients to 1e-8.
3. Restriction test size and power on simulated data (true and false restriction).
4. Cross-check with Stata `var ..., constraints(...)` on one dataset; numbers checked into
   `tests/fixtures/stata/` with the `.do` file that made them. Needs Stata access (offered by
   Dr. Bhattacharya, 2026-09-30).
5. Thesis replication when the 2011 series are recovered (open question below).

## Open questions for the faculty call

- Within the domestic block, recursive or a non-recursive `A0` as in Cushman and Zha? Which
  ordering did the 2011 thesis use?
- Levels with trends, or differences? (Affects which IRFs are comparable to the thesis.)
- Is EViews or Stata the reference implementation for ECON 505?
- Where the 2011 thesis data can be rebuilt from (IMF IFS, FRED, central bank of Nicaragua).
