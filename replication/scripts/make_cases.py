"""Write replication/cases/*.toml with fixture hashes. Re-run after a fixture changes:

    .venv/bin/python replication/scripts/make_cases.py
    .venv/bin/python replication/scripts/make_cases.py --pin results/replication/scorecard.json

Golden values are kept: an existing case file's `golden` and `golden_tol` survive a rewrite.
"""

from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path

CASES = Path("replication/cases")
BR = dict(
    foreign=["commodity", "us_act", "cn_act", "ffr"],
    domestic=["br_ip", "br_cpi", "br_selic", "br_er"],
    partners=[["us", ["us_act"]], ["cn", ["cn_act"]]],
    seasonal=True,
    trend=True,
    window=3,
    weights_lag=1,
)
DATA = {
    "brazil": "data/brazil.csv",
    "trade": "data/brazil_trade.csv",
    "nicaragua": "data/nicaragua.csv",
    "nicaragua_irf": "reports/nicaragua/outputs/svar_thesis_p1/irf.csv",
    "primiceri": "replication/fixtures/primiceri_us.csv",
}


def sha(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def toml_value(v: object) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return f'"{v}"'
    if isinstance(v, list):
        return "[" + ", ".join(toml_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {toml_value(x)}" for k, x in v.items()) + " }"
    return repr(v)


PINNED = {"m1-cesa-bianchi-2012-direction", "m2-brazil-regression"}


def pin(scorecard: Path) -> None:
    """Copy observed values of deterministic OLS cases into the case files as golden values."""
    import json

    card = json.loads(scorecard.read_text())
    for row in card["metrics"]:
        if row["case"] not in PINNED or not row["metric"]:
            continue
        path = CASES / f"{row['case']}.toml"
        text = path.read_text()
        block = f'name = "{row["metric"]}"'
        start = text.index(block)
        end = text.find("[[metric]]", start)
        end = len(text) if end < 0 else end
        body = "\n".join(
            ln for ln in text[start:end].rstrip().splitlines() if not ln.startswith("golden")
        )
        body += f"\ngolden = {row['observed']!r}\ngolden_tol = 1e-06\n"
        text = text[:start] + body + ("\n" if end < len(text) else "") + text[end:]
        path.write_text(text)


def case(
    id: str,
    model: str,
    kind: str,
    suite: str,
    function: str,
    source: str,
    seed: int,
    data: dict[str, str],
    settings: dict[str, object],
    metrics: list[dict[str, object]],
    qualitative: bool = False,
    notes: str = "",
) -> None:
    path = CASES / f"{id}.toml"
    old = {}
    if path.exists():
        old = {m["name"]: m for m in tomllib.loads(path.read_text()).get("metric", [])}
    lines = [
        f'id = "{id}"',
        f'model = "{model}"',
        f'kind = "{kind}"',
        f'suite = "{suite}"',
        f'function = "{function}"',
        f"source = {toml_value(source)}",
        f"seed = {seed}",
        f"qualitative = {toml_value(qualitative)}",
    ]
    if notes:
        lines.append(f"notes = {toml_value(notes)}")
    for name, key in data.items():
        lines += [
            "",
            "[[data]]",
            f'name = "{name}"',
            f'path = "{DATA[key]}"',
            f'sha256 = "{sha(DATA[key])}"',
        ]
    lines += ["", "[settings]"] + [f"{k} = {toml_value(v)}" for k, v in settings.items()]
    for m in metrics:
        prev = old.get(m["name"], {})
        m = {**m, **{k: prev[k] for k in ("golden", "golden_tol") if k in prev}}
        lines += ["", "[[metric]]"] + [f"{k} = {toml_value(v)}" for k, v in m.items()]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    CASES.mkdir(parents=True, exist_ok=True)
    it = dict(start="1999-07", end="2019-12")
    # M0
    case(
        "m0-parity-statsmodels",
        "m0",
        "parity",
        "fast",
        "m0_parity_statsmodels",
        "statsmodels.tsa.api.VAR, constant only",
        0,
        {"data": "brazil"},
        {"lags": 4, **it},
        [{"name": "max_abs_diff", "op": "<=", "target": 1e-8}],
    )
    case(
        "m0-nicaragua-regression",
        "m0",
        "regression",
        "fast",
        "m0_nicaragua_regression",
        "Committed Nicaragua thesis-split SVAR (change 0004 report, p = 1)",
        20261014,
        {"data": "nicaragua", "irf": "nicaragua_irf"},
        {
            "foreign": ["ffr", "us_ip", "commodity"],
            "domestic": ["ni_ip", "ni_cpi", "ni_m2", "ni_er"],
            "lags": 1,
            "horizon": 24,
            "dmax": 2,
            "draws": 2,
        },
        [{"name": "max_abs_diff", "op": "<=", "target": 1e-8}],
    )
    case(
        "m0-sim-break-power",
        "m0",
        "simulation",
        "fast",
        "m0_sim_break",
        "Andrews (1993) sup-LR, bootstrap p, M1 DGP with drifting transmission",
        11,
        {},
        {"reps": 3, "n": 400, "draws": 49, "scale": 1.0},
        [{"name": "rejection_rate", "op": ">=", "target": 0.66}],
    )
    case(
        "m0-sim-break-size",
        "m0",
        "simulation",
        "full",
        "m0_sim_break",
        "Andrews (1993) sup-LR, bootstrap p, constant-coefficient DGP",
        12,
        {},
        {"reps": 100, "n": 300, "draws": 99, "scale": 0.0},
        [{"name": "rejection_rate", "op": "between", "target": [0.0, 0.10]}],
    )
    # M1
    case(
        "m1-parity-constant",
        "m1",
        "parity",
        "fast",
        "m1_parity_constant",
        "Change 0002 block-exogenous estimator",
        0,
        {"data": "brazil", "trade": "trade"},
        {**BR, "lags": 4, **it},
        [{"name": "max_abs_diff", "op": "<=", "target": 1e-10}],
    )
    case(
        "m1-sim-coverage-fast",
        "m1",
        "simulation",
        "fast",
        "m1_sim_coverage",
        "Frozen-weight IRF coverage, M1 DGP",
        100,
        {},
        {"n": 400, "reps": 10, "draws": 99, "horizon": 12, "level": 0.9},
        [
            {"name": "coverage_first", "op": ">=", "target": 0.65},
            {"name": "coverage_last", "op": ">=", "target": 0.65},
            {"name": "coverage_diff", "op": ">=", "target": 0.6},
        ],
    )
    case(
        "m1-sim-coverage",
        "m1",
        "simulation",
        "full",
        "m1_sim_coverage",
        "Frozen-weight IRF coverage, M1 DGP",
        200,
        {},
        {"n": 400, "reps": 200, "draws": 199, "horizon": 12, "level": 0.9},
        [
            {"name": "coverage_first", "op": ">=", "target": 0.80},
            {"name": "coverage_last", "op": ">=", "target": 0.80},
            {"name": "coverage_diff", "op": ">=", "target": 0.75},
        ],
        notes="Nominal 90% Hall bands. Bootstrap IRF bands under-cover in samples this size "
        "(Kilian 1998); 40 replications gave 0.82, 0.82 and 0.76.",
    )
    case(
        "m1-sim-lr-size-fast",
        "m1",
        "simulation",
        "fast",
        "m1_sim_lr_size",
        "Constant-vs-interacted LR size and power, M1 DGP",
        300,
        {},
        {"n": 400, "reps": 40},
        [
            {"name": "size", "op": "between", "target": [0.0, 0.15]},
            {"name": "power", "op": ">=", "target": 0.8},
        ],
    )
    case(
        "m1-sim-lr-size",
        "m1",
        "simulation",
        "full",
        "m1_sim_lr_size",
        "Constant-vs-interacted LR size and power, M1 DGP",
        400,
        {},
        {"n": 400, "reps": 500},
        [
            {"name": "size", "op": "between", "target": [0.03, 0.08]},
            {"name": "power", "op": ">=", "target": 0.9},
        ],
    )
    case(
        "m1-cesa-bianchi-2012-direction",
        "m1",
        "published",
        "fast",
        "m1_direction",
        "Cesa-Bianchi, Pesaran, Rebucci and Xu (2012), IZA DP 5889, fixed 1995 vs 2009 weights",
        0,
        {"data": "brazil", "trade": "trade"},
        {
            **BR,
            "lags": 4,
            "start": "1999-07",
            "end": "2009-12",
            "year_a": 1995,
            "year_b": 2009,
            "h0": 0,
            "h1": 24,
            "pairs": {"change_cn": ["br_ip", "cn_act"], "change_us": ["br_ip", "us_act"]},
        },
        [
            {"name": "change_cn", "op": ">=", "target": 0.0},
            {"name": "change_us", "op": "<=", "target": 0.0},
        ],
        qualitative=True,
        notes="Direction only: their model is a multi-country GVAR on quarterly GDP, ours one "
        "country, monthly, p = 4 (BIC in the exogeneity screen). With p = 2 the China change "
        "is positive over months 0-12 but turns slightly negative over months 12-24; see the "
        "Brazil report's sensitivity table.",
    )
    # M2
    case(
        "m2-parity-flat",
        "m2",
        "parity",
        "fast",
        "m2_parity_flat",
        "Flat kernel equals the change 0002 estimator",
        0,
        {"data": "brazil"},
        {"foreign": BR["foreign"], "domestic": BR["domestic"], "lags": 4, **it},
        [{"name": "max_abs_diff", "op": "<=", "target": 1e-8}],
    )
    case(
        "m2-sim-sinusoid",
        "m2",
        "simulation",
        "fast",
        "m2_sim_sinusoid",
        "Giraitis, Kapetanios and Yates (2014) style smooth drift",
        500,
        {},
        {"reps": 5, "n_small": 200, "n_large": 800, "exponent": 0.5},
        [
            {"name": "mad_ratio", "op": "<=", "target": 1.0},
            {"name": "mad_large", "op": "<=", "target": 0.06},
        ],
    )
    case(
        "m2-brazil-regression",
        "m2",
        "regression",
        "fast",
        "m2_brazil_regression",
        "Pinned kernel path of Brazil IP on China activity",
        0,
        {"data": "brazil", "trade": "trade"},
        {
            **BR,
            "trend": False,
            "lags": 2,
            **it,
            "pair": ["br_ip", "cn_act"],
            "partner": "cn",
            "exponent": 0.7,
        },
        [
            {"name": "change_last_minus_first_fifth", "op": "between", "target": [-50.0, 50.0]},
            {"name": "corr_with_weight", "op": "between", "target": [-1.0, 1.0]},
        ],
        notes="Bandwidth T^0.7 with p = 2 and a local constant: GKY's T^0.5 leaves too few "
        "effective observations at the sample ends for an eight-variable monthly system.",
    )
    # M3
    case(
        "m3-parity-kalman",
        "m3",
        "parity",
        "fast",
        "m3_parity_kalman",
        "statsmodels Kalman smoother, conditional posterior mean of the coefficient states",
        7,
        {},
        {"n": 150},
        [{"name": "max_abs_diff", "op": "<=", "target": 1e-8}],
    )
    case(
        "m3-sim-coverage-fast",
        "m3",
        "simulation",
        "fast",
        "m3_sim_coverage",
        "TVP-VAR-SV recovery, drift on the prior's scale",
        600,
        {},
        {
            "reps": 2,
            "n": 200,
            "beta_sd": 0.003,
            "lv_sd": 0.05,
            "p": 1,
            "draws": 1500,
            "burn": 500,
            "thin": 2,
        },
        [
            {"name": "beta_coverage", "op": ">=", "target": 0.6},
            {"name": "log_var_coverage", "op": ">=", "target": 0.6},
            {"name": "max_foreign_response_to_domestic", "op": "<=", "target": 0.0},
        ],
    )
    case(
        "m3-sim-coverage",
        "m3",
        "simulation",
        "full",
        "m3_sim_coverage",
        "TVP-VAR-SV recovery, drift on the prior's scale",
        700,
        {},
        {
            "reps": 8,
            "n": 250,
            "beta_sd": 0.003,
            "lv_sd": 0.05,
            "p": 1,
            "draws": 4000,
            "burn": 1500,
            "thin": 3,
        },
        [
            {"name": "beta_coverage", "op": ">=", "target": 0.75},
            {"name": "log_var_coverage", "op": ">=", "target": 0.7},
            {"name": "max_foreign_response_to_domestic", "op": "<=", "target": 0.0},
        ],
    )
    for suite, draws, burn in (("fast", 3000, 1000), ("full", 10000, 2000)):
        case(
            f"m3-primiceri-2005{'-fast' if suite == 'fast' else ''}",
            "m3",
            "published",
            suite,
            "m3_primiceri",
            "Primiceri (2005), Figure 1: interest-rate volatility peaks around 1981",
            1,
            {"data": "primiceri"},
            {
                "columns": ["inflation", "unemployment", "tbill"],
                "rate": "tbill",
                "base_date": "1995Q1",
                "p": 2,
                "training": 40,
                "draws": draws,
                "burn": burn,
                "thin": 4,
            },
            [
                {"name": "rate_vol_peak_year", "op": "between", "target": [1979.0, 1983.75]},
                {"name": "rate_vol_peak_over_base", "op": ">=", "target": 3.0},
            ],
            qualitative=True,
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "--pin":
        pin(Path(sys.argv[2]))
    else:
        main()
