"""
Agent 4 Round 2 — 15m-horizon BTC reversal with 15-bar hold + cost sensitivity.

Adds the new gates from validation-gates.md:
  G3 net_sharpe gate: net Sharpe at declared cost > -0.5
  G5 batch horizon consistency: majority of G4-survivors peak at k=15m

Outputs:
  ic_table_batch_0002.csv
  ls_summary_batch_0002.csv              (net Sharpe at 5 bps/side)
  cost_sensitivity_batch_0002.csv        (net Sharpe at {2,5,8,10} bps)
  validation_gates_batch_0002.json       (G1-G4 per expression + G5 batch)
  backtest_results_batch_0002.md
  handoff_4_to_5_round2.json
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


SESSION_DIR = Path("/home/user/Factor_Zoo/logs/20260423_btc_minute_reversal_v1")
DATA_PATH   = SESSION_DIR / "inputs" / "btc_1m.parquet"
OUT_DIR     = SESSION_DIR / "outputs"
WORK_DIR    = SESSION_DIR / "working"

DELAY = 1
K_PRIMARY = 15
K_ALL = [5, 15, 30, 60]
COST_BPS_PER_SIDE_PRIMARY = 5.0
COST_CURVE_BPS = [2.0, 5.0, 8.0, 10.0]
HOLD_BARS = 15
NET_SHARPE_FLOOR = -0.5    # G3 new gate


def log(m: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)


def ts_z(s: pd.Series) -> pd.Series:
    sd = s.std(ddof=0)
    if not sd or np.isnan(sd):
        return s * 0.0
    return (s - s.mean()) / sd


def hour_demean(s: pd.Series, hour: pd.Series) -> pd.Series:
    return s - s.groupby(hour).transform("mean")


def build_panel(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("ts").reset_index(drop=True).copy()
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["r1"] = np.log(df["close"]).diff()
    for n in [15, 30, 45, 60]:
        df[f"r{n}"]   = np.log(df["close"]) - np.log(df["close"].shift(n))
        df[f"rv{n}"]  = df["r1"].rolling(n, min_periods=n).std(ddof=0)
    df["r30_ema15"] = df["r30"].ewm(span=15, adjust=False, min_periods=15).mean()
    df["hour"] = df["ts"].dt.hour
    for k in K_ALL:
        df[f"fwd_ret_{k}"] = np.log(df["close"]).shift(-(DELAY + k)) - np.log(df["close"]).shift(-DELAY)
    return df


def build_expressions(df: pd.DataFrame) -> dict:
    hour = df["hour"]
    out = {}
    out["r2_rev_15m"]          = -ts_z(df["r15"])
    out["r2_rev_30m"]          = -ts_z(df["r30"])
    out["r2_rev_45m"]          = -ts_z(df["r45"])
    out["r2_rev_60m"]          = -ts_z(df["r60"])

    vs15 = df["r15"] / df["rv15"].replace(0, np.nan)
    vs30 = df["r30"] / df["rv30"].replace(0, np.nan)
    out["r2_rev_15m_volscale"] = -ts_z(vs15)
    out["r2_rev_30m_volscale"] = -ts_z(vs30)

    out["r2_rev_30m_ema15"]    = -ts_z(df["r30_ema15"])

    vs30_hd = hour_demean(vs30, hour)
    out["r2_rev_30m_volscale_hd"] = -ts_z(vs30_hd)
    return out


def apply_hold(raw_pos: pd.Series, hold: int) -> pd.Series:
    """Keep a position for `hold` bars before re-evaluating.

    Rule: on bar t, if last position change was >= `hold` bars ago (or
    at t=0), we accept the new raw_pos; otherwise we keep the previous
    held position.
    """
    pos = np.zeros(len(raw_pos))
    last_change = -hold  # allow immediate first trade
    cur = 0.0
    rp = raw_pos.values
    for i in range(len(rp)):
        if i - last_change >= hold:
            new = 0.0 if np.isnan(rp[i]) else rp[i]
            if new != cur:
                last_change = i
                cur = new
        pos[i] = cur
    return pd.Series(pos, index=raw_pos.index)


def threshold_strategy_pnl(sig: pd.Series, df: pd.DataFrame,
                           hold: int, cost_bps_per_side: float,
                           low_q: float = 0.10, high_q: float = 0.90) -> dict:
    s = sig.copy()
    q_lo, q_hi = s.quantile(low_q), s.quantile(high_q)
    raw_pos = pd.Series(np.where(s >= q_hi, 1.0,
                        np.where(s <= q_lo, -1.0, 0.0)), index=s.index)
    pos = apply_hold(raw_pos, hold)
    pos_eff = pos.shift(1)
    r_next = np.log(df["close"]).shift(-1) - np.log(df["close"])
    gross = pos_eff * r_next
    turn  = pos_eff.diff().abs().fillna(0)
    cost  = turn * (cost_bps_per_side / 1e4)
    net   = gross - cost

    n_valid = int(net.notna().sum())
    if n_valid < 1000:
        return {"n_bars": n_valid, "note": "insufficient"}
    ann = np.sqrt(60 * 24 * 365)

    def _stats(pnl):
        mu = float(pnl.mean()); sd = float(pnl.std(ddof=0))
        sharpe = (mu / sd) * ann if sd else 0.0
        return {"mean_bp": mu * 1e4, "std_bp": sd * 1e4,
                "sharpe_ann": sharpe, "cum_logret": float(pnl.sum())}

    trade_count = int(turn.sum())
    return {
        "n_bars": n_valid,
        "hold_bars": hold,
        "cost_bps_per_side": cost_bps_per_side,
        "trade_count_abs_pos_changes": trade_count,
        "trades_per_hour": 60.0 * trade_count / n_valid,
        "long_frac":  float((pos_eff == 1).mean()),
        "short_frac": float((pos_eff == -1).mean()),
        "flat_frac":  float((pos_eff == 0).mean()),
        "gross": _stats(gross.dropna()),
        "net":   _stats(net.dropna()),
    }


def ic_table(sigs: dict, df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, s in sigs.items():
        for k in K_ALL:
            fwd = df[f"fwd_ret_{k}"]
            m = s.notna() & fwd.notna()
            n = int(m.sum())
            if n < 1000:
                rows.append({"expr": name, "k_min": k, "ic": np.nan, "ic_tstat": np.nan, "n": n})
                continue
            ic, _ = stats.pearsonr(s[m], fwd[m])
            tstat = ic * np.sqrt(n - 2) / np.sqrt(max(1e-12, 1 - ic * ic))
            rows.append({"expr": name, "k_min": k, "ic": ic, "ic_tstat": tstat, "n": n})
    return pd.DataFrame(rows)


def gate_g3(sig: pd.Series, df: pd.DataFrame, pnl_primary: dict) -> dict:
    n_total = len(sig)
    n_valid = int(sig.notna().sum())
    coverage = n_valid / n_total if n_total else 0.0
    std_ok = (sig.dropna().std(ddof=0) or 0) > 0

    trade_freq = pnl_primary.get("trades_per_hour", np.inf)
    net_sharpe = pnl_primary.get("net", {}).get("sharpe_ann", -np.inf)
    flat_frac  = pnl_primary.get("flat_frac", 1.0)

    checks = {
        "coverage":               (coverage >= 0.95, coverage, 0.95, "non-NaN fraction"),
        "std_nonzero":            (std_ok, bool(std_ok), True, "signal std > 0"),
        "trade_freq_per_hour_ok": (trade_freq <= 4.0, trade_freq, 4.0, "trades/hour ≤ 4 (tightened w/ hold)"),
        "net_sharpe_not_wipeout": (net_sharpe > NET_SHARPE_FLOOR, net_sharpe, NET_SHARPE_FLOOR, "G3 NEW: net Sharpe at 5 bps > -0.5"),
        "flat_frac_sane":         (flat_frac <= 0.9, flat_frac, 0.9, "not always flat"),
    }
    passed = all(v[0] for v in checks.values())
    return {
        "passed": passed,
        "checks": {k: {"pass": bool(v[0]), "observed": float(v[1]) if not isinstance(v[1], bool) else v[1],
                       "threshold": v[2], "desc": v[3]} for k, v in checks.items()},
    }


def gate_g4(sig: pd.Series, df: pd.DataFrame) -> dict:
    k = K_PRIMARY
    fwd = df[f"fwd_ret_{k}"]
    m = sig.notna() & fwd.notna()
    if m.sum() < 1000:
        return {"passed": False, "reason": "insufficient sample"}
    ic, _ = stats.pearsonr(sig[m], fwd[m])
    ic_sign_ok = ic > 0

    tmp = pd.DataFrame({"sig": sig[m], "fwd": fwd[m]})
    tmp["dec"] = pd.qcut(tmp["sig"], 10, labels=False, duplicates="drop")
    dec_means = tmp.groupby("dec")["fwd"].mean()
    d10_vs_d1 = float(dec_means.iloc[-1] - dec_means.iloc[0])
    direction_ok = d10_vs_d1 > 0

    # horizon decay: IC at primary k=15m should dominate IC at k=60m
    fwd60 = df["fwd_ret_60"]
    m60 = sig.notna() & fwd60.notna()
    ic60, _ = stats.pearsonr(sig[m60], fwd60[m60])
    horizon_ok = abs(ic) >= abs(ic60)

    checks = {
        "ic_sign":       (ic_sign_ok,   float(ic),            "IC sign positive"),
        "decile_dir":    (direction_ok, d10_vs_d1,            "D10 > D1"),
        "horizon_decay": (horizon_ok,   float(abs(ic) - abs(ic60)), "|IC_15m| >= |IC_60m|"),
    }
    passed = all(v[0] for v in checks.values())
    return {
        "passed": passed,
        "ic_primary": float(ic),
        "ic_60m": float(ic60),
        "checks": {k: {"pass": bool(v[0]), "observed": float(v[1]), "desc": v[2]} for k, v in checks.items()},
    }


def gate_g5_batch_horizon(sigs: dict, df: pd.DataFrame,
                          g4_results: dict, declared_k: int) -> dict:
    """
    G5: of expressions that passed G4, count how many have their peak
    |IC| at declared_k. Require >= 50% of G4-survivors.
    """
    survivors = [name for name, g in g4_results.items() if g.get("passed")]
    if not survivors:
        return {"passed": False, "reason": "no G4 survivors", "survivors": 0}

    peak_counts = {k: 0 for k in K_ALL}
    per_expr_peak = {}
    for name in survivors:
        sig = sigs[name]
        ic_by_k = {}
        for k in K_ALL:
            fwd = df[f"fwd_ret_{k}"]
            m = sig.notna() & fwd.notna()
            if m.sum() < 1000:
                continue
            ic, _ = stats.pearsonr(sig[m], fwd[m])
            ic_by_k[k] = abs(ic)
        if ic_by_k:
            peak_k = max(ic_by_k, key=ic_by_k.get)
            peak_counts[peak_k] += 1
            per_expr_peak[name] = {"peak_k": peak_k, "ic_by_k": ic_by_k}

    pct_at_declared = peak_counts[declared_k] / len(survivors)
    passed = pct_at_declared >= 0.5
    return {
        "passed": passed,
        "declared_k": declared_k,
        "survivors": len(survivors),
        "peak_counts": peak_counts,
        "fraction_peaking_at_declared_k": pct_at_declared,
        "per_expression_peak": per_expr_peak,
    }


def _walk(o):
    if isinstance(o, dict):  return {k: _walk(v) for k, v in o.items()}
    if isinstance(o, list):  return [_walk(v) for v in o]
    if isinstance(o, (np.bool_,)):    return bool(o)
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, (np.integer,)):  return int(o)
    return o


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA_PATH))
    ap.add_argument("--out",  default=str(OUT_DIR))
    args = ap.parse_args()

    log("load data + build panel")
    df = build_panel(pd.read_parquet(args.data))

    log("build expressions")
    sigs = build_expressions(df)

    log("compute per-expression strategy PnL (primary + cost curve)")
    primary_pnl = {}
    cost_curve = []
    for name, s in sigs.items():
        primary_pnl[name] = threshold_strategy_pnl(s, df, HOLD_BARS, COST_BPS_PER_SIDE_PRIMARY)
        for c in COST_CURVE_BPS:
            r = threshold_strategy_pnl(s, df, HOLD_BARS, c)
            cost_curve.append({
                "expr": name,
                "cost_bps_per_side": c,
                "trades_per_hour": r.get("trades_per_hour", np.nan),
                "gross_sharpe_ann": r.get("gross", {}).get("sharpe_ann", np.nan),
                "net_sharpe_ann": r.get("net", {}).get("sharpe_ann", np.nan),
                "net_cum_logret": r.get("net", {}).get("cum_logret", np.nan),
            })

    log("G1-G4 per expression")
    gates = {}
    g4_results = {}
    for name, s in sigs.items():
        g = {"G1": True, "G2": True}
        g["G3"] = gate_g3(s, df, primary_pnl[name])
        g["G4"] = gate_g4(s, df)
        g4_results[name] = g["G4"]
        gates[name] = g

    log("G5 batch-level horizon consistency")
    g5 = gate_g5_batch_horizon(sigs, df, g4_results, declared_k=K_PRIMARY)

    log("IC table")
    ic_df = ic_table(sigs, df)
    ic_df.to_csv(f"{args.out}/ic_table_batch_0002.csv", index=False)

    log("LS summary (primary cost)")
    rows = []
    for name, r in primary_pnl.items():
        if "gross" not in r: continue
        rows.append({
            "expr": name,
            "hold_bars": r["hold_bars"],
            "trades_per_hour": r["trades_per_hour"],
            "long_frac": r["long_frac"], "short_frac": r["short_frac"], "flat_frac": r["flat_frac"],
            "gross_sharpe_ann": r["gross"]["sharpe_ann"],
            "gross_mean_bp":    r["gross"]["mean_bp"],
            "gross_cum_logret": r["gross"]["cum_logret"],
            "net_sharpe_ann":   r["net"]["sharpe_ann"],
            "net_cum_logret":   r["net"]["cum_logret"],
            "cost_bps_per_side": r["cost_bps_per_side"],
        })
    pd.DataFrame(rows).to_csv(f"{args.out}/ls_summary_batch_0002.csv", index=False)

    log("cost sensitivity CSV")
    pd.DataFrame(cost_curve).to_csv(f"{args.out}/cost_sensitivity_batch_0002.csv", index=False)

    log("validation_gates JSON")
    with open(f"{args.out}/validation_gates_batch_0002.json", "w") as f:
        json.dump(_walk({"per_expression": gates, "G5_batch": g5}), f, indent=2)

    log("markdown summary")
    with open(f"{args.out}/backtest_results_batch_0002.md", "w") as f:
        f.write("# Backtest Results — BTC 1m Reversal Batch 0002 (Round 2)\n\n")
        f.write(f"Hold bars: {HOLD_BARS}  |  Primary k: {K_PRIMARY}m  |  Primary cost: {COST_BPS_PER_SIDE_PRIMARY} bps/side\n\n")
        f.write("## IC table\n\n```\n"); f.write(ic_df.to_string(index=False)); f.write("\n```\n\n")
        f.write("## Primary strategy summary\n\n```\n")
        f.write(pd.DataFrame(rows).to_string(index=False)); f.write("\n```\n\n")
        f.write("## Cost sensitivity\n\n```\n")
        f.write(pd.DataFrame(cost_curve).to_string(index=False)); f.write("\n```\n\n")
        f.write(f"## G5 batch-level horizon consistency: {'PASS' if g5['passed'] else 'FAIL'}\n\n")
        f.write(f"- declared primary k: {g5['declared_k']} min\n")
        f.write(f"- G4-surviving expressions: {g5['survivors']}\n")
        f.write(f"- peak-IC horizon counts among survivors: {g5['peak_counts']}\n")
        f.write(f"- fraction peaking at declared k: {g5['fraction_peaking_at_declared_k']:.2f}\n\n")
        f.write("## Per-expression gates\n\n")
        for name in sigs:
            g = gates[name]
            f.write(f"### {name}\n")
            f.write(f"- G1/G2: pass\n- G3: {'PASS' if g['G3']['passed'] else 'FAIL'}\n")
            for ck, cv in g["G3"]["checks"].items():
                v = cv["observed"]; tv = cv["threshold"]
                obs = f"{v:.4f}" if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v)
                f.write(f"    - {ck}: {'OK' if cv['pass'] else 'FAIL'}  obs={obs}  thr={tv}\n")
            f.write(f"- G4: {'PASS' if g['G4']['passed'] else 'FAIL'}\n")
            if "checks" in g["G4"]:
                for ck, cv in g["G4"]["checks"].items():
                    f.write(f"    - {ck}: {'OK' if cv['pass'] else 'FAIL'}  obs={cv['observed']:.6f}\n")
                f.write(f"    - ic_primary={g['G4'].get('ic_primary'):.6f}  ic_60m={g['G4'].get('ic_60m'):.6f}\n")
            f.write("\n")

    log("handoff_4_to_5_round2.json")
    handoff = {
        "session_id": "20260423_btc_minute_reversal_v1",
        "round": 2,
        "from": "agent_4_backtest_operator",
        "to":   "agent_5_evaluator_recorder",
        "batch_id": "0002",
        "G5_batch": _walk(g5),
        "expressions": [],
    }
    for name in sigs:
        g = gates[name]
        pnl = primary_pnl[name]
        handoff["expressions"].append({
            "id": name,
            "gates": {
                "G1": True, "G2": True,
                "G3": "pass" if g["G3"]["passed"] else "fail",
                "G4": "pass" if g["G4"]["passed"] else "fail",
            },
            "ic_primary": g["G4"].get("ic_primary"),
            "trades_per_hour": pnl.get("trades_per_hour"),
            "gross_sharpe_ann": pnl.get("gross", {}).get("sharpe_ann"),
            "net_sharpe_ann_5bps": pnl.get("net", {}).get("sharpe_ann"),
        })
    with open(f"{str(WORK_DIR)}/handoff_4_to_5_round2.json", "w") as f:
        json.dump(_walk(handoff), f, indent=2)

    log("DONE")


if __name__ == "__main__":
    main()
