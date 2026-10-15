#!/usr/bin/env bash
# Rebuild every output behind reports/brazil/report.md from the committed data.
#   bash scripts/reproduce_brazil.sh [OUT]          default OUT=results/brazil
#   FETCH=1 bash scripts/reproduce_brazil.sh        re-download data/brazil*.csv first
#   QUICK=1 bash scripts/reproduce_brazil.sh        fewer bootstrap and MCMC draws (minutes)
# Compare with the committed outputs:
#   .venv/bin/python scripts/compare_outputs.py reports/brazil/outputs results/brazil
set -euo pipefail
OUT="${1:-results/brazil}"
CLI="${CLI:-csuf-fullerton}"
command -v "$CLI" >/dev/null 2>&1 || CLI=.venv/bin/csuf-fullerton
DATA=data/brazil.csv
TRADE=data/brazil_trade.csv
THEORY=examples/brazil/theory.toml
if [[ "${FETCH:-0}" == "1" ]]; then
  "$CLI" fetch examples/brazil/data.toml --out "$DATA"
  "$CLI" trade-weights --country BRA --partners us=USA,cn=CHN --out "$TRADE"
fi
if [[ "${QUICK:-0}" == "1" ]]; then
  DRAWS=99; LR=49; BRK=49; MCMC=(--mcmc-draws 1500 --burn 500 --thin 2)
else
  DRAWS=1000; LR=199; BRK=199; MCMC=(--mcmc-draws 10000 --burn 2000 --thin 4)
fi
IT=(--start 1999-07 --end 2019-12)          # inflation targeting, before COVID
BLOCKS=(--foreign commodity,us_act,cn_act,ffr --domestic br_ip,br_cpi,br_selic,br_er)
W=(--trade "$TRADE" --partners us=us_act,cn=cn_act --weight-window 3 --weights-lag 1)
HEAD=(--headline br_ip:cn_act,br_ip:us_act,br_cpi:cn_act,br_er:cn_act)

# 1. Exogeneity and lag-order screens (theory plus data) before any VAR.
"$CLI" screen "$DATA" "$THEORY" --max-lags 6 --out "$OUT/screen_full"
"$CLI" screen "$DATA" "$THEORY" --max-lags 6 "${IT[@]}" --out "$OUT/screen_it"
for p in 2 6; do
  "$CLI" screen "$DATA" "$THEORY" --lags "$p" "${IT[@]}" --out "$OUT/screen_it_p$p"
done

# 2. M0: constant baseline, Chow test at 2009-01 and sup-LR over all dates.
"$CLI" tvsvar "$DATA" --model m0 "${BLOCKS[@]}" --lags 4 --seasonal "${IT[@]}" \
  --break 2009-01 --break-draws "$BRK" --draws "$DRAWS" --out "$OUT/m0_p4"

# 3. M1: trade-weighted SVAR. Headline: interacted, p = 4 (BIC).
for p in 2 4 6; do
  "$CLI" tvsvar "$DATA" --model m1 "${BLOCKS[@]}" "${W[@]}" "${HEAD[@]}" --lags "$p" --seasonal \
    "${IT[@]}" --frozen-years 2000,2009,2019 --draws "$DRAWS" --lr-draws "$LR" --out "$OUT/m1_p$p"
done
"$CLI" tvsvar "$DATA" --model m1 "${BLOCKS[@]}" "${W[@]}" "${HEAD[@]}" --lags 4 --seasonal \
  --variant star "${IT[@]}" --frozen-years 2000,2009,2019 --draws "$DRAWS" --lr-draws 0 \
  --out "$OUT/m1_star_p4"
"$CLI" tvsvar "$DATA" --model m1 "${BLOCKS[@]}" "${W[@]}" "${HEAD[@]}" --lags 4 --seasonal \
  --start 1999-07 --end 2023-11 --frozen-years 2000,2009,2022 --draws "$DRAWS" --lr-draws "$LR" \
  --out "$OUT/m1_p4_to2023"

# 4. M2: kernel drift check (bandwidth T^0.7, p = 2, local constant).
"$CLI" tvsvar "$DATA" --model m2 "${BLOCKS[@]}" "${W[@]}" "${HEAD[@]}" --lags 2 --no-trend \
  --seasonal --bandwidth-exp 0.7 "${IT[@]}" --out "$OUT/m2_p2"

# 5. M3: TVP-VAR with stochastic volatility on a four-variable system.
"$CLI" tvsvar "$DATA" --model m3 "${BLOCKS[@]}" --m3-vars us_act,cn_act,br_ip,br_cpi --m3-yoy br_ip,br_cpi --m3-lags 2 \
  "${MCMC[@]}" --headline br_ip:cn_act,br_ip:us_act --irf-dates 2002-06,2009-06,2019-06 \
  "${IT[@]}" --out "$OUT/m3"
echo "Brazil outputs in $OUT"
