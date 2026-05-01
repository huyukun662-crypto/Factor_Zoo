#!/usr/bin/env python3
"""Fetch expanded A-share ETF universe (target ≥ 50 names with full history).

Adds ~30 candidate tickers to the existing 30-ETF universe via Yahoo v8 endpoint.
Filters by date_min ≤ 2020-06 and bar count ≥ 1300 to ensure usable history.
Writes to /home/user/Factor_Zoo/logs/_shared_cache/etf_daily_extended.parquet.
"""
import json, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import numpy as np
import pandas as pd

CACHE = Path("/home/user/Factor_Zoo/logs/_shared_cache")
CACHE.mkdir(parents=True, exist_ok=True)

# Original 30 (after dropping 4) + ~50 new candidates
SYMBOLS_ORIG = [
    "510300.SS", "510500.SS", "510050.SS", "159915.SZ", "510180.SS",
    "159949.SZ", "588000.SS", "588080.SS", "510880.SS",
    "512880.SS", "512660.SS", "512170.SS", "512760.SS", "515030.SS",
    "512290.SS", "512690.SS", "512980.SS", "518880.SS",
    "512480.SS", "159819.SZ", "515880.SS", "159890.SZ", "159869.SZ",
    "159857.SZ", "159755.SZ", "512010.SS", "159992.SZ", "159980.SZ",
    "515220.SS", "515210.SS",
]

SYMBOLS_NEW_CANDIDATES = [
    # broad / size variants
    "510310.SS",   # HS300
    "510330.SS",   # HS300
    "159919.SZ",   # 沪深300 (深圳上市版本)
    "510510.SS",   # 治理ETF
    "510630.SS",   # 商品
    "159901.SZ",   # 深100ETF
    "159902.SZ",   # 中小板ETF
    "159903.SZ",   # 深成长
    "159905.SZ",   # 深红利
    "159907.SZ",   # 创业板
    "159912.SZ",   # 沪深300
    "159922.SZ",   # 中证500
    "159928.SZ",   # 中证消费
    "510710.SS",   # 上证民营
    "510810.SS",   # 上海国企
    "510060.SS",   # 央企
    # additional industries / themes (long history)
    "510210.SS",   # 综指
    "510170.SS",   # 治理 / 商品
    "510650.SS",   # 金融
    "510660.SS",   # 医药
    "159929.SZ",   # 医药卫生
    "159938.SZ",   # 医药
    "159968.SZ",   # 中证军工
    "159931.SZ",   # 金融地产
    "159930.SZ",   # 资源
    "159973.SZ",   # 红利
    "510630.SS",   # 商品
    "513100.SS",   # 纳指
    "513050.SS",   # 中概互联
    "513900.SS",   # 港股通
    "513500.SS",   # 标普500
    "159920.SZ",   # 恒生ETF
    "159967.SZ",   # 中证创成
    "159928.SZ",   # 中证消费
    # bond ETFs (cross-asset)
    "511010.SS",   # 国债ETF
    "511260.SS",   # 10年国债
    "511220.SS",   # 城投债
    "511880.SS",   # 银华日利 (短债)
    "511810.SS",   # 易方达国债
    # commodity / additional
    "159985.SZ",   # 豆粕
    "159980.SZ",   # 有色 (already in)
    "162411.SZ",   # 华宝油气
]
SYMBOLS_NEW_CANDIDATES = sorted(set(SYMBOLS_NEW_CANDIDATES) - set(SYMBOLS_ORIG))

START = datetime(2019, 1, 1, tzinfo=timezone.utc)
END   = datetime(2026, 5, 1, tzinfo=timezone.utc)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Referer": "https://finance.yahoo.com/",
    "Accept": "application/json, text/plain, */*",
}


def fetch_one(symbol: str) -> pd.DataFrame:
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{symbol}?interval=1d"
           f"&period1={int(START.timestamp())}&period2={int(END.timestamp())}"
           f"&events=history&includeAdjustedClose=true")
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=20) as r:
        body = json.load(r)
    chart = body["chart"]["result"][0]
    ts = chart.get("timestamp", [])
    quote = chart["indicators"]["quote"][0]
    adj = chart["indicators"].get("adjclose", [{}])[0].get("adjclose", [np.nan]*len(ts))
    if not ts:
        return pd.DataFrame()
    df = pd.DataFrame({
        "date": pd.to_datetime(ts, unit="s", utc=True).tz_convert("Asia/Shanghai").normalize().tz_localize(None),
        "open": quote.get("open"), "high": quote.get("high"), "low": quote.get("low"),
        "close": quote.get("close"), "volume": quote.get("volume"),
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


def main():
    log = []
    new_frames = []
    candidates = SYMBOLS_NEW_CANDIDATES
    print(f"Trying {len(candidates)} new candidates")
    for sym in candidates:
        tic = time.time()
        try:
            df = fetch_one(sym)
            n = len(df)
            if n == 0:
                msg = f"[{sym:<12}] EMPTY"
            else:
                date_min = df.date.min()
                date_max = df.date.max()
                msg = f"[{sym:<12}] {n:5d} bars  {date_min:%Y-%m-%d} → {date_max:%Y-%m-%d}"
                # only keep if has >= 1300 bars and starts <= 2020-06
                if n >= 1300 and date_min <= pd.Timestamp("2020-06-30"):
                    new_frames.append(df)
                    msg += "  KEEP"
                else:
                    msg += "  DROP (too short)"
        except Exception as exc:
            msg = f"[{sym:<12}] FAIL {type(exc).__name__}: {exc}"
        print(msg); log.append(msg)
        time.sleep(0.3)

    if not new_frames:
        print("No new keepable symbols")
        return

    new_panel = pd.concat(new_frames, ignore_index=True)
    new_panel = new_panel.sort_values(["symbol", "date"]).reset_index(drop=True)
    print(f"\nNew keepable symbols: {new_panel.symbol.nunique()}")

    # merge with original
    orig = pd.read_parquet(CACHE / "etf_daily.parquet")
    merged = pd.concat([orig, new_panel], ignore_index=True)
    merged = merged.drop_duplicates(["date", "symbol"]).sort_values(["symbol", "date"]).reset_index(drop=True)
    print(f"Merged total symbols: {merged.symbol.nunique()}, rows: {len(merged)}")

    out = CACHE / "etf_daily_extended.parquet"
    merged.to_parquet(out, index=False)
    with (CACHE / "fetch_extended.log").open("w") as f:
        f.write("\n".join(log) + f"\n\nFinal merged symbols: {merged.symbol.nunique()}\n")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
