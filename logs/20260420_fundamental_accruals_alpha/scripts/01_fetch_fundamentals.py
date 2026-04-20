"""
Stage 4 runtime: fetch quarterly fundamentals via Tushare _vip endpoints.

Scope: all A-share, quarters 2017Q4 .. 2024Q4 (29 quarters).
Fields: income (NI), balancesheet (TA, AR, INV, AP, dep assets), cashflow (CFO, dep).

Output: .cache/fundamentals.parquet  (NOT tracked by git)
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

PERIODS = []
for y in range(2017, 2025):
    for m in ["0331", "0630", "0930", "1231"]:
        PERIODS.append(f"{y}{m}")
# truncate to 2017Q4..2024Q4 -> start index for 2017Q4 is 3
PERIODS = PERIODS[3:]
print(f"Fetching {len(PERIODS)} quarters: {PERIODS[0]} .. {PERIODS[-1]}")

INCOME_FIELDS = "ts_code,ann_date,f_ann_date,end_date,report_type,n_income,revenue"
BS_FIELDS = "ts_code,ann_date,f_ann_date,end_date,report_type,total_assets,accounts_receiv,inventories,accounts_pay,total_share"
CF_FIELDS = "ts_code,ann_date,f_ann_date,end_date,report_type,n_cashflow_act,depr_fa_coga_dpba"


def fetch_period(api_name, period, fields):
    for attempt in range(3):
        try:
            df = pro.query(api_name, period=period, fields=fields)
            return df
        except Exception as e:
            print(f"  retry {attempt+1} for {api_name} {period}: {e}")
            time.sleep(2 * (attempt + 1))
    return pd.DataFrame()


def fetch_all(api_name, fields):
    out = []
    for p in PERIODS:
        t = time.time()
        df = fetch_period(api_name, p, fields)
        # keep only consolidated (report_type == '1' means 合并报表)
        if "report_type" in df.columns:
            df = df[df["report_type"].astype(str) == "1"]
        # drop obvious restatement dupes: keep earliest ann_date per (ts_code, end_date)
        if len(df) and "ts_code" in df.columns and "end_date" in df.columns:
            df = df.sort_values(["ts_code", "end_date", "ann_date"])
            df = df.groupby(["ts_code", "end_date"], as_index=False).first()
        out.append(df)
        print(f"  {api_name} {p}: {len(df)} rows ({time.time()-t:.1f}s)")
    return pd.concat(out, ignore_index=True)


print("\n--- income ---")
income = fetch_all("income_vip", INCOME_FIELDS)
income.to_parquet(f"{CACHE}/income.parquet", index=False)

print("\n--- balancesheet ---")
bs = fetch_all("balancesheet_vip", BS_FIELDS)
bs.to_parquet(f"{CACHE}/balancesheet.parquet", index=False)

print("\n--- cashflow ---")
cf = fetch_all("cashflow_vip", CF_FIELDS)
cf.to_parquet(f"{CACHE}/cashflow.parquet", index=False)

print("\nDone. Row counts:")
print(f"  income       {len(income):>8}")
print(f"  balancesheet {len(bs):>8}")
print(f"  cashflow     {len(cf):>8}")
