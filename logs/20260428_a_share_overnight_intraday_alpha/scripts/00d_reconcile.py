"""
Reconcile cache: find any (endpoint, trade_date) gaps and refetch.

Two earlier fetchers raced on daily_basic.parquet because both checked `seen` at
startup and never re-read. This pass walks the trade calendar, finds dates
missing per endpoint, refetches them serially with retry. Single-process so
no race.
"""
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
all_dates = set(cal[cal["is_open"] == 1]["cal_date"].astype(str))


def reconcile(name: str, fn, cols: list[str]):
    out = CACHE / f"{name}.parquet"
    if not out.exists():
        sys.exit(f"missing {out}")
    have = pd.read_parquet(out, columns=["trade_date"])
    have_set = set(have["trade_date"].astype(str).unique())
    missing = sorted(all_dates - have_set)
    print(f"[{name}] have {len(have_set)} / target {len(all_dates)} -> missing {len(missing)}", flush=True)
    if not missing:
        return
    buf, FLUSH = [], 60
    for i, d in enumerate(missing, 1):
        for tries in range(5):
            try:
                df = fn(trade_date=d)
                break
            except Exception as e:
                if tries == 4:
                    print(f"  err {d}: {e}", flush=True)
                    df = None
                time.sleep(1.5 ** tries)
        if df is None or len(df) == 0:
            continue
        keep = [c for c in cols if c in df.columns]
        df = df[keep]
        buf.append(df)
        if i % FLUSH == 0 or i == len(missing):
            new = pd.concat(buf, ignore_index=True)
            prev = pd.read_parquet(out)
            new = pd.concat([prev, new], ignore_index=True).drop_duplicates(
                subset=["ts_code", "trade_date"], keep="last")
            new.to_parquet(out, index=False)
            buf = []
            print(f"  [{name}] {i}/{len(missing)}", flush=True)
    print(f"[{name}] reconciled", flush=True)


reconcile("daily", pro.daily,
          ["ts_code", "trade_date", "open", "high", "low", "close",
           "pre_close", "vol", "amount", "pct_chg"])
reconcile("adj_factor", pro.adj_factor,
          ["ts_code", "trade_date", "adj_factor"])
reconcile("daily_basic", pro.daily_basic,
          ["ts_code", "trade_date", "total_mv", "circ_mv", "turnover_rate_f"])
print("RECONCILE DONE", flush=True)
