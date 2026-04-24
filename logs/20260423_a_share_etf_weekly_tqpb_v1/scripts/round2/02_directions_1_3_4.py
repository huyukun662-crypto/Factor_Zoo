#!/usr/bin/env python3
"""Round 2 Directions 1, 3, 4.

Direction 1: Long-only top-3 of r1_breakout_vol_conf (no short tail risk)
Direction 3: Regime-conditional overlay (activate only when V7 breadth z < 0)
Direction 4: Extend universe to ~48 ETFs (34 V7 + 14 broad-index)

Direction 2 (signal-level fusion) is in separate script 03_direction_2_v7_fusion.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "round2"
OUT.mkdir(parents=True, exist_ok=True)

V7_ROOT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")
V7_DAILY = V7_ROOT / "etf_daily.parquet"
V7_UNIVERSE = V7_ROOT / "etf_universe.csv"
V7_PNL = V7_ROOT / "round7c_v7_pnl.csv"
V7_WEEKLY = V7_ROOT / "etf_weekly.parquet"

BROAD_DAILY = OUT / "etf_daily_broad.parquet"
BROAD_UNIVERSE = OUT / "etf_universe_broad.csv"

START = "2019-01-01"
END = "2026-04-22"
STAGGER_WEEKS = 12
COST_BPS = 5.0


# ---------------- panel prep ----------------
def load_v7_daily() -> pd.DataFrame:
    df = pd.read_parquet(V7_DAILY).rename(columns={"trade_date": "date"})
    df["date"] = pd.to_datetime(df["date"])
    df = df[(df["date"] >= START) & (df["date"] <= END)].copy()
    # keep only needed cols
    return df[["date", "ts_code", "close_adj", "vol"]].sort_values(["ts_code", "date"]).reset_index(drop=True)


def load_broad_daily() -> pd.DataFrame:
    df = pd.read_parquet(BROAD_DAILY)
    df["date"] = pd.to_datetime(df["date"])
    df = df[(df["date"] >= START) & (df["date"] <= END)].copy()
    return df[["date", "ts_code", "close_adj", "vol"]].sort_values(["ts_code", "date"]).reset_index(drop=True)


def merge_panels(df34: pd.DataFrame, df14: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([df34, df14], ignore_index=True).sort_values(["ts_code", "date"]).reset_index(drop=True)


def apply_stagger(df: pd.DataFrame, weeks: int = STAGGER_WEEKS) -> pd.DataFrame:
    df = df.copy()
    df["bar_age"] = df.groupby("ts_code").cumcount()
    df = df[df["bar_age"] >= weeks * 5].reset_index(drop=True)
    return df


def add_breakout_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    g = df.groupby("ts_code", group_keys=False)
    df["log_close"] = np.log(df["close_adj"])
    df["log_ret_1"] = g["log_close"].diff()
    df["std_20d"] = g["log_ret_1"].transform(lambda s: s.rolling(20, min_periods=10).std())
    # max of PRIOR 20 bars (excludes today) — matches Round 1 semantics for breakout comparison
    df["max_high_20"] = g["close_adj"].transform(lambda s: s.shift(1).rolling(20, min_periods=10).max())
    df["vol_5"] = g["vol"].transform(lambda s: s.rolling(5, min_periods=3).mean())
    df["vol_20"] = g["vol"].transform(lambda s: s.rolling(20, min_periods=10).mean())
    return df


def build_breakout_signal(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    breakout = ((df["close_adj"] >= df["max_high_20"]) &
                (df["vol_5"] / df["vol_20"].replace(0.0, np.nan) > 1.2)).astype(float)
    raw = (df["close_adj"] - df["max_high_20"]) / df["std_20d"].replace(0.0, np.nan)
    df["signal_raw"] = raw.clip(lower=0) * breakout
    # xs demean
    df["signal"] = df["signal_raw"] - df.groupby("date")["signal_raw"].transform("mean")
    return df


# ---------------- portfolio helpers ----------------
def friday_rebalance_dates(df: pd.DataFrame) -> list[pd.Timestamp]:
    d = df[["date"]].drop_duplicates().sort_values("date")
    d["dow"] = d["date"].dt.dayofweek
    # use Fridays; if a week has no Friday bar, take the last bar of that iso-week
    d["iso_week"] = d["date"].dt.isocalendar().week
    d["iso_year"] = d["date"].dt.isocalendar().year
    reb = d.sort_values("date").groupby(["iso_year", "iso_week"])["date"].max().sort_values().tolist()
    return reb


def _dense_weekly_weights(df_sig: pd.DataFrame, mode: str, top_n: int) -> tuple[pd.DataFrame, list]:
    """Return dense DataFrame indexed by Friday rebalance dates, columns=all_symbols.
    Each Friday row holds explicit weights for the NEXT week. Cash weeks are all zeros.
    mode: 'long_only' or 'long_short'.
    """
    reb_dates = friday_rebalance_dates(df_sig)
    symbols = sorted(df_sig["ts_code"].unique())
    W = pd.DataFrame(0.0, index=pd.to_datetime(reb_dates), columns=symbols)
    for d in reb_dates:
        cross = df_sig[df_sig["date"] == d].dropna(subset=["signal"])
        if mode == "long_only":
            if len(cross) < top_n:
                continue
            cross = cross.sort_values("signal_raw", ascending=False)
            longs = cross.head(top_n)
            if longs["signal_raw"].sum() <= 1e-12:
                continue  # cash this week (row is already 0)
            for _, r in longs.iterrows():
                W.at[pd.Timestamp(d), r["ts_code"]] = 1.0 / top_n
        else:  # long_short
            if len(cross) < 2 * top_n:
                continue
            cross = cross.sort_values("signal", ascending=False)
            longs = cross.head(top_n); shorts = cross.tail(top_n)
            # require at least some positive signal on the long leg
            if longs["signal_raw"].sum() <= 1e-12:
                continue
            for _, r in longs.iterrows():
                W.at[pd.Timestamp(d), r["ts_code"]] = 1.0 / top_n
            for _, r in shorts.iterrows():
                W.at[pd.Timestamp(d), r["ts_code"]] = -1.0 / top_n
    return W, reb_dates


def long_only_topn(df_sig: pd.DataFrame, top_n: int) -> pd.DataFrame:
    W, _ = _dense_weekly_weights(df_sig, "long_only", top_n)
    return W  # returns a dense DataFrame now


def long_short_topn(df_sig: pd.DataFrame, top_n: int) -> pd.DataFrame:
    W, _ = _dense_weekly_weights(df_sig, "long_short", top_n)
    return W


def daily_pnl_from_weekly_weights(W_weekly: pd.DataFrame, panel: pd.DataFrame, cost_bps: float = COST_BPS) -> pd.DataFrame:
    """W_weekly: dense DataFrame indexed by Friday dates, columns=symbols.
    Each Friday row fully specifies target weights for the coming week (cash rows are all zero).
    """
    all_dates = np.array(sorted(panel["date"].unique()))
    if W_weekly is None or len(W_weekly) == 0:
        return pd.DataFrame({"date": all_dates, "gross_ret": 0.0, "turnover": 0.0, "cost": 0.0, "net_ret": 0.0})
    # expand to daily: each Friday's weights apply Sat..next Fri (ffill within week)
    W_daily = W_weekly.reindex(pd.to_datetime(all_dates), method="ffill").fillna(0.0)
    turnover = W_daily.diff().abs().sum(axis=1).fillna(0.0)
    cost_d = turnover * cost_bps * 1e-4
    ret = panel.pivot(index="date", columns="ts_code", values="log_ret_1").reindex(all_dates).fillna(0.0)
    cols = [c for c in ret.columns if c in W_daily.columns]
    shifted = W_daily[cols].shift(1).fillna(0.0)
    gross = (shifted * ret[cols]).sum(axis=1)
    net = gross - cost_d
    return pd.DataFrame({"date": all_dates, "gross_ret": gross.values, "turnover": turnover.values,
                         "cost": cost_d.values, "net_ret": net.values})


def weekly_agg(daily_pnl: pd.DataFrame, col: str = "net_ret") -> pd.DataFrame:
    p = daily_pnl.copy()
    p["trade_week"] = p["date"] - pd.to_timedelta(p["date"].dt.dayofweek, unit="D") + pd.to_timedelta(4, unit="D")
    out = p.groupby("trade_week")[col].sum().reset_index().rename(columns={col: "pnl_week"})
    return out


def annualize_w(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 10:
        return {"sharpe": np.nan, "annret": np.nan, "vol": np.nan, "maxdd": np.nan, "n": int(len(r))}
    cum = r.cumsum()
    dd = cum - cum.cummax()
    vol = r.std() * np.sqrt(52); mean = r.mean() * 52
    return {"sharpe": float(mean/vol) if vol > 0 else 0.0,
            "annret": float(np.exp(mean) - 1) if abs(mean) < 5 else float("nan"),
            "vol": float(vol), "maxdd": float(dd.min()), "n": int(len(r))}


# ---------------- V7 breadth computation (from weekly panel) ----------------
def compute_v7_breadth() -> pd.Series:
    W = pd.read_parquet(V7_WEEKLY)
    W["trade_week"] = pd.to_datetime(W["trade_week"])
    W = W[W["trade_week"] >= "2019-01-01"].sort_values(["trade_week", "ts_code"]).reset_index(drop=True)
    ret = W.pivot(index="trade_week", columns="ts_code", values="ret_w").sort_index()
    age = ret.notna().cumsum()
    elig = age >= 12
    cum = (1 + ret.fillna(0)).cumprod()
    br_s = ((cum > cum.rolling(20, min_periods=8).mean()).where(elig).sum(axis=1) /
            elig.sum(axis=1).replace(0, np.nan))
    br_z = (br_s - br_s.rolling(52, min_periods=20).mean()) / br_s.rolling(52, min_periods=20).std()
    return br_z


# ---------------- combine with V7 ----------------
def combine_with_v7(new_weekly: pd.DataFrame, v7: pd.DataFrame, weight_new: float) -> dict:
    merged = v7.merge(new_weekly, on="trade_week", how="inner")
    if len(merged) < 30:
        return {"error": "insufficient overlap", "n": len(merged)}
    comb = (1 - weight_new) * merged["pnl_v7"] + weight_new * merged["pnl_week"]
    v7_m = annualize_w(merged["pnl_v7"]); comb_m = annualize_w(comb)
    # per year
    mm = merged.copy(); mm["year"] = mm["trade_week"].dt.year
    py = []
    for y, g in mm.groupby("year"):
        v = annualize_w(g["pnl_v7"]); c = annualize_w((1-weight_new)*g["pnl_v7"] + weight_new*g["pnl_week"])
        py.append({"year": int(y), "n_weeks": len(g), "sh_v7": v["sharpe"], "sh_combo": c["sharpe"],
                   "delta": c["sharpe"] - v["sharpe"]})
    corr = merged[["pnl_v7", "pnl_week"]].corr().iloc[0, 1]
    return {"n_weeks": int(len(merged)), "weight_new": weight_new,
            "corr_weekly": float(corr),
            "sharpe_v7": v7_m["sharpe"], "sharpe_combo": comb_m["sharpe"],
            "delta_sharpe": comb_m["sharpe"] - v7_m["sharpe"],
            "maxdd_v7": v7_m["maxdd"], "maxdd_combo": comb_m["maxdd"],
            "vol_v7": v7_m["vol"], "vol_combo": comb_m["vol"],
            "per_year": py}


def grid_optimal_blend(new_weekly: pd.DataFrame, v7: pd.DataFrame, grid=(0.05, 0.10, 0.15, 0.20, 0.25, 0.30)) -> pd.DataFrame:
    rows = []
    for w in grid:
        r = combine_with_v7(new_weekly, v7, w)
        if "error" in r: continue
        rows.append({"weight_new": w, "sharpe_combo": r["sharpe_combo"],
                     "delta_sharpe": r["delta_sharpe"], "maxdd_combo": r["maxdd_combo"],
                     "vol_combo": r["vol_combo"]})
    return pd.DataFrame(rows)


def load_v7() -> pd.DataFrame:
    v7 = pd.read_csv(V7_PNL)
    v7.columns = ["trade_week", "pnl_v7"]
    v7["trade_week"] = pd.to_datetime(v7["trade_week"])
    return v7


# ---------------- Regime-conditional overlay (Direction 3) ----------------
def regime_conditional_overlay(v7: pd.DataFrame, new_weekly: pd.DataFrame, breadth: pd.Series,
                               base_weight: float = 0.15, regime_threshold: float = 0.0) -> dict:
    """Overlay activates only when V7 breadth[t] < threshold (i.e., low-breadth regime)."""
    br = breadth.rename("breadth_z")
    br = br.reset_index().rename(columns={"trade_week": "trade_week"})
    merged = v7.merge(new_weekly, on="trade_week", how="inner").merge(br, on="trade_week", how="left")
    regime_on = (merged["breadth_z"] < regime_threshold).astype(float).fillna(0.0)
    eff_w = base_weight * regime_on  # 0 or 15%
    comb = (1 - eff_w) * merged["pnl_v7"] + eff_w * merged["pnl_week"]
    v7_m = annualize_w(merged["pnl_v7"]); c_m = annualize_w(comb)
    # always-on baseline comparison
    always_on_c = annualize_w(0.85 * merged["pnl_v7"] + 0.15 * merged["pnl_week"])
    # regime stats
    regime_frac = float(regime_on.mean())
    # per-year
    mm = merged.copy(); mm["year"] = mm["trade_week"].dt.year; mm["comb"] = comb; mm["regime_on"] = regime_on
    py = []
    for y, g in mm.groupby("year"):
        v = annualize_w(g["pnl_v7"]); c = annualize_w(g["comb"])
        py.append({"year": int(y), "n_weeks": len(g), "regime_on_frac": float(g["regime_on"].mean()),
                   "sh_v7": v["sharpe"], "sh_combo_regime": c["sharpe"], "delta": c["sharpe"] - v["sharpe"]})
    return {"regime_threshold_breadth_z": regime_threshold, "overlay_fraction": regime_frac,
            "sharpe_v7": v7_m["sharpe"], "sharpe_regime_combo": c_m["sharpe"],
            "maxdd_v7": v7_m["maxdd"], "maxdd_regime_combo": c_m["maxdd"],
            "sharpe_always_on_15pct": always_on_c["sharpe"], "maxdd_always_on_15pct": always_on_c["maxdd"],
            "delta_vs_v7": c_m["sharpe"] - v7_m["sharpe"],
            "delta_vs_always_on": c_m["sharpe"] - always_on_c["sharpe"],
            "per_year": py}


# ---------------- MAIN ----------------
def main():
    # Direction 1 & 3 use V7's 34-ETF universe
    panel34 = add_breakout_features(apply_stagger(load_v7_daily()))
    sig34 = build_breakout_signal(panel34)

    # Direction 4 uses 34+14=48 ETFs
    panel14 = add_breakout_features(apply_stagger(load_broad_daily()))
    panel48 = pd.concat([panel34, panel14], ignore_index=True).sort_values(["ts_code", "date"]).reset_index(drop=True)
    sig48 = build_breakout_signal(panel48)

    v7 = load_v7()

    print("=" * 60)
    print("Direction 1: Long-only top-3 breakout on 34-ETF universe")
    print("=" * 60)
    w_top3 = long_only_topn(sig34, top_n=3)
    pnl_top3_daily = daily_pnl_from_weekly_weights(w_top3, panel34, cost_bps=COST_BPS)
    pnl_top3_weekly = weekly_agg(pnl_top3_daily)
    # grid over overlay weight
    grid_d1 = grid_optimal_blend(pnl_top3_weekly, v7,
                                 grid=(0.05, 0.075, 0.10, 0.125, 0.15, 0.20, 0.25, 0.30))
    print(grid_d1.to_string(index=False))
    grid_d1.to_csv(OUT / "d1_top3_grid.csv", index=False)
    # also long-only top-5 for comparison
    w_top5 = long_only_topn(sig34, top_n=5)
    pnl_top5_weekly = weekly_agg(daily_pnl_from_weekly_weights(w_top5, panel34, cost_bps=COST_BPS))
    best_d1 = grid_d1.loc[grid_d1["sharpe_combo"].idxmax()] if len(grid_d1) else None
    d1 = combine_with_v7(pnl_top3_weekly, v7, float(best_d1["weight_new"])) if best_d1 is not None else None
    # standalone stats
    standalone_top3 = annualize_w(pnl_top3_weekly["pnl_week"])
    standalone_top5 = annualize_w(pnl_top5_weekly["pnl_week"])
    # turnover annualized
    tov_annual_top3 = float(pnl_top3_daily["turnover"].sum() / (len(pnl_top3_daily) / 252.0))
    print(f"  standalone long-only top-3: Sharpe {standalone_top3['sharpe']:.2f}, "
          f"MaxDD {standalone_top3['maxdd']:.3f}, vol {standalone_top3['vol']:.3f}, "
          f"TO {tov_annual_top3*100:.0f}%/y")
    print(f"  standalone long-only top-5: Sharpe {standalone_top5['sharpe']:.2f}")
    v7_sh_baseline = annualize_w(v7["pnl_v7"])["sharpe"]
    print(f"  best blend @ w={best_d1['weight_new']:.3f}: Sh {best_d1['sharpe_combo']:.3f} "
          f"(V7 baseline Sh {v7_sh_baseline:.3f})")

    print("\n" + "=" * 60)
    print("Direction 4: Long-only top-3 breakout on EXTENDED 48-ETF universe")
    print("=" * 60)
    w_top3_48 = long_only_topn(sig48, top_n=3)
    pnl48_daily = daily_pnl_from_weekly_weights(w_top3_48, panel48, cost_bps=COST_BPS)
    pnl48_weekly = weekly_agg(pnl48_daily)
    grid_d4 = grid_optimal_blend(pnl48_weekly, v7,
                                 grid=(0.05, 0.075, 0.10, 0.125, 0.15, 0.20, 0.25, 0.30))
    print(grid_d4.to_string(index=False))
    grid_d4.to_csv(OUT / "d4_top3_ext48_grid.csv", index=False)
    standalone_48 = annualize_w(pnl48_weekly["pnl_week"])
    tov_annual_48 = float(pnl48_daily["turnover"].sum() / (len(pnl48_daily) / 252.0))
    best_d4 = grid_d4.loc[grid_d4["sharpe_combo"].idxmax()] if len(grid_d4) else None
    d4 = combine_with_v7(pnl48_weekly, v7, float(best_d4["weight_new"])) if best_d4 is not None else None
    print(f"  standalone 48-ETF top-3: Sharpe {standalone_48['sharpe']:.2f}, "
          f"MaxDD {standalone_48['maxdd']:.3f}, TO {tov_annual_48*100:.0f}%/y")

    print("\n" + "=" * 60)
    print("Direction 3: Regime-conditional overlay (breadth z < 0)")
    print("=" * 60)
    breadth = compute_v7_breadth()
    # use LS top-5/bot-5 weekly PnL from Round 1 (load saved combined csv)
    d3_ls_pnl = None
    try:
        w_ls = long_short_topn(sig34, top_n=5)
        pnl_ls_daily = daily_pnl_from_weekly_weights(w_ls, panel34, cost_bps=COST_BPS)
        d3_ls_pnl = weekly_agg(pnl_ls_daily)
    except Exception as exc:
        print("   LS rebuild failed:", exc)

    # regime-conditional using LS overlay (matches Round 1 deploy spec), threshold breadth_z<0
    d3_result = regime_conditional_overlay(v7, d3_ls_pnl, breadth, base_weight=0.15, regime_threshold=0.0)
    print(f"  overlay on fraction (weeks with breadth_z<0): {d3_result['overlay_fraction']:.2%}")
    print(f"  V7 baseline Sh: {d3_result['sharpe_v7']:.3f}, MaxDD: {d3_result['maxdd_v7']:.3f}")
    print(f"  Always-on 15% LS Sh: {d3_result['sharpe_always_on_15pct']:.3f}, "
          f"MaxDD: {d3_result['maxdd_always_on_15pct']:.3f}")
    print(f"  Regime-cond 15% Sh:  {d3_result['sharpe_regime_combo']:.3f}, "
          f"MaxDD: {d3_result['maxdd_regime_combo']:.3f}")
    print(f"  Δ vs always-on: {d3_result['delta_vs_always_on']:+.3f}")
    # sensitivity: try other thresholds
    d3_sens = []
    for thr in [-0.5, -0.25, 0.0, 0.25, 0.5]:
        r = regime_conditional_overlay(v7, d3_ls_pnl, breadth, base_weight=0.15, regime_threshold=thr)
        d3_sens.append({"threshold": thr, "overlay_frac": r["overlay_fraction"],
                        "sharpe_combo": r["sharpe_regime_combo"], "maxdd_combo": r["maxdd_regime_combo"],
                        "delta_vs_always_on": r["delta_vs_always_on"]})
    pd.DataFrame(d3_sens).to_csv(OUT / "d3_regime_sensitivity.csv", index=False)
    print("  threshold sensitivity:")
    print(pd.DataFrame(d3_sens).to_string(index=False))

    # save structured results
    out = {
        "direction_1_long_only_top3": {
            "universe_size": 34,
            "standalone": {"top3": standalone_top3, "top5": standalone_top5},
            "turnover_ann_top3": tov_annual_top3,
            "grid": grid_d1.to_dict("records"),
            "best_blend": (d1 or {}) if d1 else {},
        },
        "direction_4_extended_universe_48": {
            "universe_size": 48,
            "broad_added": 14,
            "standalone": standalone_48,
            "turnover_ann": tov_annual_48,
            "grid": grid_d4.to_dict("records"),
            "best_blend": (d4 or {}) if d4 else {},
        },
        "direction_3_regime_conditional": d3_result,
        "direction_3_threshold_sensitivity": d3_sens,
    }
    (OUT / "directions_1_3_4_results.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\n  wrote: {OUT/'directions_1_3_4_results.json'}")

    # save PnL series for audit
    pnl_top3_weekly.to_csv(OUT / "d1_top3_pnl_weekly.csv", index=False)
    pnl48_weekly.to_csv(OUT / "d4_top3_ext48_pnl_weekly.csv", index=False)
    if d3_ls_pnl is not None:
        d3_ls_pnl.to_csv(OUT / "d3_ls_top5bot5_pnl_weekly.csv", index=False)

    print("\nDONE directions 1, 3, 4.")


if __name__ == "__main__":
    main()
