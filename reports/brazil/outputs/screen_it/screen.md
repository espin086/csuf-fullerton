# Exogeneity screen: Brazil

Sample 1999-12 to 2019-12, 241 effective observations, 8 variables, lag order p = 4 (AIC 6, BIC 4, HQ 5), lag augmentation d_max = 1. Deterministic terms: constant, trend, seasonal dummies.

## Recommendation

**Foreign block {commodity, us_act, cn_act, ffr}**, domestic block {br_ip, br_cpi, br_selic, br_er}. Theory grade A (foreign block is exactly the exogenous-by-theory set); statistical verdict **mixed** (lag restriction holds but not weakly exogenous: ffr).

Runner-up: {commodity, cn_act}, grade B, verdict supported, BIC -19.932 against -20.101.

## Stage 1. Integration order

| Variable | Order | ADF p (level) | KPSS p (level) | ADF p (diff) | KPSS p (diff) | Conflict |
|---|---|---|---|---|---|---|
| commodity | I(1) | 0.767 | 0.010 | <0.001 | 0.100 |  |
| us_act | I(0) | 0.048 | 0.100 | 0.001 | 0.100 |  |
| cn_act | I(1) | 0.399 | 0.010 | <0.001 | 0.100 |  |
| ffr | I(1) | 0.004 | 0.027 | 0.009 | 0.100 | yes |
| br_ip | I(1) | 0.814 | 0.010 | <0.001 | 0.079 |  |
| br_cpi | I(1) | 0.290 | 0.010 | 0.007 | 0.095 |  |
| br_selic | I(1) | 0.106 | 0.037 | <0.001 | 0.100 |  |
| br_er | I(1) | 0.815 | 0.010 | <0.001 | 0.100 |  |

Johansen trace test: cointegrating rank 1 of 8 at 5%. Weak exogeneity tests are run on the foreign block.

## Stage 3. Pairwise evidence

Lag-augmented (Toda-Yamamoto) Granger p-values, conditional on the whole system, unadjusted. Row is the equation (effect), column the cause. Bold marks pairs that stay below 0.05 after Holm adjustment across all 56 pairs.

| effect \ cause | commodity | us_act | cn_act | ffr | br_ip | br_cpi | br_selic | br_er |
|---|---|---|---|---|---|---|---|---|
| commodity |  | 0.144 | <0.001 | 0.067 | 0.738 | 0.412 | 0.897 | 0.663 |
| us_act | 0.843 |  | 0.008 | **<0.001** | 0.389 | 0.512 | 0.279 | 0.558 |
| cn_act | 0.128 | 0.176 |  | 0.580 | 0.945 | 0.108 | 0.123 | 0.554 |
| ffr | 0.517 | **<0.001** | 0.448 |  | 0.006 | 0.150 | 0.946 | 0.624 |
| br_ip | 0.271 | 0.168 | 0.118 | 0.078 |  | 0.372 | 0.070 | 0.644 |
| br_cpi | 0.003 | 0.116 | 0.145 | 0.970 | 0.227 |  | 0.025 | **<0.001** |
| br_selic | 0.296 | 0.821 | 0.108 | 0.595 | 0.693 | 0.379 |  | 0.123 |
| br_er | 0.076 | 0.002 | 0.063 | 0.328 | 0.888 | **<0.001** | 0.522 |  |

![Granger heat map](granger.png)


DirectLiNGAM causal order of the reduced-form residuals (advisory; needs non-Gaussian residuals, 100% of series reject normality): **cn_act > br_cpi > ffr > us_act > commodity > br_selic > br_ip > br_er**.

| Pair | Pairwise direction | R |
|---|---|---|
| commodity, br_ip | commodity -> br_ip | +0.0003 |
| commodity, br_cpi | commodity -> br_cpi | +0.0000 |
| commodity, br_selic | commodity -> br_selic | +0.0001 |
| commodity, br_er | commodity -> br_er | +0.0069 |
| us_act, br_ip | us_act -> br_ip | +0.0001 |
| us_act, br_cpi | br_cpi -> us_act | -0.0003 |
| us_act, br_selic | br_selic -> us_act | -0.0000 |
| us_act, br_er | us_act -> br_er | +0.0002 |
| cn_act, br_ip | cn_act -> br_ip | +0.0012 |
| cn_act, br_cpi | cn_act -> br_cpi | +0.0015 |
| cn_act, br_selic | br_selic -> cn_act | -0.0005 |
| cn_act, br_er | cn_act -> br_er | +0.0016 |
| ffr, br_ip | br_ip -> ffr | -0.0001 |
| ffr, br_cpi | br_cpi -> ffr | -0.0020 |
| ffr, br_selic | ffr -> br_selic | +0.0022 |
| ffr, br_er | ffr -> br_er | +0.0029 |

## Stage 4 and 5. Candidate specifications

LA-Wald is the primary test (domestic lags excluded from foreign equations, robust to unit roots); its p-value is bootstrapped under the null (Hacker and Hatemi-J 2006) because the asymptotic version over-rejects in samples this size. Holm p adjusts the bootstrap p across every admissible candidate. LR is the Sims-corrected likelihood ratio of change 0002. Inst. p tests residual correlation between blocks (rejection is expected and is what the recursive impact matrix orders). CW is the Clark-West out-of-sample test that domestic lags improve foreign forecasts. LiNGAM agree is the share of foreign-domestic pairs the data-driven causal order puts foreign first, with the bootstrap 5th percentile.

| Rank | Foreign block | Theory | Verdict | LA-Wald asym. p | LA-Wald boot p | Holm p | LR p | Inst. p | Not weakly exog. | CW Holm p | BIC | LiNGAM agree (5%) | Max root |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | {commodity, us_act, cn_act, ffr} | A | mixed | 0.212 | 0.370 | 0.792 | 0.059 | 0.001 | ffr | 0.401 | -20.101 | 0.81 (0.25) | 0.980 |
| 2 | {commodity, cn_act} | B | supported | 0.170 | 0.350 | 0.792 | 0.080 | <0.001 | none | 1.000 | -19.932 | 0.75 (0.16) | 0.985 |
| 3 | {cn_act} | B | supported | 0.061 | 0.164 | 0.792 | 0.025 | 0.134 | none | 0.289 | -19.681 | 1.00 (0.14) | 0.981 |
| 4 | {us_act, cn_act, ffr} | B | mixed | 0.064 | 0.158 | 0.792 | 0.027 | <0.001 | ffr | 0.025 | -20.032 | 0.87 (0.27) | 0.976 |
| 5 | {commodity, cn_act, ffr} | B | mixed | 0.003 | 0.032 | 0.253 | 0.004 | <0.001 | ffr | 0.945 | -19.978 | 0.80 (0.27) | 0.979 |
| 6 | {commodity, us_act, cn_act} | B | mixed | 0.096 | 0.199 | 0.792 | 0.004 | 0.001 | us_act | 0.186 | -19.978 | 0.73 (0.20) | 0.986 |
| 7 | {commodity, us_act, ffr} | B | mixed | 0.002 | 0.024 | 0.217 | <0.001 | <0.001 | ffr | 0.617 | -19.875 | 0.60 (0.13) | 0.994 |
| 8 | {us_act, ffr} | B | mixed | 0.027 | 0.102 | 0.712 | 0.004 | <0.001 | us_act, ffr | 0.147 | -19.854 | 0.67 (0.08) | 0.986 |
| 9 | {us_act, cn_act} | B | mixed | 0.044 | 0.129 | 0.775 | 0.002 | 0.137 | us_act | 0.129 | -19.840 | 0.83 (0.25) | 0.978 |
| 10 | {cn_act, ffr} | B | mixed | <0.001 | 0.004 | 0.050 | <0.001 | <0.001 | ffr | 0.079 | -19.792 | 0.92 (0.33) | 0.975 |
| 11 | {commodity} | B | mixed | 0.001 | 0.013 | 0.125 | <0.001 | <0.001 | commodity | 0.071 | -19.615 | 0.43 (0.00) | 1.000 |
| 12 | {us_act} | B | mixed | <0.001 | 0.005 | 0.055 | <0.001 | 0.123 | us_act | 0.347 | -19.592 | 0.57 (0.00) | 0.988 |
| 13 | {commodity, ffr} | B | rejected | <0.001 | 0.002 | 0.023 | <0.001 | <0.001 | commodity, ffr | 0.069 | -19.723 | 0.58 (0.17) | 0.998 |
| 14 | {commodity, us_act} | B | rejected | <0.001 | <0.001 | 0.013 | <0.001 | <0.001 | commodity, us_act | 0.924 | -19.717 | 0.50 (0.08) | 0.991 |
| 15 | {ffr} | B | rejected | <0.001 | 0.002 | 0.023 | 0.002 | <0.001 | ffr | 0.230 | -19.633 | 0.71 (0.14) | 0.986 |

## Stage 6. Robustness of headline responses

- **br_ip to a cn_act shock**: recommended specification peaks at +1.0778 at horizon 12; 14 of 14 surviving specifications and orderings have the same sign there.

![robustness](robust_br_ip_cn_act.png)

- **br_ip to a us_act shock**: recommended specification peaks at +0.4283 at horizon 8; 14 of 14 surviving specifications and orderings have the same sign there.

![robustness](robust_br_ip_us_act.png)

- **br_cpi to a commodity shock**: recommended specification peaks at -0.2887 at horizon 16; 14 of 14 surviving specifications and orderings have the same sign there.

![robustness](robust_br_cpi_commodity.png)

- **br_ip to a ffr shock**: recommended specification peaks at -0.2562 at horizon 7; 14 of 14 surviving specifications and orderings have the same sign there.

![robustness](robust_br_ip_ffr.png)


## Theory file

| Variable | Prior | Rationale | Source |
|---|---|---|---|
| commodity | exogenous | World commodity price index. Brazil is a large exporter of soybeans and iron ore, so it is not a pure price taker in every market, but the all-commodity index is dominated by energy, where Brazil has no pricing power at a monthly frequency. | Kim and Roubini (2000); Cesa-Bianchi et al. (2012) on the commodity channel |
| us_act | exogenous | U.S. activity. Brazil's economy is under a tenth the size of the U.S. economy and U.S. exports to Brazil are about 1% of U.S. GDP; no plausible monthly feedback. | Cushman and Zha (1997); Mackowiak (2007) |
| cn_act | exogenous | China activity. Brazil is China's main soybean and a major iron ore supplier, which makes this the weakest exogeneity claim in the model; the screen tests it. | Cesa-Bianchi et al. (2012) |
| ffr | exogenous | U.S. policy rate; the FOMC does not react to Brazilian conditions. | Cushman and Zha (1997) |
| br_ip | endogenous | Domestic activity. |  |
| br_cpi | endogenous | Domestic prices. |  |
| br_selic | endogenous | Policy rate under inflation targeting since June 1999; reacts to domestic inflation and activity. | Banco Central do Brasil inflation-targeting regime |
| br_er | endogenous | Floating real per dollar since January 1999; reacts to domestic and foreign shocks within the month. | Banco Central do Brasil exchange-rate regime |
