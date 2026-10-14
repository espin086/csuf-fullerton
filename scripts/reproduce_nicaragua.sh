#!/usr/bin/env bash
# Rebuild every output behind reports/nicaragua/report.md from the committed data.
#   bash scripts/reproduce_nicaragua.sh [OUT]        default OUT=results/nicaragua
#   FETCH=1 bash scripts/reproduce_nicaragua.sh      re-download data/nicaragua.csv first
# Then compare with the committed outputs:
#   .venv/bin/python scripts/compare_outputs.py reports/nicaragua/outputs results/nicaragua
set -euo pipefail
OUT="${1:-results/nicaragua}"
CLI="${CLI:-csuf-fullerton}"
command -v "$CLI" >/dev/null 2>&1 || CLI=.venv/bin/csuf-fullerton
DATA=data/nicaragua.csv
THEORY=examples/nicaragua/theory.toml
if [[ "${FETCH:-0}" == "1" ]]; then
  "$CLI" fetch examples/nicaragua/data.toml --out "$DATA"
fi
"$CLI" screen "$DATA" "$THEORY" --max-lags 4 --out "$OUT/screen"
"$CLI" screen "$DATA" "$THEORY" --lags 4 --out "$OUT/screen_p4"
"$CLI" screen "$DATA" "$THEORY" --max-lags 4 --dmax 1 --out "$OUT/screen_dmax1"
THESIS=(--foreign ffr,us_ip,commodity --domestic ni_ip,ni_cpi,ni_m2,ni_er)
RECOMMENDED=(--foreign ffr,us_ip,commodity,ni_er --domestic ni_ip,ni_cpi,ni_m2)
COMMON=(--seasonal --dmax 2 --draws 1000 --bands hall)
for p in 1 4; do
  "$CLI" svar "$DATA" "${THESIS[@]}" --lags "$p" "${COMMON[@]}" --out "$OUT/svar_thesis_p$p"
  "$CLI" svar "$DATA" "${RECOMMENDED[@]}" --lags "$p" "${COMMON[@]}" --out "$OUT/svar_recommended_p$p"
done
echo "Nicaragua outputs in $OUT"
