#!/usr/bin/env python3
"""
Industry ETF dip-buy — 8 expressions, 32 ETFs, TVT split.

Universe: 34 V7_gold thematic ETFs minus 159934 (gold) and 515080 (dividend).
Execution delay: 1 bar.  Target: log(close[t+1+k]/close[t+1]).
Neutralization: universe-EW demean per date.
Rebalance: monthly (every 4th Friday, 20-bar hold).
Long-only top-3 (or top-1 for conviction variant).

Splits evaluated from the start:
  Train 2019-01-04..2022-12-31
  Val   2023
  OOS   2024-01-01..2026-04-22
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd

SESSION = Path("/home/user/Factor_Zoo/logs/20260424_a_share_etf_industry_dipbuy_v1")
OUT = SESSION / "outputs"
DATA_SRC = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs/etf_daily.parquet")

COMMON_START = pd.Timestamp("2019-01-04")
TRAIN_END = pd.Timestamp("2022-12-31")
VAL_END = pd.Timestamp("2023-12-31")
STAGGERED_JOIN_BARS = 60
EXCLUDE_SYMBOLS = ["159934.SZ", "515080.SH"]  # gold, dividend
LONG_N = 3

COST_GRID_BPS = [0, 5, 10, 15]

INDUSTRY_CLUSTERS = {
    "TMT_hardware":   ["512480.SH", "159779.SZ", "159713.SZ", "515880.SH"],
    "TMT_software":   ["515230.SH", "159869.SZ", "515980.SH", "159890.SZ", "562500.SH"],
    "consumer":       ["512690.SH", "515170.SH", "561120.SH", "159867.SZ"],
    "healthcare":     ["512010.SH", "159883.SZ", "159992.SZ"],
    "financial":      ["512800.SH", "512880.SH", "159892.SZ", "512200.SH"],
    "manufacturing":  ["512660.SH", "159227.SZ", "516750.SH", "159870.SZ", "515210.SH"],
    "new_energy":     ["515030.SH", "159857.SZ", "159755.SZ", "159326.SZ", "159980.SH", "515220.SH"],
    "oil_gas":        ["561360.SH"],
}
SYMBOL_TO_CLUSTER = {s: c for c, syms in INDUSTRY_CLUSTERS.items() for s in syms}


# --------------------------------------------------------------------------- #
# Panel + features
# --------------------------------------------------------------------------- #
def load_panel() -> pd.DataFrame:
    df = pd.read_parquet(DATA_SRC).rename(columns={"trade_date": "date", "ts_code": "symbol"})
    df = df[~df["symbol"].isin(EXCLUDE_SYMBOLS)]
    df = df.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"]).reset_index(drop=True)
    return df


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for k in [5, 20, 40, 60, 80, 250]:
        df[f"logret_{k}d"] = df.groupby("symbol")["close_adj"].transform(
            lambda s, k=k: np.log(s / s.shift(k))
        )
    # Rolling std of daily logrets (for vol-scale)
    df["logret_1d"] = df.groupby("symbol")["close_adj"].transform(lambda s: np.log(s / s.shift(1)))
    df["std_40d"] = df.groupby("symbol")["logret_1d"].transform(
        lambda s: s.rolling(40, min_periods=20).std()
    )
    # Drawdown from 40d max (includes current bar — current-state feature)
    df["max40"] = df.groupby("symbol")["close_adj"].transform(
        lambda s: s.rolling(40, min_periods=20).max()
    )
    df["dd40"] = (df["max40"] - df["close_adj"]) / df["max40"]
    # Vol ratio: recent 5d vol / recent 60d vol (< 1 ≈ calming / surrender, > 1 ≈ panic)
    df["std_5d_v"] = df.groupby("symbol")["logret_1d"].transform(
        lambda s: s.rolling(5, min_periods=3).std()
    )
    df["std_60d_v"] = df.groupby("symbol")["logret_1d"].transform(
        lambda s: s.rolling(60, min_periods=30).std()
    )
    df["vol_ratio_5_60"] = df["std_5d_v"] / df["std_60d_v"].replace(0, np.nan)

    df["bar_age"] = df.groupby("symbol").cumcount()
    df["is_live"] = df["bar_age"] >= STAGGERED_JOIN_BARS

    # Targets (for IC): log(close[t+1+k]/close[t+1])
    for k in [20, 40, 60, 80]:
        fwd_end = df.groupby("symbol")["close_adj"].shift(-(1 + k))
        fwd_start = df.groupby("symbol")["close_adj"].shift(-1)
        df[f"target_{k}"] = np.log(fwd_end / fwd_start)

    return df


# --------------------------------------------------------------------------- #
# Signal builders
# --------------------------------------------------------------------------- #
def _demean(sig: pd.Series, df: pd.DataFrame) -> pd.Series:
    s = sig.where(df["is_live"])
    return s - s.groupby(df["date"]).transform("mean")


def build_d40_baseline(df):
    return _demean(-df["logret_40d"], df)


def build_d40_vol_scaled(df):
    return _demean(-df["logret_40d"] / df["std_40d"].replace(0, np.nan), df)


def build_d40_resid_250d(df):
    """Residual of logret_40d on logret_250d, per date cross-section (≈ short-term ex long-term trend)"""
    # Cross-sectional regression per date: resid = logret_40d - beta*logret_250d - alpha
    # Negative sign so dip = positive signal
    dfx = df[["date", "symbol", "logret_40d", "logret_250d", "is_live"]].copy()
    out = np.full(len(dfx), np.nan)
    for dt, g in dfx.groupby("date"):
        valid = g[g["is_live"]].dropna(subset=["logret_40d", "logret_250d"])
        if len(valid) < 5:
            continue
        x = valid["logret_250d"].values
        y = valid["logret_40d"].values
        beta = np.cov(x, y, ddof=0)[0, 1] / (np.var(x) + 1e-12)
        alpha = y.mean() - beta * x.mean()
        resid = y - (alpha + beta * x)
        # Map back via index
        out[valid.index] = -resid  # negative so dip = positive
    sig = pd.Series(out, index=df.index)
    # already demeaned by regression residual (intercept removed); re-demean per date to be safe
    return _demean(sig, df)


def build_d40_deep_only(df):
    raw = df["dd40"] * (df["dd40"] > 0.10).astype(float)
    return _demean(raw, df)


def build_d40_bounce_conf(df):
    raw = df["dd40"] * (df["dd40"] > 0.10).astype(float) * (df["logret_5d"] > 0).astype(float)
    return _demean(raw, df)


def build_d40_low_vol_surrender(df):
    # dd40 * (1/vol_ratio_5_60) — higher dd with calmer recent vol → stronger signal
    raw = df["dd40"] / df["vol_ratio_5_60"].replace(0, np.nan)
    return _demean(raw, df)


SIGNAL_BUILDERS = {
    "d40_baseline":          build_d40_baseline,
    "d40_vol_scaled":        build_d40_vol_scaled,
    "d40_resid_250d":        build_d40_resid_250d,
    "d40_deep_only":         build_d40_deep_only,
    "d40_bounce_conf":       build_d40_bounce_conf,
    "d40_low_vol_surrender": build_d40_low_vol_surrender,
}

SIGNAL_METADATA = {
    "d40_baseline":          {"k": 40, "cluster": "signal_refinement", "long_n": 3, "mode": "topN"},
    "d40_vol_scaled":        {"k": 40, "cluster": "signal_refinement", "long_n": 3, "mode": "topN"},
    "d40_resid_250d":        {"k": 40, "cluster": "signal_refinement", "long_n": 3, "mode": "topN"},
    "d40_deep_only":         {"k": 40, "cluster": "conditional_trigger", "long_n": 3, "mode": "topN"},
    "d40_bounce_conf":       {"k": 40, "cluster": "conditional_trigger", "long_n": 3, "mode": "topN"},
    "d40_low_vol_surrender": {"k": 40, "cluster": "conditional_trigger", "long_n": 3, "mode": "topN"},
    "p_top1_conviction":     {"k": 40, "cluster": "portfolio_construction", "long_n": 1, "mode": "topN"},
    "p_top3_diversified":    {"k": 40, "cluster": "portfolio_construction", "long_n": 3, "mode": "topN_diversified"},
}


# --------------------------------------------------------------------------- #
# Weight construction
# --------------------------------------------------------------------------- #
def monthly_rebals(all_dates: pd.DatetimeIndex, dow: int = 4, every_n: int = 4) -> pd.DatetimeIndex:
    fridays = all_dates[all_dates.dayofweek == dow]
    return fridays[::every_n]


def build_topN_weights(sig_demean, df, rebals, long_n, symbols, diversified=False):
    panel = pd.DataFrame({
        "date": df["date"].values, "symbol": df["symbol"].values,
        "s": sig_demean.values, "live": df["is_live"].values,
    })
    all_d = sorted(panel["date"].unique())
    w = pd.DataFrame(0.0, index=pd.DatetimeIndex(rebals), columns=symbols)
    panel_idx = panel.set_index(["date", "symbol"])

    for dt in rebals:
        try:
            slice_df = panel_idx.xs(dt, level="date")
        except KeyError:
            continue
        slice_df = slice_df.dropna(subset=["s"])
        slice_df = slice_df[slice_df["live"]]
        if len(slice_df) < max(long_n * 2, 5):
            continue
        ranked = slice_df["s"].sort_values(ascending=False)

        if diversified:
            seen_clusters = set()
            picks = []
            for sym in ranked.index:
                cluster = SYMBOL_TO_CLUSTER.get(sym)
                if cluster in seen_clusters:
                    continue
                picks.append(sym)
                seen_clusters.add(cluster)
                if len(picks) >= long_n:
                    break
            longs = picks
        else:
            longs = ranked.iloc[:long_n].index.tolist()

        if len(longs) == 0:
            continue
        weight_each = 1.0 / len(longs)
        w.loc[dt, longs] = weight_each

    return w.reindex(pd.DatetimeIndex(all_d)).ffill().fillna(0.0)


# --------------------------------------------------------------------------- #
# PnL / metrics
# --------------------------------------------------------------------------- #
def pnl_from_weights(w, df):
    rw = df.pivot_table(index="date", columns="symbol", values="close_adj").pct_change()
    rw = rw.reindex(w.index).reindex(columns=w.columns)
    return (w.shift(1).fillna(0) * rw).sum(axis=1)


def turnover(w):
    return w.diff().fillna(w).abs().sum(axis=1)


def ann(pnl):
    p = pnl.dropna()
    if len(p) < 30:
        return {"sharpe": np.nan, "ret": np.nan, "vol": np.nan, "maxdd": np.nan, "n": len(p)}
    mu, s = p.mean() * 252, p.std() * np.sqrt(252)
    eq = (1 + p).cumprod()
    return {
        "sharpe": float(mu/s) if s > 0 else np.nan,
        "ret": float(mu), "vol": float(s),
        "maxdd": float((eq/eq.cummax() - 1).min()), "n": int(len(p)),
    }


def per_year_sh(pnl):
    p = pnl.dropna(); out = {}
    for y in sorted(set(p.index.year)):
        yp = p[p.index.year == y]
        if len(yp) < 30:
            out[int(y)] = np.nan; continue
        mu, s = yp.mean() * 252, yp.std() * np.sqrt(252)
        out[int(y)] = float(mu/s) if s > 0 else np.nan
    return out


def compute_ic(sig, target, date):
    from scipy.stats import spearmanr
    dfx = pd.DataFrame({"s": sig, "t": target, "d": date}).dropna()
    if dfx.empty: return {"ic": np.nan, "ic_t": np.nan, "n": 0}
    per = dfx.groupby("d").apply(
        lambda g: spearmanr(g["s"], g["t"])[0] if len(g) >= 5 else np.nan,
        include_groups=False
    ).dropna()
    if per.empty: return {"ic": np.nan, "ic_t": np.nan, "n": 0}
    mu, sd, n = per.mean(), per.std(), len(per)
    return {"ic": float(mu), "ic_t": float(mu / (sd / np.sqrt(n))) if sd > 0 else np.nan, "n": n}


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def main():
    print("Loading & features …")
    df = load_panel()
    df = compute_features(df)
    df = df[df["date"] >= COMMON_START].reset_index(drop=True)
    print(f"  panel: {len(df):,} rows, {df['symbol'].nunique()} symbols, "
          f"{df['date'].min().date()} → {df['date'].max().date()}")

    all_d = pd.DatetimeIndex(sorted(df["date"].unique()))
    rebals = monthly_rebals(all_d)
    symbols = sorted(df["symbol"].unique())
    print(f"  monthly rebals: {len(rebals)}")

    # ---- Build signals & weights ----
    signals = {sid: fn(df) for sid, fn in SIGNAL_BUILDERS.items()}

    # Helper: run a named strategy
    def run_strategy(sid, sig, long_n, diversified=False):
        w = build_topN_weights(sig, df, rebals, long_n, symbols, diversified=diversified)
        p = pnl_from_weights(w, df); t = turnover(w)
        net5 = p - t * 5 / 1e4
        return w, p, t, net5

    # Include p_top1_conviction and p_top3_diversified (use d40_baseline signal)
    base_sig = signals["d40_baseline"]

    ic_rows, headline_rows, per_year_rows, cost_rows = [], [], [], []
    pnl_series = {}

    for sid, meta in SIGNAL_METADATA.items():
        print(f"\n=== {sid}  (k={meta['k']}, long_n={meta['long_n']}, mode={meta['mode']}) ===")

        if sid == "p_top1_conviction":
            sig = base_sig
            w, p, t, net5 = run_strategy(sid, sig, long_n=1, diversified=False)
        elif sid == "p_top3_diversified":
            sig = base_sig
            w, p, t, net5 = run_strategy(sid, sig, long_n=3, diversified=True)
        else:
            sig = signals[sid]
            w, p, t, net5 = run_strategy(sid, sig, long_n=meta["long_n"], diversified=False)

        # G1 non-degeneracy (on raw-ish signal, if not demeaned heavily)
        nonzero_frac = float((sig.abs() > 1e-12).sum() / max(1, sig.notna().sum()))
        print(f"  G1 nonzero fraction: {nonzero_frac:.4f}")

        # IC at own horizon k=40
        ic = compute_ic(sig, df[f"target_{meta['k']}"], df["date"])
        print(f"  IC at k={meta['k']}: {ic['ic']:+.4f}  t={ic['ic_t']:+.2f}  n_dates={ic['n']}")
        ic_rows.append({"id": sid, **ic, "horizon": meta["k"]})

        # TVT per-split metrics
        splits = {
            "train": (COMMON_START, TRAIN_END),
            "val":   (TRAIN_END + pd.Timedelta(days=1), VAL_END),
            "oos":   (VAL_END + pd.Timedelta(days=1), df["date"].max()),
        }
        for split_name, (s, e) in splits.items():
            sub = net5[(net5.index >= s) & (net5.index <= e)]
            a = ann(sub); py = per_year_sh(sub)
            worst_y = min(py, key=lambda y: py[y] if not np.isnan(py[y]) else 99) if py else None
            worst_sh = py.get(worst_y, np.nan) if worst_y else np.nan
            headline_rows.append({
                "id": sid, "split": split_name,
                "sharpe_net_5bps": a["sharpe"], "ret_ann": a["ret"],
                "maxdd": a["maxdd"], "n_days": a["n"],
                "worst_year": worst_y, "worst_year_sharpe": float(worst_sh),
            })
            for yr, sh in py.items():
                per_year_rows.append({"id": sid, "split": split_name, "year": int(yr),
                                      "sharpe": float(sh)})
            print(f"  {split_name:6s}  Sh={a['sharpe']:+.3f}  ret={a['ret']:+.2%}  MaxDD={a['maxdd']:+.2%}  "
                  f"worst {worst_y} Sh={worst_sh:+.3f}")

        # Cost sensitivity on full sample
        for bps in COST_GRID_BPS:
            net = p - t * bps / 1e4
            cost_rows.append({"id": sid, "cost_bps": bps, "net_sharpe_full": ann(net)["sharpe"]})

        pnl_series[sid] = net5

    # ---- Save ----
    pd.DataFrame(ic_rows).to_csv(OUT / "ic_table_batch_0001.csv", index=False)
    pd.DataFrame(headline_rows).to_csv(OUT / "tvt_summary_batch_0001.csv", index=False)
    pd.DataFrame(per_year_rows).to_csv(OUT / "per_year_batch_0001.csv", index=False)
    pd.DataFrame(cost_rows).to_csv(OUT / "cost_sensitivity_batch_0001.csv", index=False)
    pd.DataFrame(pnl_series).to_csv(OUT / "pnl_net5_daily_batch_0001.csv")

    # ---- Summary print ----
    print("\n\n" + "=" * 80)
    print("TVT summary (Net Sharpe @5bps)")
    print("=" * 80)
    summ = pd.DataFrame(headline_rows).pivot_table(index="id", columns="split", values="sharpe_net_5bps")
    wrs = pd.DataFrame(headline_rows).pivot_table(index="id", columns="split", values="worst_year_sharpe")
    print(f"{'id':<25s}  {'train':>7s}  {'val':>7s}  {'oos':>7s}  {'w_train':>8s}  {'w_val':>7s}  {'w_oos':>7s}")
    for sid in SIGNAL_METADATA.keys():
        print(f"{sid:<25s}  {summ.loc[sid,'train']:>+7.3f}  {summ.loc[sid,'val']:>+7.3f}  {summ.loc[sid,'oos']:>+7.3f}  "
              f"{wrs.loc[sid,'train']:>+8.3f}  {wrs.loc[sid,'val']:>+7.3f}  {wrs.loc[sid,'oos']:>+7.3f}")

    print("\n✅ Batch 0001 outputs:")
    for p in sorted(OUT.glob("*_batch_0001.*")):
        print("   ", p.name)


if __name__ == "__main__":
    main()
