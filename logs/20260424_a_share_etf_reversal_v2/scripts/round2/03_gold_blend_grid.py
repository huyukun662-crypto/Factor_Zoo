#!/usr/bin/env python3
"""
Round 2 — gold blend ratio grid (always-on).

Sweep gold weight from 0 to 1 in 0.05 steps; find combination with best
worst-year Sharpe ≥ 0 while maintaining headline Sh ≥ baseline - 0.15.

Also test: D7 = k=40 ⊕ k=80 ensemble + gold blend.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

SESSION = Path("/home/user/Factor_Zoo/logs/20260424_a_share_etf_reversal_v2")
OUT = SESSION / "outputs" / "round2"
DATA_SRC = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs/etf_daily.parquet")
COMMON_START = pd.Timestamp("2019-01-04")
STAGGERED_JOIN_BARS = 60
GOLD_SYMBOL = "159934.SZ"


def load():
    df = pd.read_parquet(DATA_SRC).rename(columns={"trade_date": "date", "ts_code": "symbol"})
    df = df.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"]).reset_index(drop=True)
    for k in [40, 80]:
        df[f"logret_{k}d"] = df.groupby("symbol")["close_adj"].transform(
            lambda s, k=k: np.log(s / s.shift(k))
        )
    df["bar_age"] = df.groupby("symbol").cumcount()
    df["is_live"] = df["bar_age"] >= STAGGERED_JOIN_BARS
    return df


def demean(df, col):
    s = df[col].where(df["is_live"])
    return s - s.groupby(df["date"]).transform("mean")


def build_weights(sig, df, rebals, long_n, gold_weight, symbols):
    panel = pd.DataFrame({
        "date": df["date"].values, "symbol": df["symbol"].values,
        "s": sig.values, "live": df["is_live"].values,
    })
    all_d = sorted(panel["date"].unique())
    w = pd.DataFrame(0.0, index=pd.DatetimeIndex(rebals), columns=symbols)
    idx = panel.set_index(["date", "symbol"])
    for dt in rebals:
        try: slice_df = idx.xs(dt, level="date")
        except KeyError: continue
        slice_df = slice_df.dropna(subset=["s"]); slice_df = slice_df[slice_df["live"]]
        if len(slice_df) < long_n * 2: continue
        longs = slice_df["s"].sort_values(ascending=False).iloc[:long_n].index.tolist()
        if gold_weight < 1.0:
            w.loc[dt, longs] = (1 - gold_weight) / long_n
        if gold_weight > 0.0 and GOLD_SYMBOL in symbols:
            w.loc[dt, GOLD_SYMBOL] = gold_weight
    return w.reindex(pd.DatetimeIndex(all_d)).ffill().fillna(0.0)


def build_ensemble_weights(sig_a, sig_b, df, rebals, long_n, gold_weight, symbols, eq_weight_a=0.5):
    """Ensemble of two signals with blended gold."""
    # Each signal contributes its own top-N with eq_weight_a/1-eq_weight_a split
    panel = pd.DataFrame({
        "date": df["date"].values, "symbol": df["symbol"].values,
        "sa": sig_a.values, "sb": sig_b.values, "live": df["is_live"].values,
    })
    all_d = sorted(panel["date"].unique())
    w = pd.DataFrame(0.0, index=pd.DatetimeIndex(rebals), columns=symbols)
    idx = panel.set_index(["date", "symbol"])
    eq_rev = 1 - gold_weight
    for dt in rebals:
        try: slice_df = idx.xs(dt, level="date")
        except KeyError: continue
        slice_df = slice_df[slice_df["live"]]
        if len(slice_df) < long_n * 2: continue
        la = slice_df.dropna(subset=["sa"])["sa"].sort_values(ascending=False).iloc[:long_n].index.tolist()
        lb = slice_df.dropna(subset=["sb"])["sb"].sort_values(ascending=False).iloc[:long_n].index.tolist()
        for s in la:
            w.loc[dt, s] = w.loc[dt, s] + eq_rev * eq_weight_a / long_n
        for s in lb:
            w.loc[dt, s] = w.loc[dt, s] + eq_rev * (1 - eq_weight_a) / long_n
        if gold_weight > 0 and GOLD_SYMBOL in symbols:
            w.loc[dt, GOLD_SYMBOL] = w.loc[dt, GOLD_SYMBOL] + gold_weight
    return w.reindex(pd.DatetimeIndex(all_d)).ffill().fillna(0.0)


def pnl_fn(w, df):
    rw = df.pivot_table(index="date", columns="symbol", values="close_adj").pct_change()
    rw = rw.reindex(w.index).reindex(columns=w.columns)
    return (w.shift(1).fillna(0) * rw).sum(axis=1)


def ann(pnl):
    p = pnl.dropna()
    if len(p) < 30: return {"sharpe": np.nan, "maxdd": np.nan}
    mu, s = p.mean() * 252, p.std() * np.sqrt(252)
    eq = (1 + p).cumprod()
    return {"sharpe": float(mu / s) if s > 0 else np.nan, "maxdd": float((eq / eq.cummax() - 1).min())}


def py_sh(pnl):
    p = pnl.dropna(); out = {}
    for y in sorted(set(p.index.year)):
        yp = p[p.index.year == y]
        if len(yp) < 30: out[int(y)] = np.nan; continue
        mu, s = yp.mean() * 252, yp.std() * np.sqrt(252)
        out[int(y)] = float(mu / s) if s > 0 else np.nan
    return out


def turn(w):
    return w.diff().fillna(w).abs().sum(axis=1)


def main():
    df = load(); df = df[df["date"] >= COMMON_START].reset_index(drop=True)
    sig40 = demean(df.assign(n40=-df["logret_40d"]), "n40")
    sig80 = demean(df.assign(n80=-df["logret_80d"]), "n80")
    all_d = pd.DatetimeIndex(sorted(df["date"].unique()))
    rebals = all_d[all_d.dayofweek == 4][::4]
    symbols = sorted(df["symbol"].unique())

    print("=== Grid: k=40 only, gold blend 0% → 90% ===")
    print(f"{'gold_wt':>10s}  {'net5_sh':>8s}  {'maxdd':>7s}  {'worst':>15s}  {'Sh2023':>7s}")
    rows = []
    for gw in np.arange(0.00, 0.91, 0.05):
        w = build_weights(sig40, df, rebals, 3, float(gw), symbols)
        p = pnl_fn(w, df); t = turn(w)
        net5 = p - t * 5 / 1e4
        a = ann(net5); py = py_sh(net5)
        worst_y = min(py, key=lambda y: py[y] if not np.isnan(py[y]) else 99)
        worst_sh = py[worst_y]
        print(f"{gw:>10.2f}  {a['sharpe']:>+8.3f}  {a['maxdd']:>+7.1%}  {worst_y}:{worst_sh:>+6.3f}  {py.get(2023, np.nan):>+7.3f}")
        rows.append({
            "variant": "k40_only", "gold_weight": float(gw),
            "net5_sharpe": a["sharpe"], "maxdd": a["maxdd"],
            "worst_year": int(worst_y), "worst_sharpe": float(worst_sh),
            **{f"y{y}": float(s) for y, s in py.items()},
        })

    print("\n=== Grid: k=40 ⊕ k=80 ensemble, gold blend 0% → 90% ===")
    print(f"{'gold_wt':>10s}  {'net5_sh':>8s}  {'maxdd':>7s}  {'worst':>15s}  {'Sh2023':>7s}")
    for gw in np.arange(0.00, 0.91, 0.05):
        w = build_ensemble_weights(sig40, sig80, df, rebals, 3, float(gw), symbols)
        p = pnl_fn(w, df); t = turn(w)
        net5 = p - t * 5 / 1e4
        a = ann(net5); py = py_sh(net5)
        worst_y = min(py, key=lambda y: py[y] if not np.isnan(py[y]) else 99)
        worst_sh = py[worst_y]
        print(f"{gw:>10.2f}  {a['sharpe']:>+8.3f}  {a['maxdd']:>+7.1%}  {worst_y}:{worst_sh:>+6.3f}  {py.get(2023, np.nan):>+7.3f}")
        rows.append({
            "variant": "k40+k80_ensemble", "gold_weight": float(gw),
            "net5_sharpe": a["sharpe"], "maxdd": a["maxdd"],
            "worst_year": int(worst_y), "worst_sharpe": float(worst_sh),
            **{f"y{y}": float(s) for y, s in py.items()},
        })

    pd.DataFrame(rows).to_csv(OUT / "r2_gold_blend_grid.csv", index=False)
    print("\n✅ outputs/round2/r2_gold_blend_grid.csv")


if __name__ == "__main__":
    main()
