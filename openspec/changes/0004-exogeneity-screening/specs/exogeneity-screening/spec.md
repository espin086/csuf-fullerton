# Exogeneity screening

## ADDED Requirements

### Requirement: Candidate specifications come from a theory file

The screen SHALL enumerate every foreign block allowed by the theory file and SHALL never place
a variable whose prior is `endogenous` in a ranked candidate.

#### Scenario: Enumeration respects priors and size bounds
- **WHEN** the theory file lists two `exogenous` variables, one `candidate` and four
  `endogenous` variables with `min_foreign = 1` and `max_foreign = 3`
- **THEN** the screen SHALL evaluate the 7 non-empty subsets of the three foreign-eligible
  variables and no subset containing an `endogenous` variable

#### Scenario: Explicit specification is graded inadmissible
- **WHEN** an explicit `[[spec]]` puts an `endogenous` variable in the foreign block
- **THEN** it SHALL be reported with theory grade `X` and SHALL NOT appear in the ranking

### Requirement: Granger tests are valid for integrated data

Granger and block-exogeneity Wald tests SHALL use lag augmentation by `d_max` (Toda-Yamamoto),
with `d_max` from the integration stage.

#### Scenario: Size under unit roots
- **WHEN** 300 samples of 200 observations are simulated from an I(1) system with no feedback
  from domestic to foreign variables
- **THEN** the lag-augmented block Wald test SHALL reject at the 5% level in between 2% and 10%
  of samples

### Requirement: Every candidate is tested and graded on theory and statistics separately

Each candidate SHALL carry a theory grade (`A`, `B`, `X`), a statistical verdict (`supported`,
`mixed`, `rejected`) with Holm-adjusted p-values, information criteria, an instantaneous
causality test, and a pseudo out-of-sample comparison.

#### Scenario: True split ranks first
- **WHEN** data are simulated from a block-exogenous process whose true foreign block is
  graded `A` in the theory file
- **THEN** that split SHALL be `supported` and ranked first

#### Scenario: False split is rejected
- **WHEN** a domestic variable that Granger-causes the foreign block in the simulated process is
  forced into the domestic block of a candidate whose foreign block it feeds
- **THEN** that candidate's verdict SHALL be `rejected`

### Requirement: The screen recommends and does not select

The screen SHALL write a ranked table, a recommendation, the runner-up, and a robustness
summary of headline impulse responses across all surviving specifications. It SHALL NOT pass a
selected split to estimation on its own.

#### Scenario: Robustness summary
- **WHEN** at least two candidates survive and a `[[headline]]` pair is declared
- **THEN** the report SHALL state the share of surviving specifications whose peak response has
  the same sign as the recommended one

### Requirement: Contemporaneous direction is labelled as advisory

Non-Gaussian direction measures SHALL be reported only when Jarque-Bera rejects normality for
both residuals, and SHALL be labelled advisory.

#### Scenario: Direction recovered on non-Gaussian data
- **WHEN** `y = 0.8 x + e` with independent uniform `x` and `e`
- **THEN** the pairwise measure SHALL indicate `x -> y`
