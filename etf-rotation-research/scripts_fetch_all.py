"""One-shot script: fetch all seed-universe symbols via akshare into parquet cache.
Run from repo root: .venv/bin/python scripts_fetch_all.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data.fetch_data import fetch_panel
from strategy.universe import SYMBOLS

if __name__ == "__main__":
    panel = fetch_panel(SYMBOLS, start="2013-01-01")
    print(f"Fetched {len(panel)}/{len(SYMBOLS)} symbols")
    for s in SYMBOLS:
        if s not in panel:
            print(f"  MISSING: {s}")
