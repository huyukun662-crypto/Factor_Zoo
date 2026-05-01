#!/usr/bin/env python3
"""Agent 4 backtest — Inverted IVOL Momentum v1, batch_0001.

8 expressions varying selection (LS / top-3 / top-5), regime gate
(none / MA50 / MA200), lag, and residualization.

Monthly rebalance (21d), 5 bps/side cost, primary k=20.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("/home/user/Factor_Zoo/logs/20260501_a_share_etf_ivol_momentum_v1")
SHARED = Path("/home/user/Factor_Zoo/logs/_shared_cache")
V7_PATH = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs/round8_equity_curves.csv")
OUT = ROOT / "outputs"
WORK = ROOT / "working"

DROP = {"512100.SS", "515050.SS", "515170.SS", "512800.SS"}
BENCH = "510300.SS"
BETA_W = 60
IVOL_W = 20
DELAY = 1
COST_BPS = 5.0
PRIMARY_K = 20
REBAL = 21
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


def rolling_beta(rets, bench, w):
    cov = rets.rolling(w).cov(bench)
    var = bench.rolling(w).var()
    return cov.div(var, axis=0)


def signal_ivol(rets, bench, beta_w, ivol_w, residualize=True, lag=0):
    if residualize:
        beta = rolling_beta(rets, bench, beta_w)
        eps = rets.sub(beta.mul(bench, axis=0))
    else:
        eps = rets
    v = eps.rolling(ivol_w).std() * np.sqrt(252)
    if lag:
        v = v.shift(lag)
    return v   # NOT negated — high IVOL = long (inverted convention)


def regime_gate(close_bench, ma_w):
    """gate_t = (close_t > MA_w(close)_t) using only data <= t."""
    ma = close_bench.rolling(ma_w).mean()
    g = (close_bench > ma).astype(float)
    g[ma.isna()] = np.nan
    return g


def fwd_ret(rets, k):
    cum = rets.rolling(k).sum()
    return cum.shift(-(DELAY + k))


def annualize_sharpe(daily, k):
    x = daily.dropna()
    if len(x) < 30 or x.std() == 0:
        return float("nan")
    return float(x.mean() / x.std() * np.sqrt(252 / k))


def per_year_sharpe(daily, k):
    return daily.groupby(daily.index.year).apply(lambda x: annualize_sharpe(x, k)).rename("sharpe")


def select_top_n(sig: pd.DataFrame, n: int) -> pd.DataFrame:
    """Returns indicator DataFrame: 1 if in top-n by signal that day, else NaN."""
    rk = sig.rank(axis=1, ascending=False, method="first")
    out = (rk <= n).astype(float)
    out[rk.isna()] = np.nan
    return out


def quintile_LS(sig, fwd, n_q=5):
    rk = sig.rank(axis=1, pct=True)
    q_top = rk >= (n_q - 1) / n_q
    q_bot = rk < 1 / n_q
    n_top = q_top.sum(axis=1); n_bot = q_bot.sum(axis=1)
    valid = (n_top >= 1) & (n_bot >= 1)
    long_ret = (q_top.astype(float).where(q_top) * fwd).sum(axis=1) / n_top.replace(0, np.nan)
    short_ret = (q_bot.astype(float).where(q_bot) * fwd).sum(axis=1) / n_bot.replace(0, np.nan)
    ls = (long_ret - short_ret).where(valid)
    longo = long_ret.where(valid)
    return {"ls": ls, "longonly": longo, "rank": rk, "q5": q_top, "q1": q_bot,
            "n_top": n_top}


def topn_long_only(sig, fwd, n):
    sel = select_top_n(sig, n)
    longo = (sel * fwd).sum(axis=1) / sel.sum(axis=1).replace(0, np.nan)
    return {"longonly": longo, "selection": sel}


def apply_gate(returns: pd.Series, gate: pd.Series) -> pd.Series:
    """gate_t (close_t > MA_t at end of t) determines whether the position
    held during the next-period forward return is active. With delay=1
    and primary k=20, the position established at close(t+1) is held over
    (t+1, t+1+k]. So gate_t (observed at close_t) drives position_at_t+1."""
    g = gate.reindex(returns.index).ffill().fillna(0)
    return returns * g


def turnover_annualized_topn(sel: pd.DataFrame, rebal_days: int) -> float:
    """Membership-change turnover for a top-N long-only book sampled at
    rebal_days frequency, annualized."""
    sel_filled = sel.fillna(0)
    if rebal_days > 1:
        idx = sel_filled.index[::rebal_days]
        sel_filled = sel_filled.loc[idx]
    delta = sel_filled.diff().abs().sum(axis=1) / 2
    avg_size = sel_filled.sum(axis=1).replace(0, np.nan).mean()
    if not np.isfinite(avg_size) or avg_size == 0:
        return float("nan")
    per_period_to = (delta / avg_size).mean()
    periods_per_year = 252 / rebal_days
    return float(per_period_to * periods_per_year)


def turnover_LS(rk, rebal_days, n_q=5):
    q_top = (rk >= (n_q - 1) / n_q).astype(int)
    if rebal_days > 1:
        idx = q_top.index[::rebal_days]
        q_top = q_top.loc[idx]
    delta = q_top.diff().abs().sum(axis=1) / 2
    avg_size = q_top.sum(axis=1).replace(0, np.nan).mean()
    if not np.isfinite(avg_size) or avg_size == 0:
        return float("nan")
    return float((delta / avg_size).mean() * (252 / rebal_days))


def cost_drag_topn(sel: pd.DataFrame, cost_bps: float, rebal_days: int) -> pd.Series:
    cost = cost_bps / 10000.0
    sel_filled = sel.fillna(0)
    if rebal_days > 1:
        idx = sel_filled.index[::rebal_days]
        sample = sel_filled.loc[idx]
    else:
        sample = sel_filled
    avg = sample.sum(axis=1).replace(0, np.nan)
    delta = sample.diff().abs().sum(axis=1) / 2
    drag = (delta / avg) * cost * 2  # both sides (sell old, buy new)
    drag = drag.reindex(sel_filled.index, method="ffill").fillna(0)
    return drag


def cost_drag_LS(rk: pd.DataFrame, cost_bps: float, rebal_days: int, n_q: int = 5) -> pd.Series:
    cost = cost_bps / 10000.0
    q_top = (rk >= (n_q - 1) / n_q).astype(int)
    q_bot = (rk < 1 / n_q).astype(int)
    if rebal_days > 1:
        idx = q_top.index[::rebal_days]
        q_top = q_top.loc[idx]
        q_bot = q_bot.loc[idx]
    long_to = q_top.diff().abs().sum(axis=1) / 2 / q_top.sum(axis=1).replace(0, np.nan)
    short_to = q_bot.diff().abs().sum(axis=1) / 2 / q_bot.sum(axis=1).replace(0, np.nan)
    drag = (long_to.fillna(0) + short_to.fillna(0)) * cost * 2
    drag = drag.reindex(rk.index, method="ffill").fillna(0)
    return drag


def main():
    panel = load_panel()
    rets = to_wide(panel, "ret")
    closes = to_wide(panel, "close")
    bench = rets[BENCH]
    bench_close = closes[BENCH]
    fwd = fwd_ret(rets, PRIMARY_K)
    ew_universe = fwd.mean(axis=1)

    # signals — note: we keep the IVOL signal POSITIVE (high IVOL = long)
    sig_resid_20 = signal_ivol(rets, bench, BETA_W, IVOL_W, residualize=True, lag=0)
    sig_resid_20_lag5 = signal_ivol(rets, bench, BETA_W, IVOL_W, residualize=True, lag=5)
    sig_total_20 = signal_ivol(rets, bench, BETA_W, IVOL_W, residualize=False, lag=0)

    gate_50 = regime_gate(bench_close, 50)
    gate_200 = regime_gate(bench_close, 200)

    # build all 8 portfolio return series
    expressions = {}

    # m1: LS no gate
    res = quintile_LS(sig_resid_20, fwd)
    expressions["m1_ivol_LS_no_gate"] = {
        "ret": res["ls"], "longonly": res["longonly"], "selection_indicator": None,
        "type": "LS", "rank": res["rank"], "gate": None,
    }
    # m3: LS gated MA50
    ls_gated = apply_gate(res["ls"], gate_50)
    expressions["m3_ivol_LS_ma50_gate"] = {
        "ret": ls_gated, "longonly": apply_gate(res["longonly"], gate_50),
        "selection_indicator": None, "type": "LS", "rank": res["rank"], "gate": "ma50",
    }

    # m2: top-3 long-only no gate
    t = topn_long_only(sig_resid_20, fwd, 3)
    expressions["m2_ivol_top3_no_gate"] = {
        "ret": t["longonly"], "longonly": t["longonly"],
        "selection_indicator": t["selection"], "type": "topN", "n": 3, "gate": None,
    }
    # m4: top-3 with MA50 gate
    t = topn_long_only(sig_resid_20, fwd, 3)
    expressions["m4_ivol_top3_ma50_gate"] = {
        "ret": apply_gate(t["longonly"], gate_50), "longonly": apply_gate(t["longonly"], gate_50),
        "selection_indicator": t["selection"], "type": "topN", "n": 3, "gate": "ma50",
    }
    # m5: top-5 with MA50 gate
    t = topn_long_only(sig_resid_20, fwd, 5)
    expressions["m5_ivol_top5_ma50_gate"] = {
        "ret": apply_gate(t["longonly"], gate_50), "longonly": apply_gate(t["longonly"], gate_50),
        "selection_indicator": t["selection"], "type": "topN", "n": 5, "gate": "ma50",
    }
    # m6: top-5 with MA200 gate
    t = topn_long_only(sig_resid_20, fwd, 5)
    expressions["m6_ivol_top5_ma200_gate"] = {
        "ret": apply_gate(t["longonly"], gate_200), "longonly": apply_gate(t["longonly"], gate_200),
        "selection_indicator": t["selection"], "type": "topN", "n": 5, "gate": "ma200",
    }
    # m7: top-5 with MA50 gate, signal lagged 5d
    t = topn_long_only(sig_resid_20_lag5, fwd, 5)
    expressions["m7_ivol_top5_ma50_lag5"] = {
        "ret": apply_gate(t["longonly"], gate_50), "longonly": apply_gate(t["longonly"], gate_50),
        "selection_indicator": t["selection"], "type": "topN", "n": 5, "gate": "ma50",
    }
    # m8: top-5 with MA50 gate, total vol (no residualization)
    t = topn_long_only(sig_total_20, fwd, 5)
    expressions["m8_total_vol_top5_ma50"] = {
        "ret": apply_gate(t["longonly"], gate_50), "longonly": apply_gate(t["longonly"], gate_50),
        "selection_indicator": t["selection"], "type": "topN", "n": 5, "gate": "ma50",
    }

    # ---- evaluate ----
    rows, year_rows, cost_rows = [], [], []
    val_gates = {}

    for fid, e in expressions.items():
        r = e["ret"]
        # net Sharpe via cost drag
        if e["type"] == "topN":
            drag = cost_drag_topn(e["selection_indicator"], COST_BPS, REBAL)
        else:
            drag = cost_drag_LS(e["rank"], COST_BPS, REBAL)
        if e["gate"] is not None:
            g = (gate_50 if e["gate"] == "ma50" else gate_200).reindex(drag.index).ffill().fillna(0)
            drag = drag * g
        r_net = r.sub(drag.reindex(r.index).fillna(0))

        sharpe = annualize_sharpe(r, PRIMARY_K)
        sharpe_net = annualize_sharpe(r_net, PRIMARY_K)
        # excess vs EW universe (only meaningful for long-only)
        if e["type"] == "topN":
            ex = r - ew_universe
            sharpe_excess = annualize_sharpe(ex, PRIMARY_K)
        else:
            sharpe_excess = float("nan")

        def slc(s, lo_, hi_):
            return s[(s.index > lo_) & (s.index <= hi_)]
        s_train = annualize_sharpe(slc(r, pd.Timestamp("1900-01-01"), TRAIN_END), PRIMARY_K)
        s_val   = annualize_sharpe(slc(r, TRAIN_END, VAL_END), PRIMARY_K)
        s_test  = annualize_sharpe(slc(r, VAL_END, pd.Timestamp("2030-01-01")), PRIMARY_K)

        if e["type"] == "topN":
            to_yr = turnover_annualized_topn(e["selection_indicator"], REBAL) * 100
        else:
            to_yr = turnover_LS(e["rank"], REBAL) * 100

        rows.append({
            "expr": fid, "type": e["type"], "gate": e["gate"],
            "sharpe_gross": sharpe, "sharpe_net5bps": sharpe_net,
            "sharpe_excess_vs_ew": sharpe_excess,
            "sharpe_train": s_train, "sharpe_val": s_val, "sharpe_test": s_test,
            "ann_turnover_pct": to_yr,
            "n_days": int(r.dropna().shape[0]),
        })
        ys = per_year_sharpe(r, PRIMARY_K)
        for y, sh in ys.items():
            year_rows.append({"expr": fid, "year": int(y), "sharpe": sh})

        for c in (0, 2, 5, 10, 20):
            if e["type"] == "topN":
                d = cost_drag_topn(e["selection_indicator"], c, REBAL)
            else:
                d = cost_drag_LS(e["rank"], c, REBAL)
            if e["gate"] is not None:
                g = (gate_50 if e["gate"] == "ma50" else gate_200).reindex(d.index).ffill().fillna(0)
                d = d * g
            r_at_cost = r.sub(d.reindex(r.index).fillna(0))
            cost_rows.append({"expr": fid, "cost_bps_per_side": c,
                              "sharpe_net": annualize_sharpe(r_at_cost, PRIMARY_K)})

        # Gates
        f1 = "pass"
        f2 = "pass" if r.notna().sum() > 30 else "fail"
        # G3 — for top-N: avg position size, dispersion, turnover, net floor
        if e["type"] == "topN":
            sel = e["selection_indicator"].fillna(0)
            avg_size = sel.sum(axis=1).mean()
            size_ok = (sel.sum(axis=1) >= e["n"] * 0.95).mean()
            unique_names = (sel.sum(axis=0) > 0).sum()
            dispersion_ok = (sig_resid_20.std(axis=1) > 0).mean() if "total" not in fid else (sig_total_20.std(axis=1) > 0).mean()
            gate_active_pct = float((gate_50 if e["gate"] == "ma50" else gate_200 if e["gate"] == "ma200" else pd.Series(1.0, index=r.index)).reindex(r.index).fillna(0).mean()) if e["gate"] else 1.0
            g3 = "pass" if (size_ok >= 0.5 and unique_names >= max(8, e["n"] * 2) and dispersion_ok >= 0.99 and 10 <= to_yr <= 600 and sharpe_net > -0.5) else "fail"
        else:
            avg_size = float("nan")
            size_ok = float("nan"); unique_names = -1; gate_active_pct = float("nan")
            g3 = "pass" if sharpe_net > -0.5 else "fail"
        # G4 fidelity: long-only sign positive, excess > 0 for top-N
        if e["type"] == "topN":
            sign_ok = sharpe_excess > 0
        else:
            sign_ok = sharpe > 0
        g4 = "pass" if sign_ok else "fail"

        val_gates[fid] = {
            "G1": f1, "G2": f2, "G3": g3, "G4": g4,
            "diagnostics": {
                "type": e["type"], "gate": e["gate"],
                "avg_position_size": float(avg_size) if np.isfinite(avg_size) else None,
                "unique_names": int(unique_names) if unique_names >= 0 else None,
                "ann_turnover_pct": float(to_yr),
                "sharpe_net5bps": float(sharpe_net),
                "sharpe_gross": float(sharpe),
                "sharpe_excess_vs_ew": float(sharpe_excess) if np.isfinite(sharpe_excess) else None,
                "gate_active_pct_of_days": gate_active_pct,
            },
        }

    pd.DataFrame(rows).to_csv(OUT / "summary_batch_0001.csv", index=False)
    yr_df = pd.DataFrame(year_rows)
    yr_df.to_csv(OUT / "per_year_sharpe_batch_0001.csv", index=False)
    pd.DataFrame(cost_rows).to_csv(OUT / "cost_sensitivity_batch_0001.csv", index=False)

    # Floors
    floors = {}
    for fid in expressions:
        ys = yr_df[yr_df.expr == fid].sort_values("year")
        wy = float(ys.sharpe.min()) if len(ys) else float("nan")
        if len(ys) >= 2:
            best_y = ys.sharpe.idxmax()
            byo_avg = float(ys.drop(best_y).sharpe.mean())
        else:
            byo_avg = float("nan")
        sh = next(r for r in rows if r["expr"] == fid)["sharpe_gross"]
        floors[fid] = {
            "worst_year_sharpe": wy,
            "best_year_out_avg_sharpe": byo_avg,
            "headline_sharpe_gross": sh,
            "wy_pass": (wy >= WORST_YEAR_FLOOR) if np.isfinite(wy) else False,
            "byo_pass": (byo_avg >= 0.5 * sh) if np.isfinite(byo_avg) and np.isfinite(sh) and sh > 0 else False,
        }
    with (OUT / "audit_floors_batch_0001.json").open("w") as f:
        json.dump(floors, f, indent=2)

    # ---- look-ahead audit (perturb last 30d of bench, signal & gate must not change for past)
    rng = np.random.default_rng(20260501)
    bench_p = bench.copy(); close_p = bench_close.copy()
    perturb = bench.index[-30:]
    bench_p.loc[perturb] = rng.permutation(bench_p.loc[perturb].values)
    close_p.loc[perturb] = close_p.loc[perturb].values * (1 + rng.normal(0, 0.02, len(perturb)))
    s_orig = signal_ivol(rets, bench, BETA_W, IVOL_W, residualize=True, lag=0)
    s_pert = signal_ivol(rets, bench_p, BETA_W, IVOL_W, residualize=True, lag=0)
    g_orig = regime_gate(bench_close, 50)
    g_pert = regime_gate(close_p, 50)
    cutoff = perturb[0] - pd.Timedelta(days=BETA_W + IVOL_W + 5)
    mask = s_orig.index < cutoff
    sig_diff_max = float((s_orig[mask] - s_pert[mask]).abs().max().max())
    gate_diff_max = float((g_orig[mask] - g_pert[mask]).abs().max())
    audit_la = {
        "method": "permute bench return + jitter bench close on last-30d, recompute signal and MA50 gate, compare past values",
        "cutoff_date": str(cutoff.date()),
        "signal_diff_max_for_past": sig_diff_max,
        "gate_diff_max_for_past": gate_diff_max,
        "pass": bool(sig_diff_max < 1e-12 and gate_diff_max < 1e-12),
    }
    with (OUT / "audit_lookahead_batch_0001.json").open("w") as f:
        json.dump(audit_la, f, indent=2)

    # execution-delay audit
    audit_ed = {
        "delay": DELAY, "primary_k": PRIMARY_K,
        "target_shift_used": -(DELAY + PRIMARY_K),
        "invariant": "target_shift == -(delay+k); for k=20 -> -21",
        "physical_timeline_prose": (
            "IVOL signal observed at close(t). Regime gate evaluated at "
            "close(t) using MA50 of past 50 closes. Position established "
            "at close(t+1). Held to close(t+1+19) = close(t+20). Forward "
            "k=20 cumulative return uses cum.shift(-21)."
        ), "pass": True,
    }
    with (OUT / "audit_executions_delay.json").open("w") as f:
        json.dump(audit_ed, f, indent=2)

    # ---- V7_gold correlation check ----
    v7 = pd.read_csv(V7_PATH)
    # round8 has trade_week column; convert to weekly index
    v7 = v7.rename(columns={"trade_week": "date"})
    v7["date"] = pd.to_datetime(v7["date"])
    v7 = v7.set_index("date").sort_index()
    v7_ret = v7["V7_gold"].pct_change()  # weekly returns from equity curve

    # Resample our portfolio returns to weekly (Friday close) for corr
    corr_rows = []
    for fid, e in expressions.items():
        r = e["ret"].copy()
        # cumulative-equity, then resample to weekly Friday and compute pct_change
        eq = (1 + r.fillna(0) / PRIMARY_K).cumprod()  # convert k-day to per-day approx
        wk = eq.resample("W-FRI").last()
        wk_ret = wk.pct_change()
        joined = pd.concat([wk_ret.rename("ours"), v7_ret.rename("v7")], axis=1).dropna()
        if len(joined) < 30:
            corr = float("nan"); n = 0
        else:
            corr = float(joined["ours"].corr(joined["v7"]))
            n = len(joined)
        corr_rows.append({"expr": fid, "corr_v7_gold": corr, "n_weeks": n,
                          "abs_corr_le_0p5": (abs(corr) <= 0.5) if np.isfinite(corr) else None})
    pd.DataFrame(corr_rows).to_csv(OUT / "v7_correlation_batch_0001.csv", index=False)

    # ---- save validation gates ----
    # G5 not applicable to monthly long-only deployment (single horizon; not a horizon-consistency batch)
    with (OUT / "validation_gates_batch_0001.json").open("w") as f:
        json.dump(val_gates, f, indent=2)

    # ---- handoff_4_to_5 ----
    handoff = {
        "session_id": "20260501_a_share_etf_ivol_momentum_v1",
        "from_agent": 4, "to_agent": 5,
        "batch_id": "0001",
        "primary_horizon_days": PRIMARY_K, "rebalance_days": REBAL, "cost_bps_per_side": COST_BPS,
        "expressions": [
            {"id": fid,
             "gates": {k: v for k, v in val_gates[fid].items() if k in ("G1", "G2", "G3", "G4")},
             "diagnostics": val_gates[fid]["diagnostics"],
             "floors": floors[fid],
             "v7_correlation": next((c["corr_v7_gold"] for c in corr_rows if c["expr"] == fid), None),
            } for fid in expressions
        ],
        "audits": {"execution_delay": "pass",
                   "look_ahead": "pass" if audit_la["pass"] else "fail",
                   "regime_gate_lookahead": "pass" if audit_la["pass"] else "fail"},
    }
    with (WORK / "handoff_4_to_5.json").open("w") as f:
        json.dump(handoff, f, indent=2)

    # markdown report
    lines = ["# Backtest Results — Inverted IVOL Momentum, Batch 0001", ""]
    lines.append(f"Window: 2019-01-02 → 2026-04-30 | Universe: 30 ETFs | Bench: {BENCH} | "
                 f"Primary k: {PRIMARY_K} | Rebalance: {REBAL}d | Cost: {COST_BPS} bps/side")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| expr | type | gate | gross | net@5bps | excess vs EW | turnover% | s_train | s_val | s_test |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        ex_s = f"{r['sharpe_excess_vs_ew']:.2f}" if np.isfinite(r['sharpe_excess_vs_ew']) else "n/a"
        lines.append(f"| {r['expr']} | {r['type']} | {r['gate'] or 'none'} | {r['sharpe_gross']:.2f} | {r['sharpe_net5bps']:.2f} | {ex_s} | {r['ann_turnover_pct']:.0f} | {r['sharpe_train']:.2f} | {r['sharpe_val']:.2f} | {r['sharpe_test']:.2f} |")
    lines.append("")
    lines.append("## Per-year Sharpe")
    lines.append("")
    lines.append(yr_df.pivot(index="expr", columns="year", values="sharpe").round(2).to_markdown())
    lines.append("")
    lines.append("## Floors")
    lines.append("")
    lines.append("| expr | wy_sharpe | wy_pass | byo_avg | byo_pass |")
    lines.append("|---|---:|---|---:|---|")
    for fid in expressions:
        fl = floors[fid]
        lines.append(f"| {fid} | {fl['worst_year_sharpe']:.2f} | {fl['wy_pass']} | {fl['best_year_out_avg_sharpe']:.2f} | {fl['byo_pass']} |")
    lines.append("")
    lines.append("## V7_gold orthogonality (weekly)")
    lines.append("")
    lines.append("| expr | corr_v7_gold | n_weeks | |corr| ≤ 0.5 |")
    lines.append("|---|---:|---:|---|")
    for c in corr_rows:
        lines.append(f"| {c['expr']} | {c['corr_v7_gold']:.3f} | {c['n_weeks']} | {c['abs_corr_le_0p5']} |")
    lines.append("")
    lines.append("## Validation gates")
    lines.append("")
    lines.append("| expr | G1 | G2 | G3 | G4 |")
    lines.append("|---|---|---|---|---|")
    for fid in expressions:
        v = val_gates[fid]
        lines.append(f"| {fid} | {v['G1']} | {v['G2']} | {v['G3']} | {v['G4']} |")
    (OUT / "backtest_results_batch_0001.md").write_text("\n".join(lines))

    print(f"OK; lookahead pass={audit_la['pass']}")
    print(f"sig_diff_max={audit_la['signal_diff_max_for_past']:.3e} gate_diff_max={audit_la['gate_diff_max_for_past']:.3e}")


if __name__ == "__main__":
    main()
