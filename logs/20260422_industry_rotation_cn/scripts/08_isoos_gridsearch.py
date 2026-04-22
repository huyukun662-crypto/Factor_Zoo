"""
Round 5 · IS/OOS disciplined grid search
Target : IS (2019-01 → 2023-12-31) Sharpe ≥ 1.4 AND Calmar ≥ 2.0
OOS    : 2024-01 → 2026-04 — reported but NEVER used for selection

Grid dimensions:
  - base spec: A_penalized (λ, μ, mom_W, turn_W) × top_n
  - overlay:  regime gate (5 options) × vol target (4 options) × rebalance freq
  - fixed:    delay=1, cost 5 bps/side, long-only equal weight within top-n

We run ~600 combos on IS, select passers, then evaluate OOS untouched.
"""
import json, time, itertools
from pathlib import Path
import numpy as np, pandas as pd

OUT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")
say = lambda s: print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

W = pd.read_parquet(OUT / "etf_weekly.parquet")
uni = pd.read_csv(OUT / "etf_universe.csv")
code2name = dict(zip(uni["ts_code"], uni["name"]))

W["trade_week"] = pd.to_datetime(W["trade_week"])
W = W[W["trade_week"] >= "2019-01-01"].sort_values(["trade_week","ts_code"]).reset_index(drop=True)

ret_all = W.pivot(index="trade_week", columns="ts_code", values="ret_w").sort_index()
turn_all = W.pivot(index="trade_week", columns="ts_code", values="turnover_w").sort_index()
gross_all = 1.0 + ret_all.fillna(0)
cum_all = gross_all.cumprod()
age_all = ret_all.notna().cumsum()
elig_all = age_all >= 12

SPLIT = pd.Timestamp("2024-01-01")
IS_MASK = ret_all.index < SPLIT
OOS_MASK = ret_all.index >= SPLIT
say(f"IS weeks: {IS_MASK.sum()}   OOS weeks: {OOS_MASK.sum()}")


# ---------- signal and weight builders ----------
def mom_W(W_): return cum_all / cum_all.shift(W_) - 1
def turn_avg(W_): return turn_all.rolling(W_, min_periods=max(2, W_//2)).mean()
def zscore_cs(df):
    df = df.where(elig_all)
    mu = df.mean(axis=1); sd = df.std(axis=1)
    return df.sub(mu, axis=0).div(sd, axis=0)
def breadth_series():
    ma20 = cum_all.rolling(20, min_periods=8).mean().where(elig_all)
    n_e = elig_all.sum(axis=1).replace(0, np.nan)
    return (cum_all > ma20).where(elig_all).sum(axis=1) / n_e
BR_SER = breadth_series()

def bread_df():
    z = (BR_SER - BR_SER.rolling(52, min_periods=20).mean()) / BR_SER.rolling(52, min_periods=20).std()
    return pd.DataFrame({c: z for c in ret_all.columns})
BR_DF = bread_df()

def mkt_ma(window):
    mc = cum_all.mean(axis=1)
    return mc > mc.rolling(window, min_periods=window//2).mean()

GATES = {
    "none":         pd.Series(True, index=ret_all.index),
    "br30":         (BR_SER > 0.30),
    "br40":         (BR_SER > 0.40),
    "mkt_ma20":     mkt_ma(20),
    "mkt_ma50":     mkt_ma(50),
}

def topn_weights(score, n=3):
    score = score.reindex(columns=ret_all.columns).astype(float)
    cols = score.columns
    w_mat = np.zeros(score.shape, dtype=float)
    sv = score.values; rv = ret_all.values; em = elig_all.values
    for t_idx in range(sv.shape[0]):
        s = sv[t_idx]; v = np.isfinite(s) & np.isfinite(rv[t_idx]) & em[t_idx]
        if v.sum() < n: continue
        s_v = np.where(v, s, -np.inf)
        ix = np.argpartition(-s_v, n)[:n]
        w_mat[t_idx, ix] = 1.0/n
    return pd.DataFrame(w_mat, index=score.index, columns=cols)

def apply_gate(weights, gate):
    w = weights.copy()
    off = ~gate.reindex(w.index).fillna(False)
    w.loc[off] = 0.0
    return w

def apply_vol_target(weights, target_vol_ann, lookback_weeks=26):
    """Scale weights by target_vol / realized_portfolio_vol (26w rolling). Hard-cap leverage at 1.0 (long-only, no leverage up)."""
    pnl_raw = (weights.shift(1) * ret_all).sum(axis=1)
    rv = pnl_raw.rolling(lookback_weeks, min_periods=8).std() * np.sqrt(52)
    scale = (target_vol_ann / rv).clip(upper=1.0).fillna(0.0)
    return weights.mul(scale.reindex(weights.index), axis=0)

def apply_rebalance(weights, freq_weeks):
    """Keep weights fixed for N weeks: only re-compute on (t % freq == 0)."""
    if freq_weeks <= 1:
        return weights
    w = weights.copy().values
    out = np.zeros_like(w)
    last = None
    for t_idx in range(len(w)):
        if t_idx % freq_weeks == 0:
            last = w[t_idx]
        out[t_idx] = last if last is not None else w[t_idx]
    return pd.DataFrame(out, index=weights.index, columns=weights.columns)

def run_bt(weights, cost_bps=5):
    w_exec = weights.shift(1)
    pnl_g = (w_exec * ret_all).sum(axis=1)
    tov = (w_exec.fillna(0).diff().abs().sum(axis=1) / 2).fillna(0)
    cost = tov * (cost_bps/1e4)
    return pnl_g - cost, tov

def metrics(pnl, mask):
    r = pnl[mask].dropna()
    if len(r) < 10: return None
    yrs = len(r)/52.0
    ann = (1+r).prod()**(1/yrs)-1 if yrs>0 else np.nan
    vol = r.std()*np.sqrt(52); sh = ann/vol if vol>0 else np.nan
    eq = (1+r).cumprod(); dd = (eq/eq.cummax()-1).min()
    calmar = ann / abs(dd) if dd < 0 else np.nan
    # per-year
    r.index = pd.to_datetime(r.index)
    ws = r.groupby(r.index.year).apply(
        lambda s: (s.mean()*52)/(s.std()*np.sqrt(52)) if s.std()>0 else np.nan
    ).dropna()
    worst = ws.min() if len(ws)>0 else np.nan
    return {"ann_ret": float(ann), "vol":float(vol), "sharpe":float(sh),
            "max_dd":float(dd), "calmar":float(calmar) if np.isfinite(calmar) else np.nan,
            "worst_year_sharpe":float(worst), "n_weeks":int(len(r))}


# ---------- grid ----------
base_params = list(itertools.product(
    [4, 8, 12],           # mom_W
    [4, 8],               # turn_W
    [0.5, 1.0, 1.5],      # lambda
    [0.0, 0.3],           # mu
    [3, 4, 5],            # top_n
))
overlays = list(itertools.product(
    list(GATES.keys()),   # gate
    [None, 0.15, 0.20],   # vol target
    [1, 2, 4],            # rebalance freq (weeks)
))
say(f"Grid: {len(base_params)} base × {len(overlays)} overlays = {len(base_params)*len(overlays)}")

# Pre-compute signals to avoid repeated work
mom_map = {w_: mom_W(w_) for w_ in [4,8,12]}
turn_map = {w_: turn_avg(w_) for w_ in [4,8]}
z_mom = {k: zscore_cs(v) for k,v in mom_map.items()}
z_turn = {k: zscore_cs(v) for k,v in turn_map.items()}

rows = []
t0 = time.time()
for bi, (mw, tw, lam, mu, n) in enumerate(base_params):
    score = z_mom[mw] - lam * z_turn[tw] + mu * BR_DF
    w_base = topn_weights(score, n)
    for gate_name, vt, reb in overlays:
        w = apply_gate(w_base, GATES[gate_name])
        if reb > 1:
            w = apply_rebalance(w, reb)
        if vt is not None:
            w = apply_vol_target(w, vt, lookback_weeks=26)
        pnl, tov = run_bt(w)
        m_is = metrics(pnl, IS_MASK)
        if m_is is None: continue
        rows.append({
            "mom_w":mw, "turn_w":tw, "lambda":lam, "mu":mu, "top_n":n,
            "gate":gate_name, "vol_target":vt if vt else "none", "rebalance_w":reb,
            "is_sharpe":m_is["sharpe"], "is_calmar":m_is["calmar"],
            "is_ann_ret":m_is["ann_ret"], "is_max_dd":m_is["max_dd"],
            "is_worst_year":m_is["worst_year_sharpe"],
            "ann_tov":float(tov.mean()*52),
        })
    if (bi+1) % 10 == 0 or bi == len(base_params)-1:
        el = time.time() - t0
        say(f"  base {bi+1}/{len(base_params)}  rows={len(rows)}  elapsed {el:.0f}s")

df = pd.DataFrame(rows)
df.to_csv(OUT/"isoos_grid_full.csv", index=False)

# Rank by IS Sharpe
df_sorted = df.sort_values("is_sharpe", ascending=False)
say(f"\n===== TOP 15 by IS Sharpe =====")
print(df_sorted.head(15).to_string(index=False))

# Passers: IS Sharpe ≥ 1.4 AND Calmar ≥ 2.0
passers = df[(df["is_sharpe"]>=1.4) & (df["is_calmar"]>=2.0)].sort_values("is_sharpe", ascending=False)
say(f"\n===== PASSERS (IS Sh≥1.4 & Calmar≥2.0):  {len(passers)} =====")
print(passers.head(30).to_string(index=False))
passers.to_csv(OUT/"isoos_passers.csv", index=False)

# Also keep weaker passers (IS Sh≥1.0 & Calmar≥1.5) for OOS examination
mild = df[(df["is_sharpe"]>=1.0) & (df["is_calmar"]>=1.5)].sort_values("is_sharpe", ascending=False)
mild.to_csv(OUT/"isoos_mild_passers.csv", index=False)
say(f"Mild passers (Sh≥1.0 & Calmar≥1.5): {len(mild)}")

# ---------- evaluate OOS on top passers (up to 20) ----------
candidates = passers.head(20) if len(passers) > 0 else mild.head(20)
say(f"\n===== OOS ON TOP {len(candidates)} CANDIDATES =====")
oos_rows = []
for _, r in candidates.iterrows():
    score = z_mom[r["mom_w"]] - r["lambda"] * z_turn[r["turn_w"]] + r["mu"] * BR_DF
    w_base = topn_weights(score, int(r["top_n"]))
    w = apply_gate(w_base, GATES[r["gate"]])
    if r["rebalance_w"] > 1:
        w = apply_rebalance(w, int(r["rebalance_w"]))
    if r["vol_target"] != "none":
        w = apply_vol_target(w, float(r["vol_target"]), lookback_weeks=26)
    pnl, tov = run_bt(w)
    m_is = metrics(pnl, IS_MASK); m_oos = metrics(pnl, OOS_MASK); m_full = metrics(pnl, np.ones(len(pnl),dtype=bool))
    if m_oos is None: continue
    oos_rows.append({
        "mom_w":int(r["mom_w"]), "turn_w":int(r["turn_w"]), "lambda":r["lambda"], "mu":r["mu"],
        "top_n":int(r["top_n"]), "gate":r["gate"], "vol_target":r["vol_target"], "rebalance_w":int(r["rebalance_w"]),
        "is_sharpe": m_is["sharpe"], "is_calmar": m_is["calmar"], "is_ann":m_is["ann_ret"], "is_maxdd":m_is["max_dd"],
        "oos_sharpe": m_oos["sharpe"], "oos_calmar": m_oos["calmar"], "oos_ann":m_oos["ann_ret"], "oos_maxdd":m_oos["max_dd"],
        "full_sharpe": m_full["sharpe"], "full_calmar": m_full["calmar"],
        "oos_pass_sh14": m_oos["sharpe"]>=1.4, "oos_pass_calmar2": m_oos["calmar"]>=2.0,
    })
oos_df = pd.DataFrame(oos_rows).sort_values("oos_sharpe", ascending=False)
print(oos_df.to_string(index=False))
oos_df.to_csv(OUT/"isoos_oos_report.csv", index=False)
say("[done]")
