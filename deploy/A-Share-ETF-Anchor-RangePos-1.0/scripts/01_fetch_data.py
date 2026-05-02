"""
01_fetch_data.py — Fetch the 32 A-share ETFs needed by the
anchor / range-position strategy. Uses Yahoo Finance v8 chart endpoint
(no Tushare token required).

Outputs (in ./data_cache/):
  - etf_daily.parquet       full panel (date, symbol, OHLCV, amount)
  - fetch.log               per-symbol fetch result
"""
from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "data_cache"
CACHE.mkdir(parents=True, exist_ok=True)

# 32-symbol ETF universe matches logs/_shared_cache/fetch_etf_daily.py.
SYMBOLS = [
    # broad index (10)
    "510300.SS", "510500.SS", "510050.SS", "159915.SZ", "510180.SS",
    "159949.SZ", "588000.SS", "588080.SS", "512100.SS", "510880.SS",
    # industry / thematic (9)
    "512880.SS", "512660.SS", "512170.SS", "512760.SS", "515030.SS",
    "512290.SS", "515050.SS", "512690.SS", "512980.SS",
    # commodity / defensive (1)
    "518880.SS",
    # extra thematic (12, dropping 512800.SS / 515170.SS due to truncated
    # history per session 20260502 finding)
    "512480.SS", "159819.SZ", "515880.SS", "159890.SZ", "159869.SZ",
    "159857.SZ", "159755.SZ", "512010.SS",
    "159992.SZ", "159980.SZ", "515220.SS", "515210.SS",
]

START = datetime(2019, 1, 1, tzinfo=timezone.utc)
END = datetime.now(tz=timezone.utc)

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
    adj = chart["indicators"].get("adjclose", [{}])[0].get(
        "adjclose", [np.nan] * len(ts))
    if not ts:
        return pd.DataFrame()
    df = pd.DataFrame({
        "date": pd.to_datetime(ts, unit="s", utc=True)
        .tz_convert("Asia/Shanghai").normalize().tz_localize(None),
        "open":   quote.get("open"),
        "high":   quote.get("high"),
        "low":    quote.get("low"),
        "close":  quote.get("close"),
        "volume": quote.get("volume"),
        "adjclose": adj,
    })
    df["symbol"] = symbol
    r = df["adjclose"] / df["close"]
    for c in ("open", "high", "low", "close"):
        df[c] = df[c] * r
    df = df.drop(columns=["adjclose"])
    df["amount"] = df["close"] * df["volume"]
    df = df.dropna(subset=["close"]).reset_index(drop=True)
    return df


def main() -> None:
    log_path = CACHE / "fetch.log"
    out = CACHE / "etf_daily.parquet"
    if out.exists():
        print(f"[cache] {out} exists; delete to refresh.")
        return
    frames = []
    t0 = time.time()
    with log_path.open("w") as log:
        for sym in SYMBOLS:
            tic = time.time()
            try:
                df = fetch_one(sym)
                msg = f"[{sym:<12}] {len(df):5d} bars in {time.time()-tic:.2f}s"
                frames.append(df)
            except Exception as exc:
                msg = f"[{sym:<12}] FAIL {type(exc).__name__}: {exc}"
            print(msg)
            log.write(msg + "\n")
            log.flush()
            time.sleep(0.35)
        panel = pd.concat(frames, ignore_index=True)
        panel = panel.sort_values(["symbol", "date"]).reset_index(drop=True)
        panel.to_parquet(out, index=False)
        summary = (
            f"\nTOTAL rows={len(panel)} symbols={panel['symbol'].nunique()} "
            f"date_min={panel['date'].min():%Y-%m-%d} "
            f"date_max={panel['date'].max():%Y-%m-%d} "
            f"elapsed={time.time()-t0:.1f}s\n"
        )
        print(summary)
        log.write(summary)


if __name__ == "__main__":
    main()
