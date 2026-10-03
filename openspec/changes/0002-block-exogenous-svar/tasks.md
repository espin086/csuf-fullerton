# Tasks

Planning: [#3](https://github.com/espin086/csuf-fullerton/issues/3) (closed by the planning PR).
Feature: [#2](https://github.com/espin086/csuf-fullerton/issues/2) (closed by the last implementation PR).

- [x] P1. Tracking issues #2 (feature), #3 (plan), #5 (agent workflow, change 0003).
- [x] P2. Proposal, design and spec delta in this folder.
- [ ] P3. Maintainer merges the planning PR.
- [ ] 1. Rename `project_template` to `csuf_fullerton` with `scripts/rename.py`; switch
  `make install` from uv to `python -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"`.
  Proof: `make check` green.
- [ ] 2. `core/svar/data.py` and `blocks.py`: column checks, missing values, sample alignment,
  lag construction. Proof: `tests/core/svar/test_data.py`.
- [ ] 3. `estimate.py`: two-block OLS and the unrestricted VAR. Proof:
  `test_estimate.py::test_unrestricted_matches_statsmodels` and
  `::test_recovers_simulated_block_dgp`.
- [ ] 4. `identify.py`: recursive per block. Proof: `test_identify.py::test_recursive_a0_block_triangular`.
- [ ] 5. `irf.py`: IRF, FEVD, historical decomposition. Proof:
  `test_irf.py::test_foreign_irf_to_domestic_shock_is_zero` and `::test_fevd_rows_sum_to_one`.
- [ ] 6. `tests.py`: LR and Wald block-exogeneity tests, AIC/BIC/HQ. Proof:
  `test_tests.py::test_lr_size_under_true_restriction` and `::test_lr_rejects_false_restriction`.
- [ ] 7. `bootstrap.py`: residual and Kilian bootstrap keeping the restriction. Proof:
  `test_bootstrap.py::test_every_draw_keeps_zero_block` and `::test_band_coverage_simulated` (slow mark).
- [ ] 8. `cli/svar.py`: the `svar` command, outputs and `run.json`. Proof:
  `tests/cli/test_svar_cli.py::test_end_to_end_on_fixture_csv`.
- [ ] 9. `identify.py`: user A0 zero pattern by ML with the overidentification LR test. Proof:
  `test_identify.py::test_ml_matches_cholesky_when_just_identified`.
- [ ] 10. Stata cross-check fixture and test (needs Stata access). Proof:
  `test_stata_crosscheck.py`.
- [ ] 11. Worked example in `docs/svar.md` plus CHANGELOG line. Proof: doc commands run in
  `tests/docs/test_examples.py`.
