# Time-varying VARs for a changing main trading partner: literature and tooling

Research note for change 0005. Written 2026-10-14.

## The problem

Brazil's largest trading partner was the United States for decades; China passed it in 2009
(Brazilian trade ministry figures, reported by NPR in 2012). A constant-coefficient SVAR on a
1996-2025 sample averages the two regimes. Three ways to let the transmission of foreign shocks
change appear in the literature.

## 1. Observable-driven change: trade weights

**Cesa-Bianchi, Pesaran, Rebucci and Xu (2012)**, *Economía* 12(2); IZA DP 5889. Closest paper
to the Brazil question. GVAR with five large Latin American economies (Argentina, Brazil, Chile,
Mexico, Peru) and the major economies, 1979Q2-2009Q4. Country models are estimated with
three-year moving-average trade weights (current and previous two years). Impulse responses are
then computed with fixed weights from 1985, 1995, 2005 and 2009. Headline: the long-run effect
of a China GDP shock on a typical Latin American economy is about three times larger with 2009
weights than with 1995 weights; the effect of a U.S. GDP shock roughly halves. They attribute
the change mostly to China's larger effect on Latin America's traditional partners, not to
direct bilateral trade. https://docs.iza.org/dp5889.pdf

**GVAR foundations.** Pesaran, Schuermann and Weiner (2004), *JBES* 22(2); Dees, di Mauro,
Pesaran and Smith (2007), *JAE* 22(1); Chudik and Pesaran (2016), *Journal of Economic Surveys*
30(1) survey. Foreign "star" variables are trade-weighted averages of partner variables, and
each country model treats them as weakly exogenous. That is block exogeneity applied country by
country.

**Feldkircher and Huber (2016)**, *European Economic Review*: Bayesian GVAR, sign-restricted
U.S. shocks; spillovers run through interest rates and the real effective exchange rate. Working
paper OeNB WP 195. A time-varying-parameter GVAR follows in Crespo Cuaresma, Doppelhofer,
Feldkircher and Huber (OeNB WP 205, 2016).

**Gauvin and Rebillard (2018)**, *The World Economy* 41(12): GVAR with metals and oil added as
"commodity countries," 36 countries, 1995Q1-2014Q3; a Chinese hard landing transmitted through
trade and commodity prices. Relevant because Brazil's China exposure runs through commodities.

**Towbin and Weber (2013)**, *Journal of Development Economics* 101: interacted panel VAR in
which coefficients are linear in country characteristics (foreign currency debt, import
structure). Same idea as M1's `interacted` variant, with trade share as the interaction
variable. https://doi.org/10.1016/j.jdeveco.2012.10.007

## 2. Latent drift: TVP-VAR

**Primiceri (2005)**, *RES* 72(3): random-walk coefficients, random-walk contemporaneous
relations, stochastic volatility. U.S. 1953-2001. The **Del Negro and Primiceri (2015)**
corrigendum fixes the order of the Gibbs steps; any new code must use the corrected order.

**Cogley and Sargent (2005)**, *RED* 8(2): drifting coefficients and volatilities for U.S.
inflation dynamics.

**Nakajima (2011)**, Bank of Japan *Monetary and Economic Studies* 29: practitioner guide to
TVP-VAR with SV, with Japanese data and code.

**Liu, Mumtaz and Theophilopoulou (2014)**, *JIMF* 46: time-varying factor-augmented VAR for
the UK and 17 industrial countries. The UK response to a foreign interest-rate shock changed
after the early 1990s. The open-economy TVP precedent. BoE WP 425 (2011).

**Koop and Korobilis (2013)**, *J. Econometrics* 177(2): large TVP-VARs with forgetting
factors, cheap enough for many variables.

**Chan and Jeliazkov (2009)**: precision-based sampler for state-space models; the method
behind statsmodels' `cfa` simulation smoother and Joshua Chan's `TVPVAR.m`.

## 3. Nonparametric drift: kernel estimators

**Giraitis, Kapetanios and Yates (2014)**, *J. Econometrics* 179(1): kernel-weighted least
squares for stochastic time-varying coefficients, consistent and asymptotically normal with
simple studentization. **Kapetanios, Marcellino and Venditti (2019)**, *JAE* 34(7): extends it
to large VARs with shrinkage; closed-form, fast, competitive with Bayesian TVP-VARs in
forecasting. Replication files: https://doi.org/10.15456/jae.2022327.0711642101

## Gaps found

No paper found that estimates a single-country block-exogenous TVP-SVAR for Brazil with U.S. and
China as separate foreign blocks and trade weights driving the change. Searches turned up
TVP-VAR connectedness studies of Latin American financial markets and China spillovers to
equity volatility, which answer a different question. The Cesa-Bianchi et al. GVAR is the
benchmark to beat.

## Does statsmodels handle this?

Checked against statsmodels 0.14 documentation, 2026-10-14.

- `tsa.api.VAR` and `SVAR`: constant coefficients only. `SVAR` supports A/B contemporaneous
  restrictions but not zero restrictions on lag blocks, which is why 0002 wrote its own
  block estimator.
- No TVP-VAR class. The state-space framework (`MLEModel`, `simulation_smoother`, including
  `method="cfa"`) is enough to build one, and the official notebook "TVP-VAR, MCMC, and sparse
  simulation smoothing" does: random-walk coefficients, constant observation covariance (no
  stochastic volatility), inverse-Wishart and inverse-gamma priors, Gibbs sampling written by
  hand around the smoother.
  https://www.statsmodels.org/devel/examples/notebooks/generated/statespace_tvpvar_mcmc_cfa.html
- No multivariate stochastic volatility sampler. `MarkovAutoregression` is univariate.
- No GVAR or interacted VAR. Both are OLS on constructed regressors.

Conclusion: the estimators go into numpy and scipy. statsmodels is a test oracle (constant VAR,
homoskedastic TVP-VAR notebook) and stays a runtime dependency only for 0004's unit-root tests.

## Other implementations useful as references

- R `bvarsv` (Fabian Krueger): Primiceri model, includes the 2015 corrigendum, based on Dimitris
  Korobilis's MATLAB code. https://cran.r-project.org/package=bvarsv
- GAUSS `tvpSvFit` (Aptech), RATS code by Todd Clark replicating Primiceri.
- No maintained pip package for Primiceri's model was found.

## Search sources

- https://docs.iza.org/dp5889.pdf
- https://econpapers.repec.org/paper/idbwpaper/4732.htm
- https://www.bankofengland.co.uk/working-paper/2011/international-transmission-of-shocks
- https://strathprints.strath.ac.uk/42735/
- https://oenb.at/en/Publications/Economics/Working-Papers/2014/Working-Paper-195.html
- https://publications.banque-france.fr/sites/default/files/medias/documents/working-paper_562_2015.pdf
- https://www.npr.org/2012/01/02/144587105/brazil-sets-trade-records-due-to-chinese-demand
- https://cran.r-universe.dev/bvarsv/doc/manual.html
