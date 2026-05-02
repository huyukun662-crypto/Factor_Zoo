#!/usr/bin/env python3
"""R6 — 50/50 ensemble of anchor_range_pos_etf_v1 (v1.1) + inv_ivol_voltarget_bondrotate_etf_v2.

Hypothesis: the two factors are anti-correlated by year on the two stress
years (anchor 2022 +1.32 vs v2 2022 +0.23; anchor 2024 +0.20 vs v2 2024 +0.73).
A 50/50 blend should average both stress years > 0.5 and clear the strict
worst-year-Sharpe ≥ 0.5 PROMOTE floor.

Pipeline:
  1. Fetch the full extended Tushare panel (69 symbols + bond ETFs).
  2. Run anchor_v1.1 to get its daily excess return series.
  3. Run inv_ivol_v2 to get its daily final_ret_net5bps series.
  4. Align on common dates and compute 50/50 blend.
  5. Report metrics + per-year + decision.
"""
from __future__ import annotations
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/user/Factor_Zoo")
SESSION = ROOT / "logs/20260502_a_share_etf_anchor_high_v1"
OUT = SESSION / "outputs"
CACHE = SESSION / "data"
CACHE.mkdir(parents=True, exist_ok=True)

# ---- Universe: union of anchor v1.1 (33) + inv_ivol_v2 extended (69 + bond)
# Some overlap; collected as a set.
ANCHOR_SYMBOLS = [
    "510300.SS", "510500.SS", "510050.SS", "159915.SZ", "510180.SS",
    "159949.SZ", "588000.SS", "588080.SS", "512100.SS", "510880.SS",
    "512880.SS", "512660.SS", "512170.SS", "512760.SS", "515030.SS",
    "512290.SS", "515050.SS", "512690.SS", "512980.SS", "515290.SS",
    "518880.SS",
    "512480.SS", "159819.SZ", "515880.SS", "159890.SZ", "159869.SZ",
    "159857.SZ", "159755.SZ", "512010.SS",
    "159992.SZ", "159980.SZ", "515220.SS", "515210.SS",
]

# inv_ivol_v2 extended universe (69 from fetcher) + bond ETFs (5)
exec_globals = {}
exec(open(ROOT / "logs/_shared_cache/fetch_etf_daily_extended.py").read().split("def fetch_one")[0],
     exec_globals)
INV_IVOL_SYMBOLS = sorted(set(exec_globals["SYMBOLS_ORIG"]) | set(exec_globals["SYMBOLS_NEW_CANDIDATES"]))
BOND_ETFS = ["511010.SS", "511220.SS", "511260.SS", "511810.SS"]

ALL_SYMBOLS = sorted(set(ANCHOR_SYMBOLS) | set(INV_IVOL_SYMBOLS) | set(BOND_ETFS))
print(f"Combined universe: anchor={len(ANCHOR_SYMBOLS)}  inv_ivol={len(INV_IVOL_SYMBOLS)}  "
      f"bond={len(BOND_ETFS)}  union={len(ALL_SYMBOLS)}")


def yahoo_to_tushare(sym: str) -> str:
    code, ex = sym.split(".")
    return f"{code}.SH" if ex == "SS" else f"{code}.SZ"


# ----------------------------------------------------------------------- #
# Step 1: fetch panel via Tushare
# ----------------------------------------------------------------------- #
PANEL_PATH = CACHE / "etf_daily_extended_tushare.parquet"


def fetch_panel():
    if PANEL_PATH.exists():
        return pd.read_parquet(PANEL_PATH)
    import tushare as ts
    ts.set_token(os.environ["TUSHARE_TOKEN"])
    pro = ts.pro_api()
    start = "20190101"
    end = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    frames = []
    for ysym in ALL_SYMBOLS:
        tsym = yahoo_to_tushare(ysym)
        tic = time.time()
        try:
            df = ts.pro_bar(api=pro, ts_code=tsym, asset="FD",
                            adj="qfq", start_date=start, end_date=end)
            if df is None or df.empty:
                print(f"  [{ysym:<12}] empty"); continue
            df["date"] = pd.to_datetime(df["trade_date"])
            df = df.sort_values("date").reset_index(drop=True)
            df["symbol"] = ysym
            df = df[["date","symbol","open","high","low","close","vol","amount"]]
            df = df.rename(columns={"vol": "volume"})
            df["amount"] *= 1000.0
            frames.append(df)
            print(f"  [{ysym:<12}] {len(df):5d} bars  {time.time()-tic:.2f}s")
        except Exception as exc:
            print(f"  [{ysym:<12}] FAIL {exc}")
        time.sleep(0.15)
    panel = pd.concat(frames, ignore_index=True).sort_values(["symbol","date"]).reset_index(drop=True)
    panel.to_parquet(PANEL_PATH, index=False)
    return panel


# ----------------------------------------------------------------------- #
# Step 2: run anchor v1.1 → daily excess
# ----------------------------------------------------------------------- #
def _load_module(name, path):
    """Load a python module from explicit file path, bypassing sys.modules."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_anchor(panel):
    anchor_code = _load_module(
        "anchor_code_module",
        ROOT / "factors/price_volume/anchor_range_pos_etf_v1/code.py",
    )

    # only use anchor universe
    p = panel[panel.symbol.isin(ANCHOR_SYMBOLS)].copy()
    p = p.sort_values(["date","symbol"]).reset_index(drop=True)
    p["ret"] = p.groupby("symbol")["close"].pct_change()

    close = p.pivot(index="date", columns="symbol", values="close").sort_index()
    rets = p.pivot(index="date", columns="symbol", values="ret").sort_index()

    sig = anchor_code.signal(close)
    universe = anchor_code.core_universe(close)
    print(f"  anchor universe: {len(universe)}")

    gross, net, bench, w = anchor_code.phase_ensemble_long_only(
        sig, rets, n=anchor_code.N_TOP, rebal=anchor_code.REBAL,
        cost_bps=anchor_code.COST_BPS, universe_filter=universe,
    )
    excess_pre = net - bench
    excess = anchor_code.vol_target_overlay(excess_pre)
    return excess.dropna(), bench, "anchor_v1_1"


# ----------------------------------------------------------------------- #
# Step 3: run inv_ivol_v2 → daily final_ret_net5bps
# ----------------------------------------------------------------------- #
def run_inv_ivol_v2(panel):
    ivol_code = _load_module(
        "ivol_code_module",
        ROOT / "factors/price_volume/inv_ivol_voltarget_bondrotate_etf_v2/code.py",
    )
    p = panel.copy()
    p["ret"] = p.groupby("symbol")["close"].pct_change()
    res = ivol_code.run(p)
    return res.final_ret_net5bps.dropna(), "inv_ivol_v2"


# ----------------------------------------------------------------------- #
# Helpers
# ----------------------------------------------------------------------- #
def annualize_sharpe(daily, k=1, min_obs=20):
    x = daily.dropna()
    if len(x) < min_obs or x.std() == 0:
        return float("nan")
    return float(x.mean() / x.std() * np.sqrt(252 / k))


def per_year_table(s, label):
    rows = []
    for yr, g in s.groupby(s.index.year):
        rows.append({
            "year": int(yr),
            f"{label}_sharpe": annualize_sharpe(g),
            f"{label}_cum_ret": float(g.sum()),
            f"{label}_n_days": len(g),
        })
    return pd.DataFrame(rows).set_index("year")


# ----------------------------------------------------------------------- #
# Main
# ----------------------------------------------------------------------- #
def main():
    print("[1/3] Fetching extended panel via Tushare...")
    panel = fetch_panel()
    print(f"  panel: rows={len(panel)} symbols={panel.symbol.nunique()} "
          f"date_min={panel.date.min():%Y-%m-%d} date_max={panel.date.max():%Y-%m-%d}")

    print("\n[2/3] Running anchor v1.1...")
    anchor_excess, anchor_bench, _ = run_anchor(panel)
    print(f"  anchor excess: {len(anchor_excess)} days  "
          f"sharpe={annualize_sharpe(anchor_excess):.3f}")

    print("\n[3/3] Running inv_ivol_v2...")
    ivol_excess_raw, _ = run_inv_ivol_v2(panel)
    # SCALE FIX: inv_ivol_v2's daily series is each daily observation × 20-day
    # forward return (its catalog convention). Divide by k=20 to get
    # daily-NAV-equivalent returns comparable to anchor's true daily series.
    K_SCALE = 20
    ivol_excess = ivol_excess_raw / K_SCALE
    catalog_ivol_sharpe_k20 = (
        ivol_excess_raw.mean() / ivol_excess_raw.std() * (252 / K_SCALE) ** 0.5
    )
    print(f"  inv_ivol_v2 raw:    {len(ivol_excess_raw)} days  "
          f"catalog Sharpe (k={K_SCALE}) = {catalog_ivol_sharpe_k20:.3f}")
    print(f"  inv_ivol_v2 scaled: divided by k={K_SCALE} → daily-equivalent")

    # ---- Align ----
    common = anchor_excess.index.intersection(ivol_excess.index)
    common = common[common.year >= 2020]   # skip warmup
    a = anchor_excess.loc[common]
    b = ivol_excess.loc[common]
    print(f"\n  Common evaluation window: {common[0]:%Y-%m-%d} → {common[-1]:%Y-%m-%d}  ({len(common)} days)")

    # daily correlation
    rho_daily = a.corr(b)
    print(f"  Daily correlation (anchor vs inv_ivol): rho = {rho_daily:.3f}")

    # ---- 50/50 ensemble ----
    blend = 0.5 * a + 0.5 * b

    # ---- Metrics ----
    rows = []
    for s, label in [(a, "anchor_v1_1"), (b, "inv_ivol_v2"), (blend, "blend_50_50")]:
        rows.append({
            "factor": label,
            "sharpe_full": annualize_sharpe(s),
            "ann_ret_full": float(s.sum() / (len(s) / 252)),
            "vol_full": float(s.std() * np.sqrt(252)),
            "n_days": len(s),
        })
    summary = pd.DataFrame(rows).set_index("factor")
    print("\n=== HEADLINE ===")
    print(summary.round(3).to_string())

    # ---- Per-year ----
    py_a = per_year_table(a, "anchor")
    py_b = per_year_table(b, "ivol")
    py_blend = per_year_table(blend, "blend")
    py = py_a.join(py_b).join(py_blend)
    print("\n=== PER-YEAR (Sharpe / cum return %) ===")
    show = py[["anchor_sharpe","ivol_sharpe","blend_sharpe",
               "anchor_cum_ret","ivol_cum_ret","blend_cum_ret"]].copy()
    show[["anchor_cum_ret","ivol_cum_ret","blend_cum_ret"]] *= 100
    print(show.round(2).to_string())

    # ---- Floor check on blend ----
    blend_py = py_blend["blend_sharpe"]
    worst_year_blend = float(blend_py.min())
    n_pos_blend = int((blend_py > 0).sum())
    n_total_blend = int(blend_py.notna().sum())
    blend_sharpe_full = annualize_sharpe(blend)
    cum_blend = (1 + blend).cumprod()
    peak = cum_blend.cummax()
    dd_blend = float((cum_blend / peak - 1).min())

    floors = {
        "blend_sharpe_full": blend_sharpe_full,
        "blend_worst_year_sharpe": worst_year_blend,
        "blend_worst_year_cum_excess_pct": float(py_blend["blend_cum_ret"].min() * 100),
        "blend_n_pos_years": f"{n_pos_blend}/{n_total_blend}",
        "blend_max_dd_excess": dd_blend,
        "daily_correlation_anchor_ivol": float(rho_daily),
        "PROMOTE_sharpe_geq_1.0": blend_sharpe_full >= 1.0,
        "PROMOTE_worst_year_geq_0.5": worst_year_blend >= 0.5,
        "PROMOTE_all_years_positive": n_pos_blend == n_total_blend,
        "PROMOTE_max_dd_lt_15pct": dd_blend > -0.15,
    }
    floors["DEPLOYED_status"] = (
        floors["PROMOTE_sharpe_geq_1.0"] and
        floors["PROMOTE_worst_year_geq_0.5"] and
        floors["PROMOTE_all_years_positive"]
    )
    print("\n=== FLOOR CHECK (50/50 blend) ===")
    for k, v in floors.items():
        marker = "✓" if v is True else ("✗" if v is False else " ")
        print(f"  {marker}  {k}: {v}")

    # ---- Persist ----
    summary.to_csv(OUT / "r6_ensemble_summary.csv")
    py.to_csv(OUT / "r6_ensemble_peryear.csv")
    blend.to_csv(OUT / "r6_blend_daily_pnl.csv", header=["blend_excess"])
    a.to_csv(OUT / "r6_anchor_daily_pnl.csv", header=["anchor_excess"])
    b.to_csv(OUT / "r6_ivol_daily_pnl.csv", header=["ivol_excess"])
    with open(OUT / "r6_floors.json", "w") as f:
        json.dump(floors, f, indent=2, default=str)

    print("\n  Wrote r6_ensemble_summary.csv, r6_ensemble_peryear.csv, "
          "r6_blend_daily_pnl.csv, r6_floors.json")


if __name__ == "__main__":
    main()
