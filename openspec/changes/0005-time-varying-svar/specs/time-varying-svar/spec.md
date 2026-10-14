# Time-varying SVAR

## ADDED Requirements

### Requirement: Trade weights are built reproducibly from bilateral trade

The tool SHALL compute each partner's share of exports plus imports over the declared partners
plus rest of world, smooth it with a k-year moving average, map it to the estimation
frequency, and reject inputs that fail the share checks.

#### Scenario: Shares sum to one
- **WHEN** a user supplies annual bilateral trade for the U.S., China and the euro area
- **THEN** the weights for each period including rest of world SHALL lie in [0, 1] and sum to
  1 within 1e-10

#### Scenario: Lagged weights are predetermined
- **WHEN** `--weights-lag 1` is set
- **THEN** every quarter of year y SHALL use the moving average ending in year y-1

#### Scenario: Gaps are rejected
- **WHEN** a partner has no trade value for a year inside the estimation sample
- **THEN** the command SHALL exit non-zero naming the partner and year, and SHALL NOT impute

### Requirement: Block exogeneity holds in every time-varying model

Every model in this change (M1, M2, M3) SHALL keep foreign-block equations free of current and
lagged domestic variables at every date, in point estimates and in every bootstrap or posterior
draw.

#### Scenario: Foreign variables never respond to domestic shocks
- **WHEN** any model is estimated with `--domestic` and partner columns
- **THEN** the response of every foreign variable to every domestic shock SHALL be exactly zero
  at every horizon, every date and every frozen weight year

### Requirement: Trade-weighted SVAR reports frozen-weight impulse responses

The M1 estimator SHALL estimate the `star` or `interacted` specification by OLS and report
impulse responses with weights frozen at each requested year, plus draw-by-draw difference bands
between years.

#### Scenario: Frozen weights change the response
- **WHEN** `--frozen-weights 1995,2023` is given
- **THEN** the output SHALL contain IRFs for each year and the bootstrap distribution of
  `IRF_2023 - IRF_1995` for every domestic variable and foreign shock

#### Scenario: Constant weights reduce to the constant model
- **WHEN** the weight path is constant over the sample and `G = 0`
- **THEN** M1 IRFs SHALL equal the 0002 estimator's IRFs within 1e-10

### Requirement: Time variation is tested, not assumed

Each run SHALL report the LR test of the constant model against `interacted`, the LR test of
`star` against `interacted`, a Wald test of equal U.S. and China slopes, and, when `--break` is
given, the split-sample LR test.

#### Scenario: Weights do not matter
- **WHEN** the constant-vs-interacted LR p-value is at or above 0.05
- **THEN** the report SHALL state that the data do not reject constant transmission and SHALL
  still show the frozen-weight IRFs

### Requirement: Kernel and Bayesian models are available as robustness rungs

The tool SHALL estimate M2 (kernel weighted least squares per block, bandwidth `T^h`) and M3
(TVP-VAR with stochastic volatility, Del Negro and Primiceri 2015 sampler order) on the same
data and report date-specific impulse responses.

#### Scenario: Kernel bandwidth too small
- **WHEN** the kernel window leaves fewer effective observations at the sample ends than twice
  the regressors per equation
- **THEN** the run SHALL stop with a message naming the bandwidth and the regressor count

#### Scenario: Flat kernel equals constant model
- **WHEN** M2 runs with an infinite bandwidth
- **THEN** its coefficients at every date SHALL equal the 0002 estimate within 1e-8

#### Scenario: MCMC diagnostics are reported
- **WHEN** M3 finishes
- **THEN** the run SHALL write inefficiency factors and Geweke statistics per parameter block
  and SHALL record draws, burn-in, thinning and seed in `run.json`

### Requirement: Every run leaves an audit record

Each `tvsvar` run SHALL write `run.json` with the input and weight file hashes, partner set,
weight window and lag, model and variant, ordering, lags, bandwidth or priors, test results,
bootstrap or MCMC settings, seeds and package version.

#### Scenario: Re-running from the record
- **WHEN** a user re-runs with the arguments in `run.json` on the same files
- **THEN** point estimates SHALL be identical and bands or posterior summaries SHALL match given
  the recorded seed
