#!/usr/bin/env python3
"""
Current holdings for the winner: p_top3_diversified.

Top-3 long-only, monthly rebalance, cross-industry diversified
(max 1 ETF per industry cluster).

Universe: 32 thematic/industry ETFs (no 黄金, no 红利).
"""
from pathlib import Path
import numpy as np
import pandas as pd

DATA_SRC = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs/etf_daily.parquet")
STAGGERED_JOIN_BARS = 60
LONG_N = 3
COMMON_START = pd.Timestamp("2019-01-04")
EXCLUDE = ["159934.SZ", "515080.SH"]

INDUSTRY_CLUSTERS = {
    "TMT_hardware":  ["512480.SH", "159779.SZ", "159713.SZ", "515880.SH"],
    "TMT_software":  ["515230.SH", "159869.SZ", "515980.SH", "159890.SZ", "562500.SH"],
    "consumer":      ["512690.SH", "515170.SH", "561120.SH", "159867.SZ"],
    "healthcare":    ["512010.SH", "159883.SZ", "159992.SZ"],
    "financial":     ["512800.SH", "512880.SH", "159892.SZ", "512200.SH"],
    "manufacturing": ["512660.SH", "159227.SZ", "516750.SH", "159870.SZ", "515210.SH"],
    "new_energy":    ["515030.SH", "159857.SZ", "159755.SZ", "159326.SZ", "159980.SH", "515220.SH"],
    "oil_gas":       ["561360.SH"],
}
SYM2C = {s: c for c, syms in INDUSTRY_CLUSTERS.items() for s in syms}


def main():
    df = pd.read_parquet(DATA_SRC).rename(columns={"trade_date": "date", "ts_code": "symbol"})
    df = df[~df["symbol"].isin(EXCLUDE)]
    df = df.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"]).reset_index(drop=True)
    name_map = df.groupby("symbol")["etf_name"].first().to_dict()
    df["logret_40d"] = df.groupby("symbol")["close_adj"].transform(
        lambda s: np.log(s / s.shift(40))
    )
    df["bar_age"] = df.groupby("symbol").cumcount()
    df["is_live"] = df["bar_age"] >= STAGGERED_JOIN_BARS
    df = df[df["date"] >= COMMON_START].reset_index(drop=True)
    # signal: -logret_40d, demean per date
    sig = -df["logret_40d"].where(df["is_live"])
    sig = sig - sig.groupby(df["date"]).transform("mean")
    df["sig"] = sig

    all_d = pd.DatetimeIndex(sorted(df["date"].unique()))
    rebals = all_d[all_d.dayofweek == 4][::4]
    print(f"Latest rebal: {rebals[-1].date()}  (prev {rebals[-2].date()})")
    print(f"Data end:     {df['date'].max().date()}\n")

    for label, rd in [("LATEST", rebals[-1]), ("PREVIOUS", rebals[-2])]:
        print(f"=== {label} rebalance on {rd.date()} ===")
        snap = df[df["date"] == rd].dropna(subset=["sig"])
        snap = snap[snap["is_live"]].sort_values("sig", ascending=False)
        seen = set()
        picks = []
        skipped = []
        for _, row in snap.iterrows():
            cluster = SYM2C.get(row["symbol"], "OTHER")
            if cluster in seen:
                skipped.append((row["symbol"], cluster, row["logret_40d"]))
                continue
            picks.append((row["symbol"], cluster, row["logret_40d"]))
            seen.add(cluster)
            if len(picks) >= LONG_N:
                break

        print(f"  {'rank':>4s}  {'symbol':<12s}  {'name':<14s}  {'cluster':<16s}  {'ret_40d':>10s}  {'weight':>7s}")
        for r, (sym, cl, ret) in enumerate(picks, 1):
            print(f"  {r:>4d}  {sym:<12s}  {name_map.get(sym,''):<14s}  {cl:<16s}  {ret:>+10.2%}  {1/LONG_N:>7.2%}")

        if skipped:
            print(f"\n  Skipped (cluster already filled, top signal but not picked):")
            for sym, cl, ret in skipped[:5]:
                print(f"    {sym}  {name_map.get(sym,''):<14s}  cluster={cl:<16s}  ret_40d={ret:+.2%}")
        print()


if __name__ == "__main__":
    main()
