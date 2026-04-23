"""
Build weekly industry panel from stock-level cache (vectorized).

Step 1: Fetch SW L1 industry mapping (~28 industries) from tushare (cached).
Step 2: Join point-in-time membership → stock-day table.
Step 3: Vectorized industry aggregation (circ_mv weighted return, turnover).
Step 4: Resample to weekly (Friday close snapshot).

Output: outputs/industry_weekly.parquet, industry_daily.parquet
"""
import os, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
import tushare as ts

CACHE = Path("/home/user/Factor_Zoo/.cache")
OUT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")
OUT.mkdir(parents=True, exist_ok=True)

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


def say(s):
    print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)


# --- Step 1: SW L1 mapping ---
MAP_PATH = CACHE / "sw_l1_map.parquet"
if MAP_PATH.exists():
    sw_map = pd.read_parquet(MAP_PATH)
    say(f"[step1] loaded sw_l1_map, {len(sw_map)} member rows, {sw_map['industry_code'].nunique()} industries")
else:
    say("[step1] fetching SW L1 mapping from tushare…")
    sw_idx = pro.index_classify(level="L1", src="SW2021")
    rows = []
    for _, r in sw_idx.iterrows():
        code, name = r["index_code"], r["industry_name"]
        for tries in range(3):
            try:
                cons = pro.index_member_all(l1_code=code)
                break
            except Exception as e:
                time.sleep(2 + tries)
        else:
            cons = pd.DataFrame()
        if len(cons) == 0: continue
        cons = cons[["ts_code", "in_date", "out_date"]].copy()
        cons["industry_code"] = code
        cons["industry_name"] = name
        rows.append(cons)
    sw_map = pd.concat(rows, ignore_index=True)
    sw_map["in_date"] = pd.to_datetime(sw_map["in_date"])
    sw_map["out_date"] = pd.to_datetime(sw_map["out_date"])
    sw_map.to_parquet(MAP_PATH)
    say(f"[step1] saved {MAP_PATH}")

sw_map["out_date_fill"] = sw_map["out_date"].fillna(pd.Timestamp("2099-12-31"))

# --- Step 2: Load stock daily ---
say("[step2] loading daily cache…")
daily = pd.read_parquet(CACHE / "daily.parquet", columns=["trade_date", "ts_code", "close", "amount"])
daily_basic = pd.read_parquet(CACHE / "daily_basic.parquet", columns=["trade_date", "ts_code", "circ_mv", "total_mv"])
adj = pd.read_parquet(CACHE / "adj_factor.parquet", columns=["trade_date", "ts_code", "adj_factor"])
for d in [daily, daily_basic, adj]:
    d["trade_date"] = pd.to_datetime(d["trade_date"])

df = daily.merge(daily_basic, on=["trade_date", "ts_code"], how="inner")
df = df.merge(adj, on=["trade_date", "ts_code"], how="inner")
df["close_adj"] = df["close"] * df["adj_factor"]
df = df.sort_values(["ts_code", "trade_date"])
df["ret"] = df.groupby("ts_code")["close_adj"].pct_change()

# Daily turnover per stock: amount is in 千元 (from tushare daily), circ_mv in 万元 → ratio
df["turnover_mv"] = (df["amount"] / 10.0) / df["circ_mv"]
df = df[["trade_date", "ts_code", "ret", "turnover_mv", "circ_mv", "total_mv", "amount"]].copy()
say(f"[step2] stock-daily: {len(df):,} rows, {df['ts_code'].nunique()} stocks")

# --- Step 3: Assign each stock to one industry per point in time (latest valid) ---
say("[step3] building stock→industry assignment…")
# For each ts_code, pick the earliest in_date record (most stocks only appear once).
# If duplicated, take the record with latest in_date that is <= trade_date and out_date >= trade_date.
# For simplicity and speed, use the latest (most recent in_date) active record per ts_code for each trade day.

# Pre-aggregate: for each stock, expand its intervals.
# Simpler: since membership is usually long, just take latest-in_date record per ts_code (ignoring stocks with multiple rows, which are rare).
sw_map_sorted = sw_map.sort_values(["ts_code", "in_date"])
latest = sw_map_sorted.groupby("ts_code").tail(1)[["ts_code", "industry_code", "industry_name", "in_date", "out_date_fill"]]
say(f"[step3] latest-membership rows: {len(latest):,}")

# Join
df = df.merge(latest, on="ts_code", how="left")
# Keep only days within (in_date, out_date) window
mask = df["industry_code"].notna() & (df["trade_date"] >= df["in_date"]) & (df["trade_date"] <= df["out_date_fill"])
df = df[mask].drop(columns=["in_date", "out_date_fill"]).copy()
say(f"[step3] stock-days with valid industry: {len(df):,}")

# --- Step 4: Vectorized aggregation ---
say("[step4] vectorized industry aggregation…")
df["ret_w_num"] = df["ret"] * df["circ_mv"]
df["turn_w_num"] = df["turnover_mv"] * df["circ_mv"]

grp = df.groupby(["trade_date", "industry_code", "industry_name"], sort=False, observed=True)
agg = grp.agg(
    ret_num_sum=("ret_w_num", "sum"),
    turn_num_sum=("turn_w_num", "sum"),
    mv_sum=("circ_mv", "sum"),
    total_mv=("total_mv", "sum"),
    amount=("amount", "sum"),
    n_stocks=("ts_code", "count"),
).reset_index()
agg["ret_d"] = agg["ret_num_sum"] / agg["mv_sum"]
agg["turnover_mv_d"] = agg["turn_num_sum"] / agg["mv_sum"]
daily_ind = agg[["trade_date", "industry_code", "industry_name", "ret_d", "turnover_mv_d", "total_mv", "amount", "n_stocks"]]
say(f"[step4] daily_ind rows: {len(daily_ind):,}, industries: {daily_ind['industry_code'].nunique()}")

# --- Step 5: Resample to weekly (ISO week, last trading day as Friday proxy) ---
say("[step5] resample weekly…")
daily_ind = daily_ind.sort_values(["industry_code", "trade_date"]).reset_index(drop=True)
daily_ind["gross"] = 1.0 + daily_ind["ret_d"].fillna(0)
daily_ind["cum"] = daily_ind.groupby("industry_code")["gross"].cumprod()
daily_ind["year_week"] = daily_ind["trade_date"].dt.strftime("%G-%V")

weekly = (daily_ind.groupby(["industry_code", "industry_name", "year_week"], sort=False, observed=True)
          .agg(trade_week=("trade_date", "last"),
               cum_w=("cum", "last"),
               turnover_mv_w=("turnover_mv_d", "mean"),
               total_mv_w=("total_mv", "last"),
               amount_w=("amount", "sum"),
               n_stocks=("n_stocks", "last"))
          .reset_index())
weekly = weekly.sort_values(["industry_code", "trade_week"])
weekly["ret_w"] = weekly.groupby("industry_code")["cum_w"].pct_change()
weekly = weekly.dropna(subset=["ret_w"]).copy()
say(f"[step5] weekly rows: {len(weekly):,}, weeks: {weekly['trade_week'].nunique()}")
say(f"    sample: {weekly['trade_week'].min()} → {weekly['trade_week'].max()}")

weekly.to_parquet(OUT / "industry_weekly.parquet")
daily_ind.to_parquet(OUT / "industry_daily.parquet")
say(f"[done] wrote {OUT / 'industry_weekly.parquet'} and industry_daily.parquet")
