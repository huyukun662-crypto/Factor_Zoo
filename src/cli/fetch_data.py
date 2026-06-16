"""Fetch ETF + index daily data into .cache/ parquet files."""
from __future__ import annotations

from ..data import fetch_etf, fetch_index


def main():
    fetch_etf.main()
    fetch_index.main()


if __name__ == "__main__":
    main()
