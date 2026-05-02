"""
02_build_signal.py — Build the multi-window range-position signal panel.

Signal:
  for w in (60, 120, 252, 500):
      rp_w = (close - rolling_min(close, w)) /
             (rolling_max(close, w) - rolling_min(close, w))
  signal = mean of cross-section pct-rank of rp_w for each w

Outputs (in ./data_cache/):
  - signal.parquet            wide panel of (date, symbol -> signal value)
  - core_universe.json        the 20-ETF subset with sufficient history
"""
from __future__ import annotations
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "data_cache"

WINDOWS = (60, 120, 252, 500)
CORE_MIN_DAYS = 1500
DROP_FULL = {"512800.SS", "515170.SS"}


def say(s: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)


def range_pos(close: pd.DataFrame, w: int) -> pd.DataFrame:
    min_periods = 200 if w >= 252 else int(w * 0.8)
    pmax = close.rolling(w, min_periods=min_periods).max()
    pmin = close.rolling(w, min_periods=min_periods).min()
    return (close - pmin) / (pmax - pmin).replace(0, np.nan)


def main() -> None:
    panel_path = CACHE / "etf_daily.parquet"
    if not panel_path.exists():
        raise FileNotFoundError(
            f"Run 01_fetch_data.py first; missing {panel_path}.")

    df = pd.read_parquet(panel_path)
    df = df[~df.symbol.isin(DROP_FULL)].copy()
    df = df.sort_values(["date", "symbol"]).reset_index(drop=True)
    close = df.pivot(index="date", columns="symbol", values="close").sort_index()

    counts = close.notna().sum()
    core = counts[counts >= CORE_MIN_DAYS].index.tolist()
    say(f"Core universe size: {len(core)} of {close.shape[1]} (min_days={CORE_MIN_DAYS})")

    rp_ranks = []
    for w in WINDOWS:
        say(f"Computing range_pos at window {w} ...")
        rp = range_pos(close, w)
        rp_ranks.append(rp.rank(axis=1, pct=True))
    signal = sum(rp_ranks) / len(rp_ranks)

    out_sig = CACHE / "signal.parquet"
    signal.to_parquet(out_sig)
    say(f"Wrote {out_sig} shape={signal.shape}")

    out_uni = CACHE / "core_universe.json"
    with open(out_uni, "w") as f:
        json.dump({"size": len(core), "symbols": core, "min_days": CORE_MIN_DAYS}, f, indent=2)
    say(f"Wrote {out_uni}")

    last_date = signal.dropna(how="all").index[-1]
    valid = signal.loc[last_date].dropna()
    valid = valid[valid.index.isin(core)]
    say(f"Latest signal snapshot ({last_date:%Y-%m-%d}, {len(valid)} symbols):")
    say("  top-3:    " + ", ".join(f"{k}={v:.3f}" for k, v in valid.nlargest(3).items()))
    say("  bottom-3: " + ", ".join(f"{k}={v:.3f}" for k, v in valid.nsmallest(3).items()))


if __name__ == "__main__":
    main()
