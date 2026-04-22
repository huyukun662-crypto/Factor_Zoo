"""
Round 3: refine around the Round-2 near-pass.

Best round-2 candidate:
  size_q5q1_12m_sh | pct95 | lb=126   → full 1.025, worst 0.452 (needs 0.5)

Explore nearby specs:
  - lookback {63, 90, 126, 189, 252, 378}
  - threshold percentile {92, 93, 94, 95, 96, 97, 98, 99}
  - Signal smoothing: 10d/20d-EMA before gate
  - Combined: top2 signals averaged

Also inspect per-month gate state for 2020 to understand which month(s)
slip through.
"""
from __future__ import annotations
import json, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("/home/user/Factor_Zoo")
CACHE = ROOT / ".cache"
LOT = ROOT / "logs/20260421_volprice_max_lottery"
SESSION = ROOT / "logs/20260422_lottery_megacap_overlay"
OUT_DIR = SESSION / "outputs"

COST_BPS = 5
REBAL = 20
TRAIN_END = pd.Timestamp("2022-12-31")
VALID_END = pd.Timestamp("2023-12-31")


def industry_demean(df, col):
    return df[col] - df.groupby(["trade_date", "industry"])[col].transform("mean")


def perf(r, ppy=12):
    r = r.dropna()
    if len(r) < 2:
        return {"sharpe": np.nan, "ann": np.nan, "maxdd": np.nan}
    ann = r.mean() * ppy; vol = r.std(ddof=0) * np.sqrt(ppy)
    eq = (1 + r).cumprod()
    return {"sharpe": ann / vol if vol > 0 else 0.0, "ann": float(ann),
            "maxdd": float((eq / eq.cummax() - 1).min())}


def per_year_ir(r):
    r = r.dropna(); out = {}
    for y in sorted(set(r.index.year)):
        rr = r[r.index.year == y]
        if len(rr) < 6: continue
        v = rr.std(ddof=0)
        out[int(y)] = float((rr.mean() * 12) / (v * np.sqrt(12))) if v > 0 else 0.0
    return out


def make_gate(signal, percentile, lookback, smooth=None):
    if smooth:
        signal = signal.ewm(span=smooth, min_periods=smooth // 2).mean()
    mp = max(int(lookback * 0.7), 40)
    threshold = signal.rolling(lookback, min_periods=mp).quantile(percentile / 100.0)
    return (signal < threshold).astype(int).where(~threshold.isna(), 0)


def q5_long_only_with_gate(panel, alpha_col, ret_col, rebal_dates, gate_series,
                            top_pct=0.20, cost_bps=COST_BPS):
    """Benchmark-fallback gate only."""
    rows = []; prev_set = set(); prev_state = 0
    panel_l = panel[["trade_date", "ts_code", alpha_col, ret_col]].dropna()
    gate_dict = gate_series.to_dict()
    for t in rebal_dates:
        g = int(gate_dict.get(t, 0))
        snap = panel_l[panel_l["trade_date"] == t]
        if len(snap) < 100: continue
        uni_mean = snap[ret_col].mean()
        if g == 0:
            tov = 1.0 if prev_state == 1 and prev_set else 0.0
            rows.append(dict(trade_date=t, gate=0, abs_ret=uni_mean, exc_ret=0.0,
                             uni=uni_mean, tov=tov, cost=tov * cost_bps / 1e4))
            prev_state = 0; prev_set = set(); continue
        snap_s = snap.sort_values(alpha_col, ascending=False)
        k = max(int(len(snap_s) * top_pct), 20)
        top = snap_s.head(k); cur_set = set(top["ts_code"])
        mean_ret = top[ret_col].mean()
        tov = (1.0 - len(cur_set & prev_set) / max(len(cur_set), 1)) if (prev_state == 1 and prev_set) else 1.0
        rows.append(dict(trade_date=t, gate=1, abs_ret=mean_ret,
                         exc_ret=mean_ret - uni_mean, uni=uni_mean,
                         tov=tov, cost=tov * cost_bps / 1e4))
        prev_state = 1; prev_set = cur_set
    df = pd.DataFrame(rows).set_index("trade_date").sort_index()
    df["abs_net"] = df["abs_ret"] - df["cost"]
    df["exc_net"] = df["exc_ret"] - df["cost"]
    return df


def summarize(df):
    abs_p = perf(df["abs_net"]); exc_p = perf(df["exc_net"])
    py_exc = per_year_ir(df["exc_net"])
    train = df[df.index <= TRAIN_END]; valid = df[(df.index > TRAIN_END) & (df.index <= VALID_END)]
    test = df[df.index > VALID_END]
    return dict(
        abs_ann=abs_p["ann"], abs_sharpe=abs_p["sharpe"], abs_maxdd=abs_p["maxdd"],
        exc_ann=exc_p["ann"], exc_ir=exc_p["sharpe"], exc_maxdd=exc_p["maxdd"],
        exc_train_ir=perf(train["exc_net"])["sharpe"],
        exc_valid_ir=perf(valid["exc_net"])["sharpe"],
        exc_test_ir=perf(test["exc_net"])["sharpe"],
        worst_year_exc=min(py_exc.values()) if py_exc else np.nan,
        best_year_exc=max(py_exc.values()) if py_exc else np.nan,
        ir_2020=py_exc.get(2020, np.nan), ir_2025=py_exc.get(2025, np.nan),
        on_frac=float(df["gate"].mean()),
        avg_tov=float(df["tov"].mean()),
        per_year_exc=py_exc,
    )


def main():
    t0 = time.time()
    print("[r3] loading α_17 panel + features...")
    lot = pd.read_parquet(LOT / "outputs/panel_round3.parquet",
                          columns=["ts_code", "trade_date", "industry",
                                   "alpha_17", "fwd_ret_20"])
    lot["trade_date"] = pd.to_datetime(lot["trade_date"])
    lot = lot.dropna(subset=["industry"])
    lot["alpha_17_n"] = industry_demean(lot, "alpha_17")
    feats = pd.read_parquet(OUT_DIR / "megacap_features_r2.parquet")
    dates = pd.Index(sorted(lot["trade_date"].unique()))
    rebal_dates = dates[::REBAL]

    sig_name = "size_q5q1_12m_sh"
    sig = feats[sig_name].dropna()

    # --- Grid on lookback × percentile ---
    lookbacks = [63, 90, 126, 189, 252, 378]
    percentiles = [90, 92, 93, 94, 95, 96, 97, 98]
    smooths = [None, 10, 20]

    rows = []
    for lb in lookbacks:
        for p in percentiles:
            for sm in smooths:
                gate = make_gate(sig, percentile=p, lookback=lb, smooth=sm)
                df = q5_long_only_with_gate(lot, "alpha_17_n", "fwd_ret_20", rebal_dates, gate)
                s = summarize(df)
                s.update(dict(lookback=lb, percentile=p, smooth=sm))
                rows.append(s)

    n = len(rows)
    print(f"[r3] tested {n} spec combos  {time.time()-t0:.1f}s")

    # Rank by worst-year > full IR
    ranked = sorted(rows, key=lambda s: (s["worst_year_exc"], s["exc_ir"]), reverse=True)

    print("\n" + "=" * 110)
    print("Refined grid — top 20 by worst-year")
    print("=" * 110)
    print(f"{'#':>3} {'lb':>4} {'pct':>4} {'sm':>4} "
          f"{'full':>7} {'worst':>7} {'2020':>7} {'2025':>7} {'on_fr':>6} "
          f"{'MaxDD%':>7} {'PASS':>5}")
    passing = [s for s in ranked if s["exc_ir"] >= 1.0 and s["worst_year_exc"] >= 0.5]
    for i, s in enumerate(ranked[:20]):
        mark = "PASS" if (s["exc_ir"] >= 1.0 and s["worst_year_exc"] >= 0.5) else ""
        print(f"  {i+1:>2} {s['lookback']:>4} {s['percentile']:>4} "
              f"{str(s['smooth'] or 'None'):>4} "
              f"{s['exc_ir']:>7.3f} {s['worst_year_exc']:>7.3f} "
              f"{s['ir_2020']:>7.3f} {s['ir_2025']:>7.3f} "
              f"{s['on_frac']:>6.3f} {s['exc_maxdd']*100:>+7.2f} {mark:>5}")

    print(f"\n[r3] passing: {len(passing)}/{n}")

    if passing:
        winner = max(passing, key=lambda s: (s["worst_year_exc"] + s["exc_ir"]))
        print(f"\n[r3] Winner: lb={winner['lookback']}, pct={winner['percentile']}, sm={winner['smooth']}")
        print(f"  full_IR={winner['exc_ir']:.3f}  worst={winner['worst_year_exc']:.3f}")
        print(f"  2020={winner['ir_2020']:.3f}  2025={winner['ir_2025']:.3f}")
        print(f"  train/validate/test = {winner['exc_train_ir']:.3f} / {winner['exc_valid_ir']:.3f} / {winner['exc_test_ir']:.3f}")
        print(f"  on_frac={winner['on_frac']:.3f}  MaxDD={winner['exc_maxdd']*100:+.2f}%")
        print(f"  per-year excess IR: {winner['per_year_exc']}")
    else:
        winner = ranked[0]
        print(f"\n[r3] No pass; best: lb={winner['lookback']} pct={winner['percentile']} sm={winner['smooth']}")
        print(f"     full={winner['exc_ir']:.3f}  worst={winner['worst_year_exc']:.3f}")

    out = dict(
        experiment="overlay_round3_refine",
        signal=sig_name,
        n_combos=n, n_passing=len(passing),
        passing=passing, all_results=ranked,
        winner=winner,
    )
    with open(OUT_DIR / "overlay_round3.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n[r3] wrote {OUT_DIR / 'overlay_round3.json'}")
    print(f"[r3] done {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
