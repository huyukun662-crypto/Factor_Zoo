#!/usr/bin/env python3
"""
Round 2 extension — D6 gold fallback.

When regime gate (ew_mom_200d > 0) is OFF, swap the long-only top-3 into
100% gold ETF (159934.SZ 黄金ETF). Gold has low correlation to thematic
equities and has been strong in 2022-2023 risk-off periods.

Also: D6b = blend (50% top-3 reversal + 50% gold) as always-on hedge.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

SESSION = Path("/home/user/Factor_Zoo/logs/20260424_a_share_etf_reversal_v2")
OUT = SESSION / "outputs" / "round2"
DATA_SRC = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs/etf_daily.parquet")
COMMON_START = pd.Timestamp("2019-01-04")
STAGGERED_JOIN_BARS = 60
GOLD_SYMBOL = "159934.SZ"


def load():
    df = pd.read_parquet(DATA_SRC).rename(columns={"trade_date": "date", "ts_code": "symbol"})
    df = df.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"]).reset_index(drop=True)
    for k in [40, 200]:
        df[f"logret_{k}d"] = df.groupby("symbol")["close_adj"].transform(
            lambda s, k=k: np.log(s / s.shift(k))
        )
    df["bar_age"] = df.groupby("symbol").cumcount()
    df["is_live"] = df["bar_age"] >= STAGGERED_JOIN_BARS
    return df


def demean(df, col):
    live = df["is_live"]
    s = df[col].where(live)
    return s - s.groupby(df["date"]).transform("mean")


def build_weights_with_gold_fallback(
    sig_demean, df, rebals, long_n=3, regime_mask=None,
    blend_with_gold=False, gold_weight=0.5
) -> pd.DataFrame:
    panel = pd.DataFrame({
        "date": df["date"].values, "symbol": df["symbol"].values,
        "s": sig_demean.values, "live": df["is_live"].values,
    })
    all_dates = sorted(panel["date"].unique())
    symbols = sorted(panel["symbol"].unique())
    w = pd.DataFrame(0.0, index=pd.DatetimeIndex(rebals), columns=symbols)
    panel_idx = panel.set_index(["date", "symbol"])

    if regime_mask is not None:
        regime_mask = regime_mask.reindex(all_dates).ffill().fillna(False)

    for dt in rebals:
        try:
            slice_df = panel_idx.xs(dt, level="date")
        except KeyError:
            continue
        slice_df = slice_df.dropna(subset=["s"])
        slice_df = slice_df[slice_df["live"]]
        if len(slice_df) < long_n * 2:
            continue
        ranked = slice_df["s"].sort_values(ascending=False)
        longs = ranked.iloc[:long_n].index.tolist()

        gate_on = regime_mask is None or bool(regime_mask.get(dt, False))
        if blend_with_gold and GOLD_SYMBOL in symbols:
            # always-on blend
            w.loc[dt, longs] = (1 - gold_weight) / long_n
            w.loc[dt, GOLD_SYMBOL] = gold_weight
        elif gate_on:
            w.loc[dt, longs] = 1.0 / long_n
        elif GOLD_SYMBOL in symbols:
            w.loc[dt, GOLD_SYMBOL] = 1.0

    return w.reindex(pd.DatetimeIndex(all_dates)).ffill().fillna(0.0)


def pnl_from_weights(w, df):
    rw = df.pivot_table(index="date", columns="symbol", values="close_adj").pct_change()
    rw = rw.reindex(w.index).reindex(columns=w.columns)
    return (w.shift(1).fillna(0) * rw).sum(axis=1)


def turnover(w):
    return w.diff().fillna(w).abs().sum(axis=1)


def ann(pnl):
    p = pnl.dropna()
    if len(p) < 30: return {"sharpe": np.nan, "maxdd": np.nan}
    mu, s = p.mean() * 252, p.std() * np.sqrt(252)
    eq = (1 + p).cumprod()
    return {"sharpe": float(mu / s) if s > 0 else np.nan, "maxdd": float((eq / eq.cummax() - 1).min())}


def py_sh(pnl):
    p = pnl.dropna()
    out = {}
    for y in sorted(set(p.index.year)):
        yp = p[p.index.year == y]
        mu, s = yp.mean() * 252, yp.std() * np.sqrt(252)
        out[int(y)] = float(mu / s) if s > 0 and len(yp) >= 30 else np.nan
    return out


def main():
    df = load()
    df = df[df["date"] >= COMMON_START].reset_index(drop=True)
    sig = demean(df.assign(neg40=-df["logret_40d"]), "neg40")
    all_d = pd.DatetimeIndex(sorted(df["date"].unique()))
    rebals = all_d[all_d.dayofweek == 4][::4]
    reg = df[df["is_live"]].groupby("date")["logret_200d"].mean().reindex(all_d).ffill()
    mom_mask = reg > 0

    configs = [
        ("baseline_no_gold", {"regime_mask": None, "blend_with_gold": False}),
        ("D6_gold_fallback_mom200", {"regime_mask": mom_mask, "blend_with_gold": False}),
        ("D6b_blend_50pct_gold", {"regime_mask": None, "blend_with_gold": True, "gold_weight": 0.5}),
        ("D6c_blend_25pct_gold", {"regime_mask": None, "blend_with_gold": True, "gold_weight": 0.25}),
    ]

    rows = []
    for name, cfg in configs:
        w = build_weights_with_gold_fallback(sig, df, rebals, **cfg)
        pnl = pnl_from_weights(w, df)
        to = turnover(w)
        net5 = pnl - to * 5 / 1e4
        a = ann(net5)
        py = py_sh(net5)
        worst = min(py, key=lambda y: py[y] if not np.isnan(py[y]) else 99)
        print(f"{name:30s}  net5 Sh={a['sharpe']:+.3f}  MaxDD={a['maxdd']:+.2%}  "
              f"worst={worst} Sh={py[worst]:+.3f}")
        print(f"    per year: " + "  ".join(f"{y}:{s:+.2f}" for y, s in sorted(py.items())))
        rows.append({"variant": name, "net5_sharpe": a["sharpe"], "maxdd": a["maxdd"],
                     "worst_year": worst, "worst_sharpe": py[worst],
                     **{f"y{y}": s for y, s in py.items()}})
    pd.DataFrame(rows).to_csv(OUT / "r2_d6_gold_variants.csv", index=False)


if __name__ == "__main__":
    main()
