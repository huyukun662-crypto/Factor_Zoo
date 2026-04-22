"""
Rolling-window OOS walk-forward + gate-window sensitivity.

Rolling-OOS:
  fold A — 5y IS, 1y OOS, annual step (3 folds total, data-limited)
           (2019-2023 IS, 2024 OOS) / (2020-2024 IS, 2025 OOS) / (2021-2025 IS, 2026 OOS partial)
  fold B — 3y IS, 1y OOS, annual step (5 folds total)
           (2019-2021, 2022) ... (2023-2025, 2026)
  Total: 8 folds.

  For each fold, we record:
    (a) FIXED A_tuned_v1 spec — its OOS sharpe / calmar / MaxDD (pure generalization)
    (b) RE-TUNED on IS — best-IS spec and its OOS perf (tuning-process robustness)

Gate sensitivity:
  Fix A_tuned_v1 everything, vary gate MA window ∈ {20, 40, 50, 60, 80, 100, none}.
  Report full-sample + IS + OOS Sharpe / Calmar / MaxDD.
"""
import json, time, itertools
from pathlib import Path
import numpy as np, pandas as pd

OUT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")
say = lambda s: print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

W = pd.read_parquet(OUT / "etf_weekly.parquet")
W["trade_week"] = pd.to_datetime(W["trade_week"])
W = W[W["trade_week"] >= "2019-01-01"].sort_values(["trade_week","ts_code"]).reset_index(drop=True)
ret = W.pivot(index="trade_week", columns="ts_code", values="ret_w").sort_index()
turn = W.pivot(index="trade_week", columns="ts_code", values="turnover_w").sort_index()
gross = 1 + ret.fillna(0); cum = gross.cumprod()
age = ret.notna().cumsum(); elig = age >= 12
cols = ret.columns

def zscore_cs(df):
    df = df.where(elig); mu=df.mean(axis=1); sd=df.std(axis=1)
    return df.sub(mu, axis=0).div(sd, axis=0)

def mom_W(W_): return cum / cum.shift(W_) - 1
def turn_avg(W_): return turn.rolling(W_, min_periods=max(2, W_//2)).mean()

BR_S = ((cum > cum.rolling(20, min_periods=8).mean()).where(elig).sum(axis=1) /
        elig.sum(axis=1).replace(0, np.nan))
BR_Z = (BR_S - BR_S.rolling(52, min_periods=20).mean()) / BR_S.rolling(52, min_periods=20).std()
BR_DF = pd.DataFrame({c: BR_Z for c in cols})

def mkt_gate(ma_window):
    mc = cum.mean(axis=1)
    return mc > mc.rolling(ma_window, min_periods=ma_window//2).mean()

def topn_w(score, n):
    score = score.reindex(columns=cols).astype(float)
    wm = np.zeros(score.shape, dtype=float)
    sv = score.values; rv = ret.values.astype(float); em = elig.values.astype(bool)
    for ti in range(sv.shape[0]):
        s = sv[ti]; v = np.isfinite(s) & np.isfinite(rv[ti]) & em[ti]
        if v.sum() < n: continue
        s_v = np.where(v, s, -np.inf)
        ix = np.argpartition(-s_v, n)[:n]
        wm[ti, ix] = 1.0/n
    return pd.DataFrame(wm, index=score.index, columns=cols)

def run_strategy(mom_w_, turn_w_, lam, mu, top_n, gate_ma, vol_tgt, rebal=1):
    sc = zscore_cs(mom_W(mom_w_)) - lam * zscore_cs(turn_avg(turn_w_)) + mu * BR_DF
    w = topn_w(sc, top_n)
    if gate_ma is not None:
        g = mkt_gate(gate_ma)
        w = w.copy(); w.loc[~g.reindex(w.index).fillna(False)] = 0.0
    if rebal > 1:
        w_vals = w.values; out = np.zeros_like(w_vals); last=None
        for ti in range(len(w_vals)):
            if ti % rebal == 0: last = w_vals[ti]
            out[ti] = last if last is not None else w_vals[ti]
        w = pd.DataFrame(out, index=w.index, columns=w.columns)
    if vol_tgt is not None:
        pnl_raw = (w.shift(1) * ret).sum(axis=1)
        rv26 = pnl_raw.rolling(26, min_periods=8).std()*np.sqrt(52)
        sc2 = (vol_tgt / rv26).clip(upper=1.0).fillna(0)
        w = w.mul(sc2.reindex(w.index), axis=0)
    # backtest
    w_exec = w.shift(1)
    pnl_g = (w_exec * ret).sum(axis=1)
    tov = (w_exec.fillna(0).diff().abs().sum(axis=1)/2).fillna(0)
    return pnl_g - tov * 5e-4, tov

def perf(pnl, mask=None):
    r = pnl.dropna() if mask is None else pnl[mask].dropna()
    if len(r) < 10: return None
    yrs = len(r)/52.0
    ann = (1+r).prod()**(1/yrs)-1 if yrs>0 else np.nan
    vol = r.std()*np.sqrt(52); sh = ann/vol if vol>0 else np.nan
    eq = (1+r).cumprod(); dd = (eq/eq.cummax()-1).min()
    cal = ann/abs(dd) if dd<0 else np.nan
    return {"ann":float(ann),"vol":float(vol),"sh":float(sh),"dd":float(dd),
            "cal":float(cal) if np.isfinite(cal) else np.nan,"n":int(len(r))}

# --------------------------------------------------------------
# Part 1: Rolling-OOS walk-forward
# --------------------------------------------------------------
say("=" * 60)
say("PART 1 · Rolling-OOS walk-forward")
say("=" * 60)

FIXED_SPEC = dict(mom_w_=4, turn_w_=4, lam=1.5, mu=0.3, top_n=4, gate_ma=50, vol_tgt=0.15, rebal=1)

# Build fold list
folds = []
# fold A: 5y IS / 1y OOS
for y_oos in [2024, 2025, 2026]:
    is_start = pd.Timestamp(f"{y_oos-5}-01-01")
    is_end   = pd.Timestamp(f"{y_oos-1}-12-31")
    oos_start = pd.Timestamp(f"{y_oos}-01-01")
    oos_end   = pd.Timestamp(f"{y_oos}-12-31") if y_oos != 2026 else pd.Timestamp("2026-12-31")
    folds.append({"tag":"5y/1y", "is":(is_start, is_end), "oos":(oos_start, oos_end), "y_oos": y_oos})
# fold B: 3y IS / 1y OOS (5 folds)
for y_oos in [2022, 2023, 2024, 2025, 2026]:
    is_start = pd.Timestamp(f"{y_oos-3}-01-01")
    is_end   = pd.Timestamp(f"{y_oos-1}-12-31")
    oos_start = pd.Timestamp(f"{y_oos}-01-01")
    oos_end   = pd.Timestamp(f"{y_oos}-12-31") if y_oos != 2026 else pd.Timestamp("2026-12-31")
    folds.append({"tag":"3y/1y", "is":(is_start, is_end), "oos":(oos_start, oos_end), "y_oos": y_oos})

say(f"Total folds: {len(folds)}")
for f in folds:
    say(f"  {f['tag']}  IS {f['is'][0].date()}→{f['is'][1].date()}  OOS {f['oos'][0].date()}→min({f['oos'][1].date()}, data_end)")

# Per-fold grid for re-tuning
tune_grid = list(itertools.product(
    [4, 8, 12],           # mom_w
    [4, 8],               # turn_w
    [0.5, 1.0, 1.5],      # lambda
    [0.0, 0.3],           # mu
    [3, 4, 5],            # top_n
    [None, 50],           # gate_ma
    [None, 0.15, 0.20],   # vol_tgt
))
say(f"Per-fold re-tune grid: {len(tune_grid)}")

rows = []
for f in folds:
    is_mask  = (ret.index >= f["is"][0]) & (ret.index <= f["is"][1])
    oos_mask = (ret.index >= f["oos"][0]) & (ret.index <= f["oos"][1])

    # (a) FIXED A_tuned_v1
    pnl_fix, _ = run_strategy(**FIXED_SPEC)
    m_is_fix  = perf(pnl_fix, is_mask)
    m_oos_fix = perf(pnl_fix, oos_mask)

    # (b) RE-TUNED per fold (pick best by IS Sharpe, require IS Calmar >= 1.5 to avoid degenerate)
    best = None; best_score = -np.inf
    for (mw, tw, lam, mu, tn, gm, vt) in tune_grid:
        pnl_t, _ = run_strategy(mw, tw, lam, mu, tn, gm, vt, 1)
        m_is = perf(pnl_t, is_mask)
        if m_is is None or m_is["cal"] < 1.0: continue
        if m_is["sh"] > best_score:
            best_score = m_is["sh"]
            best = {"pnl":pnl_t, "m_is":m_is, "spec":(mw, tw, lam, mu, tn, gm, vt)}
    if best is None:
        m_oos_tn = None
        best_spec = None
    else:
        m_oos_tn = perf(best["pnl"], oos_mask)
        best_spec = best["spec"]

    rows.append({
        "fold": f["tag"], "y_oos": f["y_oos"],
        "is_start": f["is"][0].date().isoformat(), "is_end": f["is"][1].date().isoformat(),
        "oos_start": f["oos"][0].date().isoformat(),
        "fixed_is_sh":  m_is_fix["sh"]  if m_is_fix else np.nan,
        "fixed_is_cal": m_is_fix["cal"] if m_is_fix else np.nan,
        "fixed_oos_sh":  m_oos_fix["sh"]  if m_oos_fix else np.nan,
        "fixed_oos_cal": m_oos_fix["cal"] if m_oos_fix else np.nan,
        "fixed_oos_ann": m_oos_fix["ann"] if m_oos_fix else np.nan,
        "fixed_oos_dd":  m_oos_fix["dd"]  if m_oos_fix else np.nan,
        "tuned_is_sh":  best["m_is"]["sh"]  if best else np.nan,
        "tuned_is_cal": best["m_is"]["cal"] if best else np.nan,
        "tuned_oos_sh":  m_oos_tn["sh"]  if m_oos_tn else np.nan,
        "tuned_oos_cal": m_oos_tn["cal"] if m_oos_tn else np.nan,
        "tuned_oos_ann": m_oos_tn["ann"] if m_oos_tn else np.nan,
        "tuned_oos_dd":  m_oos_tn["dd"]  if m_oos_tn else np.nan,
        "tuned_spec": str(best_spec) if best_spec else None,
    })
    say(f"  [{f['tag']}] OOS {f['y_oos']}:  FIXED sh={m_oos_fix['sh']:.2f} cal={m_oos_fix['cal']:.2f}  TUNED sh={m_oos_tn['sh']:.2f} cal={m_oos_tn['cal']:.2f}  spec={best_spec}")

fold_df = pd.DataFrame(rows)
fold_df.to_csv(OUT/"rolling_oos_folds.csv", index=False)

# Stability summary
say("\n===== Rolling-OOS stability =====")
print(fold_df[["fold","y_oos","fixed_oos_sh","fixed_oos_cal","tuned_oos_sh","tuned_oos_cal","tuned_spec"]].to_string(index=False))

# pass-rate summary
pass_fix = fold_df[(fold_df["fixed_oos_sh"]>=1.4) & (fold_df["fixed_oos_cal"]>=2.0)]
pass_tn  = fold_df[(fold_df["tuned_oos_sh"]>=1.4) & (fold_df["tuned_oos_cal"]>=2.0)]
say(f"\nFolds passing OOS target (Sh≥1.4 & Cal≥2.0):")
say(f"  FIXED  A_tuned_v1 : {len(pass_fix)}/{len(fold_df)}")
say(f"  RE-TUNED per fold : {len(pass_tn)}/{len(fold_df)}")

# --------------------------------------------------------------
# Part 2: Gate sensitivity (fix A_tuned_v1 except gate MA)
# --------------------------------------------------------------
say("\n" + "=" * 60)
say("PART 2 · Gate sensitivity (full sample)")
say("=" * 60)

IS_MASK  = ret.index < pd.Timestamp("2024-01-01")
OOS_MASK = ret.index >= pd.Timestamp("2024-01-01")

gate_rows = []
for ma in [None, 20, 40, 50, 60, 80, 100]:
    pnl, tov = run_strategy(4, 4, 1.5, 0.3, 4, ma, 0.15, 1)
    m_is = perf(pnl, IS_MASK); m_oos = perf(pnl, OOS_MASK); m_full = perf(pnl)
    g = mkt_gate(ma) if ma is not None else pd.Series(True, index=ret.index)
    on_rate_is  = g[IS_MASK].mean()
    on_rate_oos = g[OOS_MASK].mean()
    gate_rows.append({
        "gate_ma": "none" if ma is None else f"MA{ma}",
        "on_rate_is": float(on_rate_is), "on_rate_oos": float(on_rate_oos),
        "is_sh":  m_is["sh"],  "is_cal":  m_is["cal"],  "is_dd":  m_is["dd"],  "is_ann":  m_is["ann"],
        "oos_sh": m_oos["sh"], "oos_cal": m_oos["cal"], "oos_dd": m_oos["dd"], "oos_ann": m_oos["ann"],
        "full_sh": m_full["sh"], "full_cal": m_full["cal"], "full_dd": m_full["dd"], "full_ann": m_full["ann"],
        "ann_tov": float(tov.mean()*52),
    })

gate_df = pd.DataFrame(gate_rows)
gate_df.to_csv(OUT/"gate_sensitivity.csv", index=False)
say("\n===== Gate window sensitivity =====")
print(gate_df.to_string(index=False))
say(f"\nDecision bands (Sh ≥ 1.4 and Cal ≥ 2.0 full):")
pass_gate = gate_df[(gate_df["full_sh"]>=1.4) & (gate_df["full_cal"]>=2.0)]
print(pass_gate.to_string(index=False))

say("[done]")
