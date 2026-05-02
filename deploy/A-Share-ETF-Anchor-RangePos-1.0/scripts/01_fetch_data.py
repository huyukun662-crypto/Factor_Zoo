"""
01_fetch_data.py — v1.1 Tushare-backed fetcher with Yahoo fallback.

Priority order:
  1. If TUSHARE_TOKEN env var is set, fetch ALL symbols from Tushare with
     forward-adjusted close (qfq). Single-source, consistent adjustment.
  2. Else fall back to Yahoo Finance (warning: 4 ETFs will have truncated
     history, see logs/20260502.../outputs/tushare_universe_verification.md).

Output: ./data_cache/etf_daily.parquet
        columns: date, symbol, open, high, low, close, volume, amount, source

v1.1 changes vs v1.0:
  - Adds 515290.SH (银行ETF天弘) — the only major A-share sector entirely
    missing from v1.0 universe.
  - Replaces 4 Yahoo-truncated ETFs with full-history Tushare data:
    512100 (中证1000), 515050 (通信), 515030 (新能源车), 159992 (创新药).
  - Symbol format internally is the Yahoo convention (.SS/.SZ) so downstream
    code from v1.0 works unchanged. The "source" column tells you which
    upstream the row came from.
"""
from __future__ import annotations
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "data_cache"
CACHE.mkdir(parents=True, exist_ok=True)

# v1.1 universe — 33 ETFs (was 32 in v1.0; +515290 banking)
SYMBOLS = [
    # broad index (10)
    "510300.SS", "510500.SS", "510050.SS", "159915.SZ", "510180.SS",
    "159949.SZ", "588000.SS", "588080.SS", "512100.SS", "510880.SS",
    # industry / thematic (10 — added 515290)
    "512880.SS", "512660.SS", "512170.SS", "512760.SS", "515030.SS",
    "512290.SS", "515050.SS", "512690.SS", "512980.SS", "515290.SS",
    # commodity / defensive (1)
    "518880.SS",
    # extra thematic (12, dropping 512800.SS / 515170.SS due to truncated
    # history per session 20260502 finding — confirmed by Tushare cross-check)
    "512480.SS", "159819.SZ", "515880.SS", "159890.SZ", "159869.SZ",
    "159857.SZ", "159755.SZ", "512010.SS",
    "159992.SZ", "159980.SZ", "515220.SS", "515210.SS",
]

START = datetime(2019, 1, 1, tzinfo=timezone.utc)
END = datetime.now(tz=timezone.utc)


# --------------------------------------------------------------------- #
# Tushare path (preferred when TUSHARE_TOKEN is set)
# --------------------------------------------------------------------- #
def yahoo_to_tushare(sym: str) -> str:
    code, ex = sym.split(".")
    return f"{code}.SH" if ex == "SS" else f"{code}.SZ"


def fetch_tushare(symbols: list[str]) -> pd.DataFrame:
    import tushare as ts
    ts.set_token(os.environ["TUSHARE_TOKEN"])
    pro = ts.pro_api()

    start = START.strftime("%Y%m%d")
    end = END.strftime("%Y%m%d")
    frames = []
    log_path = CACHE / "fetch.log"
    with log_path.open("w") as log:
        log.write(f"# v1.1 Tushare fetch  {datetime.now()}\n")
        for ysym in symbols:
            tsym = yahoo_to_tushare(ysym)
            tic = time.time()
            try:
                # qfq-adjusted bars via pro_bar (handles fund_adj internally)
                df = ts.pro_bar(
                    api=pro, ts_code=tsym, asset="FD",
                    adj="qfq",
                    start_date=start, end_date=end,
                )
                if df is None or df.empty:
                    raise RuntimeError("empty pro_bar response")
                df["date"] = pd.to_datetime(df["trade_date"])
                df = df.sort_values("date").reset_index(drop=True)
                df["symbol"] = ysym  # keep yahoo-style symbol for downstream
                df = df[["date", "symbol", "open", "high", "low", "close",
                         "vol", "amount"]].rename(columns={"vol": "volume"})
                df["amount"] = df["amount"] * 1000.0  # tushare amount is in 1k CNY
                df["source"] = "tushare_qfq"
                frames.append(df)
                msg = f"[{ysym:<12}] {len(df):5d} bars in {time.time()-tic:.2f}s  (tushare qfq)"
            except Exception as exc:
                msg = f"[{ysym:<12}] tushare FAIL {type(exc).__name__}: {exc}"
            print(msg)
            log.write(msg + "\n"); log.flush()
            time.sleep(0.20)  # be nice to API
    panel = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return panel


# --------------------------------------------------------------------- #
# Yahoo fallback (used only if no token)
# --------------------------------------------------------------------- #
HEADERS = {
    "User-Agent": "Mozilla/5.0 AppleWebKit/537.36 Chrome/125.0 Safari/537.36",
    "Referer": "https://finance.yahoo.com/",
    "Accept": "application/json, text/plain, */*",
}


def fetch_yahoo_one(symbol: str) -> pd.DataFrame:
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
        "open": quote.get("open"), "high": quote.get("high"),
        "low": quote.get("low"), "close": quote.get("close"),
        "volume": quote.get("volume"),
        "adjclose": adj,
    })
    df["symbol"] = symbol
    r = df["adjclose"] / df["close"]
    for c in ("open", "high", "low", "close"):
        df[c] = df[c] * r
    df = df.drop(columns=["adjclose"])
    df["amount"] = df["close"] * df["volume"]
    df["source"] = "yahoo_qfq"
    df = df.dropna(subset=["close"]).reset_index(drop=True)
    return df


def fetch_yahoo(symbols: list[str]) -> pd.DataFrame:
    frames = []
    log_path = CACHE / "fetch.log"
    with log_path.open("w") as log:
        log.write(f"# v1.1 Yahoo fallback fetch  {datetime.now()}\n")
        log.write("# WARNING: 4 ETFs will have truncated history "
                  "(512100, 515050, 515030, 159992).\n"
                  "# Use TUSHARE_TOKEN env var for full history.\n")
        for sym in symbols:
            tic = time.time()
            try:
                df = fetch_yahoo_one(sym)
                msg = f"[{sym:<12}] {len(df):5d} bars in {time.time()-tic:.2f}s  (yahoo)"
                frames.append(df)
            except Exception as exc:
                msg = f"[{sym:<12}] yahoo FAIL {type(exc).__name__}: {exc}"
            print(msg)
            log.write(msg + "\n"); log.flush()
            time.sleep(0.35)
    panel = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return panel


def main() -> None:
    out = CACHE / "etf_daily.parquet"
    if out.exists():
        print(f"[cache] {out} exists; delete to refresh.")
        return

    if os.environ.get("TUSHARE_TOKEN"):
        try:
            import tushare as ts  # noqa: F401
            print("[mode] TUSHARE_TOKEN set → using Tushare (qfq adjusted)")
            panel = fetch_tushare(SYMBOLS)
        except ImportError:
            print("[warn] TUSHARE_TOKEN set but `tushare` not installed; "
                  "install with `pip install tushare` for full history. "
                  "Falling back to Yahoo.")
            panel = fetch_yahoo(SYMBOLS)
    else:
        print("[mode] no TUSHARE_TOKEN → falling back to Yahoo (4 ETFs will "
              "have truncated history)")
        panel = fetch_yahoo(SYMBOLS)

    if panel.empty:
        sys.exit("ERROR: no data fetched.")

    panel = panel.sort_values(["symbol", "date"]).reset_index(drop=True)
    panel.to_parquet(out, index=False)
    summary = (
        f"\nTOTAL rows={len(panel)} symbols={panel['symbol'].nunique()} "
        f"date_min={panel['date'].min():%Y-%m-%d} "
        f"date_max={panel['date'].max():%Y-%m-%d}\n"
    )
    print(summary)
    with (CACHE / "fetch.log").open("a") as log:
        log.write(summary)


if __name__ == "__main__":
    main()
