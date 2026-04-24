#!/usr/bin/env python3
"""
Round 2 — long-only worst-year rescue variants.

Baseline:  r1_rev_40d  (=-logret_40d, demean-by-date)  →  long-only top-3 monthly
            Sh 0.774, 2023 Sh -0.585, MaxDD -42.4%

Directions:
  D1 regime_gated_breadth     — only hold when universe breadth40d > 0.30
  D1b regime_gated_200d_mom   — only hold when universe EW index 200d-mom > 0
  D2 ensemble_k40_k80         — 50/50 blend of top-3 long-only from k=40 and k=80
  D3 stoploss_20d_low         — intra-period stop: if holding breaks 20d low, exit
  D4 dispersion_conditional   — only trade when xs std of 40d returns > rolling 252d Q75
  D5 double_gate_D1_plus_D4   — both regime (breadth>0.30) AND dispersion>Q75 required

Outputs:
  outputs/round2/r2_all_equity_curves.csv
  outputs/round2/r2_headline_summary.csv
  outputs/round2/r2_per_year_sharpe.csv
  outputs/round2/r2_cost_sensitivity.csv
  outputs/round2/r2_gate_activity.csv
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

SESSION = Path("/home/user/Factor_Zoo/logs/20260424_a_share_etf_reversal_v2")
OUT = SESSION / "outputs" / "round2"
OUT.mkdir(exist_ok=True, parents=True)

DATA_SRC = Path(
    "/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs/etf_daily.parquet"
)
COMMON_START = pd.Timestamp("2019-01-04")
STAGGERED_JOIN_BARS = 60
COST_GRID_BPS = [0, 5, 10, 15]


# --------------------------------------------------------------------------- #
# Panel + features
# --------------------------------------------------------------------------- #
def load_panel() -> pd.DataFrame:
    df = pd.read_parquet(DATA_SRC)
    df = df.rename(columns={"trade_date": "date", "ts_code": "symbol"})
    df = df[["date", "symbol", "etf_name", "close_adj", "vol"]].copy()
    df = df.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"]).reset_index(drop=True)
    return df


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for k in [5, 20, 40, 80, 200]:
        df[f"logret_{k}d"] = df.groupby("symbol")["close_adj"].transform(
            lambda s, k=k: np.log(s / s.shift(k))
        )
    # rolling 20d low (for stop-loss)
    df["low20"] = df.groupby("symbol")["close_adj"].transform(
        lambda s: s.rolling(20, min_periods=10).min()
    )
    df["bar_age"] = df.groupby("symbol").cumcount()
    df["is_live"] = df["bar_age"] >= STAGGERED_JOIN_BARS
    return df


def regime_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-date regime features:
      breadth40       = fraction of live ETFs with positive 40d return
      ew_mom_200d     = mean of live ETFs' 200d log return
      disp40          = std of live ETFs' 40d log return
    """
    live = df[df["is_live"]].copy()
    g = live.groupby("date")
    reg = pd.DataFrame({
        "breadth40": g["logret_40d"].apply(lambda s: (s > 0).sum() / max(1, s.notna().sum())),
        "ew_mom_200d": g["logret_200d"].mean(),
        "disp40": g["logret_40d"].std(),
    })
    reg = reg.reindex(sorted(df["date"].unique())).ffill()
    # 252d rolling percentile of disp40
    reg["disp40_q75_roll252"] = reg["disp40"].rolling(252, min_periods=60).quantile(0.75)
    return reg


# --------------------------------------------------------------------------- #
# Signal & weights
# --------------------------------------------------------------------------- #
def demean_signal(df: pd.DataFrame, col: str) -> pd.Series:
    live = df["is_live"]
    sig = df[col].where(live)
    per_date_mean = sig.groupby(df["date"]).transform("mean")
    return sig - per_date_mean


def monthly_rebal_dates(all_dates: pd.DatetimeIndex, dow: int = 4, every_n: int = 4) -> pd.DatetimeIndex:
    d = pd.DatetimeIndex(sorted(all_dates))
    fridays = d[d.dayofweek == dow]
    return fridays[::every_n]


def long_only_top3_weights(
    sig_demean: pd.Series, df: pd.DataFrame, rebals: pd.DatetimeIndex, long_n: int = 3,
    regime_mask: pd.Series | None = None,
) -> pd.DataFrame:
    """
    Dense weights matrix. At each rebal date:
      - if regime_mask available and that date's regime is off → zero weights
      - else top-N by signal.
    Carried forward (ffill) between rebalances.
    """
    panel = pd.DataFrame({
        "date": df["date"].values, "symbol": df["symbol"].values,
        "s": sig_demean.values, "live": df["is_live"].values,
    })
    all_dates = sorted(panel["date"].unique())
    symbols = sorted(panel["symbol"].unique())
    w = pd.DataFrame(0.0, index=pd.DatetimeIndex(rebals), columns=symbols)
    panel_idx = panel.set_index(["date", "symbol"])

    # Precompute regime lookup
    if regime_mask is not None:
        regime_mask = regime_mask.reindex(all_dates).ffill().fillna(False)

    for dt in rebals:
        if regime_mask is not None and not bool(regime_mask.get(dt, False)):
            continue
        try:
            slice_df = panel_idx.xs(dt, level="date")
        except KeyError:
            continue
        slice_df = slice_df.dropna(subset=["s"])
        slice_df = slice_df[slice_df["live"]]
        if len(slice_df) < long_n * 2:
            continue
        ranked = slice_df["s"].sort_values(ascending=False)
        longs = ranked.iloc[:long_n].index.tolist()
        w.loc[dt, longs] = 1.0 / long_n

    w_full = w.reindex(pd.DatetimeIndex(all_dates)).ffill().fillna(0.0)
    return w_full


def apply_stoploss_20d_low(
    weights: pd.DataFrame, df: pd.DataFrame, rebals: pd.DatetimeIndex
) -> pd.DataFrame:
    """
    Intra-period stop: if a held ETF's close crosses below its 20d low on any
    bar, zero that symbol's weight from that bar forward, until the next rebal.
    """
    w = weights.copy()
    # wide matrices
    close_wide = df.pivot_table(index="date", columns="symbol", values="close_adj").reindex(w.index).reindex(columns=w.columns)
    low20_wide = df.pivot_table(index="date", columns="symbol", values="low20").reindex(w.index).reindex(columns=w.columns)
    # stop condition: close <= 20d low (equality handled by <=)
    stop_hit = (close_wide <= low20_wide).fillna(False)

    # Reset stop flags on each rebal date (new holdings start fresh)
    rebal_set = set(rebals)
    current_stop = pd.Series(False, index=w.columns)
    date_index = w.index.tolist()
    new_w = w.copy()
    # For each day: carry forward a "stopped" flag per symbol; reset to False on rebal
    stop_flags = pd.DataFrame(False, index=w.index, columns=w.columns)
    for dt in date_index:
        if dt in rebal_set:
            current_stop = pd.Series(False, index=w.columns)
        current_stop = current_stop | stop_hit.loc[dt]
        stop_flags.loc[dt] = current_stop.values
    new_w = w.where(~stop_flags, 0.0)
    return new_w


def ensemble_50_50_weights(
    w1: pd.DataFrame, w2: pd.DataFrame
) -> pd.DataFrame:
    return 0.5 * w1 + 0.5 * w2


# --------------------------------------------------------------------------- #
# PnL + metrics
# --------------------------------------------------------------------------- #
def pnl_from_weights(weights: pd.DataFrame, df: pd.DataFrame) -> pd.Series:
    ret_wide = df.pivot_table(index="date", columns="symbol", values="close_adj")
    ret_wide = ret_wide.pct_change().reindex(weights.index).reindex(columns=weights.columns)
    eff_w = weights.shift(1).fillna(0.0)
    return (eff_w * ret_wide).sum(axis=1)


def turnover_from_weights(weights: pd.DataFrame) -> pd.Series:
    return weights.diff().fillna(weights).abs().sum(axis=1)


def annualize(pnl: pd.Series) -> dict:
    p = pnl.dropna()
    if len(p) < 30:
        return {"sharpe": np.nan, "ret_ann": np.nan, "vol_ann": np.nan, "maxdd": np.nan, "n_days": len(p)}
    mu, sigma = p.mean() * 252, p.std() * np.sqrt(252)
    eq = (1 + p).cumprod()
    dd = float((eq / eq.cummax() - 1).min())
    return {
        "sharpe": float(mu / sigma) if sigma > 0 else np.nan,
        "ret_ann": float(mu), "vol_ann": float(sigma),
        "maxdd": dd, "n_days": int(len(p)),
    }


def per_year_sharpe(pnl: pd.Series) -> dict:
    p = pnl.dropna()
    out = {}
    for y in sorted(set(p.index.year)):
        yp = p[p.index.year == y]
        if len(yp) < 30:
            out[int(y)] = np.nan
            continue
        mu, sigma = yp.mean() * 252, yp.std() * np.sqrt(252)
        out[int(y)] = float(mu / sigma) if sigma > 0 else np.nan
    return out


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    print("Loading data & computing features …")
    raw = load_panel()
    df = compute_features(raw)
    df = df[df["date"] >= COMMON_START].reset_index(drop=True)
    reg = regime_signals(df)
    print(f"  panel: {len(df):,} rows, {df['symbol'].nunique()} symbols, "
          f"{df['date'].min().date()} → {df['date'].max().date()}")

    # ----- signals -----
    sig_40 = demean_signal(df.assign(neg40=-df["logret_40d"]), "neg40")
    sig_80 = demean_signal(df.assign(neg80=-df["logret_80d"]), "neg80")

    all_dates = pd.DatetimeIndex(sorted(df["date"].unique()))
    rebals_monthly = monthly_rebal_dates(all_dates, dow=4, every_n=4)
    print(f"  monthly rebals: {len(rebals_monthly)}")

    # ----- regime masks -----
    breadth_mask = (reg["breadth40"] > 0.30)
    mom200_mask = (reg["ew_mom_200d"] > 0)
    disp_mask = (reg["disp40"] > reg["disp40_q75_roll252"])
    double_mask = breadth_mask & disp_mask

    print(f"  regime breadth>0.30   ACTIVE on {int(breadth_mask.sum())}/{len(breadth_mask)} days "
          f"({breadth_mask.mean():.1%})")
    print(f"  regime mom200>0       ACTIVE on {int(mom200_mask.sum())}/{len(mom200_mask)} days "
          f"({mom200_mask.mean():.1%})")
    print(f"  regime disp>Q75       ACTIVE on {int(disp_mask.sum())}/{len(disp_mask)} days "
          f"({disp_mask.mean():.1%})")
    print(f"  regime (bread & disp) ACTIVE on {int(double_mask.sum())}/{len(double_mask)} days "
          f"({double_mask.mean():.1%})")

    # ----- build variants -----
    variants = {}

    # Baseline
    w_base = long_only_top3_weights(sig_40, df, rebals_monthly)
    variants["baseline_k40_monthly"] = w_base

    # D1 regime-gated by breadth
    variants["D1_regime_breadth"] = long_only_top3_weights(
        sig_40, df, rebals_monthly, regime_mask=breadth_mask
    )
    # D1b regime-gated by 200d mom
    variants["D1b_regime_mom200"] = long_only_top3_weights(
        sig_40, df, rebals_monthly, regime_mask=mom200_mask
    )

    # D2 ensemble k40 + k80
    w_40 = w_base
    w_80 = long_only_top3_weights(sig_80, df, rebals_monthly)
    variants["D2_ensemble_k40_k80"] = ensemble_50_50_weights(w_40, w_80)

    # D3 stop-loss 20d-low applied to baseline
    variants["D3_stoploss_20dlow"] = apply_stoploss_20d_low(w_base, df, rebals_monthly)

    # D4 dispersion conditional
    variants["D4_disp_gt_Q75"] = long_only_top3_weights(
        sig_40, df, rebals_monthly, regime_mask=disp_mask
    )

    # D5 double gate (breadth & disp)
    variants["D5_breadth_and_disp"] = long_only_top3_weights(
        sig_40, df, rebals_monthly, regime_mask=double_mask
    )

    # ----- compute metrics per variant -----
    headline_rows = []
    per_year_rows = []
    cost_rows = []
    equity_df = pd.DataFrame(index=all_dates)
    gate_activity = []

    for vname, w in variants.items():
        daily = pnl_from_weights(w, df)
        to = turnover_from_weights(w)

        # net@5bps as headline
        net5 = daily - to * (5.0 / 1e4)
        ann = annualize(net5)
        ann_gross = annualize(daily)
        py = per_year_sharpe(net5)
        # years summary
        worst_year = min(py, key=lambda y: py[y] if not np.isnan(py[y]) else 99)
        worst_y_sh = py[worst_year]

        turn_ann = float(to.sum() / max(1, len(to) / 252))
        # gate active pct
        nonzero_rebals = (w.loc[rebals_monthly].sum(axis=1).abs() > 1e-9).mean() if len(rebals_monthly) else np.nan

        headline_rows.append({
            "variant": vname,
            "gross_sharpe": ann_gross["sharpe"],
            "net_sharpe_5bps": ann["sharpe"],
            "net_ret_5bps": ann["ret_ann"],
            "vol_ann": ann["vol_ann"],
            "maxdd": ann["maxdd"],
            "worst_year": int(worst_year),
            "worst_year_sharpe": float(worst_y_sh),
            "turnover_ann": turn_ann,
            "gate_active_rebal_pct": float(nonzero_rebals),
            "n_days": ann["n_days"],
        })

        # per-year
        for yr, sh in py.items():
            per_year_rows.append({"variant": vname, "year": int(yr), "sharpe_net_5bps": float(sh)})

        # cost sensitivity
        for bps in COST_GRID_BPS:
            net = daily - to * (bps / 1e4)
            a = annualize(net)
            cost_rows.append({"variant": vname, "cost_bps": bps, "net_sharpe": a["sharpe"]})

        # equity curve
        equity_df[vname] = (1 + net5.fillna(0)).cumprod()

        gate_activity.append({"variant": vname, "gate_active_rebal_pct": float(nonzero_rebals)})

        print(f"\n  === {vname} ===")
        print(f"    gross Sh={ann_gross['sharpe']:+.3f}  net5 Sh={ann['sharpe']:+.3f}  "
              f"MaxDD={ann['maxdd']:+.2%}  turn_ann={turn_ann:.0f}%  "
              f"gate_active={nonzero_rebals:.1%}")
        print(f"    per year: " + "  ".join(f"{y}:{sh:+.2f}" for y, sh in sorted(py.items())))
        print(f"    worst year = {worst_year} Sh={worst_y_sh:+.3f}")

    # ----- write CSVs -----
    pd.DataFrame(headline_rows).to_csv(OUT / "r2_headline_summary.csv", index=False)
    pd.DataFrame(per_year_rows).to_csv(OUT / "r2_per_year_sharpe.csv", index=False)
    pd.DataFrame(cost_rows).to_csv(OUT / "r2_cost_sensitivity.csv", index=False)
    equity_df.to_csv(OUT / "r2_all_equity_curves.csv")
    pd.DataFrame(gate_activity).to_csv(OUT / "r2_gate_activity.csv", index=False)

    # ----- summary print: delta vs baseline -----
    base = next(r for r in headline_rows if r["variant"] == "baseline_k40_monthly")
    print("\n\n===== Delta vs baseline (r1_rev_40d long-only top-3 monthly) =====")
    print(f"  baseline: net5 Sh {base['net_sharpe_5bps']:+.3f}  worst {base['worst_year']} Sh {base['worst_year_sharpe']:+.3f}  MaxDD {base['maxdd']:+.2%}")
    for r in headline_rows:
        if r["variant"] == "baseline_k40_monthly":
            continue
        d_sh = r["net_sharpe_5bps"] - base["net_sharpe_5bps"]
        d_wy = r["worst_year_sharpe"] - base["worst_year_sharpe"]
        d_dd = r["maxdd"] - base["maxdd"]
        print(f"  {r['variant']:28s}  Sh={r['net_sharpe_5bps']:+.3f} ({d_sh:+.3f})  "
              f"worst {r['worst_year']} Sh={r['worst_year_sharpe']:+.3f} ({d_wy:+.3f})  "
              f"MaxDD={r['maxdd']:+.2%} ({d_dd:+.2%})  turn={r['turnover_ann']:.0f}%  gate={r['gate_active_rebal_pct']:.0%}")

    print("\n✅ Round 2 complete. Outputs:")
    for p in sorted(OUT.glob("r2_*")):
        print("   ", p.name)
    return 0


if __name__ == "__main__":
    main()
