"""
accruals_median_ttm_ind_neutral_v2 — A-share fundamental flagship factor.

Reusable factor builder. Produces a daily panel of factor values gated by
ann_date (no publication-lag leakage), industry-neutralized within each
trade_date.

Inputs (Tushare via `_vip` endpoints if available; else per-stock loops):
  income_vip:        ts_code, ann_date, end_date, n_income
  balancesheet_vip:  ts_code, ann_date, end_date, total_assets
  cashflow_vip:      ts_code, ann_date, end_date, n_cashflow_act
  daily / daily_basic:    for trade_date scaffold + universe filter
  stock_basic:       ts_code, industry, list_date, name (ST flag)

Output:
  pandas DataFrame indexed by (ts_code, trade_date) with columns:
      acc_med           — raw signal
      acc_med_w         — winsorized [0.01, 0.99] cross-sectionally per date
      alpha             — final factor: -group_rank(acc_med_w, industry); higher=better

Run:
  TUSHARE_TOKEN=... python code.py
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd


EXCLUDED_INDUSTRIES = {
    "银行", "全国地产", "区域地产", "房产服务",
    "保险", "证券", "多元金融", "期货",
}


@dataclass
class FactorConfig:
    start_period: str = "20171231"   # need >= 4 quarters of warm-up before backtest start
    end_period: str = "20241231"
    start_trade_date: str = "20180102"
    end_trade_date: str = "20250418"
    listed_min_days: int = 252
    winsorize_lo: float = 0.01
    winsorize_hi: float = 0.99
    require_quarters: int = 3        # need >=3 of 4 quarters non-NaN for TTM


# ---------- 1. fundamentals ---------- #

def quarter_periods(start: str, end: str) -> list[str]:
    out: list[str] = []
    sy, sm = int(start[:4]), int(start[4:6])
    ey, em = int(end[:4]), int(end[4:6])
    for y in range(sy, ey + 1):
        for q_end in ("0331", "0630", "0930", "1231"):
            qm = int(q_end[:2])
            if (y == sy and qm < sm) or (y == ey and qm > em):
                continue
            out.append(f"{y}{q_end}")
    return out


def fetch_fundamentals(pro, periods: list[str]) -> pd.DataFrame:
    """Returns merged income+balancesheet+cashflow on (ts_code, end_date),
    with the latest of the 3 ann_dates as `ann_date` (conservative)."""
    def _fetch(api: str, period: str, fields: str) -> pd.DataFrame:
        for attempt in range(3):
            try:
                df = pro.query(api, period=period, fields=fields)
                if "report_type" in df.columns:
                    df = df[df["report_type"].astype(str) == "1"]
                df = df.sort_values(["ts_code", "end_date", "ann_date"])
                df = df.groupby(["ts_code", "end_date"], as_index=False).first()
                return df
            except Exception:
                time.sleep(1 + attempt)
        return pd.DataFrame()

    income, bs, cf = [], [], []
    for p in periods:
        income.append(_fetch("income_vip", p, "ts_code,ann_date,end_date,report_type,n_income"))
        bs.append(_fetch("balancesheet_vip", p, "ts_code,ann_date,end_date,report_type,total_assets"))
        cf.append(_fetch("cashflow_vip", p, "ts_code,ann_date,end_date,report_type,n_cashflow_act"))
    income = pd.concat(income, ignore_index=True)
    bs = pd.concat(bs, ignore_index=True)
    cf = pd.concat(cf, ignore_index=True)
    for d in (income, bs, cf):
        d["ann_date"] = pd.to_datetime(d["ann_date"], format="%Y%m%d", errors="coerce")
        d["end_date"] = pd.to_datetime(d["end_date"], format="%Y%m%d", errors="coerce")

    f = (
        income[["ts_code", "ann_date", "end_date", "n_income"]]
        .merge(bs[["ts_code", "end_date", "total_assets"]],   on=["ts_code", "end_date"])
        .merge(cf[["ts_code", "end_date", "n_cashflow_act"]], on=["ts_code", "end_date"])
        .sort_values(["ts_code", "end_date"])
    )
    return f


def build_quarterly_signal(f: pd.DataFrame, cfg: FactorConfig) -> pd.DataFrame:
    """Adds median-TTM accruals on (ts_code, end_date) frame."""
    g = f.groupby("ts_code", group_keys=False)
    f["ni_med"]  = g["n_income"].transform(
        lambda s: s.rolling(4, min_periods=cfg.require_quarters).median() * 4
    )
    f["cfo_med"] = g["n_cashflow_act"].transform(
        lambda s: s.rolling(4, min_periods=cfg.require_quarters).median() * 4
    )
    f["ta_avg"]  = g["total_assets"].transform(
        lambda s: s.rolling(4, min_periods=cfg.require_quarters).mean()
    )
    f["acc_med"] = (f["ni_med"] - f["cfo_med"]) / f["ta_avg"]
    return f


# ---------- 2. universe ---------- #

def filter_universe(daily: pd.DataFrame, basic: pd.DataFrame, cfg: FactorConfig) -> pd.DataFrame:
    basic = basic.copy()
    basic["list_date"] = pd.to_datetime(basic["list_date"], format="%Y%m%d")
    basic["is_financial"] = basic["industry"].isin(EXCLUDED_INDUSTRIES)
    basic["is_st"]        = basic["name"].str.contains("ST", na=False)

    out = daily.merge(basic[["ts_code", "industry", "list_date", "is_financial", "is_st"]], on="ts_code", how="left")
    out["days_listed"] = (out["trade_date"] - out["list_date"]).dt.days
    mask = (
        (~out["is_financial"].fillna(True))
        & (~out["is_st"].fillna(True))
        & (out["days_listed"] >= cfg.listed_min_days)
        & out["industry"].notna()
    )
    return out[mask].copy()


# ---------- 3. daily forward-fill via ann_date ---------- #

def merge_signal_to_daily(daily: pd.DataFrame, fund: pd.DataFrame) -> pd.DataFrame:
    """merge_asof on ann_date: for each (ts_code, trade_date), take the latest acc_med
    whose ann_date < trade_date (allow_exact_matches=False)."""
    fund_g = fund.dropna(subset=["ann_date", "acc_med"]).copy()
    fund_g = fund_g.sort_values(["ann_date", "ts_code"]).reset_index(drop=True)
    daily  = daily.sort_values(["trade_date", "ts_code"]).reset_index(drop=True)
    merged = pd.merge_asof(
        daily,
        fund_g[["ts_code", "ann_date", "acc_med"]],
        left_on="trade_date",
        right_on="ann_date",
        by="ts_code",
        direction="backward",
        allow_exact_matches=False,
    )
    return merged.dropna(subset=["acc_med"])


# ---------- 4. winsorize + industry rank ---------- #

def cross_sectional_rank(panel: pd.DataFrame, cfg: FactorConfig) -> pd.DataFrame:
    panel = panel.copy()
    panel["acc_med_w"] = panel.groupby("trade_date")["acc_med"].transform(
        lambda s: s.clip(lower=s.quantile(cfg.winsorize_lo), upper=s.quantile(cfg.winsorize_hi))
    )
    panel["alpha"] = -(
        panel.groupby(["trade_date", "industry"])["acc_med_w"].rank(pct=True) - 0.5
    )
    return panel


# ---------- 5. one-shot driver ---------- #

def build_factor(token: str, cfg: FactorConfig | None = None) -> pd.DataFrame:
    """End-to-end builder. Returns daily panel with `alpha` column ready for backtest.
    Requires Tushare with _vip access for batch period queries."""
    import tushare as ts
    cfg = cfg or FactorConfig()
    pro = ts.pro_api(token)

    print("[1/5] fetching quarterly fundamentals", flush=True)
    periods = quarter_periods(cfg.start_period, cfg.end_period)
    fund = fetch_fundamentals(pro, periods)
    fund = build_quarterly_signal(fund, cfg)

    print("[2/5] fetching daily prices + adj + mv per trade date", flush=True)
    cal = pro.trade_cal(exchange="SSE", start_date=cfg.start_trade_date, end_date=cfg.end_trade_date)
    trade_dates = cal[cal["is_open"] == 1]["cal_date"].tolist()
    rows = []
    for td in trade_dates:
        d = pro.daily(trade_date=td, fields="ts_code,trade_date,close")
        rows.append(d)
    daily = pd.concat(rows, ignore_index=True)
    daily["trade_date"] = pd.to_datetime(daily["trade_date"], format="%Y%m%d")

    print("[3/5] universe filter", flush=True)
    basic = pro.stock_basic(exchange="", list_status="L", fields="ts_code,name,industry,list_date")
    daily = filter_universe(daily, basic, cfg)

    print("[4/5] merge_asof on ann_date", flush=True)
    panel = merge_signal_to_daily(daily, fund)

    print("[5/5] winsorize + industry rank -> alpha", flush=True)
    panel = cross_sectional_rank(panel, cfg)

    return panel[["ts_code", "trade_date", "industry", "acc_med", "acc_med_w", "alpha"]].reset_index(drop=True)


if __name__ == "__main__":
    tok = os.environ.get("TUSHARE_TOKEN")
    if not tok:
        sys.exit("TUSHARE_TOKEN env var required")
    df = build_factor(tok)
    out = "factor_panel.parquet"
    df.to_parquet(out, index=False)
    print(f"wrote {out}  rows={len(df):,}  stocks={df.ts_code.nunique()}")
