# Block-exogenous SVAR estimator (step one)

Issue: [#2](https://github.com/espin086/csuf-fullerton/issues/2). Planning sub-issue:
[#3](https://github.com/espin086/csuf-fullerton/issues/3). This is a planning-only PR; code
starts after it merges.

## Outcome

```
csuf-fullerton svar data/nicaragua.csv \
  --foreign ffr,us_ip,commodity --domestic ni_output,ni_cpi,ni_m2,ni_er \
  --lags 4 --identify recursive --horizon 24 --bands bootstrap --draws 1000 \
  --out results/
```

writes impulse responses (with bands), forecast error variance decompositions, the
block-exogeneity test, and a `run.json` audit record of every choice. The foreign block does
not respond to domestic variables, contemporaneously or at any lag.

## Why this is step one

Dr. Rokon Bhuiyan, CSUF Economics, replying on 2026-10-02 to the proposal thread "Open source
tool for VAR and impulse response models, and a possible paper":

> Although standard SVARs and recursive VARs are relatively straightforward to estimate in
> EViews and Stata, block-exogenous SVARs are less straightforward to implement in those
> programs. Having accessible, well-documented code that can be adapted to different
> countries, datasets, and research settings would be useful.

He named the users: ECON 505 students writing course research papers and M.A. students writing
VAR theses. The broader agent workflow in the proposal deck (orchestrator, routing between
levels VAR / differences / VECM / Toda-Yamamoto, diagnostics loop) is still the plan, tracked in
[#5](https://github.com/espin086/csuf-fullerton/issues/5) as change 0003. It sits on top of an
estimator that faculty trust, so the estimator ships first.

The first benchmark already needs it. JJ Espinoza's CSUF thesis, "Dynamic Affects of Foreign and
Domestic Variables on Nicaragua's Output and Prices" (July 2011, ProQuest UMI 1501514), treats
the U.S. federal funds rate, U.S. output and a world commodity price index as exogenous to
Nicaragua. That is the small open economy block structure of Cushman and Zha (1997).

## What changes

- A pure `core/svar/` package: data checks, block-restricted reduced-form estimation,
  identification within each block, impulse responses, FEVD, historical decomposition, and
  bootstrap bands that keep the block restriction in every draw.
- A likelihood-ratio test of the block-exogeneity restriction against the unrestricted VAR,
  reported on every run (the restriction is imposed by the researcher, tested by the tool).
- A `svar` CLI command (Typer) that reads a CSV, writes CSV/PNG outputs and `run.json`.
- Known-answer tests on simulated block-exogenous data, and a cross-check against Stata's
  `var ... constraints()` on one dataset.
- Package rename from the template (`project_template` to `csuf_fullerton`) and a pip-based
  `make install`, done as task 1 since every later task depends on the package name.
- Docs: a worked example a student can copy, including how to swap in another country.

## Sources

- Cushman, D. O. and Zha, T. (1997), "Identifying monetary policy in a small open economy under
  flexible exchange rates," *Journal of Monetary Economics* 39(3): 433-448.
  https://doi.org/10.1016/S0304-3932(97)00029-9
- Zha, T. (1999), "Block recursion and structural vector autoregressions," *Journal of
  Econometrics* 90(2): 291-316. https://ideas.repec.org/a/eee/econom/v90y1999i2p291-316.html
- Proposal deck V2 (`deliverables/JJ-CSUF - VAR AI Agent Proposal V2.pptx` in the Drive project
  folder) and its summary note `2026-10-01-var-agent-deck-csuf` in the Obsidian vault.
- Prior change: [0001-pr-issue-link](../0001-pr-issue-link/proposal.md) (every PR closes an issue).

## Non-goals

- The agent orchestrator, routing and diagnostics loop (change 0003, issue #5).
- VECM or cointegration inside the blocks; this change assumes the researcher has chosen
  levels or differences.
- Sign restrictions, long-run restrictions, Bayesian (Sims-Zha) priors, panel or global VARs.
  They are listed in the deck appendix as later extensions.
- Downloading data. The user supplies a CSV; a data-fetch helper is a later change.
- A public release. The repo stays private until the faculty agree on the scope.
