# Block-exogenous SVAR

Foreign block {ffr, us_ip, commodity, ni_er}, domestic block {ni_ip, ni_cpi, ni_m2}. Sample 2002-06 to 2014-06 (145 observations), p = 4, recursive identification in the order listed, 1000 bootstrap draws, 68% hall bands.

| Test | Statistic | df | p |
|---|---|---|---|
| block exogeneity LR (Sims) | 71.71 | 48 | 0.015 |
| lag-augmented Wald (p=4, d_max=2) | 54.15 | 48 | 0.251 |
| portmanteau (h=12) | 576.33 | 392 | <0.001 |
| max companion root | 0.977 |  |  |

**Warning:** the block-exogeneity restriction is rejected at 5% (LR p = 0.015, lag-augmented Wald p = 0.251). It is still imposed. With integrated data the levels LR test over-rejects; the lag-augmented Wald is the valid test (see the exogeneity screen).


![impulse responses](irf.png)

## Forecast error variance decomposition

**ni_ip**

| h | ffr | us_ip | commodity | ni_er | ni_ip | ni_cpi | ni_m2 |
|---|---|---|---|---|---|---|---|
| 0 | 0.4 | 2.3 | 0.1 | 0.0 | 97.1 | 0.0 | 0.0 |
| 6 | 9.9 | 5.2 | 1.3 | 3.2 | 78.1 | 0.8 | 1.5 |
| 12 | 10.3 | 6.3 | 1.5 | 3.3 | 74.9 | 2.0 | 1.6 |
| 24 | 10.3 | 9.7 | 2.6 | 3.2 | 69.5 | 3.1 | 1.6 |

**ni_cpi**

| h | ffr | us_ip | commodity | ni_er | ni_ip | ni_cpi | ni_m2 |
|---|---|---|---|---|---|---|---|
| 0 | 0.0 | 1.0 | 25.2 | 0.0 | 0.1 | 73.7 | 0.0 |
| 6 | 13.6 | 11.3 | 41.9 | 0.2 | 0.2 | 32.7 | 0.1 |
| 12 | 17.3 | 15.6 | 41.2 | 0.2 | 0.1 | 25.4 | 0.3 |
| 24 | 15.4 | 25.9 | 31.8 | 0.1 | 0.1 | 26.3 | 0.5 |

**ni_m2**

| h | ffr | us_ip | commodity | ni_er | ni_ip | ni_cpi | ni_m2 |
|---|---|---|---|---|---|---|---|
| 0 | 0.1 | 1.9 | 0.2 | 0.2 | 0.5 | 0.8 | 96.4 |
| 6 | 0.2 | 59.2 | 7.1 | 0.3 | 0.6 | 1.1 | 31.4 |
| 12 | 1.2 | 72.0 | 6.0 | 0.3 | 0.4 | 1.3 | 18.7 |
| 24 | 1.1 | 68.5 | 13.1 | 1.5 | 0.3 | 1.9 | 13.6 |

Share of domestic forecast error variance due to foreign shocks at the last horizon: ni_ip 25.9%, ni_cpi 73.2%, ni_m2 84.2%.
