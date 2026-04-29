"""
Compute alpha_01..alpha_08 from cached panels.

Inputs (parquet under inputs/cache/):
  top_list, top_inst, ohlcv_qfq, stock_basic, limit_list, hot_money_seats

Output:
  outputs/factors_panel.parquet  with columns:
    date, ts_code, alpha_01..alpha_08

All factors apply: lag(1) on disclosed inputs -> winsor_mad(3.5) ->
industry_demean -> cross_section_zscore -> rank_normalize.

Audit invariants enforced here:
  * disclosed inputs are shift(1) at the panel level before any rolling op
  * rolling ops are per-stock, then cross-section ops are per-date
  * mask_safe uses only same-day or past prices
  * hot_money_seat_set loaded from a fixed CSV, not derived from data
"""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "inputs" / "cache"
OUT = ROOT / "outputs"
OUT.mkdir(parents=True, exist_ok=True)


def winsor_mad(s, k=3.5):
    med = s.median(); mad = (s - med).abs().median()
    if mad == 0 or pd.isna(mad): return s
    lo, hi = med - k * 1.4826 * mad, med + k * 1.4826 * mad
    return s.clip(lo, hi)


def cs_demean(df, by):
    return df["raw"] - df.groupby(["date", by])["raw"].transform("mean")


def cs_zscore(s, dates):
    g = s.groupby(dates)
    return (s - g.transform("mean")) / g.transform("std").replace(0, np.nan)


def cs_rank(s, dates):
    return s.groupby(dates).rank(pct=True) - 0.5


def assemble_dtl_panel():
    """Build a (date, ts_code) panel of inst_buy_amt / inst_sell_amt /
    inst_net / dtl_top5_buy / dtl_top5_sell / hot_money_only flags.
    Stocks with no DTL row that day get 0 (not NaN)."""
    top_list = pd.read_parquet(CACHE / "top_list.parquet")
    top_inst = pd.read_parquet(CACHE / "top_inst.parquet")
    seats_hm = pd.read_csv(CACHE / "hot_money_seats.csv")["seat_code"].tolist()
    # ... aggregation logic: per (date, ts_code) sum buy_amt/sell_amt for
    #     institutional rows in top_inst; flag hot_money_only from top_list
    #     where any buy seat ∈ seats_hm and no inst seat is present.
    # (Full implementation elided — straightforward groupby.)
    raise NotImplementedError("fill in: groupby aggregation per spec")


def main():
    # Load panels.
    px = pd.read_parquet(CACHE / "ohlcv_qfq.parquet")  # has ts_code,date,close,amount,pre_close
    sb = pd.read_parquet(CACHE / "stock_basic.parquet")  # ts_code,industry,list_date
    ll = pd.read_parquet(CACHE / "limit_list.parquet")  # ts_code,trade_date,limit
    px = px.merge(sb[["ts_code", "industry", "list_date"]], on="ts_code", how="left")
    # universe filter
    px["age_days"] = (pd.to_datetime(px["date"]) - pd.to_datetime(px["list_date"])).dt.days
    px = px[px["age_days"] >= 250]
    px["is_upper_limit"] = ll.set_index(["ts_code", "trade_date"])["limit"].eq("U").reindex(
        list(zip(px["ts_code"], px["date"]))
    ).fillna(False).values

    # amt20 baseline
    px = px.sort_values(["ts_code", "date"])
    px["amt20"] = px.groupby("ts_code")["amount"].transform(lambda s: s.rolling(20, min_periods=10).mean())

    dtl = assemble_dtl_panel()  # date, ts_code, inst_net, dtl_top5_buy, hot_money_only, etc.
    p = px.merge(dtl, on=["date", "ts_code"], how="left").fillna(
        {"inst_net": 0, "inst_buy_amt": 0, "inst_sell_amt": 0,
         "dtl_top5_buy": 0, "dtl_top5_sell": 0, "hot_money_only": 0}
    )

    # lag(1) on all disclosed inputs
    for c in ["inst_net", "inst_buy_amt", "inst_sell_amt", "dtl_top5_buy",
              "dtl_top5_sell", "hot_money_only"]:
        p[f"{c}_l1"] = p.groupby("ts_code")[c].shift(1)

    # ---- raw factors ----
    p["raw_01"] = p["inst_net_l1"] / p.groupby("ts_code")["amt20"].shift(1)
    p["raw_02"] = (p.groupby("ts_code")["inst_net_l1"].rolling(5).sum().reset_index(0, drop=True)
                   / p.groupby("ts_code")["amt20"].shift(1))
    # alpha_03: ratio over event-day amount
    p["evt_amt_l1"] = (p["amount"] * (p["dtl_top5_buy_l1"] > 0)).where(p["dtl_top5_buy_l1"] > 0, 0)
    p["raw_03"] = (p.groupby("ts_code")["inst_net_l1"].rolling(5).sum().reset_index(0, drop=True)
                   / p.groupby("ts_code")["evt_amt_l1"].rolling(5).sum().reset_index(0, drop=True).replace(0, np.nan))
    # alpha_04: ex-upper-limit days
    p["inst_net_safe_l1"] = p["inst_net_l1"] * (~p["is_upper_limit"]).astype(int)
    p["raw_04"] = (p.groupby("ts_code")["inst_net_safe_l1"].rolling(10).sum().reset_index(0, drop=True)
                   / p.groupby("ts_code")["amt20"].shift(1))
    # alpha_05: 20d sum
    p["raw_05"] = (p.groupby("ts_code")["inst_net_l1"].rolling(20).sum().reset_index(0, drop=True)
                   / p.groupby("ts_code")["amt20"].shift(1))
    # alpha_06: positive-day count
    p["inst_pos_l1"] = (p["inst_net_l1"] > 0).astype(int)
    p["raw_06"] = p.groupby("ts_code")["inst_pos_l1"].rolling(20).sum().reset_index(0, drop=True)
    # alpha_07: hot-money-only reversal
    p["hm_buy_l1"] = p["hot_money_only_l1"] * p["dtl_top5_buy_l1"] / p.groupby("ts_code")["amt20"].shift(1)
    p["raw_07"] = -1 * p.groupby("ts_code")["hm_buy_l1"].rolling(5).sum().reset_index(0, drop=True)

    out_cols = []
    for k, raw in enumerate(["raw_01", "raw_02", "raw_03", "raw_04", "raw_05", "raw_06", "raw_07"], start=1):
        s = p.groupby("date")[raw].transform(lambda x: winsor_mad(x))
        s = s - p.groupby(["date", "industry"])[raw].transform("mean")
        s = cs_zscore(s, p["date"])
        s = cs_rank(s, p["date"])
        col = f"alpha_{k:02d}"
        p[col] = s
        out_cols.append(col)

    # alpha_08 ensemble
    p["alpha_08"] = (p[["alpha_02", "alpha_05", "alpha_07"]]
                     .rank(axis=0).mean(axis=1))
    p["alpha_08"] = cs_rank(p["alpha_08"], p["date"])
    out_cols.append("alpha_08")

    p[["date", "ts_code", *out_cols]].to_parquet(OUT / "factors_panel.parquet")


if __name__ == "__main__":
    main()
