#!/usr/bin/env python3
"""
Show current holdings of the R2 winner strategy.

Winner: k=40 ⊕ k=80 long-only top-3 monthly ensemble + 55% gold blend
Universe: 34 A-share thematic ETFs
Rebalance: every 4th Friday close, 20-bar hold
"""
from pathlib import Path
import numpy as np
import pandas as pd

DATA_SRC = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs/etf_daily.parquet")
GOLD_SYMBOL = "159934.SZ"
GOLD_WEIGHT = 0.55
LONG_N = 3
COMMON_START = pd.Timestamp("2019-01-04")
STAGGERED_JOIN_BARS = 60


def main():
    df = pd.read_parquet(DATA_SRC).rename(columns={"trade_date": "date", "ts_code": "symbol"})
    df = df.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"]).reset_index(drop=True)
    name_map = df.groupby("symbol")["etf_name"].first().to_dict()
    for k in [40, 80]:
        df[f"logret_{k}d"] = df.groupby("symbol")["close_adj"].transform(
            lambda s, k=k: np.log(s / s.shift(k))
        )
    df["bar_age"] = df.groupby("symbol").cumcount()
    df["is_live"] = df["bar_age"] >= STAGGERED_JOIN_BARS
    df = df[df["date"] >= COMMON_START].reset_index(drop=True)

    # Build signals
    def demean(col):
        s = df[col].where(df["is_live"])
        return s - s.groupby(df["date"]).transform("mean")

    df["sig40"] = demean("logret_40d").mul(-1)
    df["sig80"] = demean("logret_80d").mul(-1)

    # Find most recent rebalance dates (every 4th Friday from common start)
    all_d = pd.DatetimeIndex(sorted(df["date"].unique()))
    fridays = all_d[all_d.dayofweek == 4]
    rebals = fridays[::4]
    latest_rebal = rebals[-1]
    prev_rebal = rebals[-2]
    print(f"Latest rebalance date: {latest_rebal.date()}  (previous: {prev_rebal.date()})")
    print(f"Data-end date:         {df['date'].max().date()}")
    print(f"Gold weight:           {GOLD_WEIGHT:.0%}    Reversal leg weight: {1-GOLD_WEIGHT:.0%}\n")

    def show_rebal(rd):
        print(f"\n========== Rebalance on {rd.date()} ==========")
        snap = df[(df["date"] == rd) & df["is_live"]].set_index("symbol")
        if snap.empty:
            print("  (no data on this date)")
            return
        # k=40 top 3
        top40 = snap["sig40"].sort_values(ascending=False).dropna().head(LONG_N)
        # k=80 top 3
        top80 = snap["sig80"].sort_values(ascending=False).dropna().head(LONG_N)

        print(f"\n--- Leg A: k=40 long-only top-3 (signal = -logret_40d, demeaned) ---")
        print(f"{'rank':>4s}  {'symbol':<12s}  {'name':<14s}  {'raw_ret_40d':>11s}  {'weight':>7s}")
        wA = (1 - GOLD_WEIGHT) * 0.5 / LONG_N
        for r, (sym, s) in enumerate(top40.items(), 1):
            raw40 = snap.loc[sym, "logret_40d"]
            print(f"{r:>4d}  {sym:<12s}  {name_map.get(sym, ''):<14s}  {raw40:>+11.2%}  {wA:>7.2%}")

        print(f"\n--- Leg B: k=80 long-only top-3 (signal = -logret_80d, demeaned) ---")
        print(f"{'rank':>4s}  {'symbol':<12s}  {'name':<14s}  {'raw_ret_80d':>11s}  {'weight':>7s}")
        wB = (1 - GOLD_WEIGHT) * 0.5 / LONG_N
        for r, (sym, s) in enumerate(top80.items(), 1):
            raw80 = snap.loc[sym, "logret_80d"]
            print(f"{r:>4d}  {sym:<12s}  {name_map.get(sym, ''):<14s}  {raw80:>+11.2%}  {wB:>7.2%}")

        # Aggregate (handle overlap)
        holdings = {}
        for sym in top40.index:
            holdings[sym] = holdings.get(sym, 0.0) + wA
        for sym in top80.index:
            holdings[sym] = holdings.get(sym, 0.0) + wB
        holdings[GOLD_SYMBOL] = holdings.get(GOLD_SYMBOL, 0.0) + GOLD_WEIGHT

        print(f"\n--- Aggregate portfolio at {rd.date()} ---")
        print(f"{'symbol':<12s}  {'name':<14s}  {'weight':>8s}  {'leg':<8s}")
        for sym, w in sorted(holdings.items(), key=lambda x: -x[1]):
            legs = []
            if sym in top40.index: legs.append("k40")
            if sym in top80.index: legs.append("k80")
            if sym == GOLD_SYMBOL: legs.append("gold")
            print(f"{sym:<12s}  {name_map.get(sym, ''):<14s}  {w:>8.2%}  {'+'.join(legs):<8s}")

        print(f"\n  total exposure: {sum(holdings.values()):.1%}  (non-gold: {sum(v for s,v in holdings.items() if s != GOLD_SYMBOL):.1%})")

    show_rebal(latest_rebal)
    show_rebal(prev_rebal)


if __name__ == "__main__":
    main()
