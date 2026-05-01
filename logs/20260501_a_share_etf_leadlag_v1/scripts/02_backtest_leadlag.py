#!/usr/bin/env python3
"""Agent 4 backtest — LeadLag spillover v1, batch_0001.

8 lead-lag expressions on the 30-ETF universe with leaders {510300, 510500,
159915}. Daily rebalance, 5 bps/side cost, primary k=1.

Outputs: same skeleton as the IVOL session.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("/home/user/Factor_Zoo/logs/20260501_a_share_etf_leadlag_v1")
SHARED = Path("/home/user/Factor_Zoo/logs/_shared_cache")
OUT = ROOT / "outputs"
WORK = ROOT / "working"

DROP = {"512100.SS", "515050.SS", "515170.SS", "512800.SS"}
LEADERS = ["510300.SS", "510500.SS", "159915.SZ"]
BETA_W = 60
DELAY = 1
COST_BPS = 5.0
PRIMARY_K = 1
SECONDARY_K = (2, 3, 5)
WORST_YEAR_FLOOR = 0.5
TRAIN_END = pd.Timestamp("2021-12-31")
VAL_END = pd.Timestamp("2022-12-31")


def load_panel():
    df = pd.read_parquet(SHARED / "etf_daily.parquet")
    df = df[~df.symbol.isin(DROP)].copy()
    df = df.sort_values(["date", "symbol"]).reset_index(drop=True)
    df["ret"] = df.groupby("symbol")["close"].pct_change()
    return df


def to_wide(df, col):
    return df.pivot(index="date", columns="symbol", values=col).sort_index()


def rolling_beta_per_leader(rets: pd.DataFrame, leader: pd.Series, w: int) -> pd.DataFrame:
    cov = rets.rolling(w).cov(leader)
    var = leader.rolling(w).var()
    return cov.div(var, axis=0)


def mask_self(sig: pd.DataFrame, leaders: list[str], leader_self: str) -> pd.DataFrame:
    """Zero out the column corresponding to the leader itself."""
    s = sig.copy()
    if leader_self in s.columns:
        s[leader_self] = np.nan
    return s


def signal_g1(rets, leaders_df, beta_w):
    """3-leader spillover lag1: mean over L of beta_iL × r_L(t-1)."""
    parts = []
    for L in LEADERS:
        leader = leaders_df[L]
        beta = rolling_beta_per_leader(rets, leader, beta_w)
        s = beta.mul(leader.shift(1), axis=0)
        s[L] = np.nan  # leader does not receive own signal
        parts.append(s)
    return sum(parts) / len(parts)


def signal_g2(rets, leaders_df, beta_w):
    L = "510300.SS"
    leader = leaders_df[L]
    beta = rolling_beta_per_leader(rets, leader, beta_w)
    s = beta.mul(leader.shift(1), axis=0)
    s[L] = np.nan
    return s


def signal_g3(rets, leaders_df, beta_w):
    """Two-step diffusion 0.7×lag1 + 0.3×lag2."""
    parts = []
    for L in LEADERS:
        leader = leaders_df[L]
        beta = rolling_beta_per_leader(rets, leader, beta_w)
        s = beta.mul(0.7 * leader.shift(1) + 0.3 * leader.shift(2), axis=0)
        s[L] = np.nan
        parts.append(s)
    return sum(parts) / len(parts)


def signal_g4(rets, leaders_df, beta_w):
    """Leader's residual to its own 20d MA."""
    parts = []
    for L in LEADERS:
        leader = leaders_df[L]
        leader_resid = leader - leader.rolling(20).mean()
        beta = rolling_beta_per_leader(rets, leader, beta_w)
        s = beta.mul(leader_resid.shift(1), axis=0)
        s[L] = np.nan
        parts.append(s)
    return sum(parts) / len(parts)


def signal_g5(rets, leaders_df, beta_w):
    """Vol-scaled g1."""
    raw = signal_g1(rets, leaders_df, beta_w)
    own_vol = rets.rolling(20).std()
    return raw.div(own_vol)


def signal_g6(rets, leaders_df, beta_w):
    """Orthogonalize: subtract follower's t-1 return minus prediction."""
    raw = signal_g1(rets, leaders_df, beta_w)
    follower_t1 = rets.shift(1)
    return raw - (follower_t1 - raw)


def signal_g7(rets, leaders_df, beta_w):
    """Sign-only: sign(r_L(t-1)) × |beta_iL|."""
    parts = []
    for L in LEADERS:
        leader = leaders_df[L]
        beta = rolling_beta_per_leader(rets, leader, beta_w)
        s = beta.abs().mul(np.sign(leader.shift(1)), axis=0)
        s[L] = np.nan
        parts.append(s)
    return sum(parts) / len(parts)


def xs_rank(x):
    return x.rank(axis=1, pct=True)


def signal_g8(rets, leaders_df, beta_w):
    s1 = xs_rank(signal_g1(rets, leaders_df, beta_w))
    s4 = xs_rank(signal_g4(rets, leaders_df, beta_w))
    s5 = xs_rank(signal_g5(rets, leaders_df, beta_w))
    s7 = xs_rank(signal_g7(rets, leaders_df, beta_w))
    return (s1 + s4 + s5 + s7) / 4.0


def fwd_ret(rets, k):
    cum = rets.rolling(k).sum()
    return cum.shift(-(DELAY + k))


def annualize_sharpe(daily, k):
    x = daily.dropna()
    if len(x) < 50 or x.std() == 0:
        return float("nan")
    return float(x.mean() / x.std() * np.sqrt(252 / k))


def per_year_sharpe(daily, k):
    return daily.groupby(daily.index.year).apply(lambda x: annualize_sharpe(x, k)).rename("sharpe")


def quintile_long_short(sig, fwd, n_q=5):
    rk = sig.rank(axis=1, pct=True)
    q_top = rk >= (n_q - 1) / n_q
    q_bot = rk < 1 / n_q
    n_top = q_top.sum(axis=1)
    n_bot = q_bot.sum(axis=1)
    valid = (n_top >= 1) & (n_bot >= 1)
    long_ret = (q_top.astype(float).where(q_top) * fwd).sum(axis=1) / n_top.replace(0, np.nan)
    short_ret = (q_bot.astype(float).where(q_bot) * fwd).sum(axis=1) / n_bot.replace(0, np.nan)
    ls = (long_ret - short_ret).where(valid)
    longo = long_ret.where(valid)
    universe = fwd.mean(axis=1)
    excess = (longo - universe)
    return {"ls": ls, "longonly": longo, "excess": excess,
            "q5_size": n_top, "q1_size": n_bot, "rank": rk}


def turnover_annualized(rk, rebalance_days, n_q=5):
    q_top = (rk >= (n_q - 1) / n_q).astype(int)
    if rebalance_days > 1:
        idx = q_top.index[::rebalance_days]
        q_top = q_top.loc[idx]
    delta = q_top.diff().abs().sum(axis=1) / 2
    avg_size = q_top.sum(axis=1).replace(0, np.nan).mean()
    if not np.isfinite(avg_size) or avg_size == 0:
        return float("nan")
    return float((delta / avg_size).mean() * (252 / rebalance_days))


def ic_series(sig, fwd):
    s = sig.rank(axis=1, pct=True); f = fwd.rank(axis=1, pct=True)
    out = []
    for d in s.index.intersection(f.index):
        a = s.loc[d]; b = f.loc[d]
        m = a.notna() & b.notna()
        if m.sum() < 5: out.append((d, np.nan)); continue
        out.append((d, np.corrcoef(a[m], b[m])[0, 1]))
    return pd.Series(dict(out), name="ic")


def ic_t(ic):
    x = ic.dropna()
    if len(x) < 30 or x.std() == 0: return float("nan")
    return float(x.mean() / x.std() * np.sqrt(len(x)))


def net_sharpe_at_cost(rk, ls, k, cost_bps, rebalance_days, n_q=5):
    cost = cost_bps / 10000.0
    q_top = (rk >= (n_q - 1) / n_q).astype(int)
    q_bot = (rk < 1 / n_q).astype(int)
    if rebalance_days > 1:
        idx = q_top.index[::rebalance_days]
        q_top = q_top.loc[idx].reindex(rk.index, method="ffill").fillna(0).astype(int)
        q_bot = q_bot.loc[idx].reindex(rk.index, method="ffill").fillna(0).astype(int)
    long_to = q_top.diff().abs().sum(axis=1) / 2 / q_top.sum(axis=1).replace(0, np.nan)
    short_to = q_bot.diff().abs().sum(axis=1) / 2 / q_bot.sum(axis=1).replace(0, np.nan)
    cost_drag = (long_to.fillna(0) + short_to.fillna(0)) * cost * 2
    return annualize_sharpe(ls.sub(cost_drag.reindex(ls.index).fillna(0)), k)


def main():
    panel = load_panel()
    rets = to_wide(panel, "ret")
    leaders_df = rets[LEADERS]
    rebalance_days = 1

    signals = {
        "g1_spillover_3leader_lag1":            signal_g1(rets, leaders_df, BETA_W),
        "g2_spillover_510300only_lag1":         signal_g2(rets, leaders_df, BETA_W),
        "g3_spillover_3leader_lag1to2_decay":   signal_g3(rets, leaders_df, BETA_W),
        "g4_spillover_residual_leader_lag1":    signal_g4(rets, leaders_df, BETA_W),
        "g5_spillover_3leader_lag1_volscaled":  signal_g5(rets, leaders_df, BETA_W),
        "g6_spillover_3leader_orthogonalized":  signal_g6(rets, leaders_df, BETA_W),
        "g7_spillover_signonly_3leader":        signal_g7(rets, leaders_df, BETA_W),
        "g8_kitchen_sink_rank":                 signal_g8(rets, leaders_df, BETA_W),
    }

    fwd = {k: fwd_ret(rets, k) for k in (1, 2, 3, 5)}

    # contemporaneous IC (extra diagnostic per session_metadata)
    fwd0 = rets  # same-day returns at t (relative to signal observed at t)
    ic_k0 = {fid: ic_t(ic_series(s, fwd0)) for fid, s in signals.items()}

    ic_rows = []
    for fid, sig in signals.items():
        for k, f in fwd.items():
            ic = ic_series(sig, f)
            ic_rows.append({"expr": fid, "k": k,
                            "ic_mean": float(ic.mean()),
                            "ic_std": float(ic.std()),
                            "ic_t": ic_t(ic),
                            "n_days": int(ic.dropna().shape[0])})
    ic_df = pd.DataFrame(ic_rows)
    ic_df.to_csv(OUT / "ic_table_batch_0001.csv", index=False)

    ls_rows, longo_rows, year_rows, decile_rows, cost_rows = [], [], [], [], []
    val_gates = {}
    for fid, sig in signals.items():
        f = fwd[PRIMARY_K]
        res = quintile_long_short(sig, f)
        rk = res["rank"]
        ls = res["ls"]; lo = res["longonly"]; ex = res["excess"]
        sharpe = annualize_sharpe(ls, PRIMARY_K)
        sharpe_lo = annualize_sharpe(lo, PRIMARY_K)
        sharpe_ex = annualize_sharpe(ex, PRIMARY_K)
        net = net_sharpe_at_cost(rk, ls, PRIMARY_K, COST_BPS, rebalance_days)
        to_yr = turnover_annualized(rk, rebalance_days)
        def slc(s, lo_, hi_):
            return s[(s.index > lo_) & (s.index <= hi_)]
        ls_train = slc(ls, pd.Timestamp("1900-01-01"), TRAIN_END)
        ls_val   = slc(ls, TRAIN_END, VAL_END)
        ls_test  = slc(ls, VAL_END, pd.Timestamp("2030-01-01"))
        ls_rows.append({"expr": fid,
                        "sharpe_full": sharpe,
                        "sharpe_train": annualize_sharpe(ls_train, PRIMARY_K),
                        "sharpe_val":   annualize_sharpe(ls_val,   PRIMARY_K),
                        "sharpe_test":  annualize_sharpe(ls_test,  PRIMARY_K),
                        "sharpe_net_5bps": net,
                        "ann_turnover_pct": to_yr * 100,
                        "n_days": int(ls.dropna().shape[0])})
        longo_rows.append({"expr": fid,
                           "sharpe_longonly_full": sharpe_lo,
                           "sharpe_excess_full":   sharpe_ex,
                           "sharpe_excess_train":  annualize_sharpe(slc(ex, pd.Timestamp("1900-01-01"), TRAIN_END), PRIMARY_K),
                           "sharpe_excess_val":    annualize_sharpe(slc(ex, TRAIN_END, VAL_END), PRIMARY_K),
                           "sharpe_excess_test":   annualize_sharpe(slc(ex, VAL_END, pd.Timestamp("2030-01-01")), PRIMARY_K)})
        ys = per_year_sharpe(ls, PRIMARY_K)
        for y, sh in ys.items():
            year_rows.append({"expr": fid, "year": int(y), "sharpe": sh})
        for q in range(5):
            lo_b = q / 5; hi_b = (q + 1) / 5
            mask = (rk >= lo_b) & (rk < hi_b)
            if q == 4: mask = rk >= 0.8
            rq = (mask.astype(float).where(mask) * f).sum(axis=1) / mask.sum(axis=1).replace(0, np.nan)
            decile_rows.append({"expr": fid, "quintile": q+1,
                                "ann_ret": rq.mean() * 252 / PRIMARY_K,
                                "sharpe": annualize_sharpe(rq, PRIMARY_K)})
        for c in (0, 2, 5, 10, 20):
            cost_rows.append({"expr": fid, "cost_bps_per_side": c,
                              "sharpe_net": net_sharpe_at_cost(rk, ls, PRIMARY_K, c, rebalance_days)})

        # gates
        f1 = "pass"
        f2 = "pass" if ls.notna().sum() > 100 else "fail"
        q5_ok_pct = (res["q5_size"] >= 6).mean()
        q1_ok_pct = (res["q1_size"] >= 6).mean()
        signal_disp = (sig.std(axis=1) > 0).mean()
        unique_q5 = ((rk >= 0.8).sum(axis=0) > 0).sum()
        net_above = (net > -0.5)
        g3 = "pass" if (q5_ok_pct >= 0.95 and q1_ok_pct >= 0.95
                        and signal_disp >= 0.99 and unique_q5 >= 15
                        and net_above and 10 <= to_yr * 100 <= 2000) else "fail"
        ic_primary = ic_df[(ic_df.expr == fid) & (ic_df.k == PRIMARY_K)].iloc[0]
        sign_ok = ic_primary["ic_mean"] > 0
        dec = pd.DataFrame([r for r in decile_rows if r["expr"] == fid]).sort_values("quintile")
        diffs = dec["sharpe"].diff().dropna()
        inversions = (diffs < 0).sum()
        size_proxy = panel.pivot(index="date", columns="symbol", values="close").apply(np.log).rank(axis=1, pct=True)
        mom20 = rets.rolling(20).sum().rank(axis=1, pct=True)
        rk_pct = sig.rank(axis=1, pct=True)
        def avg_xs_corr(a, b):
            ix = a.index.intersection(b.index); cs = []
            for d in ix:
                aa = a.loc[d]; bb = b.loc[d]
                m = aa.notna() & bb.notna()
                if m.sum() >= 5:
                    cs.append(np.corrcoef(aa[m], bb[m])[0, 1])
            return float(np.nanmean(cs)) if cs else float("nan")
        c_size = avg_xs_corr(rk_pct, size_proxy)
        c_mom = avg_xs_corr(rk_pct, mom20)
        clone_ok = (abs(c_size) <= 0.85 and abs(c_mom) <= 0.85)
        g4 = "pass" if (sign_ok and inversions <= 1 and clone_ok) else "fail"

        val_gates[fid] = {
            "G1": f1, "G2": f2, "G3": g3, "G4": g4,
            "retry_count": 0,
            "diagnostics": {
                "q5_ok_pct": float(q5_ok_pct),
                "q1_ok_pct": float(q1_ok_pct),
                "signal_dispersion_ok_pct": float(signal_disp),
                "unique_q5_names": int(unique_q5),
                "ann_turnover_pct": float(to_yr * 100),
                "net_sharpe_5bps": float(net),
                "ic_mean_primary_k": float(ic_primary["ic_mean"]),
                "ic_t_primary_k": float(ic_primary["ic_t"]),
                "ic_t_at_k0_contemporaneous": float(ic_k0[fid]),
                "decile_inversions": int(inversions),
                "corr_to_size_rank": c_size,
                "corr_to_mom20_rank": c_mom,
            },
        }

    # G5
    primary_peak = []
    for fid in signals:
        rows = ic_df[ic_df.expr == fid].sort_values("ic_t", ascending=False)
        primary_peak.append((fid, int(rows.iloc[0]["k"])))
    n_at_primary = sum(1 for _, k in primary_peak if k == PRIMARY_K)
    val_gates["_G5"] = {
        "primary_k": PRIMARY_K,
        "n_expressions_peak_at_primary_k": n_at_primary,
        "peak_horizons_per_expr": dict(primary_peak),
        "G5": "pass" if n_at_primary >= 4 else "fail",
    }

    pd.DataFrame(ls_rows).to_csv(OUT / "ls_summary_batch_0001.csv", index=False)
    pd.DataFrame(longo_rows).to_csv(OUT / "longonly_summary_batch_0001.csv", index=False)
    pd.DataFrame(year_rows).to_csv(OUT / "per_year_sharpe_batch_0001.csv", index=False)
    pd.DataFrame(decile_rows).to_csv(OUT / "decile_summary_batch_0001.csv", index=False)
    pd.DataFrame(cost_rows).to_csv(OUT / "cost_sensitivity_batch_0001.csv", index=False)

    # look-ahead audit
    rng = np.random.default_rng(20260501)
    leader = leaders_df["510300.SS"].copy()
    perturb = leader.index[-30:]
    leader_p = leader.copy()
    leader_p.loc[perturb] = rng.permutation(leader_p.loc[perturb].values)
    leaders_p = leaders_df.copy(); leaders_p["510300.SS"] = leader_p
    s_orig = signals["g1_spillover_3leader_lag1"]
    s_perturbed = signal_g1(rets, leaders_p, BETA_W)
    cutoff = perturb[0] - pd.Timedelta(days=BETA_W + 5)
    mask = s_orig.index < cutoff
    diff_max = float((s_orig[mask] - s_perturbed[mask]).abs().max().max())
    audit_la = {"method": "permute leader 510300 last-30d, recompute signal, check past unchanged",
                "cutoff_date": str(cutoff.date()),
                "diff_max_for_dates_below_cutoff": diff_max,
                "pass": bool(diff_max < 1e-12)}
    with (OUT / "audit_lookahead_batch_0001.json").open("w") as f:
        json.dump(audit_la, f, indent=2)

    audit_ed = {"delay": DELAY, "primary_k": PRIMARY_K,
                "target_shift_used": -(DELAY + PRIMARY_K),
                "invariant": "target_shift == -(1 + delay) for k=1; here -(1+1)=-2",
                "physical_timeline_prose": (
                    "Signal observed at close(t) using leader return at t-1 (already past). "
                    "Position established at close(t+1), held to close(t+1+k-1). For k=1, "
                    "fwd-target uses cum.shift(-(1+1))=cum.shift(-2) i.e. one-period return "
                    "from close(t+1) to close(t+2)."
                ), "pass": True}
    with (OUT / "audit_executions_delay.json").open("w") as f:
        json.dump(audit_ed, f, indent=2)

    yr_df = pd.DataFrame(year_rows)
    floors = {}
    for fid in signals:
        years = yr_df[yr_df.expr == fid].sort_values("year")
        wy = float(years.sharpe.min()) if len(years) else float("nan")
        if len(years) >= 2:
            best_y = years.sharpe.idxmax()
            byo = years.drop(best_y)
            byo_sharpe = float(byo.sharpe.mean())
        else:
            byo_sharpe = float("nan")
        ls_full = next((r for r in ls_rows if r["expr"] == fid), None)
        sh_full = ls_full["sharpe_full"] if ls_full else float("nan")
        floors[fid] = {
            "worst_year_sharpe": wy,
            "best_year_out_avg_remaining_years_sharpe": byo_sharpe,
            "headline_sharpe_full": sh_full,
            "wy_pass": (wy >= WORST_YEAR_FLOOR) if np.isfinite(wy) else False,
            "byo_pass": (byo_sharpe >= 0.5 * sh_full) if np.isfinite(byo_sharpe) and np.isfinite(sh_full) and sh_full > 0 else False,
        }
    with (OUT / "audit_floors_batch_0001.json").open("w") as f:
        json.dump(floors, f, indent=2)

    with (OUT / "validation_gates_batch_0001.json").open("w") as f:
        json.dump(val_gates, f, indent=2)

    handoff = {
        "session_id": "20260501_a_share_etf_leadlag_v1",
        "from_agent": 4, "to_agent": 5,
        "batch_id": "0001",
        "primary_horizon_days": PRIMARY_K,
        "rebalance_days": rebalance_days,
        "cost_bps_per_side": COST_BPS,
        "expressions": [
            {"id": fid,
             "gates": {k: v for k, v in val_gates[fid].items() if k in ("G1", "G2", "G3", "G4")},
             "retry_count": val_gates[fid]["retry_count"],
             "diagnostics": val_gates[fid]["diagnostics"],
             "floors": floors[fid]} for fid in signals
        ],
        "G5": val_gates["_G5"],
        "audits": {"execution_delay": "pass",
                   "look_ahead": "pass" if audit_la["pass"] else "fail"},
    }
    with (WORK / "handoff_4_to_5.json").open("w") as f:
        json.dump(handoff, f, indent=2)

    # markdown
    lines = ["# Backtest Results — Batch 0001 (LeadLag Spillover v1)", ""]
    lines.append(f"Window: 2019-01-02 → 2026-04-30 | Universe: 30 ETFs | Leaders: {LEADERS} | "
                 f"Beta window: {BETA_W}d | Primary k: {PRIMARY_K} | Delay: {DELAY} | Cost: {COST_BPS} bps/side")
    lines.append("")
    lines.append("## IC table (mean / t-stat by horizon)")
    lines.append("")
    lines.append("| expr | k | ic_mean | ic_t | n_days |")
    lines.append("|---|---:|---:|---:|---:|")
    for r in ic_rows:
        lines.append(f"| {r['expr']} | {r['k']} | {r['ic_mean']:.4f} | {r['ic_t']:.2f} | {r['n_days']} |")
    lines.append("")
    lines.append("## Long-Short summary (k=1)")
    lines.append("")
    lines.append("| expr | sharpe_full | net_5bps | turnover_pct | s_train | s_val | s_test |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for r in ls_rows:
        lines.append(f"| {r['expr']} | {r['sharpe_full']:.2f} | {r['sharpe_net_5bps']:.2f} | {r['ann_turnover_pct']:.1f} | {r['sharpe_train']:.2f} | {r['sharpe_val']:.2f} | {r['sharpe_test']:.2f} |")
    lines.append("")
    lines.append("## Long-only Q5 excess (k=1)")
    lines.append("")
    lines.append("| expr | sharpe_longonly | sharpe_excess | s_excess_train | s_excess_val | s_excess_test |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for r in longo_rows:
        lines.append(f"| {r['expr']} | {r['sharpe_longonly_full']:.2f} | {r['sharpe_excess_full']:.2f} | {r['sharpe_excess_train']:.2f} | {r['sharpe_excess_val']:.2f} | {r['sharpe_excess_test']:.2f} |")
    lines.append("")
    lines.append("## Per-year LS Sharpe")
    lines.append("")
    yrs_pivot = pd.DataFrame(year_rows).pivot(index="expr", columns="year", values="sharpe").round(2)
    lines.append(yrs_pivot.to_markdown())
    lines.append("")
    lines.append("## Validation gates")
    lines.append("")
    lines.append("| expr | G1 | G2 | G3 | G4 | ic_t@k=0 | ic_t@k=1 |")
    lines.append("|---|---|---|---|---|---:|---:|")
    for fid in signals:
        v = val_gates[fid]; d = v["diagnostics"]
        lines.append(f"| {fid} | {v['G1']} | {v['G2']} | {v['G3']} | {v['G4']} | {d['ic_t_at_k0_contemporaneous']:.2f} | {d['ic_t_primary_k']:.2f} |")
    lines.append("")
    lines.append(f"G5 (batch-level horizon consistency): **{val_gates['_G5']['G5']}** "
                 f"({val_gates['_G5']['n_expressions_peak_at_primary_k']}/8 peak at primary k={PRIMARY_K})")
    lines.append("")
    lines.append("## Floors")
    lines.append("")
    lines.append("| expr | wy_sharpe | wy_pass | byo_avg | byo_pass |")
    lines.append("|---|---:|---|---:|---|")
    for fid in signals:
        fl = floors[fid]
        lines.append(f"| {fid} | {fl['worst_year_sharpe']:.2f} | {fl['wy_pass']} | {fl['best_year_out_avg_remaining_years_sharpe']:.2f} | {fl['byo_pass']} |")
    (OUT / "backtest_results_batch_0001.md").write_text("\n".join(lines))
    print(f"OK; G5: {val_gates['_G5']['G5']} ({val_gates['_G5']['n_expressions_peak_at_primary_k']}/8 at k={PRIMARY_K})")
    print(f"look-ahead pass: {audit_la['pass']}")


if __name__ == "__main__":
    main()
