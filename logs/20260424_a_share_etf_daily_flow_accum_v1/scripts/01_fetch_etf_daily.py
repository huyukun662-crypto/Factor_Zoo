#!/usr/bin/env python3
"""Fetch A-share ETF daily OHLCV + amount from Yahoo Finance.

Yahoo's v8/finance/chart endpoint returns JSON for A-share ETFs when
called with a browser User-Agent. Tickers use `.SS` for Shanghai and
`.SZ` for Shenzhen.

Universe = 34 A-share on-shore ETFs, merged from:
- reversal session (20260423_a_share_etf_reversal_v1): 20 ETFs (broad + thematic + gold)
- V7_gold rotation universe (20260422_industry_rotation_cn): +14 thematic ETFs

Window = 2019-01-02 → 2026-04-22 (extends one year earlier than the reversal
session so 2019 bull-market + 2020 COVID regimes sit inside TRAIN).

Usage:
    python3 01_fetch_etf_daily.py
Writes:
    ../inputs/etf_daily.parquet
    ../inputs/fetch.log
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

SESSION_ROOT = Path(__file__).resolve().parents[1]
INPUTS = SESSION_ROOT / "inputs"
INPUTS.mkdir(parents=True, exist_ok=True)

# 34 ETFs — broad-index (10), thematic/sector (23), commodity (1)
SYMBOLS = [
    # broad index (10) — from reversal session
    "510300.SS", "510500.SS", "510050.SS", "159915.SZ", "510180.SS",
    "159949.SZ", "588000.SS", "588080.SS", "512100.SS", "510880.SS",
    # industry / thematic (9) — from reversal session
    "512880.SS", "512660.SS", "512170.SS", "512760.SS", "515030.SS",
    "512290.SS", "515050.SS", "512690.SS", "512980.SS",
    # commodity / defensive (1) — from reversal session
    "518880.SS",
    # extra thematic (14) — from V7_gold universe to widen cross-section
    "512480.SS",  # 半导体
    "159819.SZ",  # 人工智能AI
    "515880.SS",  # 通信
    "159890.SZ",  # 云计算
    "159869.SZ",  # 游戏
    "159857.SZ",  # 光伏
    "159755.SZ",  # 电池
    "512800.SS",  # 银行
    "515170.SS",  # 食品
    "512010.SS",  # 医药
    "159992.SZ",  # 创新药
    "159980.SZ",  # 有色
    "515220.SS",  # 煤炭
    "515210.SS",  # 钢铁
]

START = datetime(2019, 1, 1, tzinfo=timezone.utc)
END   = datetime(2026, 4, 23, tzinfo=timezone.utc)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Referer": "https://finance.yahoo.com/",
    "Accept": "application/json, text/plain, */*",
}


def fetch_one(symbol: str) -> pd.DataFrame:
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{symbol}?interval=1d"
        f"&period1={int(START.timestamp())}&period2={int(END.timestamp())}"
        f"&events=history&includeAdjustedClose=true"
    )
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=20) as r:
        body = json.load(r)
    chart = body["chart"]["result"][0]
    ts = chart.get("timestamp", [])
    quote = chart["indicators"]["quote"][0]
    adj = chart["indicators"].get("adjclose", [{}])[0].get("adjclose", [np.nan] * len(ts))
    if not ts:
        return pd.DataFrame()
    df = pd.DataFrame({
        "date": pd.to_datetime(ts, unit="s", utc=True).tz_convert("Asia/Shanghai").normalize().tz_localize(None),
        "open":   quote.get("open"),
        "high":   quote.get("high"),
        "low":    quote.get("low"),
        "close":  quote.get("close"),
        "volume": quote.get("volume"),
        "adjclose": adj,
    })
    df["symbol"] = symbol
    # adjust OHLC by adj-close ratio so we can use adjusted prices everywhere
    r = df["adjclose"] / df["close"]
    for c in ("open", "high", "low", "close"):
        df[c] = df[c] * r
    df = df.drop(columns=["adjclose"])
    # amount in "adjusted CNY" — preserves CNY flow magnitude up to adj ratio (small)
    df["amount"] = df["close"] * df["volume"]
    df = df.dropna(subset=["close"]).reset_index(drop=True)
    return df


def main() -> None:
    log_path = INPUTS / "fetch.log"
    frames = []
    t0 = time.time()
    with log_path.open("w") as log:
        for sym in SYMBOLS:
            tic = time.time()
            try:
                df = fetch_one(sym)
                n = len(df)
                frames.append(df)
                msg = f"[{sym:<12}] {n:5d} bars in {time.time()-tic:.2f}s"
            except Exception as exc:
                msg = f"[{sym:<12}] FAIL {type(exc).__name__}: {exc}"
            print(msg)
            log.write(msg + "\n")
            log.flush()
            time.sleep(0.35)
        panel = pd.concat(frames, ignore_index=True)
        panel = panel.sort_values(["symbol", "date"]).reset_index(drop=True)
        out = INPUTS / "etf_daily.parquet"
        panel.to_parquet(out, index=False)
        summary = (
            f"\nTOTAL rows={len(panel)} "
            f"symbols={panel['symbol'].nunique()} "
            f"date_min={panel['date'].min():%Y-%m-%d} "
            f"date_max={panel['date'].max():%Y-%m-%d} "
            f"elapsed={time.time()-t0:.1f}s\n"
        )
        print(summary)
        log.write(summary)


if __name__ == "__main__":
    main()
