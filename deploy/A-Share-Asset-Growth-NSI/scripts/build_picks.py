"""
Build current-month Q5 picks for the r3_ag_orth_nsi factor.

Factor formula
--------------
1. Quarterly fundamentals (PIT-safe via f_ann_date + 1 trading day):
       AG_2y_q  = -(TA_t - TA_{t-8q}) / TA_{t-8q}
       NSI_2y_q = -(Shares_t - Shares_{t-8q}) / Shares_{t-8q}
2. Industry-demean (median per [date, industry]).
3. Winsorize 1%/99% per date, then z-score per date  -> f5, g4
4. Per-date OLS residualize: ag_orth_nsi = f5 - (a + b*g4)
5. Blend: signal = z_winsor( 0.5 * ag_orth_nsi + 0.5 * g4 )
6. Top 20% (Q5) by signal; equal-weight; monthly rebalance; T+1 execution.

Backtest 2020-01 .. 2025-04 (post-cost 5 bps/side):
  Sharpe abs 0.70   CAGR 17.5%   5/6 years positive   worst year 2022 -0.4%
"""
from __future__ import annotations
import argparse, os, sys, time
from datetime import datetime
import numpy as np
import pandas as pd

DEFAULT_CACHE = "/home/user/Factor_Zoo/.cache"
DEFAULT_OUT   = "/home/user/Factor_Zoo/deploy/A-Share-Asset-Growth-NSI/picks"


def log(m: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)


def build_signal(cache_dir: str, asof: pd.Timestamp) -> pd.DataFrame:
    """
    Build the full signal for the universe as of `asof`.
    Returns DataFrame with [ts_code, industry, total_mv, signal] for stocks tradable
    on `asof` and with valid PIT fundamentals.
    """
    # 1. balance sheet → quarterly AG and NSI (2-year window)
    log("loading balance sheet")
    bs = pd.read_parquet(f"{cache_dir}/balancesheet.parquet")
    bs = bs.dropna(subset=["total_assets", "total_share", "end_date", "f_ann_date"]).copy()
    bs["f_ann_date"] = pd.to_datetime(bs["f_ann_date"].astype(str), errors="coerce")
    bs["end_date"]   = pd.to_datetime(bs["end_date"].astype(str),   errors="coerce")
    bs = bs.dropna(subset=["f_ann_date", "end_date"])
    bs = (bs.sort_values(["ts_code", "end_date", "f_ann_date"])
            .groupby(["ts_code", "end_date"], as_index=False).last())
    bs = bs.sort_values(["ts_code", "end_date"])

    bs["ta_lag_8q"] = bs.groupby("ts_code")["total_assets"].shift(8)
    bs["ts_lag_8q"] = bs.groupby("ts_code")["total_share"].shift(8)

    eps = 1e-8
    bs["ag_2y_q"]  = -(bs["total_assets"] - bs["ta_lag_8q"]) / (bs["ta_lag_8q"].abs() + eps)
    bs["nsi_2y_q"] = -(bs["total_share"]  - bs["ts_lag_8q"]) / (bs["ts_lag_8q"].abs() + eps)
    bs["signal_date"] = bs["f_ann_date"] + pd.Timedelta(days=1)

    # 2. for each ts_code, take the latest BS row whose signal_date <= asof
    bs = bs[bs["signal_date"] <= asof].copy()
    latest = (bs.sort_values(["ts_code", "signal_date"])
                .groupby("ts_code", as_index=False).last())
    latest = latest[["ts_code", "signal_date", "ag_2y_q", "nsi_2y_q"]].dropna()

    # 3. universe: from panel.parquet, keep stocks active on/near asof
    log("loading panel snapshot")
    panel = pd.read_parquet(f"{cache_dir}/panel.parquet",
        columns=["ts_code", "trade_date", "industry", "size_bin", "total_mv"])
    panel["trade_date"] = pd.to_datetime(panel["trade_date"])
    panel = panel[panel["trade_date"] <= asof]
    if len(panel) == 0:
        raise ValueError(f"No panel data on or before {asof}")
    snap_date = panel["trade_date"].max()
    snap = panel[panel["trade_date"] == snap_date].copy()
    log(f"panel snapshot date: {snap_date.date()}  ({len(snap)} stocks)")

    # 4. join PIT fundamentals
    df = snap.merge(latest, on="ts_code", how="left")
    df["staleness_days"] = (snap_date - df["signal_date"]).dt.days
    # drop rows without recent fundamentals
    pre_n = len(df)
    df = df.dropna(subset=["ag_2y_q", "nsi_2y_q"])
    df = df[df["staleness_days"] <= 365]   # most recent annual report still valid
    log(f"PIT join + staleness filter: {pre_n} -> {len(df)}")

    # 5. industry-demean by SW or coarse industry
    df["ag_2y_ind"]  = df["ag_2y_q"]  - df.groupby("industry")["ag_2y_q"].transform("median")
    df["nsi_2y_ind"] = df["nsi_2y_q"] - df.groupby("industry")["nsi_2y_q"].transform("median")

    # 6. winsorize 1%/99% then z-score (cross-sectional, single date)
    def winsor_z(s: pd.Series) -> pd.Series:
        lo, hi = s.quantile(0.01), s.quantile(0.99)
        s = s.clip(lo, hi)
        mu, sd = s.mean(), s.std()
        return (s - mu) / sd if sd and not np.isnan(sd) else s * 0

    df["f5"] = winsor_z(df["ag_2y_ind"])
    df["g4"] = winsor_z(df["nsi_2y_ind"])

    # 7. per-date OLS residualize f5 vs g4 (single date here)
    mask = df["f5"].notna() & df["g4"].notna()
    if mask.sum() < 30:
        raise ValueError("Not enough cross-section to residualize")
    b, a = np.polyfit(df.loc[mask, "g4"].values, df.loc[mask, "f5"].values, 1)
    df["ag_orth_nsi"] = df["f5"] - (a + b * df["g4"])

    # 8. blend and final z
    df["signal_raw"] = 0.5 * df["ag_orth_nsi"] + 0.5 * df["g4"]
    df["signal"]     = winsor_z(df["signal_raw"])
    # tie-breaker for selection: composite of winsor signal + tiny weight on raw (un-clipped)
    # ensures stocks tied at the winsor cap are ordered by the underlying continuous score.
    df["signal_tiebreak"] = df["signal"] + 1e-6 * df["signal_raw"]

    return df, snap_date


def select_top(df: pd.DataFrame, top_frac: float | None = None,
               top_n: int | None = None,
               min_mv_pct: float = 0.30) -> pd.DataFrame:
    """
    Pick the top stocks. Supports either fraction (Q5 = top 20%) or fixed N
    (e.g. top 100 for a deployable list).
    `min_mv_pct` filters out the smallest stocks by total_mv (default: bottom 30%)
    to avoid picks that are uninvestable due to liquidity. Set to 0 to disable.
    """
    df = df.dropna(subset=["signal"]).copy()
    if min_mv_pct > 0:
        mv_thr = df["total_mv"].quantile(min_mv_pct)
        df = df[df["total_mv"] >= mv_thr]
    n = len(df)
    if top_n is not None:
        n_top = min(top_n, n)
    else:
        frac = top_frac if top_frac is not None else 0.20
        n_top = max(1, int(round(n * frac)))
    picks = df.nlargest(n_top, "signal_tiebreak").copy()
    picks["weight"] = 1.0 / n_top
    return picks


def main() -> None:
    ap = argparse.ArgumentParser(description="Build r3_ag_orth_nsi monthly picks")
    ap.add_argument("--asof", default="today",
                    help="As-of date (YYYY-MM-DD). Default: today.")
    ap.add_argument("--cache", default=DEFAULT_CACHE, help="parquet cache dir")
    ap.add_argument("--out",   default=DEFAULT_OUT,   help="output directory")
    ap.add_argument("--top",   default=0.20, type=float,
                    help="top fraction (default 0.20 = Q5). Used only when --top-n omitted.")
    ap.add_argument("--top-n", default=None, type=int,
                    help="if set, pick exactly N stocks (e.g. 100 for a deployable list)")
    ap.add_argument("--min-mv-pct", default=0.30, type=float,
                    help="drop bottom X%% by total_mv (default 0.30). Set 0 to disable.")
    ap.add_argument("--also-q5", action="store_true",
                    help="also write the full Q5 (top 20%%) list alongside top-N")
    args = ap.parse_args()

    asof = pd.Timestamp.today().normalize() if args.asof == "today" else pd.Timestamp(args.asof)
    log(f"as-of {asof.date()}, cache={args.cache}, top_n={args.top_n}, top_frac={args.top}")

    df, snap_date = build_signal(args.cache, asof)
    os.makedirs(args.out, exist_ok=True)
    out_cols = ["ts_code", "industry", "size_bin", "total_mv",
                "ag_2y_q", "nsi_2y_q", "ag_orth_nsi", "g4", "signal", "weight"]

    written = []

    # primary list (top-N if specified, else Q5)
    primary = select_top(df, top_frac=args.top, top_n=args.top_n,
                         min_mv_pct=args.min_mv_pct)
    p_label = f"top{args.top_n}" if args.top_n else "q5"
    p_path = os.path.join(args.out, f"picks_{snap_date.date()}_{p_label}.csv")
    primary[out_cols].sort_values("signal", ascending=False).to_csv(p_path, index=False)
    log(f"wrote {len(primary)} picks -> {p_path}")
    written.append((p_label, p_path, primary))

    # optional secondary Q5 list
    if args.top_n and args.also_q5:
        q5 = select_top(df, top_frac=0.20, min_mv_pct=args.min_mv_pct)
        q5_path = os.path.join(args.out, f"picks_{snap_date.date()}_q5.csv")
        q5[out_cols].sort_values("signal", ascending=False).to_csv(q5_path, index=False)
        log(f"wrote {len(q5)} Q5 picks -> {q5_path}")
        written.append(("q5", q5_path, q5))

    # summary
    sum_path = os.path.join(args.out, "latest.txt")
    with open(sum_path, "w") as f:
        f.write(f"as_of: {snap_date.date()}\nfactor: r3_ag_orth_nsi\n")
        for label, path, picks in written:
            f.write(f"\n--- {label} ({len(picks)} stocks) ---\n")
            f.write(f"  file: {path}\n")
            f.write(f"  median total_mv: {picks['total_mv'].median():.0f}\n")
            f.write(f"  size_bin distribution: "
                    + picks['size_bin'].astype(str).value_counts().sort_index().to_dict().__str__()
                    + "\n")
            f.write(f"  top10 industries:\n")
            f.write(picks.groupby("industry").size().sort_values(ascending=False).head(10).to_string())
            f.write("\n")
    log(f"summary -> {sum_path}")
    log("DONE")


if __name__ == "__main__":
    main()
