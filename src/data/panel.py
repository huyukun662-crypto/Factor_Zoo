"""Load merged ETF + index panel aligned on trade_date."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ETF_CACHE = Path(".cache/etf_daily.parquet")
IDX_CACHE = Path(".cache/index_daily.parquet")

ETF_MAP = {"510300.SH": "etf300", "510500.SH": "etf500", "512100.SH": "etf1000"}
IDX_MAP = {"000300.SH": "idx300", "000905.SH": "idx500", "000852.SH": "idx1000"}


def _wide(df: pd.DataFrame, code_col: str, code_map: dict, fields: list[str]) -> pd.DataFrame:
    out = None
    for code, alias in code_map.items():
        sub = df[df[code_col] == code][["trade_date"] + fields].copy()
        sub = sub.rename(columns={f: f"{alias}_{f}" for f in fields})
        sub = sub.sort_values("trade_date").reset_index(drop=True)
        out = sub if out is None else out.merge(sub, on="trade_date", how="outer")
    return out.sort_values("trade_date").reset_index(drop=True)


def load_panel() -> pd.DataFrame:
    """Returns a wide panel keyed on trade_date.

    Columns:
      etf300_close, etf300_open, etf300_high, etf300_low, etf300_vol, etf300_amount, ...
      idx300_close, idx300_open, idx300_high, idx300_low, idx300_vol, idx300_amount, ...
    Sorted ascending on trade_date.
    """
    if not ETF_CACHE.exists() or not IDX_CACHE.exists():
        raise FileNotFoundError(
            f"Missing cache. Run `python -m src.cli.fetch_data` first. "
            f"Looking for {ETF_CACHE} and {IDX_CACHE}."
        )
    etf = pd.read_parquet(ETF_CACHE)
    idx = pd.read_parquet(IDX_CACHE)

    etf_fields = ["open", "high", "low", "close", "vol", "amount"]
    idx_fields = ["open", "high", "low", "close", "vol", "amount"]

    etf_w = _wide(etf, "ts_code", ETF_MAP, etf_fields)
    idx_w = _wide(idx, "ts_code", IDX_MAP, idx_fields)

    # Index dates drive alignment (indices have full history; 512100 ETF listed 2014, 510300 listed 2012, 510500 2013).
    panel = idx_w.merge(etf_w, on="trade_date", how="left")
    panel = panel.sort_values("trade_date").reset_index(drop=True)
    panel = panel.set_index("trade_date")
    return panel


def slice_window(panel: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    out = panel
    if start is not None:
        out = out[out.index >= pd.Timestamp(start)]
    if end is not None:
        out = out[out.index < pd.Timestamp(end)]
    return out
