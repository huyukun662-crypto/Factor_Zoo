"""
Fetch DTL + OHLCV + industry from Tushare, cache to parquet.

Requires:
  pip install tushare pandas pyarrow
  export TUSHARE_TOKEN=...

Outputs (relative to session root):
  inputs/cache/top_list.parquet
  inputs/cache/top_inst.parquet
  inputs/cache/ohlcv_qfq.parquet
  inputs/cache/stock_basic.parquet
  inputs/cache/limit_list.parquet      # for is_upper_limit flag

Per CLAUDE.md A-share rule: cache aggressively. Free-tier endpoints used:
  top_list, top_inst, pro_bar(adj='qfq'), stock_basic, limit_list.
"""
import os, time
from pathlib import Path
import pandas as pd
import tushare as ts

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "inputs" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

START, END = "20180101", "20251231"

pro = ts.pro_api(os.environ["TUSHARE_TOKEN"])


def daterange(start, end, freq="B"):
    return pd.date_range(start, end, freq=freq).strftime("%Y%m%d").tolist()


def fetch_per_date(api_fn, dates, label, sleep=0.12):
    out = []
    for i, d in enumerate(dates):
        for attempt in range(4):
            try:
                df = api_fn(trade_date=d)
                if df is not None and len(df):
                    out.append(df)
                break
            except Exception as e:
                time.sleep(2 ** attempt)
        if i % 200 == 0:
            print(f"[{label}] {i}/{len(dates)}")
        time.sleep(sleep)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def main():
    dates = daterange(START, END)
    fetch_per_date(pro.top_list, dates, "top_list").to_parquet(CACHE / "top_list.parquet")
    fetch_per_date(pro.top_inst, dates, "top_inst").to_parquet(CACHE / "top_inst.parquet")
    fetch_per_date(pro.limit_list_d, dates, "limit_list").to_parquet(CACHE / "limit_list.parquet")
    pro.stock_basic(exchange="", list_status="L",
                    fields="ts_code,name,industry,list_date,market"
    ).to_parquet(CACHE / "stock_basic.parquet")
    # OHLCV via pro_bar per stock — see 00b_fetch_ohlcv.py for the loop.


if __name__ == "__main__":
    main()
