"""Macro factor fetcher with publication-lag handling.

# [NO-LOOKAHEAD] All macro series are forward-shifted by `pub_lag_days` so that
# the value usable on day T is the latest release whose publication date is ≤ T.
# Defaults are conservative: macro indicators usually publish 10-15 days after
# the reference month-end, so we use 30-day lag to be safe.

Cache: data/cache/_macro_<name>.parquet
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_macro(df: pd.DataFrame, value_col: str = "今值",
                      date_col: str = "日期", name: str = "macro") -> pd.DataFrame:
    df = df[[date_col, value_col]].copy()
    df.columns = ["pub_date", "value"]
    df["pub_date"] = pd.to_datetime(df["pub_date"]).dt.normalize()
    df = df.dropna(subset=["pub_date"]).sort_values("pub_date").drop_duplicates("pub_date")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna()


def fetch_pmi(refresh: bool = False) -> pd.DataFrame:
    fp = CACHE_DIR / "_macro_pmi.parquet"
    if fp.exists() and not refresh:
        return pd.read_parquet(fp)
    import akshare as ak
    df = _normalize_macro(ak.macro_china_pmi_yearly(), name="pmi")
    df.to_parquet(fp, index=False)
    return df


def fetch_m2(refresh: bool = False) -> pd.DataFrame:
    fp = CACHE_DIR / "_macro_m2.parquet"
    if fp.exists() and not refresh:
        return pd.read_parquet(fp)
    import akshare as ak
    df = _normalize_macro(ak.macro_china_m2_yearly(), name="m2")
    df.to_parquet(fp, index=False)
    return df


def fetch_cpi(refresh: bool = False) -> pd.DataFrame:
    """CPI YoY (Chinese-language month label parsed)."""
    fp = CACHE_DIR / "_macro_cpi.parquet"
    if fp.exists() and not refresh:
        return pd.read_parquet(fp)
    import akshare as ak
    raw = ak.macro_china_cpi()
    raw = raw.copy()
    # Parse '2024年03月份' -> 2024-03
    raw["pub_date"] = pd.to_datetime(
        raw["月份"].str.replace("年", "-").str.replace("月份", ""),
        format="%Y-%m", errors="coerce",
    )
    out = raw[["pub_date", "全国-同比增长"]].copy()
    out.columns = ["pub_date", "value"]
    out["pub_date"] = out["pub_date"].dt.to_period("M").dt.to_timestamp() + pd.offsets.MonthEnd(0)
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out.dropna().sort_values("pub_date").drop_duplicates("pub_date")
    out.to_parquet(fp, index=False)
    return out


def fetch_ppi(refresh: bool = False) -> pd.DataFrame:
    fp = CACHE_DIR / "_macro_ppi.parquet"
    if fp.exists() and not refresh:
        return pd.read_parquet(fp)
    import akshare as ak
    df = _normalize_macro(ak.macro_china_ppi_yearly(), name="ppi")
    df.to_parquet(fp, index=False)
    return df


def fetch_yield_curve(refresh: bool = False) -> pd.DataFrame:
    """Returns DataFrame with columns: pub_date, cn_2y, cn_5y, cn_10y, cn_10_2_spread,
                                          us_2y, us_10y, us_10_2_spread.
    """
    fp = CACHE_DIR / "_macro_yield.parquet"
    if fp.exists() and not refresh:
        return pd.read_parquet(fp)
    import akshare as ak
    raw = ak.bond_zh_us_rate()
    out = raw[["日期",
               "中国国债收益率2年", "中国国债收益率5年", "中国国债收益率10年", "中国国债收益率10年-2年",
               "美国国债收益率2年", "美国国债收益率10年", "美国国债收益率10年-2年"]].copy()
    out.columns = ["pub_date", "cn_2y", "cn_5y", "cn_10y", "cn_10_2_spread",
                   "us_2y", "us_10y", "us_10_2_spread"]
    out["pub_date"] = pd.to_datetime(out["pub_date"]).dt.normalize()
    out = out.sort_values("pub_date").drop_duplicates("pub_date")
    for c in out.columns:
        if c != "pub_date":
            out[c] = pd.to_numeric(out[c], errors="coerce")
    out.to_parquet(fp, index=False)
    return out


def align_to_daily(macro_df: pd.DataFrame, daily_index: pd.DatetimeIndex,
                   pub_lag_days: int = 30, value_col: str = "value"
                   ) -> pd.Series:
    """Forward-fill a monthly macro series onto a daily index, with publication lag.

    [NO-LOOKAHEAD] Each value is shifted forward by `pub_lag_days` so that on
    day T we only see releases published ≤ T - pub_lag_days. This conservatively
    handles unknown actual release dates.
    """
    df = macro_df[["pub_date", value_col]].copy()
    df["effective_date"] = df["pub_date"] + pd.Timedelta(days=pub_lag_days)
    df = df.set_index("effective_date").sort_index()
    s = df[value_col].reindex(daily_index, method="ffill")
    return s


def align_yield_to_daily(yield_df: pd.DataFrame, daily_index: pd.DatetimeIndex,
                          pub_lag_days: int = 1) -> pd.DataFrame:
    """Yield curve has daily granularity; only need T-1 lag (yield curve is
    end-of-day data, available the next morning)."""
    df = yield_df.copy()
    df["effective_date"] = df["pub_date"] + pd.Timedelta(days=pub_lag_days)
    df = df.set_index("effective_date").sort_index()
    cols = [c for c in df.columns if c not in ("pub_date",)]
    out = df[cols].reindex(daily_index, method="ffill")
    return out


def fetch_all_macro(refresh: bool = False) -> dict[str, pd.DataFrame]:
    """Fetch all macro series. Returns dict keyed by name."""
    print("[macro] fetching PMI...", end=" ", flush=True)
    out = {}
    out["pmi"] = fetch_pmi(refresh=refresh); print(f"{len(out['pmi'])} rows")
    print("[macro] fetching M2...", end=" ", flush=True)
    out["m2"] = fetch_m2(refresh=refresh); print(f"{len(out['m2'])} rows")
    print("[macro] fetching CPI...", end=" ", flush=True)
    out["cpi"] = fetch_cpi(refresh=refresh); print(f"{len(out['cpi'])} rows")
    print("[macro] fetching PPI...", end=" ", flush=True)
    out["ppi"] = fetch_ppi(refresh=refresh); print(f"{len(out['ppi'])} rows")
    print("[macro] fetching yield curve...", end=" ", flush=True)
    out["yield"] = fetch_yield_curve(refresh=refresh); print(f"{len(out['yield'])} rows")
    return out


if __name__ == "__main__":
    macro = fetch_all_macro()
    for k, df in macro.items():
        print(f"{k}: {df.shape}, {df['pub_date'].min().date()} .. {df['pub_date'].max().date()}")
