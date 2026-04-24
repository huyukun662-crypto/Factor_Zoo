"""
Fetch BTC-USD 1-minute OHLCV bars from Coinbase Exchange public API.

Coinbase endpoint:
    GET https://api.exchange.coinbase.com/products/BTC-USD/candles
      ?granularity=60       (seconds; 60=1min)
      &start=ISO8601
      &end=ISO8601
Returns: list of [ts_seconds, low, high, open, close, volume] in DESC order.
Max 300 candles per request. Public rate limit ~10 req/s.

Target: ~60 days ending (today - 1 day) in UTC. 1440 min/day => ~86,400 bars.
"""
from __future__ import annotations
import argparse, sys, time, urllib.request, json
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd


URL_BASE = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
CANDLES_PER_REQ = 300            # Coinbase cap
SECONDS_PER_MIN = 60
DEFAULT_OUT = "/home/user/Factor_Zoo/logs/20260423_btc_minute_reversal_v1/inputs/btc_1m.parquet"


def log(m: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)


def fetch_one(start: datetime, end: datetime, tries: int = 4) -> list:
    """GET one chunk (<= 300 bars)."""
    url = (f"{URL_BASE}?granularity={SECONDS_PER_MIN}"
           f"&start={start.isoformat().replace('+00:00','Z')}"
           f"&end={end.isoformat().replace('+00:00','Z')}")
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Factor_Zoo/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode("utf-8"))
            return data
        except Exception as e:
            wait = 2 ** k
            log(f"  [retry {k+1}/{tries}] {e}; sleeping {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"fetch failed after {tries} tries: {url}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--end", default=None,
                    help="UTC end datetime YYYY-MM-DDTHH:MM:SSZ. "
                         "Default: most recent full UTC hour.")
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.end:
        end = datetime.fromisoformat(args.end.replace("Z","+00:00"))
    else:
        # last complete hour, UTC
        now = datetime.now(timezone.utc).replace(microsecond=0, second=0)
        end = now.replace(minute=0)
    start = end - timedelta(days=args.days)
    log(f"target window {start.isoformat()} -> {end.isoformat()}  ({args.days} days)")

    chunk_secs = CANDLES_PER_REQ * SECONDS_PER_MIN   # 5 hours
    cur = start
    rows: list[list] = []
    n_chunks = 0
    t0 = time.monotonic()
    while cur < end:
        chunk_end = min(cur + timedelta(seconds=chunk_secs), end)
        got = fetch_one(cur, chunk_end)
        rows.extend(got)
        n_chunks += 1
        if n_chunks % 20 == 0:
            log(f"  {n_chunks} chunks, {len(rows)} bars, up to {chunk_end.isoformat()}")
        cur = chunk_end
        # public-rate limit: 10 req/s. Sleep 0.12 to be safe.
        time.sleep(0.12)

    log(f"fetched {len(rows)} raw rows in {n_chunks} requests ({time.monotonic()-t0:.1f}s)")

    df = pd.DataFrame(rows, columns=["ts", "low", "high", "open", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"].astype("int64"), unit="s", utc=True)
    df = df.drop_duplicates(subset="ts").sort_values("ts").reset_index(drop=True)
    # restrict strictly to requested window
    df = df[(df["ts"] >= pd.Timestamp(start)) & (df["ts"] < pd.Timestamp(end))]

    # minute grid coverage report
    full_grid = pd.date_range(start=df["ts"].min(), end=df["ts"].max(),
                              freq="1min", tz="UTC")
    coverage = len(df) / len(full_grid) if len(full_grid) else 0
    log(f"coverage vs full 1-min grid: {len(df)}/{len(full_grid)} = {coverage:.4f}")
    log(f"range: {df['ts'].min()} -> {df['ts'].max()}")

    df.to_parquet(args.out, index=False)
    log(f"wrote {len(df)} bars -> {args.out}")


if __name__ == "__main__":
    main()
