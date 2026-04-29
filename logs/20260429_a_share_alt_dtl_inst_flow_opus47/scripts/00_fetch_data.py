"""Fetch DTL + OHLCV + limit + industry for 2023-2025, cache to parquet."""
import os, time, sys
from pathlib import Path
import pandas as pd
import tushare as ts

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "inputs" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

START, END = "20230101", "20251231"

pro = ts.pro_api(os.environ["TUSHARE_TOKEN"])


def trade_dates(start, end):
    cal = pro.trade_cal(exchange="SSE", start_date=start, end_date=end, is_open="1")
    return cal["cal_date"].tolist()


def per_date(api, dates, label, out_path, sleep=0.18):
    if out_path.exists():
        print(f"[{label}] cached -> {out_path}"); return
    out, n = [], len(dates)
    for i, d in enumerate(dates):
        for k in range(5):
            try:
                df = api(trade_date=d)
                if df is not None and len(df): out.append(df)
                break
            except Exception as e:
                wait = min(2 ** k, 30)
                if k == 4: print(f"[{label}] FAIL {d}: {e}", file=sys.stderr)
                time.sleep(wait)
        if i % 100 == 0: print(f"[{label}] {i}/{n}")
        time.sleep(sleep)
    pd.concat(out, ignore_index=True).to_parquet(out_path)
    print(f"[{label}] -> {out_path} rows={sum(len(x) for x in out)}")


def main():
    dates = trade_dates(START, END)
    print("trade dates:", len(dates), dates[0], "->", dates[-1])

    # stock basic (one shot)
    sb_path = CACHE / "stock_basic.parquet"
    if not sb_path.exists():
        pro.stock_basic(exchange="", list_status="L",
                        fields="ts_code,name,industry,list_date,market"
        ).to_parquet(sb_path)
        # also fetch delisted to capture survivorship-relevant tickers
        d = pro.stock_basic(exchange="", list_status="D",
                            fields="ts_code,name,industry,list_date,delist_date,market")
        d.to_parquet(CACHE / "stock_basic_delisted.parquet")
        print("[stock_basic] OK")

    per_date(pro.top_list, dates, "top_list", CACHE / "top_list.parquet")
    per_date(pro.top_inst, dates, "top_inst", CACHE / "top_inst.parquet")
    per_date(pro.limit_list_d, dates, "limit_list", CACHE / "limit_list.parquet")
    per_date(pro.daily, dates, "daily", CACHE / "daily.parquet", sleep=0.15)

    # adj_factor for survivorship-correct returns
    per_date(pro.adj_factor, dates, "adj_factor", CACHE / "adj_factor.parquet", sleep=0.15)


if __name__ == "__main__":
    main()
