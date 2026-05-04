"""Analyze which defensive / hedge assets perform best when USD strong + RMB weak.

Double-pressure regime definitions tried:
  loose : dxy_mom_60 > 0 AND usdcny_mom_60 > 0
  mid   : dxy_mom_60 > 0.02 AND usdcny_mom_60 > 0.01
  strict: dxy_mom_60 > 0.04 AND usdcny_mom_60 > 0.02

Asset pool tested (defensives + cross-border equity):
  511010 国债, 511260 国开, 511880 货币
  518880 黄金
  515080 红利低波
  515220 煤炭
  513100 纳指, 513500 标普500, 513050 中概互联, 159920 恒生 (QDII)
  +baseline 510300 沪深300

# [GUARDRAIL] Strict IS only (2013-01-01 to 2023-12-31).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analysis.is_search import load_is_panels  # noqa: E402
from data.fetch_macro import fetch_all_macro  # noqa: E402
from strategy.regime import build_regime_panel  # noqa: E402
from strategy.universe import BENCHMARK_SYMBOL  # noqa: E402

OUT = REPO_ROOT / "report" / "outputs"

ASSET_POOL = [
    ("510300", "沪深300 (基准)"),
    ("511010", "10Y 国债"),
    ("511260", "10Y 国开"),
    ("511880", "货币基金"),
    ("518880", "黄金"),
    ("515080", "红利低波"),
    ("515220", "煤炭"),
    ("513100", "纳指"),
    ("513500", "标普500"),
    ("513050", "中概互联"),
    ("159920", "恒生"),
    ("162411", "华宝油气"),
]


def _stats(daily_ret: pd.Series, label: str) -> dict:
    """Compute headline stats on a daily return series."""
    s = daily_ret.dropna()
    if len(s) < 5:
        return dict(label=label, n=len(s), ann_ret=np.nan, ann_vol=np.nan,
                    sharpe=np.nan, max_dd=np.nan, hit_rate=np.nan,
                    pos_mean=np.nan, neg_mean=np.nan)
    eq = (1 + s).cumprod()
    yrs = max(len(s) / 252, 1e-9)
    ann_ret = eq.iloc[-1] ** (1 / yrs) - 1
    ann_vol = s.std() * np.sqrt(252)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
    peak = eq.cummax()
    max_dd = (eq / peak - 1).min()
    hit_rate = (s > 0).mean()
    pos_mean = s[s > 0].mean() if (s > 0).any() else 0
    neg_mean = s[s < 0].mean() if (s < 0).any() else 0
    return dict(label=label, n=len(s),
                ann_ret=float(ann_ret), ann_vol=float(ann_vol),
                sharpe=float(sharpe), max_dd=float(max_dd),
                hit_rate=float(hit_rate),
                pos_mean=float(pos_mean), neg_mean=float(neg_mean))


def main():
    panels = load_is_panels()
    macro = fetch_all_macro()
    bench = panels["close"][BENCHMARK_SYMBOL]
    regime_panel = build_regime_panel(bench, macro=macro, ma_window=200, vol_window=60)

    close = panels["close"]
    daily_ret = close.pct_change()

    # Define double-pressure masks
    dxy_mom = regime_panel["dxy_mom_60"]
    usdcny_mom = regime_panel["usdcny_mom_60"]
    dxy_strong = regime_panel["dxy_strong"].fillna(0).astype(int)
    print(f"DXY momentum range: {dxy_mom.min():.3f} .. {dxy_mom.max():.3f}")
    print(f"USDCNY momentum range: {usdcny_mom.min():.3f} .. {usdcny_mom.max():.3f}")

    masks = {
        "loose": (dxy_mom > 0) & (usdcny_mom > 0),
        "mid": (dxy_mom > 0.02) & (usdcny_mom > 0.01),
        "strict": (dxy_mom > 0.04) & (usdcny_mom > 0.02),
        "very_strict": (dxy_mom > 0.06) & (usdcny_mom > 0.03),
    }

    print("\nDouble-pressure day counts (out of 2672 IS days):")
    for k, m in masks.items():
        print(f"  {k:12s}: {m.sum()} days ({100*m.sum()/len(m):.1f}%)")

    # For each mask, compute per-asset stats
    all_results = []
    for mask_name, mask in masks.items():
        for sym, label in ASSET_POOL:
            if sym not in daily_ret.columns:
                continue
            sub = daily_ret[sym].loc[mask]
            res = _stats(sub, f"{sym} {label}")
            res["regime"] = mask_name
            res["symbol"] = sym
            res["asset"] = label
            all_results.append(res)

    df = pd.DataFrame(all_results)
    df.to_csv(OUT / "double_pressure_asset_stats.csv", index=False)

    # Print headline ranking per regime
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)
    for mask_name in masks.keys():
        sub = df[df["regime"] == mask_name].copy()
        sub = sub.sort_values("sharpe", ascending=False)
        print(f"\n=== Regime '{mask_name}' (n={int(sub['n'].max() if not sub.empty else 0)} days) — top by Sharpe ===")
        print(sub[["asset", "n", "ann_ret", "ann_vol", "sharpe", "max_dd", "hit_rate"]]
                .round(3).to_string(index=False))

    # ---- Also analyze 2022 specifically ----
    print("\n=== 2022 only (the failure year) ===")
    mask_2022 = (regime_panel.index.year == 2022)
    rows_2022 = []
    for sym, label in ASSET_POOL:
        if sym not in daily_ret.columns:
            continue
        sub = daily_ret[sym].loc[mask_2022]
        res = _stats(sub, f"{sym} {label}")
        res["symbol"] = sym
        res["asset"] = label
        rows_2022.append(res)
    df_2022 = pd.DataFrame(rows_2022).sort_values("sharpe", ascending=False)
    print(df_2022[["asset", "n", "ann_ret", "ann_vol", "sharpe", "max_dd", "hit_rate"]]
            .round(3).to_string(index=False))
    df_2022.to_csv(OUT / "double_pressure_2022.csv", index=False)

    # ---- Rolling mode: per-window double-pressure asset performance ----
    # Show monthly average return per asset in double-pressure days (mid threshold)
    print("\n=== Mid-threshold double-pressure: monthly avg return per asset (top 5) ===")
    mid_mask = masks["mid"]
    mid_idx = regime_panel.index[mid_mask]
    if len(mid_idx) > 0:
        for sym, label in ASSET_POOL[:6]:  # first 6 assets
            if sym not in daily_ret.columns:
                continue
            mask_sym = daily_ret[sym].loc[mid_mask].dropna()
            monthly = mask_sym.groupby(mask_sym.index.to_period("M")).sum()
            if len(monthly) > 0:
                print(f"  {label}: monthly avg = {monthly.mean()*100:.2f}%, "
                      f"hit_rate = {(monthly > 0).mean():.2f}, "
                      f"n_months = {len(monthly)}")

    print(f"\nSaved: {OUT / 'double_pressure_asset_stats.csv'}")
    print(f"Saved: {OUT / 'double_pressure_2022.csv'}")


if __name__ == "__main__":
    main()
