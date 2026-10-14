# Tasks

Planning: [#17](https://github.com/espin086/csuf-fullerton/issues/17) (closed by the planning PR).
Feature: [#16](https://github.com/espin086/csuf-fullerton/issues/16) (closed by the last implementation PR).
Depends on: 0002 and 0004, merged in PR #14.

- [x] P1. Tracking issues #16 (feature) and #17 (plan).
- [x] P2. Proposal, design, spec deltas (`time-varying-svar`, `replication-eval`) and the
  literature note in `context-lake/`.
- [ ] P3. Maintainer merges the planning PR.

Replication harness first, so every later task lands with its cases.

- [x] 1. `core/replication/cases.py` and `run.py`, `cli/replicate.py`, fixture hashing,
  `scorecard.json` and `replication.md`. Proof:
  `tests/core/replication/test_run.py::test_hash_mismatch_fails` and
  `::test_registry_requires_three_kinds`.
- [x] 2. `core/tvsvar/simulate.py`: DGPs for M1 (rising China weight), M2 (sinusoidal drift)
  and M3 (random walk plus SV). Proof: `tests/core/tvsvar/test_simulate.py::test_dgp_stable`.
- [x] 3. `weights.py`: shares, moving average, quarterly mapping, lag option, checks. Proof:
  `test_weights.py::test_shares_sum_to_one`, `::test_lagged_weights_predetermined`,
  `::test_gap_rejected`.
- [x] 4. `m0.py`: split-sample LR and rolling wrapper, plus the statsmodels parity case and the
  Nicaragua regression case. Proof: `test_m0.py::test_unrestricted_matches_statsmodels`,
  replication case `m0-nicaragua-regression`.
- [x] 5. `design.py` and `m1.py`: `star` and `interacted` estimation, frozen-weight IRFs, LR and
  Wald tests. Proof: `test_m1.py::test_constant_weights_equal_0002`,
  `::test_star_equals_prebuilt_star_column`, `::test_foreign_irf_to_domestic_shock_is_zero`.
- [x] 6. `bootstrap.py`: fixed-weight-path bootstrap and difference bands; M1 recovery cases
  (coverage and LR size). Proof: replication cases `m1-sim-coverage`, `m1-sim-lr-size`
  (full suite) and their 20-replication fast versions.
- [x] 7. `m2.py`: kernel block estimates, local IRFs, GKY variance; confirm the default
  bandwidth exponent against Giraitis, Kapetanios and Yates (2014) first. Proof:
  `test_m2.py::test_flat_kernel_equals_constant`, case `m2-sim-sinusoid`.
- [x] 8. `precision.py` and `m3.py` homoskedastic: banded precision sampler and Gibbs steps.
  Generate the statsmodels notebook fixture with `replication/scripts/statsmodels_tvpvar.py`.
  Proof: case `m3-parity-statsmodels-cfa`, `test_m3.py::test_block_zero_every_draw`.
- [x] 9. `m3.py` stochastic volatility (KSC mixture, Del Negro and Primiceri order) and MCMC
  diagnostics. Generate the `bvarsv` fixture with `replication/scripts/bvarsv_reference.R`
  (needs R once). Proof: cases `m3-parity-bvarsv`, `m3-sim-sv-coverage`.
- [x] 10. Published-result cases: `m3-primiceri-2005-vol-peak` and
  `m1-cesa-bianchi-2012-direction` with the Brazil 1995/2009 fixture. Proof: both cases pass in
  the full suite; thresholds reviewed by the faculty contact before pinning.
- [x] 11. `cli/tvsvar.py`: command, outputs and `run.json`. Proof:
  `tests/cli/test_tvsvar_cli.py::test_end_to_end_on_fixture_csv` and `::test_rerun_from_run_json`.
- [x] 12. Wire the fast suite into `make check`, add `make replicate` and a `workflow_dispatch`
  workflow for the full suite. Proof: `make check` green with the fast suite under 3 minutes;
  `tests/core/replication/test_run.py::test_fast_suite_in_make_check`.
- [x] 13. Brazil worked example (`examples/brazil/`), report under `reports/brazil/`,
  `docs/tvsvar.md`, CHANGELOG line, pin golden values. Proof: `tests/docs/test_examples.py`
  runs the doc commands.
- [x] 14. `QUICKSTART.md` at the repo root: install, Nicaragua screen and SVAR report, Brazil
  time-varying report, replication suite, each as copy-paste commands with expected outputs.
  Proof: `tests/docs/test_quickstart.py` checks every command in it parses against the CLI.
- [x] 15. Secret scanning: `make secrets` (gitleaks over history and the working tree), GitHub
  secret scanning and push protection enabled on the repository, and a test that fetched CSVs
  and `run.json` never contain the FRED key. Proof:
  `tests/cli/test_fetch_no_secret.py::test_key_not_written_to_outputs`.

## Implementation status (2026-10-14)

All tasks are implemented on `feat/0005-time-varying-svar`; the planning PR (#15) has not yet
merged, so the implementation PR is stacked on it and waits for it. Deviations, with evidence,
are in design.md "Implementation notes". Two items differ from the task text:

- Task 8 proves the coefficient sampler against the statsmodels Kalman smoother
  (`m3-parity-kalman`) rather than the statsmodels TVP-VAR notebook's MCMC output: the smoother
  check is exact, the notebook check is only within Monte Carlo error.
- Task 9's `bvarsv` fixture is deferred (R is not installed on the build machine); the
  Primiceri (2005) published case covers the stochastic-volatility sampler meanwhile.
