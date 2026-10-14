# Tasks

Feature: [#2](https://github.com/espin086/csuf-fullerton/issues/2). Builds on change 0002.
JJ asked on 2026-10-14 to fix the spec and build in the same session; the planning PR and the
implementation travel together in one PR for maintainer review.

- [x] 1. 0002 tasks 2 to 8: data, blocks, estimate, identify, irf, tests, bootstrap, `svar` CLI.
  Proof: `tests/core/svar/test_estimate.py`, `test_irf.py`, `test_tests.py`, `test_bootstrap.py`.
- [x] 2. `unitroot.py` and lag-augmented Wald in `tests.py`. Proof:
  `test_screening.py::test_lag_augmented_wald_size_under_unit_roots`.
- [x] 3. `theory.py` enumeration and grades. Proof:
  `test_theory.py::test_enumeration_respects_priors_and_size_bounds`,
  `::test_explicit_endogenous_spec_is_inadmissible`.
- [x] 4. `direction.py`. Proof: `test_direction.py::test_direction_recovered_on_non_gaussian_data`.
- [x] 5. `forecast.py` Clark-West. Proof: `test_forecast.py::test_clark_west_known_answer`.
- [x] 6. `screening.py` stages, ranking, robustness. Proof:
  `test_screening.py::test_true_split_ranks_first`, `::test_false_split_is_rejected`,
  `::test_robustness_summary`.
- [x] 7. `adapters/` FRED, IMF, credentials; `init` and `fetch` commands. Proof:
  `tests/cli/test_init.py::test_init_stores_key`, `::test_environment_wins`,
  `tests/test_fetch.py::test_transforms_recorded`.
- [x] 8. `screen` command, Markdown report, figures. Proof:
  `tests/cli/test_screen_cli.py::test_screen_end_to_end`.
- [x] 9. Nicaragua example (`examples/nicaragua/`), report (`reports/nicaragua/`), README and
  CHANGELOG.
