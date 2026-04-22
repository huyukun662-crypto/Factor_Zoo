"""
Fetch ETF daily data for the 34-ETF tradable universe.
Diagnostic: report inception date / coverage per ETF.
"""
import os, sys, time
from pathlib import Path
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
pro = ts.pro_api(os.environ["TUSHARE_TOKEN"])
say = lambda s: print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

# ---- 34 ETF universe (user-provided) ----
ETFS = {
    # 科技成长
    "半导体ETF": "512480.SH", "消费电子ETF": "159779.SZ", "软件ETF": "515230.SH",
    "通信ETF": "515880.SH", "云计算ETF": "159890.SZ", "AI_ETF": "515980.SH",
    "游戏ETF": "159869.SZ",
    # 新能源
    "光伏ETF": "159857.SZ", "电池ETF": "159755.SZ", "新能源车ETF": "515030.SH",
    "电网设备ETF": "159326.SZ",
    # 高端制造
    "机器人ETF": "562500.SH", "航空航天ETF": "159227.SZ", "军工ETF": "512660.SH",
    # 大金融
    "银行ETF": "512800.SH", "证券ETF": "512880.SH", "非银ETF": "159892.SZ",
    # 大消费
    "酒ETF": "512690.SH", "家电ETF": "561120.SH", "食品ETF": "515170.SH",
    "医药ETF": "512010.SH", "创新药ETF": "159992.SZ", "医疗器械ETF": "159883.SZ",
    # 周期 / 上游
    "有色ETF": "159980.SZ", "煤炭ETF": "515220.SH", "钢铁ETF": "515210.SH",
    "石油ETF": "561360.SH", "化工ETF": "159870.SZ", "稀土ETF": "159713.SZ",
    "黄金ETF": "159934.SZ",
    # 地产链
    "房地产ETF": "512200.SH", "建材ETF": "516750.SH",
    # 农业
    "畜牧ETF": "159867.SZ",
    # 红利
    "红利ETF": "515080.SH",
}

GROUPS = {
    "科技成长": ["半导体ETF","消费电子ETF","软件ETF","通信ETF","云计算ETF","AI_ETF","游戏ETF"],
    "新能源":   ["光伏ETF","电池ETF","新能源车ETF","电网设备ETF"],
    "高端制造": ["机器人ETF","航空航天ETF","军工ETF"],
    "大金融":   ["银行ETF","证券ETF","非银ETF"],
    "大消费":   ["酒ETF","家电ETF","食品ETF","医药ETF","创新药ETF","医疗器械ETF"],
    "周期资源": ["有色ETF","煤炭ETF","钢铁ETF","石油ETF","化工ETF","稀土ETF","黄金ETF"],
    "地产链":   ["房地产ETF","建材ETF"],
    "农业":     ["畜牧ETF"],
    "红利":     ["红利ETF"],
}

# Save mapping
pd.DataFrame(
    [{"name": n, "ts_code": c,
      "group": next((g for g,m in GROUPS.items() if n in m), None)}
     for n, c in ETFS.items()]
).to_csv(OUT / "etf_universe.csv", index=False)
say(f"ETF universe: {len(ETFS)} ETFs across {len(GROUPS)} groups")

# ---- Fetch fund_daily per ETF ----
FD = CACHE / "fund_daily_34.parquet"
if FD.exists():
    fd = pd.read_parquet(FD)
    say(f"Loaded cached fund_daily: {len(fd):,} rows")
else:
    all_rows = []
    for name, code in ETFS.items():
        for tries in range(3):
            try:
                df = pro.fund_daily(ts_code=code, start_date="20150101", end_date="20260422")
                break
            except Exception as e:
                time.sleep(2 + tries)
        else:
            df = pd.DataFrame()
        if len(df) == 0:
            say(f"  NO DATA for {name} ({code})"); continue
        df["etf_name"] = name
        all_rows.append(df)
        say(f"  {name} ({code}): {len(df)} rows, {df['trade_date'].min()} → {df['trade_date'].max()}")
    fd = pd.concat(all_rows, ignore_index=True)
    fd["trade_date"] = pd.to_datetime(fd["trade_date"])
    fd.to_parquet(FD)
    say(f"Cached: {FD}")

# ---- Fetch fund_adj (adj_factor) ----
FAJ = CACHE / "fund_adj_34.parquet"
if FAJ.exists():
    fadj = pd.read_parquet(FAJ)
else:
    all_rows = []
    for name, code in ETFS.items():
        for tries in range(3):
            try:
                df = pro.fund_adj(ts_code=code, start_date="20150101", end_date="20260422")
                break
            except Exception as e:
                time.sleep(2 + tries)
        else:
            df = pd.DataFrame()
        if len(df) == 0: continue
        all_rows.append(df)
    fadj = pd.concat(all_rows, ignore_index=True)
    fadj["trade_date"] = pd.to_datetime(fadj["trade_date"])
    fadj.to_parquet(FAJ)
    say(f"Cached: {FAJ}")

# Merge
fd = fd.merge(fadj, on=["ts_code", "trade_date"], how="left")
fd["close_adj"] = fd["close"] * fd["adj_factor"].fillna(1.0)
fd = fd.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)

# ---- Coverage diagnostic ----
cov = (fd.groupby(["etf_name", "ts_code"])
       .agg(first=("trade_date", "min"), last=("trade_date", "max"), n=("trade_date", "count"))
       .reset_index().sort_values("first"))
cov["group"] = cov["etf_name"].map({n: next((g for g,m in GROUPS.items() if n in m), None) for n in ETFS})
cov["years"] = (cov["last"] - cov["first"]).dt.days / 365.25
say("\n===== ETF COVERAGE =====")
print(cov[["etf_name","ts_code","group","first","last","n","years"]].to_string(index=False))
cov.to_csv(OUT/"etf_coverage.csv", index=False)

# ---- Build ETF daily returns + turnover ----
fd["ret"] = fd.groupby("ts_code")["close_adj"].pct_change()
# turnover proxy = amount / circ market cap (ETF doesn't have circ_mv; use amount itself normalized by etf's own rolling amount)
# Simpler: use dollar-amount — higher amount = more activity
fd["turnover_proxy"] = fd["amount"]  # raw amount (千元); cross-section z within day

# Save daily ETF panel
fd[["trade_date","ts_code","etf_name","close","close_adj","ret","vol","amount","turnover_proxy"]].to_parquet(
    OUT / "etf_daily.parquet"
)
say(f"[done] wrote etf_daily.parquet ({len(fd):,} rows)")

# Weekly aggregation
fd["year_week"] = fd["trade_date"].dt.strftime("%G-%V")
fd["gross"] = 1.0 + fd["ret"].fillna(0)
fd["cum"] = fd.groupby("ts_code")["gross"].cumprod()
weekly = (fd.groupby(["ts_code","etf_name","year_week"], sort=False)
          .agg(trade_week=("trade_date","last"),
               cum_w=("cum","last"),
               turnover_w=("turnover_proxy","mean"),
               amount_w=("amount","sum"),
               vol_w=("vol","sum"))
          .reset_index())
weekly = weekly.sort_values(["ts_code","trade_week"])
weekly["ret_w"] = weekly.groupby("ts_code")["cum_w"].pct_change()
weekly = weekly.dropna(subset=["ret_w"]).copy()
weekly.to_parquet(OUT / "etf_weekly.parquet")
say(f"[done] wrote etf_weekly.parquet ({len(weekly):,} rows, {weekly['trade_week'].nunique()} weeks)")
