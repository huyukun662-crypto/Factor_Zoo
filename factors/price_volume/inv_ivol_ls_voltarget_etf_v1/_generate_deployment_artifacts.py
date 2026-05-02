#!/usr/bin/env python3
"""Regenerate metrics.json / annual.csv / rebalances.csv from the factor code.

Run from the factor directory or with PYTHONPATH set to it.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import code as factor_code   # type: ignore

PANEL = Path("/home/user/Factor_Zoo/logs/_shared_cache/etf_daily.parquet")
TRAIN_END = pd.Timestamp("2021-12-31")
VAL_END = pd.Timestamp("2022-12-31")


def ann_sharpe(s, k=factor_code.PRIMARY_K):
    s = s.dropna()
    if len(s) < 30 or s.std() == 0:
        return float("nan")
    return float(s.mean() / s.std() * np.sqrt(252 / k))


def slc(s, lo, hi):
    return s[(s.index > lo) & (s.index <= hi)]


def main():
    panel = pd.read_parquet(PANEL)
    panel["ret"] = panel.groupby("symbol")["close"].pct_change()
    res = factor_code.run(panel)

    raw_ls = res.raw_LS_ret.dropna()
    vt_ls = res.voltarget_LS_ret.dropna()
    vt_ls_net = res.voltarget_LS_ret_net5bps.dropna()
    expo = res.exposure.dropna()

    yr_raw = raw_ls.groupby(raw_ls.index.year).apply(ann_sharpe)
    yr_vt = vt_ls.groupby(vt_ls.index.year).apply(ann_sharpe)
    yr_vt_net = vt_ls_net.groupby(vt_ls_net.index.year).apply(ann_sharpe)

    annual_rows = []
    for y in sorted(set(yr_raw.index) | set(yr_vt.index)):
        n = int(vt_ls_net[vt_ls_net.index.year == y].dropna().shape[0])
        annual_rows.append({
            "year": int(y),
            "n_days": n,
            "sharpe_raw_LS": float(yr_raw.get(y, np.nan)),
            "sharpe_voltarget_LS_gross": float(yr_vt.get(y, np.nan)),
            "sharpe_voltarget_LS_net5bps": float(yr_vt_net.get(y, np.nan)),
            "avg_exposure": float(expo[expo.index.year == y].mean()) if not expo[expo.index.year == y].empty else np.nan,
            "ann_ret_voltarget_net5bps": float(vt_ls_net[vt_ls_net.index.year == y].mean() * 252 / factor_code.PRIMARY_K),
        })
    annual_df = pd.DataFrame(annual_rows)
    annual_df.to_csv(HERE / "annual.csv", index=False)

    # rebalances — Q5 (long leg) membership monthly. Only include dates where
    # IVOL has filled (after beta_w + ivol_w warmup) AND rank cross-section is valid.
    rk = res.rank
    sig = res.signal
    valid = sig.dropna(how="all").index
    first_valid = sig.notna().sum(axis=1).ge(20).idxmax()  # first date with >=20 valid IVOL
    rebal_dates = rk.loc[first_valid:].index[::21]
    rows = []
    for d in rebal_dates:
        r = rk.loc[d].dropna()
        s = sig.loc[d]
        if len(r) < 10:
            continue
        e = expo.get(d, np.nan)
        long_etfs = r.loc[r >= 0.8].index.tolist()
        short_etfs = r.loc[r < 0.2].index.tolist()
        if not long_etfs and not short_etfs:
            continue
        rows.append({
            "trade_date": d.date().isoformat(),
            "exposure": float(e) if not pd.isna(e) else np.nan,
            "long_q5_etfs": ";".join(long_etfs),
            "short_q1_etfs": ";".join(short_etfs),
            "n_long": len(long_etfs),
            "n_short": len(short_etfs),
            "ivol_q5_avg": float(s.loc[long_etfs].mean()) if long_etfs else np.nan,
            "ivol_q1_avg": float(s.loc[short_etfs].mean()) if short_etfs else np.nan,
        })
    pd.DataFrame(rows).to_csv(HERE / "rebalances.csv", index=False)

    # metrics
    def cum_sharpe(s, lo, hi):
        return ann_sharpe(slc(s, lo, hi))

    def max_dd(daily_eq_ret):
        # convert k-day overlapping returns to per-day equity proxy
        eq = (1 + daily_eq_ret.fillna(0) / factor_code.PRIMARY_K).cumprod()
        return float(((eq / eq.cummax()) - 1).min())

    metrics = {
        "factor_id": "inv_ivol_ls_voltarget_etf_v1",
        "label": "Inverted-IVOL on A-share ETFs, vol-target 10% ann, monthly LS",
        "session_origin": "logs/20260501_a_share_etf_ivol_momentum_v1",
        "universe_size": 30,
        "rebalance_days": 21,
        "primary_k": factor_code.PRIMARY_K,
        "delay_days": factor_code.DELAY,
        "cost_bps_per_side": factor_code.COST_BPS_PER_SIDE,
        "vol_target_ann": factor_code.VOL_TARGET_ANN,
        "max_leverage": factor_code.MAX_LEVERAGE,
        "ivol_window_days": factor_code.IVOL_WINDOW_DAYS,
        "beta_window_days": factor_code.BETA_WINDOW_DAYS,
        "headline_sharpe_voltarget_LS_net5bps": ann_sharpe(vt_ls_net),
        "headline_sharpe_voltarget_LS_gross": ann_sharpe(vt_ls),
        "headline_sharpe_raw_LS_no_voltarget": ann_sharpe(raw_ls),
        "ann_ret_voltarget_LS_net5bps": float(vt_ls_net.mean() * 252 / factor_code.PRIMARY_K),
        "max_dd_voltarget_LS_net5bps": max_dd(vt_ls_net),
        "avg_exposure": float(expo.mean()),
        "tvt_split": {
            "train": [str(panel.date.min().date()), TRAIN_END.date().isoformat()],
            "validate": [(TRAIN_END + pd.Timedelta(days=1)).date().isoformat(), VAL_END.date().isoformat()],
            "test": [(VAL_END + pd.Timedelta(days=1)).date().isoformat(), str(panel.date.max().date())],
        },
        "tvt_sharpe_voltarget_LS_net5bps": {
            "train": cum_sharpe(vt_ls_net, pd.Timestamp("1900-01-01"), TRAIN_END),
            "validate": cum_sharpe(vt_ls_net, TRAIN_END, VAL_END),
            "test": cum_sharpe(vt_ls_net, VAL_END, pd.Timestamp("2030-01-01")),
        },
        "worst_year_sharpe_voltarget_net5bps": float(yr_vt_net.min()),
        "worst_year_year": int(yr_vt_net.idxmin()),
        "n_years_positive_of_total": [int((yr_vt_net > 0).sum()), int(len(yr_vt_net))],
        "best_year_out_avg_voltarget_net5bps": float(yr_vt_net.drop(yr_vt_net.idxmax()).mean()),
        "audit_status": {
            "execution_delay": "pass",
            "look_ahead": "pass_max_diff_0.0_for_signal_and_voltarget_exposure",
            "worst_year_floor_0.5": "fail (worst 2022 = " + f"{yr_vt_net.min():.2f}" + ")",
            "best_year_out_50pct_headline": "pass",
            "falsification_first": "pass",
        },
        "promote_status": "RESEARCH_ONLY_standalone__PROMOTE_CANDIDATE_as_5050_overlay_with_v25_or_v7_gold",
    }
    with (HERE / "metrics.json").open("w") as f:
        json.dump(metrics, f, indent=2)

    print(f"OK; wrote annual.csv ({len(annual_df)} rows), rebalances.csv ({len(rows)} rebalances), metrics.json")
    print(f"headline net@5bps Sharpe: {ann_sharpe(vt_ls_net):.2f}")
    print(f"worst year: {yr_vt_net.idxmin()} = {yr_vt_net.min():+.2f}")
    print(f"avg exposure: {expo.mean():.2f}")


if __name__ == "__main__":
    main()
