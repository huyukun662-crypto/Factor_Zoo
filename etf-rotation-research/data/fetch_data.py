"""akshare ETF daily fetcher with parquet cache.

Cache layout: data/cache/<symbol>.parquet (one file per symbol).
A small data/cache/_manifest.csv records last-fetch metadata.

Public API:
    fetch_one(symbol, start='2013-01-01', end=None, refresh=False) -> pd.DataFrame
    fetch_panel(symbols, start='2013-01-01', end=None, refresh=False) -> dict[str, pd.DataFrame]
    load_panel(symbols, start='2013-01-01', end=None) -> dict[str, pd.DataFrame]
    build_close_open_panels(panel) -> (close_df, open_df, vol_df, amount_df)
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Iterable

import pandas as pd
from tqdm import tqdm

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CN_TO_EN = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",       # 手 (100 shares)
    "成交额": "amount",       # CNY
    "振幅": "amplitude",
    "涨跌幅": "pct_chg",
    "涨跌额": "chg",
    "换手率": "turnover_rate",
}


def _normalize(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    df = df.rename(columns=CN_TO_EN).copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df = df.sort_values("date").drop_duplicates("date")
    df["symbol"] = symbol
    keep = ["date", "symbol", "open", "high", "low", "close",
            "volume", "amount", "turnover_rate"]
    return df[keep].reset_index(drop=True)


def fetch_one(symbol: str, start: str = "2013-01-01", end: str | None = None,
              refresh: bool = False, retries: int = 3, sleep: float = 0.5) -> pd.DataFrame:
    """Fetch single ETF qfq daily; cache to parquet. Returns normalized DataFrame."""
    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    cache_fp = CACHE_DIR / f"{symbol}.parquet"
    if cache_fp.exists() and not refresh:
        df = pd.read_parquet(cache_fp)
        if df["date"].min() <= pd.Timestamp(start) and df["date"].max() >= pd.Timestamp(end) - pd.Timedelta(days=7):
            return df

    import akshare as ak  # local import keeps module light when only reading cache
    last_err = None
    for attempt in range(retries):
        try:
            raw = ak.fund_etf_hist_em(
                symbol=symbol,
                period="daily",
                start_date=start.replace("-", ""),
                end_date=end.replace("-", ""),
                adjust="qfq",
            )
            if raw is None or len(raw) == 0:
                raise RuntimeError(f"empty response for {symbol}")
            df = _normalize(raw, symbol)
            df.to_parquet(cache_fp, index=False)
            return df
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(sleep * (2 ** attempt))
    raise RuntimeError(f"fetch_one failed for {symbol}: {last_err}")


def fetch_panel(symbols: Iterable[str], start: str = "2013-01-01",
                end: str | None = None, refresh: bool = False) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    failed: list[str] = []
    for s in tqdm(list(symbols), desc="fetch_panel"):
        try:
            out[s] = fetch_one(s, start=start, end=end, refresh=refresh)
        except Exception as e:  # noqa: BLE001
            failed.append(f"{s}: {e}")
    if failed:
        log_fp = CACHE_DIR / "_fetch_failed.log"
        log_fp.write_text("\n".join(failed))
        print(f"[fetch_panel] {len(failed)} failed; see {log_fp}")
    _write_manifest(out)
    return out


def load_panel(symbols: Iterable[str], start: str = "2013-01-01",
               end: str | None = None) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for s in symbols:
        fp = CACHE_DIR / f"{s}.parquet"
        if not fp.exists():
            continue
        df = pd.read_parquet(fp)
        if start:
            df = df[df["date"] >= pd.Timestamp(start)]
        if end:
            df = df[df["date"] <= pd.Timestamp(end)]
        if len(df):
            out[s] = df.reset_index(drop=True)
    return out


def _write_manifest(panel: dict[str, pd.DataFrame]) -> None:
    rows = []
    for s, df in panel.items():
        rows.append({
            "symbol": s,
            "n_bars": len(df),
            "first_date": df["date"].min().strftime("%Y-%m-%d") if len(df) else None,
            "last_date": df["date"].max().strftime("%Y-%m-%d") if len(df) else None,
            "median_amount_60d": float(df["amount"].tail(60).median()) if len(df) >= 60 else None,
        })
    pd.DataFrame(rows).to_csv(CACHE_DIR / "_manifest.csv", index=False)


def build_close_open_panels(panel: dict[str, pd.DataFrame]
                            ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Pivot list-of-DFs into wide panels keyed on date (rows) × symbol (cols).

    Returns: close, open, high, low, volume, amount
    """
    if not panel:
        raise ValueError("empty panel")
    long_df = pd.concat([df for df in panel.values()], ignore_index=True)
    long_df = long_df.sort_values(["date", "symbol"])

    def pivot(col: str) -> pd.DataFrame:
        return long_df.pivot(index="date", columns="symbol", values=col).sort_index()

    close = pivot("close")
    open_ = pivot("open")
    high = pivot("high")
    low = pivot("low")
    volume = pivot("volume")
    amount = pivot("amount")
    return close, open_, high, low, volume, amount


if __name__ == "__main__":
    smoke = fetch_one("510300", start="2013-01-01")
    print(smoke.head(2).to_string(index=False))
    print(smoke.tail(2).to_string(index=False))
    print(f"shape={smoke.shape}, first={smoke['date'].min().date()}, last={smoke['date'].max().date()}")
