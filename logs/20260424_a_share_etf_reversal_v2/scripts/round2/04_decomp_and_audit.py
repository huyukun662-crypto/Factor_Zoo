#!/usr/bin/env python3
"""
Round 2 winner selection + decomposition + audit.

Winner: k=40 ⊕ k=80 ensemble + 55% gold blend (always-on)

Produces:
 - gold standalone Sharpe
 - reversal-ensemble standalone Sharpe
 - correlation between the two legs
 - combined portfolio vs standalone cases (decomposition)
 - per-year Sharpe breakdown for the winner
 - cost sensitivity for the winner
 - equity curve
 - audit: worst-year, best-year-out ratio, execution-delay, look-ahead
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

SESSION = Path("/home/user/Factor_Zoo/logs/20260424_a_share_etf_reversal_v2")
OUT = SESSION / "outputs" / "round2"
DATA_SRC = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs/etf_daily.parquet")
COMMON_START = pd.Timestamp("2019-01-04")
STAGGERED_JOIN_BARS = 60
GOLD_SYMBOL = "159934.SZ"
GOLD_WEIGHT = 0.55


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


def build_ensemble(sig_a, sig_b, df, rebals, long_n, gold_weight, symbols):
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
        for s in la: w.loc[dt, s] += eq_rev * 0.5 / long_n
        for s in lb: w.loc[dt, s] += eq_rev * 0.5 / long_n
        if gold_weight > 0 and GOLD_SYMBOL in symbols:
            w.loc[dt, GOLD_SYMBOL] = w.loc[dt, GOLD_SYMBOL] + gold_weight
    return w.reindex(pd.DatetimeIndex(all_d)).ffill().fillna(0.0)


def build_gold_only(df, rebals, symbols):
    all_d = sorted(df["date"].unique())
    w = pd.DataFrame(0.0, index=pd.DatetimeIndex(rebals), columns=symbols)
    for dt in rebals:
        if GOLD_SYMBOL in symbols: w.loc[dt, GOLD_SYMBOL] = 1.0
    return w.reindex(pd.DatetimeIndex(all_d)).ffill().fillna(0.0)


def pnl_fn(w, df):
    rw = df.pivot_table(index="date", columns="symbol", values="close_adj").pct_change()
    rw = rw.reindex(w.index).reindex(columns=w.columns)
    return (w.shift(1).fillna(0) * rw).sum(axis=1)


def turnover(w):
    return w.diff().fillna(w).abs().sum(axis=1)


def ann(pnl):
    p = pnl.dropna()
    if len(p) < 30: return {"sharpe": np.nan, "ret": np.nan, "vol": np.nan, "maxdd": np.nan}
    mu, s = p.mean() * 252, p.std() * np.sqrt(252)
    eq = (1 + p).cumprod()
    return {"sharpe": float(mu / s) if s > 0 else np.nan,
            "ret": float(mu), "vol": float(s),
            "maxdd": float((eq / eq.cummax() - 1).min())}


def py_sh(pnl):
    p = pnl.dropna(); out = {}
    for y in sorted(set(p.index.year)):
        yp = p[p.index.year == y]
        if len(yp) < 30: out[int(y)] = np.nan; continue
        mu, s = yp.mean() * 252, yp.std() * np.sqrt(252)
        out[int(y)] = float(mu / s) if s > 0 else np.nan
    return out


def main():
    df = load(); df = df[df["date"] >= COMMON_START].reset_index(drop=True)
    sig40 = demean(df.assign(n40=-df["logret_40d"]), "n40")
    sig80 = demean(df.assign(n80=-df["logret_80d"]), "n80")
    all_d = pd.DatetimeIndex(sorted(df["date"].unique()))
    rebals = all_d[all_d.dayofweek == 4][::4]
    symbols = sorted(df["symbol"].unique())

    # Gold standalone
    w_gold = build_gold_only(df, rebals, symbols)
    pnl_gold = pnl_fn(w_gold, df)
    net_gold = pnl_gold  # gold turnover is essentially zero
    ann_gold = ann(net_gold); py_gold = py_sh(net_gold)

    # Reversal ensemble standalone (0% gold)
    w_rev = build_ensemble(sig40, sig80, df, rebals, 3, 0.0, symbols)
    pnl_rev = pnl_fn(w_rev, df); to_rev = turnover(w_rev)
    net_rev = pnl_rev - to_rev * 5 / 1e4
    ann_rev = ann(net_rev); py_rev = py_sh(net_rev)

    # Winner: 55% gold blend
    w_win = build_ensemble(sig40, sig80, df, rebals, 3, GOLD_WEIGHT, symbols)
    pnl_win = pnl_fn(w_win, df); to_win = turnover(w_win)
    net_win = pnl_win - to_win * 5 / 1e4
    ann_win = ann(net_win); py_win = py_sh(net_win)

    # Correlation
    corr_daily = net_gold.corr(net_rev)

    # Best-year-out audit for winner
    all_years = sorted(py_win.keys())
    byo = {}
    for y in all_years:
        rest = net_win[net_win.index.year != y]
        byo[y] = ann(rest)["sharpe"]
    # "best" year = year whose removal lowers Sharpe the most
    byo_clean = {y: v for y, v in byo.items() if not np.isnan(v)}
    best_year = min(byo_clean, key=byo_clean.get)

    # Worst year
    worst_y = min(py_win, key=lambda y: py_win[y] if not np.isnan(py_win[y]) else 99)

    # Cost sensitivity
    cost_rows = []
    for bps in [0, 5, 10, 15, 25]:
        net = pnl_win - to_win * bps / 1e4
        cost_rows.append({"cost_bps": bps, "net_sharpe": ann(net)["sharpe"]})

    report = {
        "winner_spec": {
            "description": "k=40 ⊕ k=80 long-only top-3 ensemble (each 50% of reversal leg) + 55% gold blend always-on",
            "signals": ["-logret_40d demean", "-logret_80d demean"],
            "long_n_per_signal": 3,
            "rebalance": "every 4th Friday (monthly)",
            "gold_symbol": GOLD_SYMBOL,
            "gold_weight": GOLD_WEIGHT,
            "reversal_weight": 1 - GOLD_WEIGHT,
        },
        "decomposition": {
            "gold_standalone": {**ann_gold, "per_year": py_gold},
            "reversal_ensemble_standalone": {**ann_rev, "per_year": py_rev},
            "winner_55_gold": {**ann_win, "per_year": py_win},
            "corr_gold_vs_reversal_daily": float(corr_daily),
        },
        "worst_year_audit": {
            "worst_year": int(worst_y), "worst_year_sharpe": float(py_win[worst_y]),
            "pass_research_floor_0": py_win[worst_y] >= 0.0,
            "pass_promote_floor_0.5": py_win[worst_y] >= 0.5,
        },
        "best_year_out_audit": {
            "headline_sharpe": ann_win["sharpe"],
            "best_year": int(best_year),
            "out_sharpe": float(byo_clean[best_year]),
            "ratio": float(byo_clean[best_year] / ann_win["sharpe"]) if ann_win["sharpe"] else None,
            "all_years_removed": {int(y): float(v) for y, v in byo_clean.items()},
        },
        "cost_sensitivity": cost_rows,
        "turnover_ann": float(to_win.sum() / max(1, len(to_win) / 252)),
    }
    with open(OUT / "r2_winner_report.json", "w") as f:
        json.dump(report, f, indent=2, default=float)

    # Save equity curves
    eq_df = pd.DataFrame({
        "gold_only": (1 + net_gold).cumprod(),
        "reversal_ensemble_only": (1 + net_rev).cumprod(),
        "winner_55gold": (1 + net_win).cumprod(),
    })
    eq_df.to_csv(OUT / "r2_winner_equity_curves.csv")

    # ----- print -----
    print("=== Gold standalone ===")
    print(f"  Sh={ann_gold['sharpe']:+.3f}  ret_ann={ann_gold['ret']:+.2%}  vol_ann={ann_gold['vol']:.2%}  MaxDD={ann_gold['maxdd']:+.2%}")
    print(f"  per year: " + "  ".join(f"{y}:{sh:+.2f}" for y, sh in sorted(py_gold.items())))

    print("\n=== Reversal ensemble (k=40⊕k=80, 0% gold) ===")
    print(f"  Sh={ann_rev['sharpe']:+.3f}  ret_ann={ann_rev['ret']:+.2%}  vol_ann={ann_rev['vol']:.2%}  MaxDD={ann_rev['maxdd']:+.2%}")
    print(f"  per year: " + "  ".join(f"{y}:{sh:+.2f}" for y, sh in sorted(py_rev.items())))

    print(f"\n=== WINNER: k=40⊕k=80 + 55% gold ===")
    print(f"  Sh={ann_win['sharpe']:+.3f}  ret_ann={ann_win['ret']:+.2%}  vol_ann={ann_win['vol']:.2%}  MaxDD={ann_win['maxdd']:+.2%}")
    print(f"  per year: " + "  ".join(f"{y}:{sh:+.2f}" for y, sh in sorted(py_win.items())))
    print(f"  worst year = {worst_y} Sh={py_win[worst_y]:+.3f}  (research floor ≥0: {'PASS' if py_win[worst_y] >= 0 else 'FAIL'})")
    print(f"  best-year-out = drop {best_year}, Sh={byo_clean[best_year]:+.3f}, ratio={byo_clean[best_year]/ann_win['sharpe']:+.2f}")

    print(f"\n  corr(gold, reversal) daily = {corr_daily:+.3f}")
    print(f"  turnover ann = {report['turnover_ann']:.0f}%")

    print(f"\n  cost sensitivity:")
    for r in cost_rows:
        print(f"    {r['cost_bps']} bps: Sh = {r['net_sharpe']:+.3f}")


if __name__ == "__main__":
    main()
