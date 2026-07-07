"""Compute alpha_01..alpha_08 with lag(1) on disclosed inputs, industry demean, rank."""
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"


def winsor_mad(s, k=3.5):
    s = s.astype(float); med = s.median(); mad = (s - med).abs().median()
    if not np.isfinite(mad) or mad == 0: return s
    lo, hi = med - k * 1.4826 * mad, med + k * 1.4826 * mad
    return s.clip(lo, hi)


def cs_pipeline(panel, raw_col):
    """winsor by date -> industry demean -> cs zscore -> cs rank (centered)."""
    s = panel.groupby("trade_date")[raw_col].transform(winsor_mad)
    ind_mean = panel.assign(_x=s).groupby(["trade_date", "industry"])["_x"].transform("mean")
    s = s - ind_mean
    g = s.groupby(panel["trade_date"])
    s = (s - g.transform("mean")) / g.transform("std").replace(0, np.nan)
    s = s.groupby(panel["trade_date"]).rank(pct=True) - 0.5
    return s


def main():
    p = pd.read_parquet(OUT / "panel.parquet").sort_values(["ts_code", "trade_date"]).reset_index(drop=True)

    g = p.groupby("ts_code")
    for c in ["inst_net", "inst_buy_amt", "inst_sell_amt",
              "dtl_top5_buy", "dtl_top5_sell", "hot_money_only", "dtl_event"]:
        p[f"{c}_l1"] = g[c].shift(1)
    p["amt20_l1"] = g["amt20"].shift(1)
    p["close_qfq_l1"] = g["adj_close"].shift(1)
    p["is_ulim_l1"] = g["is_upper_limit"].shift(1).fillna(False)

    g2 = p.groupby("ts_code")
    p["raw_01"] = p["inst_net_l1"] / p["amt20_l1"]
    p["raw_02"] = g2["inst_net_l1"].rolling(5, min_periods=2).sum().reset_index(0, drop=True) / p["amt20_l1"]

    # event-amount denominator
    evt_amt_l1 = (p["amount"].shift(1) * (p["dtl_event_l1"] > 0)).fillna(0)
    num03 = g2["inst_net_l1"].rolling(5, min_periods=2).sum().reset_index(0, drop=True)
    den03 = evt_amt_l1.groupby(p["ts_code"]).rolling(5, min_periods=1).sum().reset_index(0, drop=True)
    p["raw_03"] = num03 / den03.replace(0, np.nan)

    inst_safe = p["inst_net_l1"] * (~p["is_ulim_l1"]).astype(int)
    p["raw_04"] = inst_safe.groupby(p["ts_code"]).rolling(10, min_periods=3).sum().reset_index(0, drop=True) / p["amt20_l1"]

    p["raw_05"] = g2["inst_net_l1"].rolling(20, min_periods=5).sum().reset_index(0, drop=True) / p["amt20_l1"]

    inst_pos = (p["inst_net_l1"] > 0).astype(int)
    p["raw_06"] = inst_pos.groupby(p["ts_code"]).rolling(20, min_periods=5).sum().reset_index(0, drop=True)

    hm_buy = p["hot_money_only_l1"] * p["dtl_top5_buy_l1"] / p["amt20_l1"]
    p["raw_07"] = -1 * hm_buy.groupby(p["ts_code"]).rolling(5, min_periods=2).sum().reset_index(0, drop=True)

    cols = []
    for k in range(1, 8):
        col = f"alpha_{k:02d}"
        p[col] = cs_pipeline(p, f"raw_{k:02d}")
        cols.append(col)

    # alpha_08: ensemble of alpha_02, alpha_05, alpha_07 (cross-section rank average)
    ens = (p[["alpha_02", "alpha_05", "alpha_07"]].mean(axis=1))
    p["alpha_08"] = ens.groupby(p["trade_date"]).rank(pct=True) - 0.5
    cols.append("alpha_08")

    out = p[["trade_date", "ts_code", "industry", "adj_close", "amount",
             "is_upper_limit", "amt20", "dtl_event", "inst_net"] + cols].copy()
    out.to_parquet(OUT / "factors_panel.parquet")
    coverage = (out[cols].notna() & (out[cols] != 0)).sum() / len(out)
    print("nonzero/notna coverage per alpha:")
    print(coverage)


if __name__ == "__main__":
    main()
