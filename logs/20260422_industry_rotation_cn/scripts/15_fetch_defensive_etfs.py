"""
Fetch defensive-asset ETFs (not in the original 34-universe) for gate-off basket:
  - 铜ETF       159981.SZ
  - 白银LOF      161226.SZ
  - 纳指ETF      159941.SZ
  - 恒生ETF      159920.SZ
  - (石油ETF 561360.SH already in universe)
  - (黄金ETF 159934.SZ already in universe)

Output: outputs/defensive_weekly.parquet (weekly ret_w/close_adj/etc)
"""
import os, sys, time
from pathlib import Path
import numpy as np, pandas as pd
import tushare as ts

CACHE = Path("/home/user/Factor_Zoo/.cache")
OUT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")

if not os.environ.get("TUSHARE_TOKEN"):
    secret = Path("/home/user/Factor_Zoo/.secrets/tushare.env")
    if secret.exists():
        for line in secret.read_text().splitlines():
            if line.startswith("TUSHARE_TOKEN="):
                os.environ["TUSHARE_TOKEN"] = line.split("=", 1)[1].strip()
                break
pro = ts.pro_api(os.environ["TUSHARE_TOKEN"])
say = lambda s: print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

DEFS = {
    "铜ETF":    "159981.SZ",
    "白银LOF":   "161226.SZ",
    "纳指ETF":   "159941.SZ",
    "恒生ETF":   "159920.SZ",
}

FD = CACHE / "fund_daily_defensive.parquet"
FAJ = CACHE / "fund_adj_defensive.parquet"

if FD.exists() and FAJ.exists():
    say("already cached — skip fetch")
else:
    all_d, all_a = [], []
    for name, code in DEFS.items():
        for tries in range(3):
            try:
                d = pro.fund_daily(ts_code=code, start_date="20150101", end_date="20260422")
                break
            except Exception as e:
                time.sleep(2+tries)
        else:
            d = pd.DataFrame()
        if len(d) == 0:
            say(f"  NO DATA for {name} ({code})"); continue
        d["etf_name"] = name
        all_d.append(d)
        say(f"  {name} ({code}): {len(d)} rows, {d['trade_date'].min()} → {d['trade_date'].max()}")
        # adj
        for tries in range(3):
            try:
                a = pro.fund_adj(ts_code=code, start_date="20150101", end_date="20260422")
                break
            except Exception as e:
                time.sleep(2+tries)
        else:
            a = pd.DataFrame()
        if len(a): all_a.append(a)
    fd = pd.concat(all_d, ignore_index=True) if all_d else pd.DataFrame()
    fa = pd.concat(all_a, ignore_index=True) if all_a else pd.DataFrame()
    if len(fd): fd["trade_date"] = pd.to_datetime(fd["trade_date"])
    if len(fa): fa["trade_date"] = pd.to_datetime(fa["trade_date"])
    fd.to_parquet(FD)
    fa.to_parquet(FAJ)

fd = pd.read_parquet(FD)
fa = pd.read_parquet(FAJ)
fd = fd.merge(fa, on=["ts_code","trade_date"], how="left")
fd["close_adj"] = fd["close"] * fd["adj_factor"].fillna(1.0)
fd = fd.sort_values(["ts_code","trade_date"]).reset_index(drop=True)
fd["ret"] = fd.groupby("ts_code")["close_adj"].pct_change()

# Coverage
say("\n===== Coverage =====")
cov = fd.groupby("ts_code").agg(first=("trade_date","min"), last=("trade_date","max"),
                                 n=("trade_date","count")).reset_index()
cov["years"] = (cov["last"]-cov["first"]).dt.days/365.25
print(cov.to_string(index=False))

# Weekly
fd["year_week"] = fd["trade_date"].dt.strftime("%G-%V")
fd["gross"] = 1 + fd["ret"].fillna(0)
fd["cum"] = fd.groupby("ts_code")["gross"].cumprod()
weekly = (fd.groupby(["ts_code","year_week"], sort=False)
          .agg(trade_week=("trade_date","last"), cum_w=("cum","last"),
               amount_w=("amount","sum"))
          .reset_index())
weekly = weekly.sort_values(["ts_code","trade_week"])
weekly["ret_w"] = weekly.groupby("ts_code")["cum_w"].pct_change()
weekly = weekly.dropna(subset=["ret_w"]).copy()
weekly.to_parquet(OUT / "defensive_weekly.parquet")
say(f"\n[done] defensive_weekly: {len(weekly):,} rows, {weekly['ts_code'].nunique()} ETFs, {weekly['trade_week'].nunique()} weeks")
print(weekly.groupby("ts_code").agg(first=("trade_week","min"), last=("trade_week","max"),
                                     n=("trade_week","count")).to_string())
