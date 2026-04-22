"""
Forward-extend daily cache from 2025-04-21 → today, then invalidate
rotation/momentum caches so the next rotation run picks up fresh data.

Modelled on 08_extend_daily_2018_2019.py but runs forward.
"""
import os, sys, time
from pathlib import Path
import pandas as pd
import tushare as ts

CACHE = Path("/home/user/Factor_Zoo/.cache")

# Load token from secrets if not in env
if not os.environ.get("TUSHARE_TOKEN"):
    secret = Path("/home/user/Factor_Zoo/.secrets/tushare.env")
    if secret.exists():
        for line in secret.read_text().splitlines():
            if line.startswith("TUSHARE_TOKEN="):
                os.environ["TUSHARE_TOKEN"] = line.split("=", 1)[1].strip()
                break
TOKEN = os.environ.get("TUSHARE_TOKEN")
if not TOKEN:
    sys.exit("TUSHARE_TOKEN required")
pro = ts.pro_api(TOKEN)

LOG_PATH = CACHE / "fetch_extend_fwd.log"
LOG = open(LOG_PATH, "w", buffering=1)


def say(s):
    print(s, flush=True)
    LOG.write(s + "\n")


# Extend from day after current cache max. Check current max.
existing_daily = pd.read_parquet(CACHE / "daily.parquet", columns=["trade_date"])
existing_daily["trade_date"] = pd.to_datetime(existing_daily["trade_date"])
cache_max = existing_daily["trade_date"].max()
start_d = (cache_max + pd.Timedelta(days=1)).strftime("%Y%m%d")
end_d = pd.Timestamp.today().strftime("%Y%m%d")
say(f"Cache max: {cache_max.date()}, extending {start_d} → {end_d}")

cal = pro.trade_cal(exchange="SSE", start_date=start_d, end_date=end_d)
td = cal[cal["is_open"] == 1]["cal_date"].tolist()
if not td:
    say(f"No new trade days in range — cache is up to date."); sys.exit(0)
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
    if (i + 1) % 20 == 0 or i == len(td) - 1:
        el = time.time() - t0
        eta = el / (i + 1) * (len(td) - i - 1)
        say(f"[{i+1}/{len(td)}] {d} elapsed={el:.0f}s eta={eta:.0f}s")


def append(name, rows, cols):
    df = pd.concat([r for r in rows if len(r)], ignore_index=True)
    if len(df) == 0:
        say(f"{name}.parquet: no new rows — skipping"); return
    df = df[cols]
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
    existing = pd.read_parquet(CACHE / f"{name}.parquet")
    combo = pd.concat([existing, df], ignore_index=True)
    combo = combo.drop_duplicates(subset=["ts_code", "trade_date"], keep="last")
    combo = combo.sort_values(["trade_date", "ts_code"]).reset_index(drop=True)
    combo.to_parquet(CACHE / f"{name}.parquet", index=False)
    say(f"{name}.parquet: {len(existing):,} + {len(df):,} new -> {len(combo):,} total")


append("daily", daily_rows, ["ts_code", "trade_date", "open", "close", "vol", "amount"])
append("adj_factor", adj_rows, ["ts_code", "trade_date", "adj_factor"])
append("daily_basic", db_rows, ["ts_code", "trade_date", "total_mv", "circ_mv"])

# Invalidate derived caches so downstream rebuilds see fresh data
cache_file = CACHE / "alpha_n_mom_for_rotation.parquet"
if cache_file.exists():
    cache_file.unlink()
    say(f"invalidated {cache_file.name}")

say(f"Total {time.time()-t0:.0f}s")
LOG.close()
