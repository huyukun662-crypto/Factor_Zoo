#!/usr/bin/env python3
"""
Agent 3 + Agent 4: Build 8 reversal expressions and run the full backtest
battery (G1 → G4 + audit probes) on 34 thematic A-share ETFs.

Outputs:
  outputs/ic_table_batch_0001.csv
  outputs/ls_summary_batch_0001.csv
  outputs/longonly_summary_batch_0001.csv
  outputs/decile_summary_batch_0001.csv
  outputs/per_year_sharpe_batch_0001.csv
  outputs/cost_sensitivity_batch_0001.csv
  outputs/validation_gates_batch_0001.json
  outputs/signal_panel.parquet         (for downstream fusion)
  outputs/longonly_top3_equity_<id>.csv (for survivors only)
  outputs/ls_top4_equity_<id>.csv       (for survivors only)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


SESSION = Path("/home/user/Factor_Zoo/logs/20260424_a_share_etf_reversal_v2")
OUT = SESSION / "outputs"
OUT.mkdir(exist_ok=True)

DATA_SRC = Path(
    "/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs/etf_daily.parquet"
)
COMMON_START = pd.Timestamp("2019-01-04")
STAGGERED_JOIN_BARS = 60

# --------------------------------------------------------------------------- #
# Expression config (from handoff_2_to_3.json)
# --------------------------------------------------------------------------- #
EXPRESSIONS = [
    {"id": "r1_rev_1d",       "cluster": "short_falsification", "k": 1,  "hold_bars": 5,  "kind": "logret"},
    {"id": "r1_rev_5d",       "cluster": "short_falsification", "k": 5,  "hold_bars": 5,  "kind": "logret"},
    {"id": "r1_rev_20d",      "cluster": "medium_scan",         "k": 20, "hold_bars": 20, "kind": "logret"},
    {"id": "r1_rev_40d",      "cluster": "medium_scan",         "k": 40, "hold_bars": 20, "kind": "logret"},
    {"id": "r1_rev_60d",      "cluster": "medium_scan",         "k": 60, "hold_bars": 20, "kind": "logret"},
    {"id": "r1_rev_80d",      "cluster": "medium_scan",         "k": 80, "hold_bars": 20, "kind": "logret"},
    {"id": "r1_dd60_raw",     "cluster": "drawdown_event",      "k": 60, "hold_bars": 20, "kind": "dd60_raw"},
    {"id": "r1_dd60_recover", "cluster": "drawdown_event",      "k": 60, "hold_bars": 20, "kind": "dd60_recover"},
]

# Audit probe
PROBE = {"id": "probe_mom_20d_plus", "k": 60, "hold_bars": 20, "kind": "mom_probe"}

HORIZONS_ALL = sorted(set(e["k"] for e in EXPRESSIONS) | {60})  # for IC table
COST_GRID_BPS = [0, 5, 10, 15]


# --------------------------------------------------------------------------- #
# Load data
# --------------------------------------------------------------------------- #
def load_panel() -> pd.DataFrame:
    df = pd.read_parquet(DATA_SRC)
    df = df.rename(columns={"trade_date": "date", "ts_code": "symbol"})
    df = df[["date", "symbol", "etf_name", "close_adj", "close", "vol"]].copy()
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    # Deduplicate (some prior panels had duplicate rows)
    df = df.drop_duplicates(subset=["symbol", "date"])
    return df


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["logret_1d"] = df.groupby("symbol")["close_adj"].transform(
        lambda s: np.log(s / s.shift(1))
    )
    for k in [5, 20, 40, 60, 80]:
        df[f"logret_{k}d"] = df.groupby("symbol")["close_adj"].transform(
            lambda s, k=k: np.log(s / s.shift(k))
        )
    # rolling 60d max (current-state, includes current bar per spec)
    df["max60"] = df.groupby("symbol")["close_adj"].transform(
        lambda s: s.rolling(60, min_periods=30).max()
    )
    df["dd60_raw"] = (df["max60"] - df["close_adj"]) / df["max60"]
    df["dd60_recover"] = df["dd60_raw"] * (df["logret_5d"] > 0).astype(float)
    # Age filter: require STAGGERED_JOIN_BARS bars of history
    df["bar_age"] = df.groupby("symbol").cumcount()
    df["is_live"] = df["bar_age"] >= STAGGERED_JOIN_BARS
    # Forward targets — canonical path: shift on close_adj, then compute log diff
    # target_k[t] = log(close[t+1+k]) - log(close[t+1])
    for k in HORIZONS_ALL:
        fwd_end = df.groupby("symbol")["close_adj"].shift(-(1 + k))
        fwd_start = df.groupby("symbol")["close_adj"].shift(-1)
        df[f"target_{k}"] = np.log(fwd_end / fwd_start)
    return df


# --------------------------------------------------------------------------- #
# Signal construction
# --------------------------------------------------------------------------- #
def build_signal(df: pd.DataFrame, spec: dict) -> pd.Series:
    k = spec["k"]
    kind = spec["kind"]
    if kind == "logret":
        raw = -df[f"logret_{k}d"]
    elif kind == "dd60_raw":
        raw = df["dd60_raw"]
    elif kind == "dd60_recover":
        raw = df["dd60_recover"]
    elif kind == "mom_probe":
        raw = df["logret_20d"]
    else:
        raise ValueError(f"Unknown signal kind: {kind}")
    return raw


def demean_cross_sectional(sig: pd.Series, df: pd.DataFrame) -> pd.Series:
    # universe-EW demean per date, using only live symbols
    mask = df["is_live"]
    masked = sig.where(mask)
    per_date_mean = masked.groupby(df["date"]).transform("mean")
    demean = masked - per_date_mean
    return demean


# --------------------------------------------------------------------------- #
# Gates / metrics
# --------------------------------------------------------------------------- #
def g1_non_degeneracy(raw: pd.Series) -> dict:
    n_total = raw.notna().sum()
    n_nonzero = (raw.fillna(0).abs() > 1e-12).sum()
    frac = n_nonzero / max(1, n_total)
    return {
        "n_total": int(n_total),
        "n_nonzero": int(n_nonzero),
        "nonzero_fraction": float(frac),
        "pass": bool(frac >= 0.01),
    }


def compute_ic(sig: pd.Series, target: pd.Series, date: pd.Series) -> dict:
    dfx = pd.DataFrame({"s": sig, "t": target, "d": date}).dropna()
    if dfx.empty:
        return {"ic": np.nan, "ic_t": np.nan, "n_dates": 0}
    per_date = dfx.groupby("d").apply(
        lambda g: g["s"].corr(g["t"], method="spearman") if len(g) >= 5 else np.nan,
        include_groups=False,
    )
    per_date = per_date.dropna()
    if per_date.empty:
        return {"ic": np.nan, "ic_t": np.nan, "n_dates": 0}
    ic_mean = per_date.mean()
    ic_std = per_date.std()
    ic_t = ic_mean / (ic_std / np.sqrt(len(per_date))) if ic_std > 0 else np.nan
    return {
        "ic": float(ic_mean),
        "ic_t": float(ic_t),
        "ic_std": float(ic_std),
        "n_dates": int(len(per_date)),
    }


def compute_quintile(sig: pd.Series, target: pd.Series, date: pd.Series, n_q: int = 5) -> dict:
    dfx = pd.DataFrame({"s": sig, "t": target, "d": date}).dropna()
    if dfx.empty:
        return {f"q{i+1}": np.nan for i in range(n_q)}

    def assign_q(g: pd.DataFrame) -> pd.DataFrame:
        if len(g) < n_q:
            g = g.copy()
            g["q"] = np.nan
            return g
        g = g.copy()
        g["q"] = pd.qcut(g["s"].rank(method="first"), n_q, labels=False, duplicates="drop") + 1
        return g

    dfx = dfx.groupby("d", group_keys=False)[["s", "t"]].apply(assign_q).reset_index(drop=True)
    out = {}
    for q in range(1, n_q + 1):
        sub = dfx[dfx.get("q") == q]
        out[f"q{q}_mean"] = float(sub["t"].mean()) if len(sub) else np.nan
    return out


# --------------------------------------------------------------------------- #
# Backtest wrappers
# --------------------------------------------------------------------------- #
def dense_weekly_weights(
    signal_demean: pd.Series,
    df: pd.DataFrame,
    *,
    long_n: int,
    short_n: int,
    hold_bars: int,
    rebalance_dow: int = 4,  # Friday = 4
) -> pd.DataFrame:
    """
    Returns a (date × symbol) weights matrix, dense on rebalance dates,
    held flat between rebalances via ffill (reset to zero at each rebalance).
    """
    panel = pd.DataFrame(
        {"date": df["date"].values, "symbol": df["symbol"].values, "s": signal_demean.values, "live": df["is_live"].values}
    )
    # Rebalance dates: Fridays (or last trading day of each calendar week)
    all_dates = sorted(panel["date"].unique())
    date_idx = pd.DatetimeIndex(all_dates)
    # Use every hold_bars-th Friday for monthly; every Friday for weekly
    fridays = date_idx[date_idx.dayofweek == rebalance_dow]
    if hold_bars == 5:
        rebals = list(fridays)
    else:
        # For 20-bar monthly hold, take every 4th Friday
        rebals = list(fridays[::4])
    rebals = pd.DatetimeIndex(rebals)

    symbols = sorted(panel["symbol"].unique())
    w = pd.DataFrame(0.0, index=rebals, columns=symbols)

    panel_idx = panel.set_index(["date", "symbol"])

    for dt in rebals:
        try:
            slice_df = panel_idx.xs(dt, level="date")
        except KeyError:
            continue
        slice_df = slice_df.dropna(subset=["s"])
        slice_df = slice_df[slice_df["live"]]
        if len(slice_df) < max(long_n, short_n) * 2:
            continue
        ranked = slice_df["s"].sort_values(ascending=False)
        longs = ranked.iloc[:long_n].index.tolist() if long_n > 0 else []
        shorts = ranked.iloc[-short_n:].index.tolist() if short_n > 0 else []
        if long_n > 0:
            w.loc[dt, longs] = 1.0 / long_n
        if short_n > 0:
            w.loc[dt, shorts] = -1.0 / short_n

    # Reindex to full date index and ffill until next rebalance
    w_full = w.reindex(pd.DatetimeIndex(all_dates))
    w_full = w_full.ffill().fillna(0.0)
    return w_full


def pnl_from_weights(weights: pd.DataFrame, df: pd.DataFrame) -> pd.Series:
    # Daily arithmetic return per symbol
    ret_wide = df.pivot_table(index="date", columns="symbol", values="close_adj")
    ret_wide = ret_wide.pct_change().reindex(weights.index).reindex(columns=weights.columns)
    # Apply execution delay: positions set at close on rebal date, earns from next bar
    eff_w = weights.shift(1).fillna(0.0)
    daily_pnl = (eff_w * ret_wide).sum(axis=1)
    return daily_pnl


def turnover_from_weights(weights: pd.DataFrame) -> pd.Series:
    # One-sided turnover per day (sum of abs weight changes)
    delta = weights.diff().fillna(weights).abs().sum(axis=1)
    return delta


def net_pnl(daily_pnl: pd.Series, turnover: pd.Series, bps_side: float) -> pd.Series:
    cost = turnover * (bps_side / 1e4)
    return daily_pnl - cost


def annualize(pnl: pd.Series) -> dict:
    p = pnl.dropna()
    if len(p) < 30:
        return {"sharpe": np.nan, "ret_ann": np.nan, "vol_ann": np.nan, "maxdd": np.nan, "n_days": len(p)}
    mu = p.mean() * 252
    sigma = p.std() * np.sqrt(252)
    sharpe = mu / sigma if sigma > 0 else np.nan
    eq = (1 + p).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    return {
        "sharpe": float(sharpe),
        "ret_ann": float(mu),
        "vol_ann": float(sigma),
        "maxdd": float(dd),
        "n_days": int(len(p)),
    }


def per_year_sharpe(pnl: pd.Series) -> dict:
    p = pnl.dropna()
    if p.empty:
        return {}
    years = p.index.year
    out = {}
    for y in sorted(set(years)):
        yp = p[p.index.year == y]
        if len(yp) < 30:
            out[int(y)] = {"sharpe": np.nan, "n": len(yp)}
            continue
        mu = yp.mean() * 252
        sigma = yp.std() * np.sqrt(252)
        out[int(y)] = {
            "sharpe": float(mu / sigma) if sigma > 0 else np.nan,
            "n": int(len(yp)),
        }
    return out


def best_year_out_sharpe(pnl: pd.Series) -> dict:
    p = pnl.dropna()
    if p.empty:
        return {"sharpe": np.nan, "dropped_year": None}
    years = sorted(set(p.index.year))
    sharpes = {}
    for y in years:
        rest = p[p.index.year != y]
        if len(rest) < 30:
            continue
        mu = rest.mean() * 252
        sigma = rest.std() * np.sqrt(252)
        sharpes[y] = mu / sigma if sigma > 0 else np.nan
    if not sharpes:
        return {"sharpe": np.nan, "dropped_year": None}
    best_dropped = min(sharpes, key=lambda y: sharpes[y])  # the year whose removal GIVES THE LOWEST remainder → is the "best year"
    return {
        "sharpe": float(sharpes[best_dropped]),
        "dropped_year": int(best_dropped),
        "all": {int(y): float(v) for y, v in sharpes.items()},
    }


# --------------------------------------------------------------------------- #
# Main driver
# --------------------------------------------------------------------------- #
def main() -> int:
    print("Loading data …")
    raw = load_panel()
    df = compute_features(raw)
    df = df[df["date"] >= COMMON_START].reset_index(drop=True)
    live_mask = df["is_live"]
    print(
        f"  panel: {len(df):,} rows, {df['symbol'].nunique()} symbols, "
        f"{df['date'].min().date()} → {df['date'].max().date()}, "
        f"{live_mask.sum():,} live rows ({live_mask.mean():.1%})"
    )

    all_specs = EXPRESSIONS + [PROBE]

    ic_rows = []
    decile_rows = []
    ls_rows = []
    lo_rows = []
    per_year_rows = []
    cost_rows = []
    validation = {}
    signal_panel = pd.DataFrame({"date": df["date"], "symbol": df["symbol"]})

    for spec in all_specs:
        sid = spec["id"]
        print(f"\n=== {sid} (k={spec['k']}, kind={spec['kind']}) ===")
        raw_sig = build_signal(df, spec)
        demean = demean_cross_sectional(raw_sig, df)
        signal_panel[sid] = demean.values

        # G1: non-degeneracy
        g1 = g1_non_degeneracy(raw_sig.where(live_mask))
        print(f"  G1 non-degeneracy: nonzero fraction = {g1['nonzero_fraction']:.4f}  pass={g1['pass']}")
        # Compute IC across all horizons
        ic_all = {}
        for k in HORIZONS_ALL:
            ic = compute_ic(demean.where(live_mask), df[f"target_{k}"], df["date"])
            ic_all[k] = ic
            ic_rows.append({
                "id": sid, "cluster": spec.get("cluster", "probe"),
                "horizon_k": k, "ic": ic["ic"], "ic_t": ic["ic_t"],
                "n_dates": ic["n_dates"],
            })
        target_k = spec["k"]
        print(
            f"  IC at own horizon k={target_k}: "
            f"{ic_all[target_k]['ic']:+.4f}  t={ic_all[target_k]['ic_t']:+.2f}  "
            f"(n_dates={ic_all[target_k]['n_dates']})"
        )

        # Quintiles at own horizon
        q = compute_quintile(demean.where(live_mask), df[f"target_{target_k}"], df["date"])
        q_row = {"id": sid, "horizon_k": target_k, **q}
        decile_rows.append(q_row)
        q_vals = [q.get(f"q{i}_mean", np.nan) for i in range(1, 6)]
        print(f"  Q1..Q5 means (k={target_k}): " + "  ".join(f"{v:+.4f}" if not np.isnan(v) else "nan" for v in q_vals))

        # Skip strategy backtest for audit probe
        if spec.get("kind") == "mom_probe":
            validation[sid] = {"g1": g1, "ic_own_horizon": ic_all[target_k]}
            continue

        # Four strategy wrappers
        strategies = [
            ("ls_top4_bot4_weekly",    {"long_n": 4, "short_n": 4, "hold_bars": 5}),
            ("ls_top4_bot4_monthly",   {"long_n": 4, "short_n": 4, "hold_bars": 20}),
            ("longonly_top3_weekly",   {"long_n": 3, "short_n": 0, "hold_bars": 5}),
            ("longonly_top3_monthly",  {"long_n": 3, "short_n": 0, "hold_bars": 20}),
        ]
        strat_pnls = {}
        for sname, cfg in strategies:
            w = dense_weekly_weights(demean, df, **cfg)
            daily = pnl_from_weights(w, df)
            to = turnover_from_weights(w)

            # Net Sharpe at 5 bps baseline
            net5 = net_pnl(daily, to, 5.0)
            ann = annualize(net5)
            ann_gross = annualize(daily)
            turn_ann = float(to.sum() / max(1, (len(to) / 252)))
            row = {
                "id": sid, "strategy": sname,
                "gross_sharpe": ann_gross["sharpe"], "gross_ret": ann_gross["ret_ann"],
                "net_sharpe_5bps": ann["sharpe"], "net_ret_5bps": ann["ret_ann"],
                "vol_ann": ann["vol_ann"], "maxdd": ann["maxdd"],
                "turnover_ann": turn_ann, "n_days": ann["n_days"],
            }
            if sname.startswith("ls"):
                ls_rows.append(row)
            else:
                lo_rows.append(row)

            # Cost sensitivity
            for bps in COST_GRID_BPS:
                net = net_pnl(daily, to, bps)
                a = annualize(net)
                cost_rows.append({
                    "id": sid, "strategy": sname, "cost_bps": bps,
                    "net_sharpe": a["sharpe"], "net_ret": a["ret_ann"],
                })
            # Per-year Sharpe
            py = per_year_sharpe(net5)
            for yr, d in py.items():
                per_year_rows.append({
                    "id": sid, "strategy": sname, "year": yr,
                    "sharpe_net_5bps": d["sharpe"], "n_days": d["n"],
                })
            strat_pnls[sname] = {"daily": daily, "net5": net5, "turnover": to}
            print(
                f"    {sname:28s}  gross_Sh={ann_gross['sharpe']:+.3f}  net5_Sh={ann['sharpe']:+.3f}  "
                f"MaxDD={ann['maxdd']:+.2%}  turn_ann={turn_ann:.0f}%"
            )

        # Save the best strategy's daily pnl and weights for this expression
        best_sname = max(strat_pnls.keys(), key=lambda s: (annualize(strat_pnls[s]["net5"])["sharpe"] or -99))
        strat_pnls[best_sname]["net5"].to_csv(OUT / f"pnl_{sid}_{best_sname}.csv", header=["pnl_net_5bps"])
        validation[sid] = {
            "g1": g1,
            "ic_own_horizon": ic_all[target_k],
            "ic_k60": ic_all[60],
            "best_strategy": best_sname,
            "best_net_sharpe_5bps": annualize(strat_pnls[best_sname]["net5"])["sharpe"],
            "best_maxdd": annualize(strat_pnls[best_sname]["net5"])["maxdd"],
        }

    # ---------------- Write CSVs / JSON ----------------
    pd.DataFrame(ic_rows).to_csv(OUT / "ic_table_batch_0001.csv", index=False)
    pd.DataFrame(decile_rows).to_csv(OUT / "decile_summary_batch_0001.csv", index=False)
    pd.DataFrame(ls_rows).to_csv(OUT / "ls_summary_batch_0001.csv", index=False)
    pd.DataFrame(lo_rows).to_csv(OUT / "longonly_summary_batch_0001.csv", index=False)
    pd.DataFrame(per_year_rows).to_csv(OUT / "per_year_sharpe_batch_0001.csv", index=False)
    pd.DataFrame(cost_rows).to_csv(OUT / "cost_sensitivity_batch_0001.csv", index=False)
    with open(OUT / "validation_gates_batch_0001.json", "w") as f:
        json.dump(validation, f, indent=2, default=float)
    signal_panel.to_parquet(OUT / "signal_panel.parquet", index=False)

    print("\n✅ Batch 0001 complete. Outputs:")
    for p in sorted(OUT.glob("*_batch_0001.*")) + [OUT / "signal_panel.parquet"]:
        print("   ", p.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
