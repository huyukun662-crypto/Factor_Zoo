#!/usr/bin/env python3
"""Agent 3 + 4 for Round 2 (long-term reversal + selective oversold).

Produces 8 reversal expressions targeting k ∈ {20, 60, 120} trading days,
monthly rebalance, + an audit probe (+logret_20d) as a pipeline sanity
check (reported separately, not in Rule of 8).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INP = ROOT / "inputs"
OUT = ROOT / "outputs"
WRK = ROOT / "working"

PRIMARY_K = 60
HORIZON_GRID = [20, 60, 120]
REBAL_PERIOD = 20     # monthly
COST_GRID_BPS = [2.0, 5.0, 8.0]
ANN_FACTOR = 252
TOP_N = 4


# ---------- panel prep ----------
def load_panel() -> pd.DataFrame:
    df = pd.read_parquet(INP / "etf_daily.parquet")
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    df["log_close"] = np.log(df["close"])
    df["log_ret_1"] = df.groupby("symbol")["log_close"].diff()
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("symbol", group_keys=False)
    # cumulative log returns
    for k in [5, 20, 60, 120, 250]:
        df[f"logret_{k}d"] = g["log_close"].apply(lambda s, k=k: s - s.shift(k))
    # rolling stds (of daily log-ret)
    for w in [20, 60, 120]:
        df[f"std_{w}"] = g["log_ret_1"].apply(lambda s, w=w: s.rolling(w, min_periods=max(10, w//3)).std())
    df["max_high_20"] = g["high"].apply(lambda s: s.rolling(20, min_periods=10).max())
    df["dd20"] = (df["close"] - df["max_high_20"]) / df["max_high_20"]
    df["vol20"] = g["volume"].apply(lambda s: s.rolling(20, min_periods=10).mean())
    df["vol60"] = g["volume"].apply(lambda s: s.rolling(60, min_periods=20).mean())
    # Wilder RSI(14)
    ch = df.groupby("symbol")["close"].diff()
    up = ch.clip(lower=0.0)
    dn = (-ch).clip(lower=0.0)
    alpha = 1.0 / 14.0
    avg_up = up.groupby(df["symbol"]).transform(lambda s: s.ewm(alpha=alpha, adjust=False, min_periods=14).mean())
    avg_dn = dn.groupby(df["symbol"]).transform(lambda s: s.ewm(alpha=alpha, adjust=False, min_periods=14).mean())
    rs = avg_up / avg_dn.replace(0.0, np.nan)
    df["rsi14"] = 100.0 - 100.0 / (1.0 + rs)
    return df


def xs_demean(s: pd.Series, df: pd.DataFrame) -> pd.Series:
    tmp = pd.DataFrame({"v": s, "date": df["date"]})
    return s - tmp.groupby("date")["v"].transform("mean")


def ts_z(s: pd.Series, df: pd.DataFrame, win: int = 120) -> pd.Series:
    out = []
    for sym, idx in df.groupby("symbol").indices.items():
        ss = s.iloc[idx]
        mu = ss.rolling(win, min_periods=win//3).mean()
        sd = ss.rolling(win, min_periods=win//3).std()
        out.append(pd.Series(((ss - mu) / sd).values, index=idx))
    return pd.concat(out).sort_index()


def residualize(y: pd.Series, x: pd.Series, df: pd.DataFrame) -> pd.Series:
    """Per-date OLS residual of y on x (no intercept needed after demean)."""
    tmp = pd.DataFrame({"y": y, "x": x, "date": df["date"]})
    out = pd.Series(np.nan, index=df.index)
    for d, grp in tmp.groupby("date"):
        xs = grp["x"].values
        ys = grp["y"].values
        mask = ~(np.isnan(xs) | np.isnan(ys))
        if mask.sum() < 5:
            continue
        x0 = xs[mask]
        y0 = ys[mask]
        # simple OLS
        denom = (x0 ** 2).sum()
        if denom == 0:
            continue
        beta = (x0 * y0).sum() / denom
        resid = y0 - beta * x0
        idx_in_date = grp.index[mask]
        for j, idx in enumerate(idx_in_date):
            out.iloc[idx] = resid[j]
    return out


def build_expressions(df: pd.DataFrame) -> pd.DataFrame:
    sig = pd.DataFrame(index=df.index)

    # 1. 60d long-term reversal
    sig["r2_lt_rev_60d"]    = -df["logret_60d"]
    # 2. 120d
    sig["r2_lt_rev_120d"]   = -df["logret_120d"]
    # 3. 250d
    sig["r2_lt_rev_250d"]   = -df["logret_250d"]
    # 4. vol-scaled 120d
    sig["r2_vol_scaled_lt_120"] = -df["logret_120d"] / df["std_60"]
    # 5. deep dip selective 5d rev: only trigger when dd20 < -5% (i.e. meaningful dip)
    mask_deep = (df["dd20"] < -0.05).astype(float)
    sig["r2_deep_dip_rev"] = -df["logret_5d"] * mask_deep
    # 6. RSI extreme: only when RSI<30
    mask_os = (df["rsi14"] < 30).astype(float)
    sig["r2_rsi_extreme_os"] = (30 - df["rsi14"]).clip(lower=0) * mask_os
    # 7. vol-confirmed long-term reversal: -logret_60 × z(log(vol20/vol60))
    vol_ratio = np.log(df["vol20"] / df["vol60"])
    z_vr = ts_z(vol_ratio, df, win=120)
    sig["r2_vol_confirmed_lt60"] = -df["logret_60d"] * z_vr
    # 8. residual short-term reversal after 60d trend
    sig["r2_residual_rev"] = residualize(-df["logret_5d"], df["logret_60d"], df)

    # Audit probe (separate!)
    probe = pd.DataFrame(index=df.index)
    probe["probe_momentum_20d"] = df["logret_20d"]

    # neutralize
    for col in sig.columns:
        sig[col] = xs_demean(sig[col], df)
    for col in probe.columns:
        probe[col] = xs_demean(probe[col], df)
    return sig, probe


# ---------- forward returns, IC, portfolio ----------
def forward_returns(df: pd.DataFrame, k: int, delay: int = 1) -> pd.Series:
    g = df.groupby("symbol", group_keys=False)
    fwd_entry = g["log_close"].shift(-delay)
    fwd_exit  = g["log_close"].shift(-(delay + k))
    return fwd_exit - fwd_entry


def ic_by_date(signal: pd.Series, target: pd.Series, df: pd.DataFrame) -> pd.Series:
    tmp = pd.DataFrame({"s": signal, "t": target, "date": df["date"]}).dropna()
    out = []
    for d, grp in tmp.groupby("date"):
        if len(grp) >= 6:
            out.append((d, grp["s"].rank().corr(grp["t"].rank())))
    return pd.Series(dict(out))


def ic_table(signals: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in signals.columns:
        for k in HORIZON_GRID:
            tgt = forward_returns(df, k=k)
            ics = ic_by_date(signals[col], tgt, df)
            rows.append({
                "expression": col, "horizon_days": k,
                "ic_mean":  ics.mean(),
                "ic_std":   ics.std(),
                "ic_tstat": (ics.mean() / (ics.std() / np.sqrt(len(ics)))) if len(ics) > 1 else np.nan,
                "n_days":   len(ics),
                "icir_ann": (ics.mean() / ics.std() * np.sqrt(252)) if ics.std() > 0 else np.nan,
            })
    return pd.DataFrame(rows)


def monthly_rebalance_portfolio(signal: pd.Series, df: pd.DataFrame, period: int = REBAL_PERIOD, top_n: int = TOP_N) -> pd.DataFrame:
    tmp = pd.DataFrame({"s": signal, "date": df["date"], "symbol": df["symbol"]})
    days = np.array(sorted(tmp["date"].dt.normalize().unique()))
    sel = days[np.arange(len(days)) % period == 0]
    rows = []
    for d in sel:
        cross = tmp[tmp["date"] == d].dropna(subset=["s"])
        if len(cross) < 2 * top_n:
            continue
        cross = cross.sort_values("s")
        shorts = cross.head(top_n)["symbol"].tolist()
        longs  = cross.tail(top_n)["symbol"].tolist()
        for s in longs:  rows.append({"date": d, "symbol": s, "weight":  1.0 / top_n})
        for s in shorts: rows.append({"date": d, "symbol": s, "weight": -1.0 / top_n})
    return pd.DataFrame(rows)


def strategy_pnl(weights: pd.DataFrame, df: pd.DataFrame, cost_bps_per_side: float) -> pd.DataFrame:
    panel = df[["date", "symbol", "log_ret_1"]].copy()
    all_dates = np.array(sorted(panel["date"].unique()))
    sym_weights = {}
    for sym, grp in weights.groupby("symbol"):
        w = grp[["date", "weight"]].drop_duplicates("date").set_index("date")["weight"]
        w_ff = w.reindex(all_dates, method="ffill").fillna(0.0)
        sym_weights[sym] = w_ff
    w_panel = pd.DataFrame(sym_weights).fillna(0.0)
    turnover = (w_panel.diff().abs().sum(axis=1)).fillna(0.0)
    cost_daily = turnover * (cost_bps_per_side * 1e-4)
    ret = panel.pivot(index="date", columns="symbol", values="log_ret_1").reindex(all_dates).fillna(0.0)
    shifted_w = w_panel.shift(1).fillna(0.0)
    gross_daily = (shifted_w * ret).sum(axis=1)
    net_daily   = gross_daily - cost_daily
    return pd.DataFrame({
        "date": all_dates,
        "gross_ret": gross_daily.values,
        "turnover":  turnover.values,
        "cost":      cost_daily.values,
        "net_ret":   net_daily.values,
    })


def annualize(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 30:
        return {"sharpe": np.nan, "cagr": np.nan, "vol": np.nan, "maxdd": np.nan, "n": len(r)}
    cum = r.cumsum()
    dd = cum - cum.cummax()
    vol = r.std() * np.sqrt(ANN_FACTOR)
    mean = r.mean() * ANN_FACTOR
    return {"sharpe": mean/vol if vol > 0 else 0.0, "cagr": np.exp(mean) - 1 if abs(mean) < 5 else np.nan, "vol": vol, "maxdd": dd.min(), "n": len(r)}


def per_year_sharpe(pnl: pd.DataFrame, col: str = "net_ret") -> pd.DataFrame:
    p = pnl[["date", col]].copy()
    p["year"] = p["date"].dt.year
    rows = []
    for y, g in p.groupby("year"):
        s = g[col].dropna()
        if len(s) < 30: continue
        vol = s.std() * np.sqrt(ANN_FACTOR); mean = s.mean() * ANN_FACTOR
        rows.append({"year": int(y), "n_days": len(s), "mean_ann": mean, "vol_ann": vol, "sharpe": mean / vol if vol > 0 else 0.0})
    return pd.DataFrame(rows)


def decile_summary(signal: pd.Series, df: pd.DataFrame, k: int = PRIMARY_K) -> pd.DataFrame:
    tmp = pd.DataFrame({"s": signal, "date": df["date"], "t": forward_returns(df, k=k)}).dropna()
    tmp["bin"] = tmp.groupby("date")["s"].transform(lambda s: pd.qcut(s, q=5, labels=False, duplicates="drop"))
    bin_ret = tmp.groupby("bin")["t"].mean()
    bin_cnt = tmp.groupby("bin")["t"].count()
    return pd.DataFrame({"bin": bin_ret.index.astype(int), "fwd_ret": bin_ret.values, "n_obs": bin_cnt.values}).sort_values("bin").reset_index(drop=True)


def main():
    df = load_panel()
    df = add_features(df)
    signals, probe = build_expressions(df)
    exprs = list(signals.columns)
    assert len(exprs) == 8

    # IC
    ic_df = ic_table(signals, df); ic_df.to_csv(OUT / "ic_table_batch_0002.csv", index=False)

    # Decile
    decile_rows = []
    for col in exprs:
        d = decile_summary(signals[col], df, k=PRIMARY_K); d.insert(0, "expression", col); decile_rows.append(d)
    decile_all = pd.concat(decile_rows, ignore_index=True)
    decile_all.to_csv(OUT / "decile_summary_batch_0002.csv", index=False)

    # LS + cost sensitivity
    ls_rows = []; cost_rows = []; gates_all = {"session": "20260423_a_share_etf_reversal_v1", "round": 2, "expressions": {}}
    uni_ew = df.set_index(["date", "symbol"])["log_ret_1"].unstack("symbol").mean(axis=1)

    for col in exprs:
        w = monthly_rebalance_portfolio(signals[col], df, period=REBAL_PERIOD, top_n=TOP_N)
        pnl5 = strategy_pnl(w, df, cost_bps_per_side=5.0)
        for cb in COST_GRID_BPS:
            p = strategy_pnl(w, df, cost_bps_per_side=cb)
            m = annualize(p["net_ret"])
            cost_rows.append({
                "expression": col, "cost_bps_side": cb,
                "gross_sharpe": annualize(p["gross_ret"])["sharpe"],
                "net_sharpe":   m["sharpe"], "net_cagr": m["cagr"],
                "net_maxdd":    m["maxdd"],
                "ann_turnover_pct": float(p["turnover"].sum() * 252 / len(p) * 100),
            })
        g_ann = annualize(pnl5["gross_ret"]); n_ann = annualize(pnl5["net_ret"])
        pa = per_year_sharpe(pnl5, "net_ret")
        ic_row = ic_df[ic_df["expression"] == col].copy()
        d_here = decile_all[decile_all["expression"] == col]

        # G3, G4
        sig_by_date = signals[col].groupby(df["date"]).count()
        pct_enough = (sig_by_date >= 14).mean()
        turnover_ann = float(pnl5["turnover"].sum() * 252 / len(pnl5) * 100)
        zero_reb = float((pnl5["turnover"] < 1e-8).mean())
        G3_pass = bool(pct_enough >= 0.90 and 5 <= turnover_ann <= 2000 and zero_reb <= 0.05 and n_ann["sharpe"] >= -0.5)
        ic_at_k = float(ic_row[ic_row["horizon_days"] == PRIMARY_K]["ic_mean"].iloc[0])
        mono = d_here["fwd_ret"].values
        inv = sum(1 for i in range(1, len(mono)) if mono[i] < mono[i-1])
        q5_q1 = float(mono[-1] - mono[0])
        gross = pnl5.set_index("date")["gross_ret"]; u = uni_ew.reindex(gross.index).fillna(0.0)
        corr_u = float(gross.corr(u)) if gross.std() > 0 else 0.0
        G4_pass = bool(ic_at_k > 0 and inv <= 2 and q5_q1 > 0 and abs(corr_u) <= 0.85)
        peak_k = int(ic_row.sort_values("ic_mean", ascending=False).iloc[0]["horizon_days"])
        gates_all["expressions"][col] = {
            "G3": {"pct_enough_signal": float(pct_enough), "ann_turnover_pct": turnover_ann, "zero_reb": zero_reb, "net_sharpe_5bps": n_ann["sharpe"], "pass": G3_pass},
            "G4": {"ic_at_primary_k": ic_at_k, "inversions": inv, "q5_q1": q5_q1, "corr_vs_uew": corr_u, "pass": G4_pass},
            "peak_k": peak_k,
        }
        ls_rows.append({
            "expression": col,
            "gross_sharpe":     g_ann["sharpe"],
            "net_sharpe_5bps":  n_ann["sharpe"],
            "net_cagr":         n_ann["cagr"], "net_maxdd": n_ann["maxdd"],
            "ann_turnover_pct": turnover_ann,
            "worst_year_sharpe": pa["sharpe"].min() if len(pa) else np.nan,
            "n_years":          len(pa),
            "G3_pass":          G3_pass, "G4_pass": G4_pass, "peak_k": peak_k,
            "ic_at_primary_k":  ic_at_k,
        })

    ls_df = pd.DataFrame(ls_rows); ls_df.to_csv(OUT / "ls_summary_batch_0002.csv", index=False)
    cost_df = pd.DataFrame(cost_rows); cost_df.to_csv(OUT / "cost_sensitivity_batch_0002.csv", index=False)

    # G5 batch
    surv = ls_df[ls_df["G4_pass"]]["expression"].tolist()
    peak_dist = {k: 0 for k in HORIZON_GRID}
    for c in surv:
        pk = gates_all["expressions"][c]["peak_k"]
        peak_dist[pk] = peak_dist.get(pk, 0) + 1
    frac_decl = peak_dist.get(PRIMARY_K, 0) / max(len(surv), 1)
    gates_all["G5_batch"] = {
        "declared_k": PRIMARY_K,
        "n_g4_survivors": len(surv),
        "peak_k_counts": peak_dist,
        "fraction_peaking_at_declared_k": frac_decl,
        "pass": frac_decl >= 0.5,
    }

    with (OUT / "validation_gates_batch_0002.json").open("w") as f:
        json.dump(gates_all, f, indent=2, default=str)

    # per-year
    py_rows = []
    for col in exprs:
        w = monthly_rebalance_portfolio(signals[col], df, period=REBAL_PERIOD, top_n=TOP_N)
        pnl = strategy_pnl(w, df, cost_bps_per_side=5.0)
        p = per_year_sharpe(pnl, "net_ret"); p.insert(0, "expression", col); py_rows.append(p)
    py_all = pd.concat(py_rows, ignore_index=True)
    py_all.to_csv(OUT / "per_year_sharpe_batch_0002.csv", index=False)

    # momentum probe
    probe_rows = []
    for col in probe.columns:
        w = monthly_rebalance_portfolio(probe[col], df, period=REBAL_PERIOD, top_n=TOP_N)
        pnl = strategy_pnl(w, df, cost_bps_per_side=5.0)
        g_ann = annualize(pnl["gross_ret"]); n_ann = annualize(pnl["net_ret"])
        tgt = forward_returns(df, k=PRIMARY_K)
        ics = ic_by_date(probe[col], tgt, df)
        probe_rows.append({
            "expression": col,
            "ic_at_primary_k": float(ics.mean()),
            "ic_tstat":        float(ics.mean() / (ics.std() / np.sqrt(len(ics)))) if len(ics) > 1 else None,
            "gross_sharpe":    g_ann["sharpe"],
            "net_sharpe_5bps": n_ann["sharpe"],
            "net_cagr":        n_ann["cagr"],
            "role":            "pipeline sanity probe — NOT an alpha candidate",
        })
    with (OUT / "momentum_probe_batch_0002.json").open("w") as f:
        json.dump(probe_rows, f, indent=2, default=str)

    # print
    pd.set_option('display.width', 140)
    pd.set_option('display.max_columns', 14)
    print("=== Round 2 IC table ===")
    print(ic_df.to_string(index=False))
    print("\n=== Round 2 LS summary (monthly, 5bps) ===")
    print(ls_df.to_string(index=False))
    print("\n=== Round 2 cost sensitivity ===")
    print(cost_df.to_string(index=False))
    print("\n=== G5 batch ===")
    print(json.dumps(gates_all["G5_batch"], indent=2))
    print("\n=== Momentum probe (sanity, not alpha) ===")
    print(json.dumps(probe_rows, indent=2))
    print("\n=== Per-year Sharpe (net, 5 bps) ===")
    print(py_all.to_string(index=False))


if __name__ == "__main__":
    main()
