# Correctness checklist (read during step 4 only)

- Behaviour: does the code do what the scenario says for the boundary cases the scenario
  implies (empty, None, zero, negative, unicode, very large)?
- Errors: are failures raised with the documented exit code, never swallowed?
- Layering: `core/` imports nothing from I/O or `cli/`; `cli/` does no arithmetic or
  branching on business rules.
- Tests: assert on outcomes, not on implementation; no network; no sleeps; fixtures
  hand-computed and cited.
- Data: no bare magic numbers (name them in `core/conventions.py`); no float money formatting
  inside `core/`.
- Concurrency and state: no module-level mutable state; no hidden caches.
- Dependencies: new ones justified in the proposal, pinned with a lower bound, maintained.
- Security: input reaching shell, filesystem, SQL, or eval; secrets in code or logs.
- Docs: public functions have docstrings that cite the rule or formula; README still true.
