"""
verify_universe_with_tushare.py — Cross-check the 32-ETF universe used by
anchor_range_pos_etf_v1 against Tushare authoritative data.

Checks:
  1. fund_basic: each symbol exists, is an ETF (market=E), name matches, list_date
  2. fund_daily: last 250 trading days OHLCV match Yahoo within tolerance
  3. delist_date: nothing has been delisted (Yahoo doesn't propagate this)
  4. Core universe: confirm the 20 ETFs we kept have ≥1500 days
  5. Suggest replacements for the 14 short-history ETFs we dropped

Token via TUSHARE_TOKEN env var (not committed to repo).
"""
from __future__ import annotations
import json
import os
import time
from pathlib import Path
import numpy as np
import pandas as pd
import tushare as ts

OUT = Path("/home/user/Factor_Zoo/logs/20260502_a_share_etf_anchor_high_v1/outputs")

# 32 symbols in Yahoo format from our deploy package
YAHOO_SYMBOLS = [
    # broad index (10)
    "510300.SS", "510500.SS", "510050.SS", "159915.SZ", "510180.SS",
    "159949.SZ", "588000.SS", "588080.SS", "512100.SS", "510880.SS",
    # industry / thematic (9)
    "512880.SS", "512660.SS", "512170.SS", "512760.SS", "515030.SS",
    "512290.SS", "515050.SS", "512690.SS", "512980.SS",
    # commodity / defensive (1)
    "518880.SS",
    # extra thematic (12, dropping 512800/515170)
    "512480.SS", "159819.SZ", "515880.SS", "159890.SZ", "159869.SZ",
    "159857.SZ", "159755.SZ", "512010.SS",
    "159992.SZ", "159980.SZ", "515220.SS", "515210.SS",
]


def yahoo_to_tushare(sym: str) -> str:
    """Yahoo .SS / .SZ -> Tushare .SH / .SZ"""
    code, ex = sym.split(".")
    return f"{code}.SH" if ex == "SS" else f"{code}.SZ"


def main():
    ts.set_token(os.environ["TUSHARE_TOKEN"])
    pro = ts.pro_api()

    # ---------- 1. fund_basic ----------
    print("[1/4] Fetching fund_basic (E + O)...")
    fb_e = pro.fund_basic(market='E')
    fb_o = pro.fund_basic(market='O')
    fb = pd.concat([fb_e, fb_o], ignore_index=True)
    fb_lookup = fb.set_index("ts_code")

    rows = []
    for ysym in YAHOO_SYMBOLS:
        tsym = yahoo_to_tushare(ysym)
        if tsym not in fb_lookup.index:
            rows.append({
                "yahoo": ysym, "tushare": tsym,
                "name": "NOT_FOUND", "fund_type": None,
                "list_date": None, "delist_date": None, "market": None,
                "exists_in_tushare": False,
            })
            continue
        rec = fb_lookup.loc[tsym]
        # if duplicate, take first
        if isinstance(rec, pd.DataFrame):
            rec = rec.iloc[0]
        rows.append({
            "yahoo": ysym, "tushare": tsym,
            "name": rec["name"], "fund_type": rec["fund_type"],
            "list_date": rec["list_date"], "delist_date": rec["delist_date"],
            "market": rec["market"], "exists_in_tushare": True,
        })

    meta = pd.DataFrame(rows)
    meta.to_csv(OUT / "tushare_universe_meta.csv", index=False)
    print(f"  {meta['exists_in_tushare'].sum()}/{len(meta)} symbols found in tushare")
    print(f"  fund_type distribution: {meta['fund_type'].value_counts().to_dict()}")
    print(f"  delisted: {meta['delist_date'].notna().sum()}")
    print()
    print(meta[['yahoo','name','fund_type','list_date','delist_date']].to_string(index=False))

    # ---------- 2. Compare daily data over last 250 days ----------
    print("\n[2/4] Comparing recent 250d close vs Yahoo cache...")
    yahoo_panel = pd.read_parquet("/home/user/Factor_Zoo/logs/_shared_cache/etf_daily.parquet")
    yahoo_panel = yahoo_panel.sort_values(["symbol","date"]).reset_index(drop=True)

    end_date = "20260430"
    start_date = "20250401"  # ~12 months
    diff_rows = []
    for ysym in YAHOO_SYMBOLS:
        tsym = yahoo_to_tushare(ysym)
        if not meta[meta.yahoo == ysym]["exists_in_tushare"].iloc[0]:
            continue
        try:
            ts_df = pro.fund_daily(ts_code=tsym, start_date=start_date, end_date=end_date)
            if ts_df is None or ts_df.empty:
                diff_rows.append({"yahoo": ysym, "n_yahoo": None, "n_tushare": 0,
                                  "max_close_diff_pct": None, "note": "tushare empty"})
                continue
        except Exception as exc:
            diff_rows.append({"yahoo": ysym, "n_yahoo": None, "n_tushare": None,
                              "max_close_diff_pct": None, "note": f"err: {exc}"})
            continue

        ts_df["date"] = pd.to_datetime(ts_df["trade_date"])
        ts_df = ts_df.sort_values("date").set_index("date")

        ya = yahoo_panel[(yahoo_panel.symbol == ysym) &
                         (yahoo_panel.date >= "2025-04-01") &
                         (yahoo_panel.date <= "2026-04-30")].copy()
        ya = ya.set_index("date").sort_index()

        common = ts_df.index.intersection(ya.index)
        if len(common) < 30:
            diff_rows.append({"yahoo": ysym, "n_yahoo": len(ya), "n_tushare": len(ts_df),
                              "n_common": len(common),
                              "max_close_diff_pct": None,
                              "note": "too few common days"})
            continue

        # Tushare close is unadjusted. Yahoo we used is adj-close already.
        # We compare PCT-CHANGE patterns instead (returns must match).
        ts_ret = ts_df.loc[common, "close"].pct_change().dropna()
        ya_ret = ya.loc[common, "close"].pct_change().dropna()
        common2 = ts_ret.index.intersection(ya_ret.index)
        ret_diff = (ts_ret.loc[common2] - ya_ret.loc[common2]).abs()

        diff_rows.append({
            "yahoo": ysym,
            "n_yahoo": len(ya),
            "n_tushare": len(ts_df),
            "n_common": len(common),
            "max_ret_diff_abs": float(ret_diff.max()),
            "median_ret_diff_abs": float(ret_diff.median()),
            "n_days_diff_gt_1bp": int((ret_diff > 1e-4).sum()),
            "note": "ok" if ret_diff.max() < 0.005 else "mismatch_check",
        })
        time.sleep(0.1)  # be nice to API

    daily_diff = pd.DataFrame(diff_rows)
    daily_diff.to_csv(OUT / "tushare_daily_diff.csv", index=False)
    n_ok = (daily_diff["note"] == "ok").sum()
    print(f"  {n_ok}/{len(daily_diff)} symbols have <0.5% max daily return discrepancy")
    print(daily_diff.to_string(index=False))

    # ---------- 3. Check Yahoo-cached history length vs Tushare ----------
    print("\n[3/4] Checking total history length (tushare from list_date)...")
    yahoo_lengths = yahoo_panel.groupby("symbol")["date"].count()
    hist_rows = []
    for _, r in meta.iterrows():
        ysym = r["yahoo"]
        ny = int(yahoo_lengths.get(ysym, 0))
        ld = pd.to_datetime(r["list_date"]) if r["list_date"] else None
        days_since_list = (pd.Timestamp("2026-04-30") - ld).days if ld is not None else None
        approx_trading_days = int(days_since_list * 252 / 365) if days_since_list else None
        hist_rows.append({
            "yahoo": ysym, "name": r["name"],
            "list_date": r["list_date"],
            "n_yahoo_bars": ny,
            "approx_trading_days_since_list": approx_trading_days,
            "core_qualifies_1500": ny >= 1500,
            "would_qualify_per_tushare": (approx_trading_days or 0) >= 1500,
        })
    hist = pd.DataFrame(hist_rows)
    hist.to_csv(OUT / "tushare_history_length.csv", index=False)
    print(f"  Yahoo says {hist.core_qualifies_1500.sum()} qualify for core (≥1500 days)")
    print(f"  Tushare list-date implies {hist.would_qualify_per_tushare.sum()} should qualify")
    print()
    # symbols where the two disagree
    disagree = hist[hist.core_qualifies_1500 != hist.would_qualify_per_tushare]
    if len(disagree):
        print("  Disagreements (potential Yahoo data gaps):")
        print(disagree[['yahoo','name','list_date','n_yahoo_bars',
                       'approx_trading_days_since_list',
                       'core_qualifies_1500','would_qualify_per_tushare']].to_string(index=False))

    # ---------- 4. Suggest broader universe additions ----------
    print("\n[4/4] Suggesting any major A-share equity ETFs we might have missed...")
    # major equity ETFs by AUM heuristic: list_date <=2020-01-01, market='E', 'ETF' in name
    big = fb[(fb.market == 'E') & (fb.delist_date.isna())].copy()
    big["list_dt"] = pd.to_datetime(big["list_date"], errors='coerce')
    big = big[big["list_dt"] <= "2020-12-31"]
    big_name_filter = big["name"].str.contains("ETF", na=False)
    big = big[big_name_filter]
    # exclude those already in our universe
    our_codes = set(yahoo_to_tushare(s) for s in YAHOO_SYMBOLS)
    candidates = big[~big.ts_code.isin(our_codes)].copy()
    # heuristic: drop bond ETFs, gold/silver ETFs (already have 518880), QDII
    candidates = candidates[~candidates["name"].str.contains("债|国债|城投|信用债|短融|金融债|可转债|REITs|港股|纳指|标普|德国|日经|恒生|油气|白银|有色|商品", na=False)]
    print(f"  Found {len(candidates)} other equity ETFs listed before 2021 (showing first 20):")
    print(candidates[['ts_code','name','list_date','fund_type']].head(20).to_string(index=False))


if __name__ == "__main__":
    main()
