#!/usr/bin/env python3
"""Round 2 Direction 4: extend universe to 44-49 ETFs by adding broad-index ETFs.

Fetches daily OHLCV via Yahoo Finance v8/chart for:
- 510300.SS (沪深300 ETF)
- 510500.SS (中证500 ETF)
- 510050.SS (上证50 ETF)
- 510180.SS (180ETF)
- 588000.SS (科创50 ETF)
- 588080.SS (科创板50 ETF)
- 512100.SS (中证1000 ETF)  -- retry
- 159915.SZ (创业板 ETF)
- 159949.SZ (创业板50 ETF)
- 159845.SZ (中证1000 ETF, SZ)
- 510900.SS (H股 ETF)
- 518880.SS (黄金 ETF, SS side)  -- deduped vs 159934.SZ
- 513100.SS (纳指 ETF)
- 513050.SS (中概互联网 ETF)
"""
from __future__ import annotations

import io
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "round2"
OUT.mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"

# code -> (yahoo_sym, name, group)
BROAD = [
    ("510300.SH", "510300.SS", "沪深300ETF", "大盘指数"),
    ("510500.SH", "510500.SS", "中证500ETF", "大盘指数"),
    ("510050.SH", "510050.SS", "上证50ETF", "大盘指数"),
    ("510180.SH", "510180.SS", "180ETF", "大盘指数"),
    ("588000.SH", "588000.SS", "科创50ETF", "大盘指数"),
    ("588080.SH", "588080.SS", "科创板50ETF", "大盘指数"),
    ("159915.SZ", "159915.SZ", "创业板ETF", "大盘指数"),
    ("159949.SZ", "159949.SZ", "创业板50ETF", "大盘指数"),
    ("159845.SZ", "159845.SZ", "中证1000ETF", "大盘指数"),
    ("510900.SH", "510900.SS", "H股ETF", "港股"),
    ("513050.SH", "513050.SS", "中概互联网ETF", "港股"),
    ("513100.SH", "513100.SS", "纳指ETF", "海外"),
    ("159941.SZ", "159941.SZ", "纳指ETF（SZ）", "海外"),
    ("518880.SH", "518880.SS", "黄金ETF（SH）", "黄金"),
]

START = "2019-01-01"
END = "2026-04-22"


def fetch(sym_yahoo: str) -> pd.DataFrame | None:
    s = int(pd.Timestamp(START).timestamp())
    e = int(pd.Timestamp(END).timestamp()) + 86400
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{sym_yahoo}"
        f"?period1={s}&period2={e}&interval=1d&includePrePost=false&events=history"
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
    except urllib.error.HTTPError as exc:
        print(f"   {sym_yahoo}: HTTP {exc.code}")
        return None
    except Exception as exc:
        print(f"   {sym_yahoo}: {exc}")
        return None
    try:
        j = json.loads(raw.decode("utf-8"))
        res = j["chart"]["result"][0]
    except Exception as exc:
        print(f"   {sym_yahoo}: parse error {exc}")
        return None
    ts = res.get("timestamp") or []
    q = res["indicators"]["quote"][0]
    ac = None
    try:
        ac = res["indicators"]["adjclose"][0]["adjclose"]
    except Exception:
        ac = q.get("close", [])
    if not ts:
        print(f"   {sym_yahoo}: empty")
        return None
    df = pd.DataFrame({
        "date":  pd.to_datetime(ts, unit="s").tz_localize("UTC").tz_convert("Asia/Shanghai").normalize().tz_localize(None),
        "open":  q.get("open"),
        "high":  q.get("high"),
        "low":   q.get("low"),
        "close": q.get("close"),
        "vol":   q.get("volume"),
        "close_adj": ac,
    })
    return df.dropna(subset=["close"])


def main():
    rows = []
    for ts_code, yh, name, group in BROAD:
        print(f"[fetch] {ts_code} ({yh}) = {name}")
        df = fetch(yh)
        if df is None or len(df) < 200:
            print(f"   SKIP ({len(df) if df is not None else 0} bars)")
            time.sleep(0.8)
            continue
        df["ts_code"] = ts_code
        rows.append(df)
        time.sleep(0.8)
    if not rows:
        raise SystemExit("no data fetched")
    all_df = pd.concat(rows, ignore_index=True).sort_values(["ts_code", "date"]).reset_index(drop=True)

    # assemble universe meta
    meta = pd.DataFrame([
        {"name": name, "ts_code": ts_code, "group": group}
        for ts_code, yh, name, group in BROAD
        if ts_code in all_df["ts_code"].unique()
    ])

    all_df.to_parquet(OUT / "etf_daily_broad.parquet", index=False)
    meta.to_csv(OUT / "etf_universe_broad.csv", index=False)
    print(f"\n  broad fetched: {all_df['ts_code'].nunique()} ETFs, {len(all_df)} rows")
    print(f"  bars per ETF:")
    print(all_df.groupby("ts_code")["date"].count().sort_values().to_string())
    print(f"  wrote: {OUT/'etf_daily_broad.parquet'}")


if __name__ == "__main__":
    main()
