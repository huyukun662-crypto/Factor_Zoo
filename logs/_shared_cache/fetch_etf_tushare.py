#!/usr/bin/env python3
"""Fetch a wide A-share ETF universe via Tushare (paid token).

Filters:
- listed by 2020-06-30 (so we have ≥ ~5y of history before the 2026 cutoff)
- not delisted as of fetch
- invest_type ∈ {被动指数型, 增强指数型}  (equity index trackers)
- name does NOT contain {债, 货币, REIT, 信用, 短债, 中债, 国债}
- equity / commodity broad/sector ETFs only

Output: /home/user/Factor_Zoo/logs/_shared_cache/etf_daily_tushare.parquet
Columns: date, symbol, open, high, low, close, volume, amount, adj_factor
where close/open/high/low are FORWARD-adjusted (multiplied by adj_factor /
latest_adj_factor) so total-return adjusted at present price.

Run from repo root:
    TS_TOKEN=... python3 logs/_shared_cache/fetch_etf_tushare.py
"""
import os, time, json
from pathlib import Path
import numpy as np
import pandas as pd
import tushare as ts

CACHE = Path("/home/user/Factor_Zoo/logs/_shared_cache")
CACHE.mkdir(parents=True, exist_ok=True)

TOKEN = os.environ.get("TS_TOKEN") or "ddd1b26b20ff085ac9b60c9bd902ae76bbff60910863e8cc0168da53"
ts.set_token(TOKEN)
pro = ts.pro_api()

START = "20190101"
END   = "20260501"

EXCLUDE_NAME_TOKENS = ["债", "货币", "REIT", "信用", "短债", "中债", "国债",
                       "现金", "理财", "存单", "城投"]
KEEP_INVEST_TYPES = {"被动指数型", "增强指数型"}


def select_universe():
    df = pro.fund_basic(market="E")
    df["list_date"] = df["list_date"].astype("Int64")
    df = df[(df.list_date <= 20200630) & (df.delist_date.isna())]
    df = df[df.invest_type.isin(KEEP_INVEST_TYPES)]
    mask = ~df.name.fillna("").apply(
        lambda s: any(tok in s for tok in EXCLUDE_NAME_TOKENS))
    df = df[mask].copy()
    df = df.sort_values("ts_code").reset_index(drop=True)
    return df


def fetch_one(ts_code: str, retry=3) -> pd.DataFrame:
    last_err = None
    for k in range(retry):
        try:
            d = pro.fund_daily(ts_code=ts_code, start_date=START, end_date=END)
            a = pro.fund_adj(ts_code=ts_code, start_date=START, end_date=END)
            if d.empty or a.empty:
                return pd.DataFrame()
            df = d.merge(a, on=["ts_code", "trade_date"], how="left")
            df = df.sort_values("trade_date").reset_index(drop=True)
            df["adj_factor"] = df.adj_factor.ffill().bfill()
            latest = df.adj_factor.iloc[-1]
            ratio  = df.adj_factor / latest
            for c in ("open", "high", "low", "close", "pre_close"):
                df[c] = df[c] * ratio
            df = df.rename(columns={"trade_date": "date", "ts_code": "symbol",
                                    "vol": "volume"})
            df["date"] = pd.to_datetime(df.date, format="%Y%m%d")
            df = df[["date", "symbol", "open", "high", "low", "close",
                    "volume", "amount", "adj_factor"]]
            return df
        except Exception as e:
            last_err = e
            time.sleep(0.6 * (2 ** k))
    print(f"   FAIL {ts_code}: {last_err}")
    return pd.DataFrame()


def main():
    uni = select_universe()
    print(f"[uni] {len(uni)} candidate ETFs")
    frames = []
    log = []
    tic_total = time.time()
    for i, row in uni.iterrows():
        sym = row.ts_code
        tic = time.time()
        df = fetch_one(sym)
        n  = len(df)
        msg = f"[{i+1:>3}/{len(uni)}] {sym:<12} {row['name'][:18]:<20} {n:>4} bars  {time.time()-tic:.2f}s"
        if n >= 1000:
            frames.append(df)
            msg += "  KEEP"
        else:
            msg += "  DROP"
        if i % 10 == 0:
            print(msg)
        log.append(msg)
        time.sleep(0.18)   # rate-limit pad

    panel = pd.concat(frames, ignore_index=True)
    panel = panel.sort_values(["symbol", "date"]).reset_index(drop=True)
    out = CACHE / "etf_daily_tushare.parquet"
    panel.to_parquet(out, index=False)
    summary = (f"\nTOTAL rows={len(panel)} symbols={panel.symbol.nunique()} "
               f"date_min={panel.date.min():%Y-%m-%d} date_max={panel.date.max():%Y-%m-%d} "
               f"elapsed={time.time()-tic_total:.1f}s")
    print(summary); log.append(summary)
    (CACHE / "fetch_tushare.log").write_text("\n".join(log) + "\n")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
