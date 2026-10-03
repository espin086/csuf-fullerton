# SVAR estimation

## ADDED Requirements

### Requirement: Foreign block is exogenous to the domestic block

The estimator SHALL impose zero coefficients on every current and lagged domestic variable in
every foreign-block equation, in the point estimate and in every bootstrap draw.

#### Scenario: Foreign variables do not respond to domestic shocks
- **WHEN** a user runs `svar` with `--foreign` and `--domestic` column lists
- **THEN** the impulse response of every foreign variable to every domestic shock SHALL be
  exactly zero at all horizons

#### Scenario: Bootstrap draws keep the restriction
- **WHEN** bands are computed with `--bands bootstrap`
- **THEN** every re-estimated draw SHALL have zeros in the foreign-on-domestic block of `A0`
  and every lag matrix

### Requirement: The restriction is tested on every run

The tool SHALL report a likelihood-ratio test (with small-sample correction) and a Wald test of
block exogeneity against the unrestricted VAR, with degrees of freedom and p-value.

#### Scenario: Restriction rejected
- **WHEN** the block-exogeneity test p-value is below 0.05
- **THEN** the run SHALL still impose the restriction and SHALL print a warning naming the test
  statistic and p-value

### Requirement: Results match a known answer

The estimator SHALL recover the parameters of a simulated block-exogenous process, and with the
restriction removed SHALL match a reference unrestricted VAR implementation.

#### Scenario: Unrestricted equivalence
- **WHEN** the same data and lags are estimated with no foreign block
- **THEN** reduced-form coefficients SHALL match `statsmodels` VAR within 1e-8

#### Scenario: Simulated recovery
- **WHEN** the estimator runs on 400 observations simulated from a known block-exogenous process
- **THEN** each true impulse response SHALL fall inside the 95% bootstrap band in at least 90%
  of 200 replications

### Requirement: Every run leaves an audit record

Each run SHALL write `run.json` with the input file hash, column blocks, lags and lag criteria,
identification scheme, test results, bootstrap settings and package version.

#### Scenario: Re-running from the record
- **WHEN** a user re-runs the command with the arguments in `run.json` on the same file
- **THEN** point estimates SHALL be identical and bands SHALL match given the recorded seed
