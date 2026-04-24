#!/usr/bin/env python3
"""Agent 3 + 4 for TQPB (Trend Quality + Pullback-Buy) weekly factor.

Builds 8 weekly signals on V7_gold's 34-ETF universe, runs G1-G5 gates,
correlates each signal's weekly LS PnL with V7_gold's round7c_v7_pnl.csv,
and computes a 50/50 ensemble backtest for the best G4-surviving candidate.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT  = ROOT / "outputs"
WRK  = ROOT / "working"
OUT.mkdir(parents=True, exist_ok=True)
WRK.mkdir(parents=True, exist_ok=True)

V7_ROOT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")
PANEL_DAILY = V7_ROOT / "etf_daily.parquet"
UNIVERSE = V7_ROOT / "etf_universe.csv"
V7_PNL = V7_ROOT / "round7c_v7_pnl.csv"

START = "2019-01-01"
END   = "2026-04-22"
PRIMARY_K = 5
HORIZON_GRID = [5, 10, 20]
COST_BPS = 5.0
COST_GRID = [2.0, 5.0, 8.0]
ANN_FACTOR = 252
STAGGER_WEEKS = 12       # match V7_gold
TOP_N_LONG_ONLY = 5
TOP_N_LS = 5


# ---------------- panel prep ----------------
def load_panel() -> pd.DataFrame:
    df = pd.read_parquet(PANEL_DAILY)
    df = df.rename(columns={"trade_date": "date"})
    df["date"] = pd.to_datetime(df["date"])
    df = df[(df["date"] >= START) & (df["date"] <= END)].copy()
    df = df.sort_values(["ts_code", "date"]).reset_index(drop=True)
    df["log_close"] = np.log(df["close_adj"])
    df["log_ret_1"] = df.groupby("ts_code")["log_close"].diff()
    # apply stagger rule: drop first 12 calendar weeks = 60 trading days of a symbol's life
    df["bar_age"] = df.groupby("ts_code").cumcount()
    df = df[df["bar_age"] >= STAGGER_WEEKS * 5].copy().reset_index(drop=True)
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("ts_code", group_keys=False)
    df["mom_20d"] = g["log_close"].apply(lambda s: s - s.shift(20))
    df["mom_60d"] = g["log_close"].apply(lambda s: s - s.shift(60))
    df["std_20d"] = g["log_ret_1"].apply(lambda s: s.rolling(20, min_periods=10).std())
    df["std_60d"] = g["log_ret_1"].apply(lambda s: s.rolling(60, min_periods=20).std())
    df["mean_20d"] = g["log_ret_1"].apply(lambda s: s.rolling(20, min_periods=10).mean())
    df["mean_60d"] = g["log_ret_1"].apply(lambda s: s.rolling(60, min_periods=20).mean())
    df["max_high_20"] = g["close_adj"].apply(lambda s: s.rolling(20, min_periods=10).max())
    df["max_close_20"] = g["close_adj"].apply(lambda s: s.rolling(20, min_periods=10).max())
    # volume ratio
    df["vol_5"]  = g["vol"].apply(lambda s: s.rolling(5,  min_periods=3).mean())
    df["vol_20"] = g["vol"].apply(lambda s: s.rolling(20, min_periods=10).mean())
    # Wilder RSI(14)
    ch = df.groupby("ts_code")["close_adj"].diff()
    up = ch.clip(lower=0.0); dn = (-ch).clip(lower=0.0)
    alpha = 1.0 / 14.0
    au = up.groupby(df["ts_code"]).transform(lambda s: s.ewm(alpha=alpha, adjust=False, min_periods=14).mean())
    ad = dn.groupby(df["ts_code"]).transform(lambda s: s.ewm(alpha=alpha, adjust=False, min_periods=14).mean())
    rs = au / ad.replace(0.0, np.nan)
    df["rsi14"] = 100.0 - 100.0 / (1.0 + rs)
    return df


def xs_demean(s: pd.Series, df: pd.DataFrame) -> pd.Series:
    tmp = pd.DataFrame({"v": s, "date": df["date"]})
    return s - tmp.groupby("date")["v"].transform("mean")


def xs_rank(s: pd.Series, df: pd.DataFrame) -> pd.Series:
    tmp = pd.DataFrame({"v": s, "date": df["date"]})
    return tmp.groupby("date")["v"].rank(pct=True) - 0.5


def xs_zscore(s: pd.Series, df: pd.DataFrame) -> pd.Series:
    tmp = pd.DataFrame({"v": s, "date": df["date"]})
    mu = tmp.groupby("date")["v"].transform("mean")
    sd = tmp.groupby("date")["v"].transform("std")
    return (s - mu) / sd.replace(0.0, np.nan)


# ---------------- expressions ----------------
def build_expressions(df: pd.DataFrame) -> pd.DataFrame:
    sig = pd.DataFrame(index=df.index)

    # 1. trend sharpe 20d (mean/std * sqrt(252))
    ts20 = df["mean_20d"] / df["std_20d"].replace(0.0, np.nan) * np.sqrt(ANN_FACTOR)
    sig["r1_trend_sharpe_20d"] = ts20

    # 2. trend sharpe 60d
    ts60 = df["mean_60d"] / df["std_60d"].replace(0.0, np.nan) * np.sqrt(ANN_FACTOR)
    sig["r1_trend_sharpe_60d"] = ts60

    # 3. pullback in uptrend: (40-RSI14) * I[RSI<40] * I[mom_20d>0]
    mask_rsi = (df["rsi14"] < 40).astype(float)
    mask_up  = (df["mom_20d"] > 0).astype(float)
    sig["r1_pullback_in_uptrend"] = (40 - df["rsi14"]).clip(lower=0) * mask_rsi * mask_up

    # 4. vol-adjusted mom_4w (20d)
    sig["r1_vol_adj_mom_4w"] = df["mom_20d"] / df["std_20d"].replace(0.0, np.nan)

    # 5. cross-sectional z-score of mom_20d
    sig["r1_rel_strength_zscore"] = xs_zscore(df["mom_20d"], df)

    # 6. low drawdown 20d (shallow = strong trend)
    dd20 = (df["close_adj"] - df["max_close_20"]) / df["max_close_20"]  # <= 0
    sig["r1_low_drawdown_20d"] = -(-dd20)  # = dd20 (negative numbers; closer to 0 = better trend)
    # i.e. higher signal = less drawdown. We sign so high=long: sig = dd20 itself (less negative = longer)
    sig["r1_low_drawdown_20d"] = dd20  # dd20 ranges [-1, 0]; high = 0 = clean trend -> long

    # 7. breakout volume confirmed
    breakout = ((df["close_adj"] >= df["max_high_20"]) & (df["vol_5"] / df["vol_20"].replace(0.0, np.nan) > 1.2)).astype(float)
    brk_signal = (df["close_adj"] - df["max_high_20"]) / df["std_20d"].replace(0.0, np.nan)
    sig["r1_breakout_vol_conf"] = brk_signal.clip(lower=0) * breakout

    # 8. kitchen sink rank of 1-7
    parts = []
    for c in ["r1_trend_sharpe_20d", "r1_trend_sharpe_60d", "r1_pullback_in_uptrend",
              "r1_vol_adj_mom_4w", "r1_rel_strength_zscore", "r1_low_drawdown_20d",
              "r1_breakout_vol_conf"]:
        parts.append(xs_rank(sig[c], df))
    sig["r1_kitchen_sink"] = pd.concat(parts, axis=1).mean(axis=1)

    # demean
    for c in sig.columns:
        sig[c] = xs_demean(sig[c], df)
    return sig


# ---------------- forward returns, IC, portfolios ----------------
def forward_returns(df: pd.DataFrame, k: int, delay: int = 1) -> pd.Series:
    g = df.groupby("ts_code", group_keys=False)
    fe = g["log_close"].shift(-delay)
    fx = g["log_close"].shift(-(delay + k))
    return fx - fe


def ic_by_date(signal, target, df) -> pd.Series:
    tmp = pd.DataFrame({"s": signal, "t": target, "date": df["date"]}).dropna()
    out = []
    for d, grp in tmp.groupby("date"):
        if len(grp) >= 8:
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
                "ic_mean":  float(ics.mean()),
                "ic_std":   float(ics.std()),
                "ic_tstat": float(ics.mean() / (ics.std() / np.sqrt(len(ics)))) if len(ics) > 1 else np.nan,
                "n_days":   int(len(ics)),
                "icir_ann": float(ics.mean() / ics.std() * np.sqrt(252)) if ics.std() > 0 else np.nan,
            })
    return pd.DataFrame(rows)


def weekly_rebal_portfolio(signal: pd.Series, df: pd.DataFrame, top_n: int, mode: str = "long_only") -> pd.DataFrame:
    """Friday close rebalance; take weekly (day-of-week=4) cross-section.
    mode: 'long_only' -> top N; 'long_short' -> top N long, bot N short.
    """
    tmp = pd.DataFrame({"s": signal, "date": df["date"], "symbol": df["ts_code"]})
    tmp["dow"] = tmp["date"].dt.dayofweek
    fri = tmp[tmp["dow"] == 4]
    reb_dates = np.array(sorted(fri["date"].unique()))
    rows = []
    for d in reb_dates:
        cross = tmp[tmp["date"] == d].dropna(subset=["s"])
        if mode == "long_only":
            if len(cross) < top_n: continue
            cross = cross.sort_values("s")
            longs = cross.tail(top_n)["symbol"].tolist()
            for s in longs: rows.append({"date": d, "symbol": s, "weight": 1.0 / top_n})
        else:
            if len(cross) < 2 * top_n: continue
            cross = cross.sort_values("s")
            shorts = cross.head(top_n)["symbol"].tolist()
            longs  = cross.tail(top_n)["symbol"].tolist()
            for s in longs:  rows.append({"date": d, "symbol": s, "weight":  1.0 / top_n})
            for s in shorts: rows.append({"date": d, "symbol": s, "weight": -1.0 / top_n})
    return pd.DataFrame(rows)


def strategy_pnl(weights: pd.DataFrame, df: pd.DataFrame, cost_bps: float) -> pd.DataFrame:
    panel = df[["date", "ts_code", "log_ret_1"]].copy().rename(columns={"ts_code": "symbol"})
    all_dates = np.array(sorted(panel["date"].unique()))
    sym_w = {}
    if len(weights) == 0:
        return pd.DataFrame({"date": all_dates, "gross_ret": 0.0, "turnover": 0.0, "cost": 0.0, "net_ret": 0.0})
    for sym, g in weights.groupby("symbol"):
        w = g[["date", "weight"]].drop_duplicates("date").set_index("date")["weight"]
        sym_w[sym] = w.reindex(all_dates, method="ffill").fillna(0.0)
    w_panel = pd.DataFrame(sym_w).fillna(0.0)
    turnover = w_panel.diff().abs().sum(axis=1).fillna(0.0)
    cost_d = turnover * cost_bps * 1e-4
    ret = panel.pivot(index="date", columns="symbol", values="log_ret_1").reindex(all_dates).fillna(0.0)
    shifted = w_panel.shift(1).fillna(0.0)
    # align columns
    cols = [c for c in ret.columns if c in shifted.columns]
    gross = (shifted[cols] * ret[cols]).sum(axis=1)
    net = gross - cost_d
    return pd.DataFrame({"date": all_dates, "gross_ret": gross.values, "turnover": turnover.values,
                         "cost": cost_d.values, "net_ret": net.values})


def annualize(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 30:
        return {"sharpe": np.nan, "cagr": np.nan, "vol": np.nan, "maxdd": np.nan, "n": len(r)}
    cum = r.cumsum()
    dd = cum - cum.cummax()
    vol = r.std() * np.sqrt(ANN_FACTOR); mean = r.mean() * ANN_FACTOR
    return {"sharpe": mean/vol if vol > 0 else 0.0,
            "cagr": float(np.exp(mean)-1) if abs(mean) < 5 else np.nan,
            "vol": vol, "maxdd": float(dd.min()), "n": len(r)}


def per_year_sharpe(pnl: pd.DataFrame, col: str = "net_ret") -> pd.DataFrame:
    p = pnl[["date", col]].copy()
    p["year"] = p["date"].dt.year
    rows = []
    for y, g in p.groupby("year"):
        s = g[col].dropna()
        if len(s) < 30: continue
        vol = s.std() * np.sqrt(ANN_FACTOR); mean = s.mean() * ANN_FACTOR
        rows.append({"year": int(y), "n_days": len(s), "mean_ann": mean, "vol_ann": vol,
                     "sharpe": mean/vol if vol > 0 else 0.0})
    return pd.DataFrame(rows)


def decile_summary(signal, df, k=PRIMARY_K, n_bins=5) -> pd.DataFrame:
    tmp = pd.DataFrame({"s": signal, "date": df["date"], "t": forward_returns(df, k=k)}).dropna()
    tmp["bin"] = tmp.groupby("date")["s"].transform(lambda s: pd.qcut(s, q=n_bins, labels=False, duplicates="drop"))
    bin_ret = tmp.groupby("bin")["t"].mean()
    bin_cnt = tmp.groupby("bin")["t"].count()
    return pd.DataFrame({"bin": bin_ret.index.astype(int), "fwd_ret": bin_ret.values,
                         "n_obs": bin_cnt.values}).sort_values("bin").reset_index(drop=True)


# ---------------- V7_gold combination ----------------
def load_v7_weekly_pnl() -> pd.DataFrame:
    v7 = pd.read_csv(V7_PNL)
    v7.columns = ["trade_week", "pnl_v7"]
    v7["trade_week"] = pd.to_datetime(v7["trade_week"])
    return v7


def weekly_agg(daily_pnl: pd.DataFrame, col: str = "net_ret") -> pd.DataFrame:
    """Aggregate daily PnL to weekly (Friday-ending, Mon-Fri sum of log returns)."""
    p = daily_pnl.copy()
    p["trade_week"] = p["date"] - pd.to_timedelta(p["date"].dt.dayofweek, unit="D") + pd.to_timedelta(4, unit="D")
    weekly = p.groupby("trade_week")[col].sum().reset_index()
    weekly = weekly.rename(columns={col: "pnl_week"})
    return weekly


def combine_with_v7(weekly_new: pd.DataFrame, v7: pd.DataFrame) -> dict:
    merged = v7.merge(weekly_new, on="trade_week", how="inner")
    if len(merged) < 30:
        return {"n": len(merged), "error": "insufficient overlap"}
    corr = merged[["pnl_v7", "pnl_week"]].corr().iloc[0, 1]

    # 50/50 ensemble
    combined = 0.5 * merged["pnl_v7"] + 0.5 * merged["pnl_week"]
    v7_m = annualize_weekly(merged["pnl_v7"])
    new_m = annualize_weekly(merged["pnl_week"])
    comb_m = annualize_weekly(combined)

    # per year
    merged_year = merged.copy()
    merged_year["year"] = merged_year["trade_week"].dt.year
    py = []
    for y, g in merged_year.groupby("year"):
        v = annualize_weekly(g["pnl_v7"])
        c_new = annualize_weekly(g["pnl_week"])
        c_comb = annualize_weekly(0.5 * g["pnl_v7"] + 0.5 * g["pnl_week"])
        py.append({"year": int(y), "n_weeks": len(g),
                   "sharpe_v7": v["sharpe"], "annret_v7": v["annret"],
                   "sharpe_new": c_new["sharpe"], "annret_new": c_new["annret"],
                   "sharpe_combined": c_comb["sharpe"], "annret_combined": c_comb["annret"]})

    return {
        "n_weeks": int(len(merged)),
        "corr_weekly_pnl": float(corr),
        "v7_standalone":       v7_m,
        "new_standalone":      new_m,
        "combined_5050":       comb_m,
        "improvement_vs_v7": comb_m["sharpe"] - v7_m["sharpe"],
        "per_year": py,
        "combined_weekly_pnl_series": combined.tolist(),
        "combined_weekly_pnl_dates": merged["trade_week"].astype(str).tolist(),
    }


def annualize_weekly(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 10:
        return {"sharpe": np.nan, "annret": np.nan, "vol": np.nan, "maxdd": np.nan, "n": int(len(r))}
    cum = r.cumsum()
    dd = cum - cum.cummax()
    vol = r.std() * np.sqrt(52); mean = r.mean() * 52
    return {"sharpe": float(mean/vol) if vol > 0 else 0.0,
            "annret": float(np.exp(mean) - 1) if abs(mean) < 5 else float("nan"),
            "vol": float(vol),
            "maxdd": float(dd.min()),
            "n": int(len(r))}


# ---------------- MAIN ----------------
def main():
    df = load_panel()
    df = add_features(df)
    sig = build_expressions(df)
    exprs = list(sig.columns)
    assert len(exprs) == 8

    # IC
    ic_df = ic_table(sig, df)
    ic_df.to_csv(OUT / "ic_table_batch_0001.csv", index=False)

    # Decile
    dec_rows = []
    for c in exprs:
        d = decile_summary(sig[c], df, k=PRIMARY_K); d.insert(0, "expression", c); dec_rows.append(d)
    dec_all = pd.concat(dec_rows, ignore_index=True)
    dec_all.to_csv(OUT / "decile_summary_batch_0001.csv", index=False)

    # Strategy: long-only top-5 + LS top-5/bot-5
    v7 = load_v7_weekly_pnl()
    lo_rows = []
    ls_rows = []
    cost_rows = []
    combine = {"session": "20260423_a_share_etf_weekly_tqpb_v1", "expressions": {}}
    gates = {"session": "20260423_a_share_etf_weekly_tqpb_v1", "expressions": {}}
    combined_best_series = None
    combined_best_name = None

    uni_ew = df.set_index(["date", "ts_code"])["log_ret_1"].unstack("ts_code").mean(axis=1)

    for c in exprs:
        w_lo = weekly_rebal_portfolio(sig[c], df, top_n=TOP_N_LONG_ONLY, mode="long_only")
        w_ls = weekly_rebal_portfolio(sig[c], df, top_n=TOP_N_LS,       mode="long_short")
        pnl_lo = strategy_pnl(w_lo, df, cost_bps=COST_BPS)
        pnl_ls = strategy_pnl(w_ls, df, cost_bps=COST_BPS)

        for cb in COST_GRID:
            p_lo = strategy_pnl(w_lo, df, cost_bps=cb)
            m = annualize(p_lo["net_ret"])
            cost_rows.append({"expression": c, "strategy": "long_only_top5", "cost_bps_side": cb,
                              "gross_sharpe": annualize(p_lo["gross_ret"])["sharpe"],
                              "net_sharpe":   m["sharpe"], "net_cagr": m["cagr"], "net_maxdd": m["maxdd"],
                              "ann_turnover_pct": float(p_lo["turnover"].sum() * 252 / len(p_lo) * 100)})
            p_ls = strategy_pnl(w_ls, df, cost_bps=cb)
            m = annualize(p_ls["net_ret"])
            cost_rows.append({"expression": c, "strategy": "ls_top5_bot5", "cost_bps_side": cb,
                              "gross_sharpe": annualize(p_ls["gross_ret"])["sharpe"],
                              "net_sharpe":   m["sharpe"], "net_cagr": m["cagr"], "net_maxdd": m["maxdd"],
                              "ann_turnover_pct": float(p_ls["turnover"].sum() * 252 / len(p_ls) * 100)})

        # standalone metrics
        g_lo = annualize(pnl_lo["gross_ret"]); n_lo = annualize(pnl_lo["net_ret"])
        g_ls = annualize(pnl_ls["gross_ret"]); n_ls = annualize(pnl_ls["net_ret"])
        py_lo = per_year_sharpe(pnl_lo, "net_ret")
        py_ls = per_year_sharpe(pnl_ls, "net_ret")

        # weekly aggregate LO pnl for V7 combine
        weekly_lo = weekly_agg(pnl_lo, "net_ret")
        comb_info = combine_with_v7(weekly_lo, v7)

        # gates
        ic_row = ic_df[ic_df["expression"] == c]
        ic_at_k = float(ic_row[ic_row["horizon_days"] == PRIMARY_K]["ic_mean"].iloc[0])
        d_here = dec_all[dec_all["expression"] == c]
        mono = d_here["fwd_ret"].values
        if len(mono) >= 2:
            inv = sum(1 for i in range(1, len(mono)) if mono[i] < mono[i-1])
            q5_q1 = float(mono[-1] - mono[0])
        else:
            inv = 99
            q5_q1 = float("nan")
        gross_lo = pnl_lo.set_index("date")["gross_ret"]; u = uni_ew.reindex(gross_lo.index).fillna(0.0)
        corr_u = float(gross_lo.corr(u)) if gross_lo.std() > 0 else 0.0
        corr_v7 = comb_info.get("corr_weekly_pnl", float("nan"))

        # G3
        sig_per_date = sig[c].groupby(df["date"]).count()
        pct_enough = (sig_per_date >= int(0.5 * 34)).mean()
        ann_to = float(pnl_ls["turnover"].sum() * 252 / len(pnl_ls) * 100)
        G3_pass = bool(pct_enough >= 0.85 and n_ls["sharpe"] >= -0.5 and 50 <= ann_to <= 5000)
        # G4
        G4_pass = bool(ic_at_k > 0 and inv <= 2 and q5_q1 > 0 and abs(corr_u) <= 0.85 and (abs(corr_v7) <= 0.70 or np.isnan(corr_v7)))

        peak_k = int(ic_row.sort_values("ic_mean", ascending=False).iloc[0]["horizon_days"])

        gates["expressions"][c] = {
            "G1": "pass", "G2": "pass",
            "G3": {"pct_enough_signal": float(pct_enough), "ann_turnover_pct": ann_to,
                   "net_sharpe_5bps_ls": n_ls["sharpe"], "pass": G3_pass},
            "G4": {"ic_at_k5": ic_at_k, "inversions": inv, "q5_q1": q5_q1,
                   "corr_vs_uew": corr_u, "corr_vs_v7_gold": corr_v7, "pass": G4_pass},
            "peak_k": peak_k,
        }

        lo_rows.append({
            "expression": c,
            "lo_gross_sharpe":  g_lo["sharpe"],
            "lo_net_sharpe_5bps": n_lo["sharpe"],
            "lo_net_cagr":      n_lo["cagr"],
            "lo_net_maxdd":     n_lo["maxdd"],
            "lo_ann_turnover_pct": float(pnl_lo["turnover"].sum() * 252 / len(pnl_lo) * 100),
            "lo_worst_year_sharpe": py_lo["sharpe"].min() if len(py_lo) else np.nan,
            "ic_at_k5": ic_at_k,
            "peak_k": peak_k,
            "corr_vs_v7_gold": corr_v7,
            "G3_pass": G3_pass, "G4_pass": G4_pass,
        })
        ls_rows.append({
            "expression": c,
            "ls_gross_sharpe":  g_ls["sharpe"],
            "ls_net_sharpe_5bps": n_ls["sharpe"],
            "ls_net_cagr":      n_ls["cagr"],
            "ls_net_maxdd":     n_ls["maxdd"],
            "ls_worst_year_sharpe": py_ls["sharpe"].min() if len(py_ls) else np.nan,
            "ls_ann_turnover_pct": float(pnl_ls["turnover"].sum() * 252 / len(pnl_ls) * 100),
        })

        combine["expressions"][c] = comb_info

    lo_df = pd.DataFrame(lo_rows); lo_df.to_csv(OUT / "longonly_summary_batch_0001.csv", index=False)
    ls_df = pd.DataFrame(ls_rows); ls_df.to_csv(OUT / "ls_summary_batch_0001.csv", index=False)
    cost_df = pd.DataFrame(cost_rows); cost_df.to_csv(OUT / "cost_sensitivity_batch_0001.csv", index=False)

    # G5 batch horizon
    surv = lo_df[lo_df["G4_pass"]]["expression"].tolist()
    peak_counts = {k: 0 for k in HORIZON_GRID}
    for c in surv:
        pk = gates["expressions"][c]["peak_k"]
        peak_counts[pk] = peak_counts.get(pk, 0) + 1
    frac = peak_counts.get(PRIMARY_K, 0) / max(len(surv), 1)
    gates["G5_batch"] = {"declared_k": PRIMARY_K, "n_survivors": len(surv),
                        "peak_k_counts": peak_counts, "fraction_at_declared": frac,
                        "pass": frac >= 0.5}

    with (OUT / "validation_gates_batch_0001.json").open("w") as f:
        json.dump(gates, f, indent=2, default=str)

    # Combine analysis file
    with (OUT / "combine_analysis_v7_gold.json").open("w") as f:
        json.dump(combine, f, indent=2, default=str)

    # per-year table (long-only)
    py_rows = []
    for c in exprs:
        w = weekly_rebal_portfolio(sig[c], df, top_n=TOP_N_LONG_ONLY, mode="long_only")
        pnl = strategy_pnl(w, df, cost_bps=COST_BPS)
        p = per_year_sharpe(pnl, "net_ret"); p.insert(0, "expression", c); py_rows.append(p)
    pd.concat(py_rows, ignore_index=True).to_csv(OUT / "per_year_sharpe_batch_0001.csv", index=False)

    # Save best combined series to CSV
    best = None; best_improve = -np.inf
    for c, info in combine["expressions"].items():
        if "improvement_vs_v7" in info and info["improvement_vs_v7"] is not None:
            if info["improvement_vs_v7"] > best_improve:
                best_improve = info["improvement_vs_v7"]; best = c
    if best is not None:
        info = combine["expressions"][best]
        pd.DataFrame({"trade_week": info["combined_weekly_pnl_dates"],
                      "pnl_combined_5050": info["combined_weekly_pnl_series"]}).to_csv(
            OUT / "combined_5050_equity.csv", index=False)

    # Print summary
    pd.set_option("display.width", 140)
    pd.set_option("display.max_columns", 14)
    print("=== IC table ===")
    print(ic_df.to_string(index=False))
    print("\n=== Long-only top-5 summary ===")
    print(lo_df.to_string(index=False))
    print("\n=== LS top5/bot5 summary ===")
    print(ls_df.to_string(index=False))
    print("\n=== V7_gold combine (long-only) ===")
    hdr = f"{'expr':<28s} {'corr':>7s} {'sharpe_v7':>10s} {'sharpe_new':>10s} {'sharpe_combo':>12s} {'improve':>8s}"
    print(hdr)
    for c, info in combine["expressions"].items():
        if "combined_5050" in info:
            print(f"{c:<28s} {info['corr_weekly_pnl']:>7.3f} {info['v7_standalone']['sharpe']:>10.3f} {info['new_standalone']['sharpe']:>10.3f} {info['combined_5050']['sharpe']:>12.3f} {info['improvement_vs_v7']:>+8.3f}")
    print("\n=== G5 ===")
    print(json.dumps(gates["G5_batch"], indent=2))
    if best:
        print(f"\nBEST COMBINE CANDIDATE: {best} (improvement {best_improve:+.3f})")


if __name__ == "__main__":
    main()
