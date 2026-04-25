"""Fetch ETF daily for the three broad-base ETFs and cache to parquet."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from .tushare_client import call_with_retry, get_pro

ETF_CODES = ["510300.SH", "510500.SH", "512100.SH"]
START = "20180101"
END = "20260425"
CACHE = Path(".cache/etf_daily.parquet")


def fetch_one(pro, ts_code: str) -> pd.DataFrame:
    df = call_with_retry(pro.fund_daily, ts_code=ts_code, start_date=START, end_date=END)
    if df is None or df.empty:
        raise RuntimeError(f"empty daily for {ts_code}")
    df = df.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values("trade_date").reset_index(drop=True)
    return df


def main():
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    pro = get_pro()
    frames = []
    for code in ETF_CODES:
        print(f"[etf] fetching {code} ...")
        frames.append(fetch_one(pro, code))
    out = pd.concat(frames, ignore_index=True)
    out.to_parquet(CACHE, index=False)
    print(f"[etf] wrote {len(out)} rows -> {CACHE}")
    print(out.groupby("ts_code").size().to_string())


if __name__ == "__main__":
    main()
