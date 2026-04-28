"""Parallel fetch — daily_basic only. Resumable."""
import os, sys, time
from pathlib import Path
import pandas as pd
import tushare as ts

_tok = os.environ.get("TUSHARE_TOKEN")
if not _tok:
    sys.exit("set env TUSHARE_TOKEN before running")
ts.set_token(_tok)
pro = ts.pro_api()
CACHE = Path("/home/user/Factor_Zoo/.cache")

cal = pd.read_parquet(CACHE / "trade_cal.parquet")
dates = cal[cal["is_open"] == 1]["cal_date"].astype(str).tolist()

out = CACHE / "daily_basic.parquet"
seen = set()
if out.exists():
    seen = set(pd.read_parquet(out, columns=["trade_date"])["trade_date"].astype(str).unique())
todo = [d for d in dates if d not in seen]
print(f"daily_basic todo {len(todo)}", flush=True)

buf, FLUSH = [], 60
COLS = ["ts_code", "trade_date", "total_mv", "circ_mv", "turnover_rate_f"]
for i, d in enumerate(todo, 1):
    for tries in range(5):
        try:
            df = pro.daily_basic(trade_date=d)
            break
        except Exception as e:
            if tries == 4:
                print(f"err {d}: {e}", flush=True)
                df = None
            time.sleep(1.5 ** tries)
    if df is None or len(df) == 0:
        continue
    keep = [c for c in COLS if c in df.columns]
    df = df[keep]
    buf.append(df)
    if i % FLUSH == 0 or i == len(todo):
        new = pd.concat(buf, ignore_index=True)
        if out.exists():
            prev = pd.read_parquet(out)
            new = pd.concat([prev, new], ignore_index=True).drop_duplicates(
                subset=["ts_code", "trade_date"], keep="last")
        new.to_parquet(out, index=False)
        buf = []
        print(f"daily_basic {i}/{len(todo)}", flush=True)
print("daily_basic DONE", flush=True)
