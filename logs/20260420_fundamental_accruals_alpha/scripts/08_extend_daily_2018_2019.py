"""
Round 3: extend daily panel backward to 2018-01 .. 2019-12.
Appends to existing daily/adj/daily_basic parquets rather than refetching.
"""
import os, sys, time
import pandas as pd
import tushare as ts

TOKEN = os.environ.get("TUSHARE_TOKEN")
if not TOKEN:
    sys.exit("TUSHARE_TOKEN env var required")
pro = ts.pro_api(TOKEN)

CACHE = "/home/user/Factor_Zoo/.cache"
LOG = open(f"{CACHE}/fetch_extend.log", "w", buffering=1)


def say(s):
    print(s, flush=True)
    LOG.write(s + "\n")


cal = pro.trade_cal(exchange="SSE", start_date="20180101", end_date="20191231")
td = cal[cal["is_open"] == 1]["cal_date"].tolist()
say(f"Need {len(td)} trade days from {td[0]} to {td[-1]}")


def fetch(fn, d, fields=None):
    for i in range(3):
        try:
            k = {"trade_date": d}
            if fields:
                k["fields"] = fields
            return getattr(pro, fn)(**k)
        except Exception as e:
            time.sleep(1 + i)
    return pd.DataFrame()


daily_rows, adj_rows, db_rows = [], [], []
t0 = time.time()
for i, d in enumerate(td):
    daily_rows.append(fetch("daily", d, "ts_code,trade_date,open,close,vol,amount"))
    adj_rows.append(fetch("adj_factor", d, "ts_code,trade_date,adj_factor"))
    db_rows.append(fetch("daily_basic", d, "ts_code,trade_date,total_mv,circ_mv"))
    if (i + 1) % 50 == 0 or i == len(td) - 1:
        el = time.time() - t0
        eta = el / (i + 1) * (len(td) - i - 1)
        say(f"[{i+1}/{len(td)}] {d} elapsed={el:.0f}s eta={eta:.0f}s")


def append(name, rows, cols):
    df = pd.concat([r for r in rows if len(r)], ignore_index=True)
    df = df[cols]
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
    # append to existing parquet
    existing = pd.read_parquet(f"{CACHE}/{name}.parquet")
    combo = pd.concat([df, existing], ignore_index=True)
    combo = combo.drop_duplicates(subset=["ts_code", "trade_date"], keep="last")
    combo = combo.sort_values(["trade_date", "ts_code"]).reset_index(drop=True)
    combo.to_parquet(f"{CACHE}/{name}.parquet", index=False)
    say(f"{name}.parquet: {len(existing):,} + {len(df):,} new -> {len(combo):,} total")


append("daily", daily_rows, ["ts_code","trade_date","open","close","vol","amount"])
append("adj_factor", adj_rows, ["ts_code","trade_date","adj_factor"])
append("daily_basic", db_rows, ["ts_code","trade_date","total_mv","circ_mv"])
say(f"Total {time.time()-t0:.0f}s")
LOG.close()
