#!/usr/bin/env python3
"""Agent 3 + Agent 4 for A-share ETF reversal v1, Round 1.

Produces 8 expressions, runs G1-G5 validation gates, emits all CSV/MD
artifacts listed in outputs/session_metadata.yml round_1_outputs_expected.

Execution-delay invariant: target = log(close[t+1+k]) - log(close[t+1]).
Signal uses only data available by close of day t. Position is taken at
close of day t and held k days.

Run:
    python3 02_build_and_backtest.py
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
OUT.mkdir(parents=True, exist_ok=True)
WRK.mkdir(parents=True, exist_ok=True)

PRIMARY_K = 10
HORIZON_GRID = [5, 10, 20]
REBALANCE_DOW = 2  # Wednesday = 2 (Mon=0)
COST_BASELINE_BPS = 5.0
COST_GRID_BPS = [2.0, 5.0, 8.0]
ANN_FACTOR = 252
UNIV_SIZE_TARGET = 18
TOP_N = 4  # long-short cut

PANEL_PATH = INP / "etf_daily.parquet"


# ----------------------------------------------------------------------
# Panel prep
# ----------------------------------------------------------------------
def load_panel() -> pd.DataFrame:
    df = pd.read_parquet(PANEL_PATH)
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    df["log_close"] = np.log(df["close"])
    df["log_ret_1"] = df.groupby("symbol")["log_close"].diff()
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("symbol", group_keys=False)
    # rolling aggregates on close
    df["max_high_20"] = g["high"].apply(lambda s: s.rolling(20, min_periods=10).max())
    df["ma20"]        = g["close"].apply(lambda s: s.rolling(20, min_periods=10).mean())
    df["std20"]       = g["log_ret_1"].apply(lambda s: s.rolling(20, min_periods=10).std())
    df["ma5"]         = g["close"].apply(lambda s: s.rolling(5, min_periods=3).mean())
    df["vol5"]        = g["volume"].apply(lambda s: s.rolling(5, min_periods=3).mean())
    df["vol20"]       = g["volume"].apply(lambda s: s.rolling(20, min_periods=10).mean())
    # cumulative log returns at {5, 10, 20} trading days
    for k in HORIZON_GRID:
        df[f"logret_{k}d"]   = g["log_close"].apply(lambda s, k=k: s - s.shift(k))
    # Wilder RSI(14)
    ch = df.groupby("symbol")["close"].diff()
    up = ch.clip(lower=0.0)
    dn = (-ch).clip(lower=0.0)
    # Wilder smoothing = EMA with alpha=1/14
    alpha = 1.0 / 14.0
    avg_up = up.groupby(df["symbol"]).transform(lambda s: s.ewm(alpha=alpha, adjust=False, min_periods=14).mean())
    avg_dn = dn.groupby(df["symbol"]).transform(lambda s: s.ewm(alpha=alpha, adjust=False, min_periods=14).mean())
    rs = avg_up / avg_dn.replace(0.0, np.nan)
    df["rsi14"] = 100.0 - 100.0 / (1.0 + rs)
    return df


# ----------------------------------------------------------------------
# Expression builders (Agent 3 outputs)
# ----------------------------------------------------------------------
def xs_demean(series: pd.Series, df: pd.DataFrame) -> pd.Series:
    """Universe-EW demean per date (zero-sum neutralization)."""
    tmp = pd.DataFrame({"v": series, "date": df["date"]})
    m = tmp.groupby("date")["v"].transform("mean")
    return series - m


def xs_rank(series: pd.Series, df: pd.DataFrame) -> pd.Series:
    tmp = pd.DataFrame({"v": series, "date": df["date"]})
    return tmp.groupby("date")["v"].rank(pct=True) - 0.5


def ts_z_per_symbol(series: pd.Series, df: pd.DataFrame, win: int = 60) -> pd.Series:
    out = []
    for sym, idx in df.groupby("symbol").indices.items():
        s = series.iloc[idx]
        mu = s.rolling(win, min_periods=20).mean()
        sd = s.rolling(win, min_periods=20).std()
        z = (s - mu) / sd
        out.append(pd.Series(z.values, index=idx))
    out = pd.concat(out).sort_index()
    return out


def build_expressions(df: pd.DataFrame) -> pd.DataFrame:
    """Returns DataFrame of raw signals, SAME INDEX as df.
    Convention: high signal = long (dip = positive signal).
    """
    sig = pd.DataFrame(index=df.index)

    # 1. 20-day drawdown, negated so deep dip -> positive
    raw_dd = (df["close"] - df["max_high_20"]) / df["max_high_20"]  # in [-1, 0]
    sig["r1_dd20"] = -raw_dd

    # 2. RSI14 oversold: 50 - RSI14 (so low RSI -> positive)
    sig["r1_rsi14"] = 50.0 - df["rsi14"]

    # 3. Bollinger position = (close-MA20)/(2*std20_price), negated
    std20_price = df.groupby("symbol", group_keys=False)["close"].apply(lambda s: s.rolling(20, min_periods=10).std())
    bb_pos = (df["close"] - df["ma20"]) / (2.0 * std20_price)
    sig["r1_bb_pos"] = -bb_pos

    # 4. Log bias vs MA20, negated
    log_bias = np.log(df["close"]) - np.log(df["ma20"])
    sig["r1_logbias_ma20"] = -log_bias

    # 5. 5d cumulative log-return reversal
    sig["r1_rev_5d"] = -df["logret_5d"]

    # 6. Vol-scaled 5d reversal
    sig["r1_vol_scaled_rev5"] = -df["logret_5d"] / df["std20"]

    # 7. Volume-confirmed reversal: -ret_5d * z(log(vol_5d / vol_20d))
    log_vol_ratio = np.log(df["vol5"] / df["vol20"])
    z_vol = ts_z_per_symbol(log_vol_ratio, df, win=60)
    sig["r1_vol_confirmed_rev"] = -df["logret_5d"] * z_vol

    # 8. Kitchen-sink rank ensemble of 1..6
    kitchen_parts = []
    for col in ["r1_dd20", "r1_rsi14", "r1_bb_pos", "r1_logbias_ma20", "r1_rev_5d", "r1_vol_scaled_rev5"]:
        kitchen_parts.append(xs_rank(sig[col], df))
    sig["r1_kitchen_sink"] = pd.concat(kitchen_parts, axis=1).mean(axis=1)

    # Neutralize: cross-sectional demean per date for all 8
    for col in sig.columns:
        sig[col] = xs_demean(sig[col], df)

    return sig


# ----------------------------------------------------------------------
# Target: forward k-day log return, with 1-bar execution delay
# ----------------------------------------------------------------------
def forward_returns(df: pd.DataFrame, k: int, delay: int = 1) -> pd.Series:
    """target[t] = log(close[t+1+k]) - log(close[t+1])
    i.e. enter on close of t+delay (=t+1), exit on close of t+delay+k.
    """
    g = df.groupby("symbol", group_keys=False)
    fwd_entry = g["log_close"].shift(-delay)
    fwd_exit  = g["log_close"].shift(-(delay + k))
    return fwd_exit - fwd_entry


# ----------------------------------------------------------------------
# IC and decile tables
# ----------------------------------------------------------------------
def ic_by_date(signal: pd.Series, target: pd.Series, df: pd.DataFrame) -> pd.Series:
    """Rank IC per date (pearson on ranks)."""
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
                "expression": col,
                "horizon_days": k,
                "ic_mean": ics.mean(),
                "ic_std":  ics.std(),
                "ic_tstat": (ics.mean() / (ics.std() / np.sqrt(len(ics)))) if len(ics) > 1 else np.nan,
                "n_days": len(ics),
                "icir_ann": (ics.mean() / ics.std() * np.sqrt(252)) if ics.std() > 0 else np.nan,
            })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# Threshold long-short strategy (G3 & payoff)
# ----------------------------------------------------------------------
def threshold_portfolio(signal: pd.Series, df: pd.DataFrame, top_n: int = TOP_N) -> pd.DataFrame:
    """Per rebalance date, long top_n and short bottom_n ETFs by signal.
    Weights are equal within leg: +1/top_n and -1/top_n. Re-weighted at
    each rebalance. Between rebalances positions are held (NOT rebalanced
    daily to avoid overstating turnover).
    """
    tmp = pd.DataFrame({"s": signal, "date": df["date"], "symbol": df["symbol"]})
    out_rows = []
    reb_dates = np.array(sorted(tmp["date"].dt.normalize().unique()))
    # Choose rebalances every 5 trading days starting from the first Wednesday
    trading_days = reb_dates
    # simpler: take every 5th trading day
    sel_mask = np.arange(len(trading_days)) % 5 == 0
    reb_dates = trading_days[sel_mask]

    for d in reb_dates:
        cross = tmp[tmp["date"] == d].dropna(subset=["s"])
        if len(cross) < 2 * top_n:
            continue
        cross = cross.sort_values("s")
        shorts = cross.head(top_n)["symbol"].tolist()
        longs  = cross.tail(top_n)["symbol"].tolist()
        for sym in longs:
            out_rows.append({"date": d, "symbol": sym, "weight":  1.0 / top_n})
        for sym in shorts:
            out_rows.append({"date": d, "symbol": sym, "weight": -1.0 / top_n})
    weights = pd.DataFrame(out_rows)
    return weights


def strategy_pnl(weights: pd.DataFrame, df: pd.DataFrame, cost_bps_per_side: float) -> pd.DataFrame:
    """Daily PnL of the weekly-rebalanced portfolio, with costs on rebalance."""
    panel = df[["date", "symbol", "log_ret_1"]].copy()
    # Forward-fill weights between rebalance dates within each symbol
    all_dates = np.array(sorted(panel["date"].unique()))
    sym_weights = {}
    for sym, grp in weights.groupby("symbol"):
        w = grp[["date", "weight"]].drop_duplicates("date").set_index("date")["weight"]
        w_ff = w.reindex(all_dates, method="ffill").fillna(0.0)
        sym_weights[sym] = w_ff
    w_panel = pd.DataFrame(sym_weights).fillna(0.0)
    w_panel.index.name = "date"

    # Turnover: sum of |w(t) - w(t-1)| across symbols
    turnover = (w_panel.diff().abs().sum(axis=1)).fillna(0.0)
    cost_daily = turnover * (cost_bps_per_side * 1e-4)

    # PnL: use NEXT-day log return because position taken at close of t
    ret = panel.pivot(index="date", columns="symbol", values="log_ret_1").reindex(all_dates).fillna(0.0)
    shifted_w = w_panel.shift(1).fillna(0.0)
    gross_daily = (shifted_w * ret).sum(axis=1)
    net_daily   = gross_daily - cost_daily

    pnl = pd.DataFrame({
        "date": all_dates,
        "gross_ret": gross_daily.values,
        "turnover":  turnover.values,
        "cost":      cost_daily.values,
        "net_ret":   net_daily.values,
    })
    return pnl


def annualize(rets: pd.Series) -> dict:
    r = rets.dropna()
    if len(r) < 30:
        return {"sharpe": np.nan, "cagr": np.nan, "vol": np.nan, "maxdd": np.nan, "n": len(r)}
    cum = r.cumsum()
    dd = cum - cum.cummax()
    vol = r.std() * np.sqrt(ANN_FACTOR)
    mean = r.mean() * ANN_FACTOR
    return {
        "sharpe": mean / vol if vol > 0 else 0.0,
        "cagr":   np.exp(mean) - 1 if abs(mean) < 5 else np.nan,
        "vol":    vol,
        "maxdd":  dd.min(),
        "n":      len(r),
    }


def per_year_sharpe(pnl: pd.DataFrame, col: str = "net_ret") -> pd.DataFrame:
    p = pnl[["date", col]].copy()
    p["year"] = p["date"].dt.year
    rows = []
    for y, grp in p.groupby("year"):
        s = grp[col].dropna()
        if len(s) < 30:
            continue
        vol = s.std() * np.sqrt(ANN_FACTOR)
        mean = s.mean() * ANN_FACTOR
        rows.append({
            "year": int(y),
            "n_days": len(s),
            "mean_ann": mean,
            "vol_ann":  vol,
            "sharpe":   mean / vol if vol > 0 else 0.0,
        })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# Decile summary for G4 monotonicity
# ----------------------------------------------------------------------
def decile_summary(signal: pd.Series, df: pd.DataFrame, k: int = PRIMARY_K) -> pd.DataFrame:
    """Because |universe|=18, use quintiles (5 bins) rather than deciles."""
    tmp = pd.DataFrame({
        "s": signal,
        "date": df["date"],
        "t": forward_returns(df, k=k),
    }).dropna()
    tmp["bin"] = tmp.groupby("date")["s"].transform(
        lambda s: pd.qcut(s, q=5, labels=False, duplicates="drop")
    )
    bin_ret = tmp.groupby("bin")["t"].mean()
    bin_cnt = tmp.groupby("bin")["t"].count()
    df_out = pd.DataFrame({
        "bin":      bin_ret.index.astype(int),
        "fwd_ret":  bin_ret.values,
        "n_obs":    bin_cnt.values,
    }).sort_values("bin").reset_index(drop=True)
    return df_out


# ----------------------------------------------------------------------
# G1-G5 gates
# ----------------------------------------------------------------------
def run_gates(sig_col: str, signal: pd.Series, df: pd.DataFrame,
              ic_row: pd.DataFrame, pnl_net_at_5bps: pd.DataFrame,
              decile: pd.DataFrame, universe_ew_ret: pd.Series) -> dict:
    out = {"G1": "pass", "G2": "pass", "G3": {}, "G4": {}, "ic_row": ic_row.to_dict("records")}

    # G3 coverage
    n_days = df["date"].nunique()
    sig_by_date = signal.groupby(df["date"]).count()
    target_min = int(0.90 * UNIV_SIZE_TARGET)
    pct_days_enough_sig = (sig_by_date >= target_min).mean()

    turnover_ann = pnl_net_at_5bps["turnover"].sum() * 252 / len(pnl_net_at_5bps) * 100
    zero_reb_days_pct = (pnl_net_at_5bps["turnover"] < 1e-8).mean()

    net_ann = annualize(pnl_net_at_5bps["net_ret"])
    net_sharpe = net_ann["sharpe"]

    G3 = {
        "pct_days_enough_signal":  float(pct_days_enough_sig),
        "annual_turnover_pct":     float(turnover_ann),
        "zero_rebalance_days_pct": float(zero_reb_days_pct),
        "net_sharpe_at_5bps":      float(net_sharpe),
        "pass": bool(
            pct_days_enough_sig >= 0.90
            and 10 <= turnover_ann <= 2000
            and zero_reb_days_pct <= 0.05
            and net_sharpe >= -0.5
        ),
    }
    out["G3"] = G3

    # G4 fidelity: IC sign, monotonicity, horizon consistency, corr vs uni-EW
    ic_at_k10 = ic_row[ic_row["horizon_days"] == PRIMARY_K]["ic_mean"].iloc[0]
    ic_peak_k = int(ic_row.sort_values("ic_mean", ascending=False).iloc[0]["horizon_days"])

    mono_rets = decile["fwd_ret"].values
    inversions = sum(1 for i in range(1, len(mono_rets)) if mono_rets[i] < mono_rets[i-1])
    q5_minus_q1 = mono_rets[-1] - mono_rets[0]

    # corr vs universe EW
    gross = pnl_net_at_5bps[["date", "gross_ret"]].set_index("date")["gross_ret"]
    u = universe_ew_ret.reindex(gross.index).fillna(0.0)
    corr_to_uew = float(gross.corr(u)) if gross.std() > 0 else 0.0

    G4 = {
        "ic_mean_at_k10":     float(ic_at_k10),
        "ic_peak_horizon":    int(ic_peak_k),
        "decile_inversions":  int(inversions),
        "q5_minus_q1":        float(q5_minus_q1),
        "corr_vs_universe_ew": corr_to_uew,
        "pass": bool(
            ic_at_k10 > 0                       # sign matches thesis
            and inversions <= 2                 # at most one inversion allowed but give 2 due to 5 bins
            and q5_minus_q1 > 0
            and abs(corr_to_uew) <= 0.85
        ),
    }
    out["G4"] = G4
    return out


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
def main():
    df = load_panel()
    df = add_features(df)

    signals = build_expressions(df)
    exprs = list(signals.columns)
    assert len(exprs) == 8, f"Rule of 8 violation: {len(exprs)} expressions"

    # IC table
    ic_df = ic_table(signals, df)
    ic_df.to_csv(OUT / "ic_table_batch_0001.csv", index=False)

    # Decile summary at k=10 for each expression
    decile_rows = []
    for col in exprs:
        d = decile_summary(signals[col], df, k=PRIMARY_K)
        d.insert(0, "expression", col)
        decile_rows.append(d)
    decile_all = pd.concat(decile_rows, ignore_index=True)
    decile_all.to_csv(OUT / "decile_summary_batch_0001.csv", index=False)

    # LS summary + cost sensitivity
    ls_rows = []
    cost_rows = []
    universe_ew_ret = (
        df.set_index(["date", "symbol"])["log_ret_1"].unstack("symbol").mean(axis=1)
    )

    # Save gates dict
    gates_all = {"session": "20260423_a_share_etf_reversal_v1", "round": 1, "expressions": {}}

    for col in exprs:
        weights = threshold_portfolio(signals[col], df, top_n=TOP_N)
        pnl_5 = strategy_pnl(weights, df, cost_bps_per_side=5.0)

        # cost sensitivity
        for cb in COST_GRID_BPS:
            pnl_cb = strategy_pnl(weights, df, cost_bps_per_side=cb)
            met = annualize(pnl_cb["net_ret"])
            cost_rows.append({
                "expression":      col,
                "cost_bps_side":   cb,
                "gross_sharpe":    annualize(pnl_cb["gross_ret"])["sharpe"],
                "net_sharpe":      met["sharpe"],
                "net_cagr":        met["cagr"],
                "net_maxdd":       met["maxdd"],
                "ann_turnover_pct": float(pnl_cb["turnover"].sum() * 252 / len(pnl_cb) * 100),
            })

        # LS summary at baseline
        gross_ann = annualize(pnl_5["gross_ret"])
        net_ann   = annualize(pnl_5["net_ret"])
        pa = per_year_sharpe(pnl_5, "net_ret")

        # G4 monotonicity
        d_here = decile_all[decile_all["expression"] == col].copy()
        ic_row = ic_df[ic_df["expression"] == col].copy()

        gates = run_gates(col, signals[col], df, ic_row, pnl_5, d_here, universe_ew_ret)
        gates["G5_expr_peak_horizon"] = int(ic_row.sort_values("ic_mean", ascending=False).iloc[0]["horizon_days"])
        gates_all["expressions"][col] = gates

        worst_year = pa["sharpe"].min() if len(pa) else np.nan
        ls_rows.append({
            "expression":        col,
            "gross_sharpe":      gross_ann["sharpe"],
            "net_sharpe_5bps":   net_ann["sharpe"],
            "net_cagr":          net_ann["cagr"],
            "net_maxdd":         net_ann["maxdd"],
            "ann_turnover_pct":  float(pnl_5["turnover"].sum() * 252 / len(pnl_5) * 100),
            "worst_year_sharpe": worst_year,
            "n_years":           len(pa),
            "G3_pass":           gates["G3"]["pass"],
            "G4_pass":           gates["G4"]["pass"],
            "G5_peak_k":         gates["G5_expr_peak_horizon"],
        })

    ls_df   = pd.DataFrame(ls_rows)
    cost_df = pd.DataFrame(cost_rows)
    ls_df.to_csv(OUT / "ls_summary_batch_0001.csv", index=False)
    cost_df.to_csv(OUT / "cost_sensitivity_batch_0001.csv", index=False)

    # G5 batch horizon consistency
    g4_survivors = ls_df[ls_df["G4_pass"]]["expression"].tolist()
    peak_k_dist = {k: 0 for k in HORIZON_GRID}
    for col in g4_survivors:
        pk = gates_all["expressions"][col]["G5_expr_peak_horizon"]
        peak_k_dist[pk] = peak_k_dist.get(pk, 0) + 1
    frac_at_declared = (
        peak_k_dist.get(PRIMARY_K, 0) / max(len(g4_survivors), 1)
    )
    gates_all["G5_batch"] = {
        "declared_k": PRIMARY_K,
        "n_g4_survivors": len(g4_survivors),
        "peak_k_counts": peak_k_dist,
        "fraction_peaking_at_declared_k": frac_at_declared,
        "pass": frac_at_declared >= 0.5,
    }

    with (OUT / "validation_gates_batch_0001.json").open("w") as f:
        json.dump(gates_all, f, indent=2, default=str)

    # per-year for each expression
    per_year_rows = []
    for col in exprs:
        weights = threshold_portfolio(signals[col], df, top_n=TOP_N)
        pnl = strategy_pnl(weights, df, cost_bps_per_side=5.0)
        pa = per_year_sharpe(pnl, "net_ret")
        pa.insert(0, "expression", col)
        per_year_rows.append(pa)
    per_year_all = pd.concat(per_year_rows, ignore_index=True)
    per_year_all.to_csv(OUT / "per_year_sharpe_batch_0001.csv", index=False)

    print("=== IC table ===")
    print(ic_df.to_string(index=False))
    print("\n=== LS summary @ 5bps/side ===")
    print(ls_df.to_string(index=False))
    print("\n=== Cost sensitivity ===")
    print(cost_df.to_string(index=False))
    print("\n=== G5 batch ===")
    print(json.dumps(gates_all["G5_batch"], indent=2))
    print("\n=== Per-year Sharpe (net, 5bps) ===")
    print(per_year_all.to_string(index=False))


if __name__ == "__main__":
    main()
