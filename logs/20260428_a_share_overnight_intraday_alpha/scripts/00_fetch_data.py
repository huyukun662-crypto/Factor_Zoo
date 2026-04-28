"""
A-share Tushare cache builder for the 20260428 overnight-intraday session.

Cache layout (gitignored, /home/user/Factor_Zoo/.cache/):
  daily.parquet        : ts_code, trade_date, open, high, low, close, pre_close,
                         vol, amount, pct_chg
  adj_factor.parquet   : ts_code, trade_date, adj_factor
  daily_basic.parquet  : ts_code, trade_date, total_mv, circ_mv, turnover_rate_f
  stock_basic.parquet  : ts_code, name, industry, market, list_date
  trade_cal.parquet    : cal_date, is_open

Resumable per-date: skips dates already present in the on-disk parquet.
"""
import os, sys, time
from pathlib import Path
import pandas as pd
import tushare as ts

TOKEN = os.environ.get("TUSHARE_TOKEN")
if not TOKEN:
    sys.exit("set env TUSHARE_TOKEN before running")
ts.set_token(TOKEN)
pro = ts.pro_api()

CACHE = Path("/home/user/Factor_Zoo/.cache")
CACHE.mkdir(exist_ok=True)

START = "20180101"
END   = "20260428"

def _retry(fn, *args, tries=5, base=1.5, **kwargs):
    for i in range(tries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(base ** i)


def fetch_stock_basic():
    out = CACHE / "stock_basic.parquet"
    df = _retry(pro.stock_basic, exchange='', list_status='L',
                fields='ts_code,symbol,name,area,industry,list_date,market')
    # Also pull delisted to keep the universe full historically
    delisted = _retry(pro.stock_basic, exchange='', list_status='D',
                      fields='ts_code,symbol,name,area,industry,list_date,delist_date,market')
    df = pd.concat([df, delisted], ignore_index=True)
    # exclude 北交所
    df = df[df["market"].isin(["主板", "创业板", "科创板"])].reset_index(drop=True)
    df.to_parquet(out, index=False)
    print(f"[stock_basic] {len(df)} rows -> {out}")


def fetch_trade_cal():
    out = CACHE / "trade_cal.parquet"
    cal = _retry(pro.trade_cal, exchange='SSE', start_date=START, end_date=END)
    cal.to_parquet(out, index=False)
    print(f"[trade_cal] {len(cal)} rows -> {out}")
    return cal[cal["is_open"] == 1]["cal_date"].tolist()


def _append_partition(out: Path, frames: list[pd.DataFrame]):
    if not frames:
        return
    new = pd.concat(frames, ignore_index=True)
    if out.exists():
        prev = pd.read_parquet(out)
        new = pd.concat([prev, new], ignore_index=True).drop_duplicates(
            subset=["ts_code", "trade_date"], keep="last")
    new.to_parquet(out, index=False)


def fetch_panel(name: str, fn, dates: list[str], cols=None):
    out = CACHE / f"{name}.parquet"
    seen = set()
    if out.exists():
        seen = set(pd.read_parquet(out, columns=["trade_date"])["trade_date"].astype(str).unique())
        print(f"[{name}] {len(seen)} dates already cached, resuming")
    todo = [d for d in dates if d not in seen]
    print(f"[{name}] fetching {len(todo)} dates")
    buf = []
    flush_every = 60   # flush every 60 dates (~3 trading months) to limit memory
    for i, d in enumerate(todo, 1):
        try:
            df = _retry(fn, trade_date=d)
        except Exception as e:
            print(f"  err {d}: {e}", flush=True)
            continue
        if cols is not None:
            keep = [c for c in cols if c in df.columns]
            df = df[keep]
        buf.append(df)
        if i % flush_every == 0 or i == len(todo):
            _append_partition(out, buf)
            buf = []
            print(f"  [{name}] {i}/{len(todo)} done", flush=True)
            time.sleep(0.05)


def main():
    fetch_stock_basic()
    open_dates = fetch_trade_cal()
    print(f"trading dates {open_dates[0]} .. {open_dates[-1]} (n={len(open_dates)})")

    fetch_panel("daily", pro.daily, open_dates,
                cols=["ts_code","trade_date","open","high","low","close","pre_close",
                      "vol","amount","pct_chg"])
    fetch_panel("adj_factor", pro.adj_factor, open_dates,
                cols=["ts_code","trade_date","adj_factor"])
    fetch_panel("daily_basic", pro.daily_basic, open_dates,
                cols=["ts_code","trade_date","total_mv","circ_mv","turnover_rate_f"])
    print("ALL DONE")


if __name__ == "__main__":
    main()
