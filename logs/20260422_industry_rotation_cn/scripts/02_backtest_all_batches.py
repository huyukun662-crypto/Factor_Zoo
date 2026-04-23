"""
Agent 4 · Backtest Operator · batches 0001/0002/0003 (24 specs)

Inputs : outputs/industry_weekly.parquet
Outputs:
  outputs/backtest_results_batch_0001.parquet (8 A-variants)
  outputs/backtest_results_batch_0002.parquet (8 B-variants)
  outputs/backtest_results_batch_0003.parquet (8 C-variants)
  outputs/equity_curves.parquet (all 24 + equal-weight bench + cash)
  outputs/backtest_summary.csv

Conventions:
  - delay = 1 (Fri signal, Mon open execute)
  - weekly rebalance, top-3 long-only equal weight (except C8 LS)
  - cost_bps_per_side = 5 (applied on turnover)
  - benchmark = industry equal-weight (31 industries reweighted weekly)
"""
import os, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")
W = pd.read_parquet(OUT / "industry_weekly.parquet")
W = W.sort_values(["trade_week", "industry_code"]).reset_index(drop=True)
INDS = sorted(W["industry_code"].unique().tolist())
say = lambda s: print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)
say(f"Loaded weekly panel: {len(W):,} rows  {len(INDS)} industries  {W['trade_week'].nunique()} weeks")

# Build wide matrices indexed by trade_week × industry
def pivot(col):
    return W.pivot(index="trade_week", columns="industry_code", values=col).sort_index()

ret = pivot("ret_w")              # T × N  (realized return for week ending t)
turn = pivot("turnover_mv_w")     # T × N  (weekly turnover ratio)
dates = ret.index
T, N = ret.shape
say(f"ret matrix: {T}×{N}")

# Cumulative index for signal computation
# cum[t] = prod(1 + ret[:t]) → use shift to avoid lookahead
gross = 1.0 + ret.fillna(0)
cum = gross.cumprod()

# --- Feature builders ---
def mom_W(W_):
    """W-week return ending at t (uses info up to and including t)."""
    return cum / cum.shift(W_) - 1

def turn_avg(W_):
    return turn.rolling(W_, min_periods=max(2, W_ // 2)).mean()

def turn_delta_52(W_):
    """Short/long turnover ratio - 1 (crowding delta)."""
    num = turn.rolling(W_, min_periods=max(2, W_//2)).mean()
    den = turn.rolling(52, min_periods=20).mean()
    return num / den - 1.0

def zscore_cs(df):
    """Cross-sectional z per row (across industries)."""
    mu = df.mean(axis=1)
    sd = df.std(axis=1)
    return df.sub(mu, axis=0).div(sd, axis=0)

def breadth():
    """Market-wide breadth: % industries with cum above its 20w mean — broadcast to all industries."""
    ma20 = cum.rolling(20, min_periods=8).mean()
    above = (cum > ma20).astype(float).mean(axis=1)  # series T
    # Center around 0 by subtracting long-run mean, scale by std
    z = (above - above.rolling(52, min_periods=20).mean()) / above.rolling(52, min_periods=20).std()
    # Broadcast to T×N
    return pd.DataFrame({c: z for c in INDS})

# --- Portfolio construction from score ---
def topn_weights(score, n=3, long_only=True):
    """Given T×N score, compute long-only top-n equal weights (delay applied outside).
    Build via numpy then wrap back to DataFrame (avoids CoW chained assignment bug)."""
    cols = score.columns
    w_mat = np.zeros_like(score.values, dtype=float)
    sv = score.values
    rv = ret.values
    for t_idx in range(sv.shape[0]):
        s = sv[t_idx]
        v = np.isfinite(s) & np.isfinite(rv[t_idx])
        if v.sum() < n:
            continue
        s_v = np.where(v, s, -np.inf)
        top_ix = np.argpartition(-s_v, n)[:n]
        w_mat[t_idx, top_ix] = 1.0 / n
        if not long_only:
            s_v2 = np.where(v, s, np.inf)
            bot_ix = np.argpartition(s_v2, n)[:n]
            w_mat[t_idx, bot_ix] = -1.0 / n
    return pd.DataFrame(w_mat, index=score.index, columns=cols)

def layered_select(mom_score, crowd_score, k=10, n=3):
    """Step1: top K by mom; step2: lowest n by crowd_score within those K."""
    cols = mom_score.columns
    w_mat = np.zeros_like(mom_score.values, dtype=float)
    mv = mom_score.values
    cv = crowd_score.reindex(index=mom_score.index, columns=cols).values
    for t_idx in range(mv.shape[0]):
        m = mv[t_idx]; c = cv[t_idx]
        vm = np.isfinite(m)
        if vm.sum() < k: continue
        m_v = np.where(vm, m, -np.inf)
        topk_ix = np.argpartition(-m_v, k)[:k]
        c_top = c[topk_ix]
        vc = np.isfinite(c_top)
        if vc.sum() < n: continue
        c_top_v = np.where(vc, c_top, np.inf)
        sel_in_k = np.argpartition(c_top_v, n)[:n]
        sel_ix = topk_ix[sel_in_k]
        w_mat[t_idx, sel_ix] = 1.0 / n
    return pd.DataFrame(w_mat, index=mom_score.index, columns=cols)

# --- Run backtest on weight matrix ---
def run_backtest(weights, name, cost_bps=5):
    """weights: T×N (signal available at t, executed at t+1 open → return from t+1 to t+2 uses ret.shift(-1) style).
    We apply delay=1 by shifting weights forward by 1 week before pairing with ret.
    """
    w_exec = weights.shift(1)   # delay=1
    # Realized weekly return for portfolio = sum(w_exec * ret)
    pnl_gross = (w_exec * ret).sum(axis=1)
    # Turnover = sum(|w_exec_t - w_exec_{t-1}|) / 2 (one-way)
    tov = (w_exec.fillna(0).diff().abs().sum(axis=1) / 2.0).fillna(0)
    cost = tov * (cost_bps / 1e4)
    pnl_net = pnl_gross - cost
    eq = (1.0 + pnl_net).cumprod()
    return pd.DataFrame({
        "trade_week": ret.index,
        "pnl_gross": pnl_gross.values,
        "turnover": tov.values,
        "cost": cost.values,
        "pnl_net": pnl_net.values,
        "equity": eq.values,
    }).assign(spec=name)

# --- Summary stats ---
def summarize(bt, name):
    r = bt["pnl_net"].dropna()
    yrs = len(r) / 52.0
    ann_ret = (1.0 + r).prod()**(1/yrs) - 1 if yrs > 0 else np.nan
    ann_vol = r.std() * np.sqrt(52)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else np.nan
    eq = (1+r).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    tov = bt["turnover"].mean() * 52.0  # annualized one-way
    # Per-year sharpe
    y = bt.set_index("trade_week")["pnl_net"]
    y.index = pd.to_datetime(y.index)
    per_year = y.resample("YE").apply(
        lambda s: (s.mean()*52) / (s.std()*np.sqrt(52)) if len(s) > 4 and s.std() > 0 else np.nan
    ).rename("sharpe_y")
    py = per_year.dropna()
    worst = py.min() if len(py) else np.nan
    best  = py.max() if len(py) else np.nan
    # best-out sharpe
    if len(py) >= 2:
        idx_max = py.idxmax()
        r_no = y[y.index.year != idx_max.year]
        sh_no = (r_no.mean()*52) / (r_no.std()*np.sqrt(52)) if r_no.std() > 0 else np.nan
    else:
        sh_no = np.nan
    return {
        "spec": name, "ann_ret": ann_ret, "ann_vol": ann_vol, "sharpe": sharpe,
        "max_dd": dd, "turnover_ann": tov, "worst_year_sharpe": worst,
        "best_year_sharpe": best, "sharpe_ex_best_year": sh_no, "n_weeks": len(r),
    }

# ============================================================
# Build all signals & run
# ============================================================
all_bt = []
summary_rows = []

# Pre-compute features
mom = {w_: mom_W(w_) for w_ in [1, 2, 3, 4, 8, 12]}
t_avg = {w_: turn_avg(w_) for w_ in [2, 4, 8]}
t_delta = turn_delta_52(4)
bread = breadth()

# --- Batch 0001 · Variant A (penalized) ---
say("[batch 0001] Variant A …")
A_specs = [
    ("A1_lam05_m4_t4",   zscore_cs(mom[4])  - 0.5 * zscore_cs(t_avg[4])),
    ("A2_lam10_m4_t4",   zscore_cs(mom[4])  - 1.0 * zscore_cs(t_avg[4])),
    ("A3_lam15_m4_t4",   zscore_cs(mom[4])  - 1.5 * zscore_cs(t_avg[4])),
    ("A4_lam10_m8_t4",   zscore_cs(mom[8])  - 1.0 * zscore_cs(t_avg[4])),
    ("A5_lam10_m12_t4",  zscore_cs(mom[12]) - 1.0 * zscore_cs(t_avg[4])),
    ("A6_lam10_m4_t8",   zscore_cs(mom[4])  - 1.0 * zscore_cs(t_avg[8])),
    ("A7_lam10_m4_t4_b", zscore_cs(mom[4])  - 1.0 * zscore_cs(t_avg[4]) + 0.3 * bread),
    ("A8_lam00_pure_m4", zscore_cs(mom[4])),
]
batch_A = []
for name, score in A_specs:
    w = topn_weights(score, n=3)
    bt = run_backtest(w, name)
    batch_A.append(bt)
    summary_rows.append(summarize(bt, name) | {"family": "A"})
pd.concat(batch_A).to_parquet(OUT / "backtest_results_batch_0001.parquet")
say(f"[batch 0001] wrote 8 A-variants")

# --- Batch 0002 · Variant B (layered) ---
say("[batch 0002] Variant B …")
B_specs = [
    ("B1_m4_K10_t4",   mom[4], t_avg[4], 10),
    ("B2_m4_K8_t4",    mom[4], t_avg[4],  8),
    ("B3_m4_K14_t4",   mom[4], t_avg[4], 14),
    ("B4_m8_K10_t4",   mom[8], t_avg[4], 10),
    ("B5_m12_K10_t4",  mom[12], t_avg[4], 10),
    ("B6_m4_K10_t8",   mom[4], t_avg[8], 10),
    ("B7_m4_K10_t4_br", mom[4], t_avg[4] - 0.3 * zscore_cs(bread), 10),
    ("B8_m4_K10_dturn", mom[4], t_delta, 10),
]
batch_B = []
for name, mscore, cscore, k in B_specs:
    w = layered_select(mscore, cscore, k=k, n=3)
    bt = run_backtest(w, name)
    batch_B.append(bt)
    summary_rows.append(summarize(bt, name) | {"family": "B"})
pd.concat(batch_B).to_parquet(OUT / "backtest_results_batch_0002.parquet")
say(f"[batch 0002] wrote 8 B-variants")

# --- Batch 0003 · Variant C (reversal) ---
say("[batch 0003] Variant C …")
C_specs = [
    ("C1_rev1w",        -mom[1],   3, True,  False),
    ("C2_rev2w",        -mom[2],   3, True,  False),
    ("C3_rev3w",        -mom[3],   3, True,  False),
    ("C4_rev4w",        -mom[4],   3, True,  False),
    ("C5_rev2w_crowdx", (-mom[2]) * (1 + 0.5 * zscore_cs(t_avg[2])), 3, True, False),
    ("C6_rev4w_crowdx", (-mom[4]) * (1 + 0.5 * zscore_cs(t_avg[4])), 3, True, False),
    ("C7_rev2w_long",   -mom[2],   3, True,  False),
    ("C8_rev2w_LS",     -mom[2],   3, False, True),  # long bottom-3, short top-3
]
batch_C = []
for name, score, n, long_only, ls in C_specs:
    if ls:
        # long bottom-3, short top-3 via w_top + w_bot from both ends
        w_pos = topn_weights(score, n=n)                   # top-score = bottom-mom (long)
        w_neg = -topn_weights(-score, n=n)                  # bottom-score = top-mom (short)
        w = w_pos + w_neg
    else:
        w = topn_weights(score, n=n, long_only=long_only)
    bt = run_backtest(w, name)
    batch_C.append(bt)
    summary_rows.append(summarize(bt, name) | {"family": "C"})
pd.concat(batch_C).to_parquet(OUT / "backtest_results_batch_0003.parquet")
say(f"[batch 0003] wrote 8 C-variants")

# --- Benchmark: equal-weight 31 industries ---
w_eq = pd.DataFrame(1.0/N, index=ret.index, columns=ret.columns).where(ret.notna(), 0.0)
bt_eq = run_backtest(w_eq, "EQW_BENCH")
summary_rows.append(summarize(bt_eq, "EQW_BENCH") | {"family": "bench"})

# --- Save ---
summary = pd.DataFrame(summary_rows).sort_values(["family", "sharpe"], ascending=[True, False])
summary.to_csv(OUT / "backtest_summary.csv", index=False)

# Equity curves (all)
curves = pd.concat(batch_A + batch_B + batch_C + [bt_eq])
curves.to_parquet(OUT / "equity_curves.parquet")

# Print compact summary
say("\n========== SUMMARY ==========")
print(summary[["spec","family","ann_ret","sharpe","max_dd","turnover_ann","worst_year_sharpe","sharpe_ex_best_year"]].to_string(index=False))
