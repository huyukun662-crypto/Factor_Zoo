#!/usr/bin/env python3
"""
Out-of-sample validation for R2 winner.

Splits:
  Train: 2019-01-04 → 2022-12-31  (4 years, pre-2023 regime break)
  Val:   2023-01-01 → 2023-12-31  (the known problem year)
  OOS:   2024-01-01 → 2026-04-22  (2.3 years, never used in selection)

Questions:
  Q1. Winner (gold_weight=55%) — what is the per-split Sharpe / MaxDD / CAGR?
  Q2. If we re-select gold_weight using TRAIN ONLY (maximize train net Sh,
      subject to worst train-year ≥ 0), what weight does it pick?
  Q3. Does train-picked weight generalize to Val and OOS?
"""
from pathlib import Path
import numpy as np
import pandas as pd

DATA_SRC = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs/etf_daily.parquet")
OUT = Path("/home/user/Factor_Zoo/logs/20260424_a_share_etf_reversal_v2/outputs/round2")
GOLD_SYMBOL = "159934.SZ"
STAGGERED_JOIN_BARS = 60
LONG_N = 3
COMMON_START = pd.Timestamp("2019-01-04")

TRAIN_END = pd.Timestamp("2022-12-31")
VAL_END = pd.Timestamp("2023-12-31")


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


def build_weights(sig_a, sig_b, df, rebals, gold_weight, symbols):
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
        if len(slice_df) < LONG_N * 2: continue
        la = slice_df.dropna(subset=["sa"])["sa"].sort_values(ascending=False).iloc[:LONG_N].index.tolist()
        lb = slice_df.dropna(subset=["sb"])["sb"].sort_values(ascending=False).iloc[:LONG_N].index.tolist()
        for s in la: w.loc[dt, s] += eq_rev * 0.5 / LONG_N
        for s in lb: w.loc[dt, s] += eq_rev * 0.5 / LONG_N
        if gold_weight > 0 and GOLD_SYMBOL in symbols:
            w.loc[dt, GOLD_SYMBOL] += gold_weight
    return w.reindex(pd.DatetimeIndex(all_d)).ffill().fillna(0.0)


def pnl_fn(w, df):
    rw = df.pivot_table(index="date", columns="symbol", values="close_adj").pct_change()
    rw = rw.reindex(w.index).reindex(columns=w.columns)
    return (w.shift(1).fillna(0) * rw).sum(axis=1)


def turn(w):
    return w.diff().fillna(w).abs().sum(axis=1)


def ann(pnl):
    p = pnl.dropna()
    if len(p) < 10:
        return {"sharpe": np.nan, "ret": np.nan, "vol": np.nan, "maxdd": np.nan, "n": len(p)}
    mu, s = p.mean() * 252, p.std() * np.sqrt(252)
    eq = (1 + p).cumprod()
    return {"sharpe": float(mu/s) if s > 0 else np.nan, "ret": float(mu), "vol": float(s),
            "maxdd": float((eq/eq.cummax() - 1).min()), "n": int(len(p))}


def py(pnl):
    p = pnl.dropna(); out = {}
    for y in sorted(set(p.index.year)):
        yp = p[p.index.year == y]
        if len(yp) < 10: out[int(y)] = np.nan; continue
        mu, s = yp.mean() * 252, yp.std() * np.sqrt(252)
        out[int(y)] = float(mu/s) if s > 0 else np.nan
    return out


def main():
    df = load(); df = df[df["date"] >= COMMON_START].reset_index(drop=True)
    sig40 = demean(df.assign(n40=-df["logret_40d"]), "n40")
    sig80 = demean(df.assign(n80=-df["logret_80d"]), "n80")
    all_d = pd.DatetimeIndex(sorted(df["date"].unique()))
    rebals = all_d[all_d.dayofweek == 4][::4]
    symbols = sorted(df["symbol"].unique())

    # ----- Q1: Winner (55% gold) per-split -----
    w_win = build_weights(sig40, sig80, df, rebals, 0.55, symbols)
    pnl = pnl_fn(w_win, df)
    to = turn(w_win)
    net5 = pnl - to * 5 / 1e4

    splits = {
        "train_2019_2022": (COMMON_START, TRAIN_END),
        "val_2023":        (TRAIN_END + pd.Timedelta(days=1), VAL_END),
        "oos_2024_2026":   (VAL_END + pd.Timedelta(days=1), df["date"].max()),
    }
    full = ann(net5)
    py_full = py(net5)

    print("=" * 75)
    print("Q1: Winner (gold_weight=55%, full-sample hyperparameter) per split")
    print("=" * 75)
    print(f"{'split':<25s}  {'range':<25s}  {'Sh':>7s}  {'ret_ann':>8s}  {'MaxDD':>7s}  {'n_days':>6s}")
    rows = []
    for name, (s, e) in splits.items():
        sub = net5[(net5.index >= s) & (net5.index <= e)]
        a = ann(sub); yrs = py(sub)
        worst_y = min(yrs, key=lambda y: yrs[y] if not np.isnan(yrs[y]) else 99) if yrs else None
        print(f"{name:<25s}  {s.date()} → {e.date()}  "
              f"{a['sharpe']:>+7.3f}  {a['ret']:>+8.2%}  {a['maxdd']:>+7.1%}  {a['n']:>6d}")
        rows.append({"split": name, "start": str(s.date()), "end": str(e.date()),
                     "sharpe": a["sharpe"], "ret_ann": a["ret"], "vol_ann": a["vol"],
                     "maxdd": a["maxdd"], "n_days": a["n"],
                     "worst_year": worst_y, "worst_year_sh": yrs.get(worst_y, np.nan) if worst_y else np.nan,
                     "per_year_sharpes": {int(y): float(s) for y, s in yrs.items()}})
    print(f"\n{'full_sample':<25s}  {COMMON_START.date()} → {df['date'].max().date()}  "
          f"{full['sharpe']:>+7.3f}  {full['ret']:>+8.2%}  {full['maxdd']:>+7.1%}  {full['n']:>6d}")

    print(f"\n  Per-year Sharpe across the full sample:")
    for y, s in sorted(py_full.items()):
        flag = ""
        if y <= 2022: flag = "TRAIN"
        elif y == 2023: flag = "VAL"
        else: flag = "OOS"
        print(f"    {y}  {flag:<6s}  Sh = {s:+.3f}")

    # ----- Q2: re-select gold_weight using TRAIN ONLY -----
    print("\n" + "=" * 75)
    print("Q2: Re-select gold_weight using TRAIN ONLY (2019-2022)")
    print("=" * 75)
    grid = np.arange(0.0, 0.96, 0.05)
    print(f"{'gw':>6s}  {'train_Sh':>9s}  {'train_worst_y':>15s}  {'val_2023_Sh':>12s}  {'oos_Sh':>7s}")
    train_results = []
    for gw in grid:
        w = build_weights(sig40, sig80, df, rebals, float(gw), symbols)
        pp = pnl_fn(w, df); tt = turn(w)
        net = pp - tt * 5 / 1e4
        train = net[(net.index >= COMMON_START) & (net.index <= TRAIN_END)]
        val = net[(net.index > TRAIN_END) & (net.index <= VAL_END)]
        oos = net[net.index > VAL_END]
        ann_tr = ann(train); ann_va = ann(val); ann_oo = ann(oos)
        py_tr = py(train)
        worst_tr_y = min(py_tr, key=lambda y: py_tr[y] if not np.isnan(py_tr[y]) else 99) if py_tr else None
        worst_tr_sh = py_tr.get(worst_tr_y, np.nan) if worst_tr_y else np.nan
        train_results.append({
            "gw": float(gw), "train_sh": ann_tr["sharpe"],
            "train_worst_y": worst_tr_y, "train_worst_sh": worst_tr_sh,
            "val_sh": ann_va["sharpe"], "oos_sh": ann_oo["sharpe"],
        })
        print(f"{gw:>6.2f}  {ann_tr['sharpe']:>+9.3f}  "
              f"{str(worst_tr_y)+':'+f'{worst_tr_sh:+.2f}':>15s}  "
              f"{ann_va['sharpe']:>+12.3f}  {ann_oo['sharpe']:>+7.3f}")

    # Train-optimal: max train sharpe subject to train worst-year >= 0
    valid = [r for r in train_results if not np.isnan(r["train_worst_sh"]) and r["train_worst_sh"] >= 0]
    if valid:
        best = max(valid, key=lambda r: r["train_sh"])
    else:
        # relax: pick the smallest train worst-year deficit
        best = max(train_results, key=lambda r: (r["train_worst_sh"], r["train_sh"]))
    print(f"\n  Train-optimal gold_weight = {best['gw']:.2f}  (train Sh {best['train_sh']:+.3f}, "
          f"train worst yr {best['train_worst_y']}:{best['train_worst_sh']:+.3f})")
    print(f"  → its VAL (2023) Sharpe:  {best['val_sh']:+.3f}")
    print(f"  → its OOS (24-26) Sharpe: {best['oos_sh']:+.3f}")

    # Also report full-sample pick (what we called "winner" = 0.55)
    r55 = next(r for r in train_results if abs(r["gw"] - 0.55) < 1e-9)
    print(f"\n  Full-sample pick (0.55): train Sh {r55['train_sh']:+.3f}, "
          f"val 2023 Sh {r55['val_sh']:+.3f}, OOS Sh {r55['oos_sh']:+.3f}")

    # Save
    pd.DataFrame(rows).to_csv(OUT / "r2_winner_tvt_splits.csv", index=False)
    pd.DataFrame(train_results).to_csv(OUT / "r2_train_only_gold_grid.csv", index=False)
    print(f"\n✅ outputs/round2/r2_winner_tvt_splits.csv")
    print(f"✅ outputs/round2/r2_train_only_gold_grid.csv")


if __name__ == "__main__":
    main()
