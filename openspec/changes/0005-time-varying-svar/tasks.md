# Tasks

Planning: [#17](https://github.com/espin086/csuf-fullerton/issues/17) (closed by the planning PR).
Feature: [#16](https://github.com/espin086/csuf-fullerton/issues/16) (closed by the last implementation PR).
Depends on: 0002 and 0004, merged in PR #14.

- [x] P1. Tracking issues #16 (feature) and #17 (plan).
- [x] P2. Proposal, design, spec deltas (`time-varying-svar`, `replication-eval`) and the
  literature note in `context-lake/`.
- [ ] P3. Maintainer merges the planning PR.

Replication harness first, so every later task lands with its cases.

- [ ] 1. `core/replication/cases.py` and `run.py`, `cli/replicate.py`, fixture hashing,
  `scorecard.json` and `replication.md`. Proof:
  `tests/core/replication/test_run.py::test_hash_mismatch_fails` and
  `::test_registry_requires_three_kinds`.
- [ ] 2. `core/tvsvar/simulate.py`: DGPs for M1 (rising China weight), M2 (sinusoidal drift)
  and M3 (random walk plus SV). Proof: `tests/core/tvsvar/test_simulate.py::test_dgp_stable`.
- [ ] 3. `weights.py`: shares, moving average, quarterly mapping, lag option, checks. Proof:
  `test_weights.py::test_shares_sum_to_one`, `::test_lagged_weights_predetermined`,
  `::test_gap_rejected`.
- [ ] 4. `m0.py`: split-sample LR and rolling wrapper, plus the statsmodels parity case and the
  Nicaragua regression case. Proof: `test_m0.py::test_unrestricted_matches_statsmodels`,
  replication case `m0-nicaragua-regression`.
- [ ] 5. `design.py` and `m1.py`: `star` and `interacted` estimation, frozen-weight IRFs, LR and
  Wald tests. Proof: `test_m1.py::test_constant_weights_equal_0002`,
  `::test_star_equals_prebuilt_star_column`, `::test_foreign_irf_to_domestic_shock_is_zero`.
- [ ] 6. `bootstrap.py`: fixed-weight-path bootstrap and difference bands; M1 recovery cases
  (coverage and LR size). Proof: replication cases `m1-sim-coverage`, `m1-sim-lr-size`
  (full suite) and their 20-replication fast versions.
- [ ] 7. `m2.py`: kernel block estimates, local IRFs, GKY variance; confirm the default
  bandwidth exponent against Giraitis, Kapetanios and Yates (2014) first. Proof:
  `test_m2.py::test_flat_kernel_equals_constant`, case `m2-sim-sinusoid`.
- [ ] 8. `precision.py` and `m3.py` homoskedastic: banded precision sampler and Gibbs steps.
  Generate the statsmodels notebook fixture with `replication/scripts/statsmodels_tvpvar.py`.
  Proof: case `m3-parity-statsmodels-cfa`, `test_m3.py::test_block_zero_every_draw`.
- [ ] 9. `m3.py` stochastic volatility (KSC mixture, Del Negro and Primiceri order) and MCMC
  diagnostics. Generate the `bvarsv` fixture with `replication/scripts/bvarsv_reference.R`
  (needs R once). Proof: cases `m3-parity-bvarsv`, `m3-sim-sv-coverage`.
- [ ] 10. Published-result cases: `m3-primiceri-2005-vol-peak` and
  `m1-cesa-bianchi-2012-direction` with the Brazil 1995/2009 fixture. Proof: both cases pass in
  the full suite; thresholds reviewed by the faculty contact before pinning.
- [ ] 11. `cli/tvsvar.py`: command, outputs and `run.json`. Proof:
  `tests/cli/test_tvsvar_cli.py::test_end_to_end_on_fixture_csv` and `::test_rerun_from_run_json`.
- [ ] 12. Wire the fast suite into `make check`, add `make replicate` and a `workflow_dispatch`
  workflow for the full suite. Proof: `make check` green with the fast suite under 3 minutes;
  `tests/core/replication/test_run.py::test_fast_suite_in_make_check`.
- [ ] 13. Brazil worked example (`examples/brazil/`), report under `reports/brazil/`,
  `docs/tvsvar.md`, CHANGELOG line, pin golden values. Proof: `tests/docs/test_examples.py`
  runs the doc commands.
- [ ] 14. `QUICKSTART.md` at the repo root: install, Nicaragua screen and SVAR report, Brazil
  time-varying report, replication suite, each as copy-paste commands with expected outputs.
  Proof: `tests/docs/test_quickstart.py` checks every command in it parses against the CLI.
- [ ] 15. Secret scanning: `make secrets` (gitleaks over history and the working tree), GitHub
  secret scanning and push protection enabled on the repository, and a test that fetched CSVs
  and `run.json` never contain the FRED key. Proof:
  `tests/cli/test_fetch_no_secret.py::test_key_not_written_to_outputs`.
