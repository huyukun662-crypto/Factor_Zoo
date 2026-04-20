"""
Fetch daily prices, adj_factor, daily_basic(total_mv) per trading date.

Scope: 2020-01-02 .. 2025-04-18  (train=2020-22, validate=2023, test=2024+YTD 2025).
Strategy: iterate per trade_date to get cross-section in one call each (3 calls/date).
Output: .cache/daily.parquet, adj_factor.parquet, daily_basic.parquet
"""
import os, sys, time
import pandas as pd
import tushare as ts

TOKEN = os.environ.get("TUSHARE_TOKEN")
if not TOKEN:
    sys.exit("TUSHARE_TOKEN env var required")
pro = ts.pro_api(TOKEN)

CACHE = "/home/user/Factor_Zoo/.cache"
os.makedirs(CACHE, exist_ok=True)

LOG = open(f"{CACHE}/fetch_daily.log", "w", buffering=1)


def say(s):
    print(s, flush=True)
    LOG.write(s + "\n")


cal = pro.trade_cal(exchange="SSE", start_date="20200101", end_date="20250418")
trade_dates = cal[cal["is_open"] == 1]["cal_date"].tolist()
say(f"Trade days: {len(trade_dates)} from {trade_dates[0]} to {trade_dates[-1]}")


def fetch_one(fn_name, trade_date, fields=None):
    for attempt in range(3):
        try:
            kwargs = {"trade_date": trade_date}
            if fields:
                kwargs["fields"] = fields
            return getattr(pro, fn_name)(**kwargs)
        except Exception as e:
            time.sleep(1 + attempt)
    return pd.DataFrame()


daily_rows, adj_rows, db_rows = [], [], []
t0 = time.time()
for i, td in enumerate(trade_dates):
    d = fetch_one("daily", td, "ts_code,trade_date,open,close,vol,amount")
    a = fetch_one("adj_factor", td, "ts_code,trade_date,adj_factor")
    b = fetch_one("daily_basic", td, "ts_code,trade_date,total_mv,circ_mv")
    daily_rows.append(d)
    adj_rows.append(a)
    db_rows.append(b)
    if (i + 1) % 50 == 0 or i == len(trade_dates) - 1:
        elapsed = time.time() - t0
        eta = elapsed / (i + 1) * (len(trade_dates) - i - 1)
        say(f"[{i+1}/{len(trade_dates)}] {td} elapsed={elapsed:.0f}s eta={eta:.0f}s")


def dump(name, rows, cols):
    df = pd.concat([r for r in rows if len(r)], ignore_index=True)
    df = df[cols]
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
    df.to_parquet(f"{CACHE}/{name}.parquet", index=False)
    say(f"wrote {name}.parquet  rows={len(df)}")


dump("daily", daily_rows, ["ts_code", "trade_date", "open", "close", "vol", "amount"])
dump("adj_factor", adj_rows, ["ts_code", "trade_date", "adj_factor"])
dump("daily_basic", db_rows, ["ts_code", "trade_date", "total_mv", "circ_mv"])
say(f"Total {time.time()-t0:.0f}s")
LOG.close()
