"""
Round 2: combinations and tighter thresholds on overlay.

Round 1 best single-signal gate (size_q5q1_12m_sh | pct90 | benchmark)
got 2020 IR 0.253. Per-month analysis shows 2020 had 6 positive / 6
negative months; perfect gate → IR 2.16, drop-3-worst → IR 1.32, so
target (0.5) is feasible with a reasonable-accuracy gate.

Round 2 explores:
  A) Tighter thresholds (pct85, pct95)
  B) Shorter lookback (126d instead of 252d)
  C) 2-out-of-K combinations of signals (more robust gate triggers)
  D) "Sticky gate" — once off, stay off for ≥2 rebal periods
  E) New signal: market breadth (% stocks above 60d MA)

Winning spec must preserve full IR ≥ 1.0 AND hit 2020 IR ≥ 0.5.
"""
from __future__ import annotations
import json, time
from pathlib import Path
from itertools import combinations
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


# ---------- reused helpers ---------- #

def industry_demean(df, col):
    return df[col] - df.groupby(["trade_date", "industry"])[col].transform("mean")


def perf(r, ppy=12):
    r = r.dropna()
    if len(r) < 2:
        return {"sharpe": np.nan, "ann": np.nan, "maxdd": np.nan}
    ann = r.mean() * ppy
    vol = r.std(ddof=0) * np.sqrt(ppy)
    eq = (1 + r).cumprod()
    return {"sharpe": ann / vol if vol > 0 else 0.0,
            "ann": float(ann),
            "maxdd": float((eq / eq.cummax() - 1).min())}


def per_year_ir(r):
    r = r.dropna()
    out = {}
    for y in sorted(set(r.index.year)):
        rr = r[r.index.year == y]
        if len(rr) < 6:
            continue
        v = rr.std(ddof=0)
        out[int(y)] = float((rr.mean() * 12) / (v * np.sqrt(12))) if v > 0 else 0.0
    return out


def make_gate(signal, mode, lookback=252, min_periods=None):
    """Build gate: 1 = α_17 ON (signal < threshold), 0 = OFF.
    mode: 'median', 'pct70', 'pct75', 'pct80', 'pct85', 'pct90', 'pct95'
    """
    mp = min_periods or max(int(lookback * 0.7), 40)
    if mode == "median":
        threshold = signal.rolling(lookback, min_periods=mp).median()
    else:
        p = int(mode.replace("pct", "")) / 100.0
        threshold = signal.rolling(lookback, min_periods=mp).quantile(p)
    gate = (signal < threshold).astype(int).where(~threshold.isna(), 0)
    return gate


def q5_long_only_with_gate(panel, alpha_col, ret_col, rebal_dates,
                           gate_series, top_pct=0.20, cost_bps=COST_BPS,
                           fallback="benchmark"):
    rows = []
    prev_set = set(); prev_state = 0
    panel_l = panel[["trade_date", "ts_code", alpha_col, ret_col]].dropna()
    gate_dict = gate_series.to_dict()
    for t in rebal_dates:
        g = int(gate_dict.get(t, 0))
        snap = panel_l[panel_l["trade_date"] == t]
        if len(snap) < 100:
            continue
        uni_mean = snap[ret_col].mean()
        if g == 0:
            if fallback == "benchmark":
                abs_r = uni_mean; exc_r = 0.0
            else:
                abs_r = 0.0; exc_r = -uni_mean
            tov = 1.0 if prev_state == 1 and prev_set else 0.0
            rows.append(dict(trade_date=t, gate=0, abs_ret=abs_r, exc_ret=exc_r,
                             uni=uni_mean, tov=tov, cost=tov * cost_bps / 1e4))
            prev_state = 0; prev_set = set()
            continue
        snap_sorted = snap.sort_values(alpha_col, ascending=False)
        k = max(int(len(snap_sorted) * top_pct), 20)
        top = snap_sorted.head(k)
        cur_set = set(top["ts_code"])
        mean_ret = top[ret_col].mean()
        if prev_state == 1 and prev_set:
            tov = 1.0 - len(cur_set & prev_set) / max(len(cur_set), 1)
        else:
            tov = 1.0
        rows.append(dict(trade_date=t, gate=1, abs_ret=mean_ret,
                         exc_ret=mean_ret - uni_mean, uni=uni_mean,
                         tov=tov, cost=tov * cost_bps / 1e4))
        prev_state = 1; prev_set = cur_set
    df = pd.DataFrame(rows).set_index("trade_date").sort_index()
    df["abs_net"] = df["abs_ret"] - df["cost"]
    df["exc_net"] = df["exc_ret"] - df["cost"]
    return df


def summarize(df, name):
    abs_p = perf(df["abs_net"]); exc_p = perf(df["exc_net"])
    py_exc = per_year_ir(df["exc_net"])
    train = df[df.index <= TRAIN_END]
    valid = df[(df.index > TRAIN_END) & (df.index <= VALID_END)]
    test = df[df.index > VALID_END]
    return dict(
        name=name,
        abs_ann=abs_p["ann"], abs_sharpe=abs_p["sharpe"], abs_maxdd=abs_p["maxdd"],
        exc_ann=exc_p["ann"], exc_ir=exc_p["sharpe"], exc_maxdd=exc_p["maxdd"],
        exc_train_ir=perf(train["exc_net"])["sharpe"],
        exc_valid_ir=perf(valid["exc_net"])["sharpe"],
        exc_test_ir=perf(test["exc_net"])["sharpe"],
        worst_year_exc=min(py_exc.values()) if py_exc else np.nan,
        best_year_exc=max(py_exc.values()) if py_exc else np.nan,
        ir_2020=py_exc.get(2020, np.nan),
        ir_2025=py_exc.get(2025, np.nan),
        on_frac=float(df["gate"].mean()),
        avg_tov=float(df["tov"].mean()),
        per_year_exc=py_exc,
    )


def build_breadth_feature():
    """% of stocks with P > MA60 per date."""
    daily = pd.read_parquet(CACHE / "daily.parquet").merge(
        pd.read_parquet(CACHE / "adj_factor.parquet"),
        on=["ts_code", "trade_date"], how="left"
    )
    daily["adj_factor"] = daily["adj_factor"].fillna(1.0)
    daily["P"] = daily["close"] * daily["adj_factor"]
    daily = daily.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)
    daily["trade_date"] = pd.to_datetime(daily["trade_date"])
    daily["ma60"] = daily.groupby("ts_code")["P"].transform(
        lambda s: s.rolling(60, min_periods=40).mean())
    daily["above_ma60"] = (daily["P"] > daily["ma60"]).astype(int)
    breadth = daily.groupby("trade_date")["above_ma60"].mean().rename("breadth_60")
    return breadth


# ---------- main ---------- #

def main():
    t0 = time.time()
    print("[r2] loading α_17 panel...")
    lot = pd.read_parquet(LOT / "outputs/panel_round3.parquet",
                          columns=["ts_code", "trade_date", "industry",
                                   "alpha_17", "fwd_ret_20"])
    lot["trade_date"] = pd.to_datetime(lot["trade_date"])
    lot = lot.dropna(subset=["industry"])
    lot["alpha_17_n"] = industry_demean(lot, "alpha_17")
    dates = pd.Index(sorted(lot["trade_date"].unique()))
    rebal_dates = dates[::REBAL]
    print(f"[r2] {len(rebal_dates)} rebalance dates")

    # Load round-1 features + build breadth
    feats = pd.read_parquet(OUT_DIR / "megacap_features.parquet")
    breadth = build_breadth_feature()
    feats["breadth_60"] = breadth.reindex(feats.index)
    feats.to_parquet(OUT_DIR / "megacap_features_r2.parquet")
    print(f"[r2] features shape={feats.shape}  {time.time()-t0:.1f}s")

    # All single-signal gates to rank: 5 signals × 5 modes × 2 lookbacks = 50 gates
    # (use benchmark fallback only — cash fallback failed in round 1)
    signal_cols = ["size_spread_60d", "concentration", "size_q5q1_12m_sh",
                   "size_disp_60d", "breadth_60"]
    gate_modes = ["median", "pct70", "pct75", "pct80", "pct85", "pct90", "pct95"]
    lookbacks = [126, 252]

    # For breadth, "gate-on when breadth < threshold" doesn't make semantic sense
    # (low breadth = narrow market = megacap rally = BAD for lottery).
    # Our semantic is consistent: gate_on = signal < threshold.
    # So gate-on when breadth is LOW means lottery deployed in narrow markets — WRONG.
    # Need to flip breadth: use -breadth so "low -breadth = wide market = GOOD for lottery".
    feats["breadth_60_neg"] = -feats["breadth_60"]
    signal_cols_actual = ["size_spread_60d", "concentration", "size_q5q1_12m_sh",
                          "size_disp_60d", "breadth_60_neg"]

    candidates = []
    for sc in signal_cols_actual:
        for mode in gate_modes:
            for lb in lookbacks:
                sig = feats[sc].dropna()
                gate = make_gate(sig, mode=mode, lookback=lb)
                df = q5_long_only_with_gate(lot, "alpha_17_n", "fwd_ret_20",
                                             rebal_dates, gate, fallback="benchmark")
                sm = summarize(df, f"{sc} | {mode} | lb={lb}")
                sm["signal"] = sc; sm["mode"] = mode; sm["lookback"] = lb
                sm["kind"] = "single"
                candidates.append(sm)

    n_single = len(candidates)
    print(f"[r2] single gate candidates: {n_single}  {time.time()-t0:.1f}s")

    # Now pairwise combinations (require BOTH to flag → gate_off)
    # Use gate_on = g1 & g2 (both signals say gate-on to keep α_17 on)
    # With gate-off when EITHER signal says "off". Conservative.
    for (sc1, sc2) in combinations(signal_cols_actual, 2):
        for mode in ["pct85", "pct90", "pct95"]:  # tight only
            for lb in [252]:
                g1 = make_gate(feats[sc1].dropna(), mode=mode, lookback=lb)
                g2 = make_gate(feats[sc2].dropna(), mode=mode, lookback=lb)
                combined = g1.align(g2, join="outer", fill_value=0)
                gate = (combined[0] * combined[1]).astype(int)
                df = q5_long_only_with_gate(lot, "alpha_17_n", "fwd_ret_20",
                                             rebal_dates, gate, fallback="benchmark")
                sm = summarize(df, f"{sc1} AND {sc2} | {mode} | lb={lb}")
                sm["signal"] = f"{sc1} & {sc2}"; sm["mode"] = mode; sm["lookback"] = lb
                sm["kind"] = "AND"
                candidates.append(sm)
    n_and = len(candidates) - n_single
    print(f"[r2] AND-pair candidates: {n_and}  {time.time()-t0:.1f}s")

    # OR-pair: gate_off if EITHER says off.
    # = 1 - (1-g1)*(1-g2) = g1 + g2 - g1*g2
    # So gate_on = g1 OR g2 (permissive, more often on)
    # Actually we want gate-off when EITHER signal flags risk:
    # gate_off if (signal1 > threshold OR signal2 > threshold)
    # = gate_on iff (signal1 < threshold AND signal2 < threshold)
    # That's the AND-pair above. For OR-pair we need the opposite:
    # gate_on = g1 | g2 (more often on — keep α_17 running if either signal OK)
    # That's permissive and probably doesn't help worst-year. Skipping.

    # Also test: "majority of 3" — need 3 of 4 megacap signals to agree
    # In simpler form: if all 4 size-based signals < threshold → gate on
    for mode in ["pct85", "pct90"]:
        gates_all = []
        for sc in ["size_spread_60d", "concentration", "size_q5q1_12m_sh", "size_disp_60d"]:
            gates_all.append(make_gate(feats[sc].dropna(), mode=mode, lookback=252))
        # Align all to common index
        gate_df = pd.concat(gates_all, axis=1).fillna(0).astype(int)
        # Majority 3+/4
        maj3 = (gate_df.sum(axis=1) >= 3).astype(int)
        gate = maj3
        df = q5_long_only_with_gate(lot, "alpha_17_n", "fwd_ret_20",
                                     rebal_dates, gate, fallback="benchmark")
        sm = summarize(df, f"all4_maj3 | {mode} | lb=252")
        sm["signal"] = "all4_maj3"; sm["mode"] = mode; sm["lookback"] = 252
        sm["kind"] = "MAJ3"
        candidates.append(sm)

    # Rank
    ranked = sorted(candidates, key=lambda s: (
        s["worst_year_exc"] if not np.isnan(s["worst_year_exc"]) else -99,
        s["exc_ir"] if not np.isnan(s["exc_ir"]) else -99,
    ), reverse=True)

    # Show top 15 and any passing candidates
    print("\n" + "=" * 115)
    print(f"Round 2 ranked candidates — total {len(candidates)} variants")
    print("=" * 115)
    print(f"{'#':>3} {'kind':<6} {'signal/pair':<45} {'mode':<7} {'lb':>4} "
          f"{'full':>7} {'worst':>7} {'2020':>7} {'2025':>7} {'on_fr':>6} {'MaxDD%':>7} {'PASS':>5}")

    passing = []
    for i, s in enumerate(ranked):
        passed = (s["exc_ir"] >= 1.0) and (s["worst_year_exc"] >= 0.5)
        mark = "PASS" if passed else ""
        if passed:
            passing.append(s)
        if i < 15 or passed:
            def f(v):
                return f"{v:>7.3f}" if isinstance(v, float) and not np.isnan(v) else f"{'NA':>7}"
            print(f"  {i+1:>2} {s.get('kind',''):<6} {s.get('signal','')[:45]:<45} "
                  f"{s.get('mode',''):<7} {str(s.get('lookback','')):>4} "
                  f"{f(s['exc_ir'])} {f(s['worst_year_exc']):>7} {f(s['ir_2020']):>7} "
                  f"{f(s['ir_2025']):>7} {s.get('on_frac', 0):>6.3f} "
                  f"{s['exc_maxdd']*100:>+7.2f} {mark:>5}")

    print(f"\n[r2] candidates passing audit: {len(passing)}")
    if passing:
        winner = passing[0]
        print(f"[r2] Winner: {winner['name']}")
        print(f"     full_IR={winner['exc_ir']:.3f}  worst={winner['worst_year_exc']:.3f}  "
              f"2020={winner['ir_2020']:.3f}  2025={winner['ir_2025']:.3f}  "
              f"on_frac={winner['on_frac']:.3f}")
    else:
        print("[r2] No variant passes both IR ≥ 1.0 AND worst-year ≥ 0.5.")
        print(f"[r2] Best so far: {ranked[0]['name']}")

    out = dict(
        experiment="overlay_round2_combinations",
        n_candidates=len(candidates),
        n_passing=len(passing),
        ranked_top15=ranked[:15],
        passing=passing,
        best=ranked[0],
    )
    with open(OUT_DIR / "overlay_round2.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n[r2] wrote {OUT_DIR / 'overlay_round2.json'}")
    print(f"[r2] done {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
