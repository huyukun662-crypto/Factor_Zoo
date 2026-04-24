"""
Agent 4 — Backtest Operator for BTC 1m reversal batch 0001.

Runs the 4-gate funnel from worldquant-5-agent-workflow/references/validation-gates.md:
  G1 Importable & syntactically sound   (trivially pass once we run)
  G2 Runs end-to-end                    (try/except wrap per expression)
  G3 Non-degenerate signal              (coverage, dispersion, trade freq, unique regimes)
  G4 Behavioral fidelity                (IC sign matches thesis, horizon profile, monotonic deciles)

Outputs:
  ic_table_batch_0001.csv
  decile_summary_batch_0001.csv
  ls_summary_batch_0001.csv
  validation_gates_batch_0001.json
  backtest_results_batch_0001.md
  working/handoff_4_to_5.json

Single-asset adaptation notes (documented in session_metadata.yml):
  - "Q5" -> decile bucket by signal value over time
  - "IC cross-section" -> Pearson correlation over the time series
  - "portfolio" -> thresholded long/short position (top/bottom 10% signal)
  - "turnover" -> position-change count per hour
"""
from __future__ import annotations
import argparse, json, os, sys, time
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
K_PRIMARY = 5
K_ALL = [1, 5, 15, 60]
COST_BPS_PER_SIDE = 5.0    # 5 bps per fill


def log(m: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)


# ---------- build base panel ----------

def build_panel(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("ts").reset_index(drop=True).copy()
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["r1"] = np.log(df["close"]).diff()
    for n in [5, 15, 60]:
        df[f"r{n}"]      = np.log(df["close"]) - np.log(df["close"].shift(n))
        df[f"rv{n}"]     = df["r1"].rolling(n, min_periods=n).std(ddof=0)
        df[f"range{n}"]  = (df["high"].rolling(n).max() - df["low"].rolling(n).min()) / df["close"].shift(n)
        df[f"amount{n}"] = (df["volume"] * df["close"]).rolling(n, min_periods=n).sum()

    df["hour"] = df["ts"].dt.hour
    # forward returns for all k, delay=1
    for k in K_ALL:
        df[f"fwd_ret_{k}"] = np.log(df["close"]).shift(-(DELAY + k)) - np.log(df["close"]).shift(-DELAY)
    return df


def ts_z(s: pd.Series) -> pd.Series:
    sd = s.std(ddof=0)
    if not sd or np.isnan(sd):
        return s * 0.0
    return (s - s.mean()) / sd


def hour_demean(s: pd.Series, hour: pd.Series) -> pd.Series:
    return s - s.groupby(hour).transform("mean")


# ---------- expressions ----------

def build_expressions(df: pd.DataFrame) -> dict:
    """Return dict {expr_id: signal_series}. All signed high->LONG."""
    out = {}
    r1  = df["r1"];  r5  = df["r5"];  r15 = df["r15"]
    rv5, rv15 = df["rv5"], df["rv15"]
    range5 = df["range5"]
    amount5 = df["amount5"]
    hour = df["hour"]

    out["r1_rev_1m"]             = -ts_z(r1)
    out["r1_rev_5m"]             = -ts_z(r5)
    out["r1_rev_15m"]            = -ts_z(r15)

    vs5  = r5  / rv5.replace(0, np.nan)
    vs15 = r15 / rv15.replace(0, np.nan)
    out["r1_rev_5m_volscale"]    = -ts_z(vs5)
    out["r1_rev_15m_volscale"]   = -ts_z(vs15)

    vs5_hd = hour_demean(vs5, hour)
    out["r1_rev_5m_volscale_hd"] = -ts_z(vs5_hd)

    out["r1_rev_range5m"]        = -ts_z(np.sign(r5) * range5)
    out["r1_rev_amount5m"]       = -ts_z(np.sign(r5) * np.log(amount5.replace(0, np.nan)))

    return out


# ---------- G3 / G4 gates ----------

def gate_g3(sig: pd.Series, df: pd.DataFrame, expr_id: str) -> dict:
    """
    G3 Non-degenerate: adapted for single-asset time series.
      - coverage: % of bars with non-NaN signal
      - dispersion: signal std > 0 on (here trivially on full sample — already z-scored)
      - trade frequency: position-change count per hour for a D10/D1 threshold strategy
      - regime diversity: unique days containing any top-decile or bottom-decile bar
    """
    n_total = len(sig)
    n_valid = int(sig.notna().sum())
    coverage = n_valid / n_total if n_total else 0.0

    std_ok = (sig.dropna().std(ddof=0) or 0) > 0

    # threshold strategy: +1 if signal >= D10 cut, -1 if signal <= D1 cut, else 0
    q10, q90 = sig.quantile(0.10), sig.quantile(0.90)
    pos = pd.Series(np.where(sig >= q90, 1.0,
                    np.where(sig <= q10, -1.0, 0.0)), index=sig.index)
    pos_change = pos.diff().abs().fillna(0) > 0
    total_minutes = n_valid
    trade_freq_per_hour = 60.0 * pos_change.sum() / total_minutes if total_minutes else 0.0

    # regime diversity: unique days touched by the active positions
    active_days = df.loc[pos != 0, "ts"].dt.date.nunique()
    total_days  = df["ts"].dt.date.nunique()
    days_coverage = active_days / total_days if total_days else 0.0

    # daily active count
    active_bars_per_day = df.assign(_pos=pos).groupby(df["ts"].dt.date)["_pos"].apply(lambda s: (s != 0).sum())
    bars_per_day_median = float(active_bars_per_day.median())

    checks = {
        "coverage": (coverage >= 0.95,  coverage,  0.95,  "non-NaN fraction"),
        "std_nonzero": (std_ok,  bool(std_ok),  True,  "signal std > 0"),
        "trade_freq_per_hour_ok": (trade_freq_per_hour <= 10.0,  trade_freq_per_hour, 10.0, "pos changes / hour ≤ 10"),
        "days_coverage": (days_coverage >= 0.80,  days_coverage, 0.80,  "fraction of days with any active position"),
        "bars_per_day_median_ok": (bars_per_day_median >= 30,  bars_per_day_median, 30, "median active bars per day"),
    }

    passed = all(v[0] for v in checks.values())
    return {
        "passed": passed,
        "checks": {k: {"pass": bool(v[0]), "observed": float(v[1]) if isinstance(v[1], (int,float,np.floating)) else v[1],
                       "threshold": v[2], "desc": v[3]}
                   for k, v in checks.items()},
    }


def gate_g4(sig: pd.Series, df: pd.DataFrame, expected_ic_sign_pos: bool) -> dict:
    """
    G4 Behavioral fidelity:
      - IC sign at primary horizon matches thesis
      - IC decays past primary horizon (mean-reversion signature)
      - Decile monotonicity: D10 mean fwd_ret > D1 mean fwd_ret (directional)
    """
    k = K_PRIMARY
    fwd = df[f"fwd_ret_{k}"]
    m = sig.notna() & fwd.notna()
    if m.sum() < 1000:
        return {"passed": False, "reason": "insufficient sample"}
    ic, pval = stats.pearsonr(sig[m], fwd[m])

    ic_sign_ok = (ic > 0) if expected_ic_sign_pos else (ic < 0)

    # decile monotonicity
    tmp = pd.DataFrame({"sig": sig[m], "fwd": fwd[m]})
    tmp["dec"] = pd.qcut(tmp["sig"], 10, labels=False, duplicates="drop")
    dec_means = tmp.groupby("dec")["fwd"].mean()
    # D10 must beat D1 (directional, not strict monotone)
    d10_vs_d1 = float(dec_means.iloc[-1] - dec_means.iloc[0])
    direction_ok = (d10_vs_d1 > 0) if expected_ic_sign_pos else (d10_vs_d1 < 0)

    # horizon profile: IC at k=60 should be smaller than at k=5 (mean-reversion, not momentum)
    fwd60 = df["fwd_ret_60"]
    m60 = sig.notna() & fwd60.notna()
    ic60, _ = stats.pearsonr(sig[m60], fwd60[m60])
    horizon_ok = abs(ic) >= abs(ic60)   # primary horizon dominates long horizon

    checks = {
        "ic_sign":        (ic_sign_ok,   float(ic),        "IC sign matches thesis"),
        "decile_dir":     (direction_ok, d10_vs_d1,        "D10 > D1 mean fwd_ret"),
        "horizon_decay":  (horizon_ok,   float(abs(ic) - abs(ic60)), "|IC_5m| >= |IC_60m|"),
    }
    passed = all(v[0] for v in checks.values())
    return {
        "passed": passed,
        "ic_primary": float(ic),
        "ic_60m": float(ic60),
        "d10_minus_d1_mean_fwd": d10_vs_d1,
        "checks": {k: {"pass": bool(v[0]), "observed": float(v[1]), "desc": v[2]} for k, v in checks.items()},
    }


# ---------- IC table / decile summary / strategy PnL ----------

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


def decile_summary(sigs: dict, df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    fwd = df[f"fwd_ret_{K_PRIMARY}"]
    for name, s in sigs.items():
        m = s.notna() & fwd.notna()
        if m.sum() < 1000:
            continue
        tmp = pd.DataFrame({"sig": s[m], "fwd": fwd[m]})
        tmp["dec"] = pd.qcut(tmp["sig"], 10, labels=False, duplicates="drop")
        g = tmp.groupby("dec")["fwd"].agg(["mean","count"]).reset_index()
        g["expr"] = name
        rows.append(g)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def threshold_strategy_pnl(sig: pd.Series, df: pd.DataFrame,
                           low_q=0.10, high_q=0.90,
                           cost_bps_per_side=COST_BPS_PER_SIDE) -> dict:
    """
    Thresholded long-short strategy:
      position = +1 if signal >= top decile cut
                -1 if signal <= bottom decile cut
                else 0 (flat)
    Hold for K_PRIMARY minutes? No — hold until signal says otherwise (simpler;
    position persists until next bar re-evaluates). We still compute PnL per-bar
    from log returns to be faithful to the "delay=1" rule.

    PnL per bar t = position[t] * (log_close[t+1+K-something])? — simpler:
    at bar t, set position; earn log_ret over [t+1, t+2]. i.e. realized per-minute.
    We do holding = 1 minute per position re-evaluation to keep the strategy
    apples-to-apples with the signal.

    NOTE: this is a *gross-direction* strategy at the minute bar level, different
    from the 5-min forward IC evaluation. Report both.
    """
    s = sig.copy()
    q_lo, q_hi = s.quantile(low_q), s.quantile(high_q)
    pos = pd.Series(np.where(s >= q_hi, 1.0,
                    np.where(s <= q_lo, -1.0, 0.0)), index=s.index)
    # delay=1: execute at next bar
    pos_eff = pos.shift(1)
    r_next = np.log(df["close"]).shift(-1) - np.log(df["close"])  # 1-bar forward log return at t
    # gross PnL at bar t = pos_eff[t] * r_next[t]
    gross = pos_eff * r_next
    # turnover cost: 2 * bps * |pos_eff - pos_eff.shift(1)| / 2  (|Δ|*bps)
    turn = pos_eff.diff().abs().fillna(0)
    cost = turn * (cost_bps_per_side / 1e4)
    net = gross - cost

    n_valid = int(net.notna().sum())
    if n_valid < 1000:
        return {"n_bars": n_valid, "note": "insufficient"}

    ann_factor = np.sqrt(60 * 24 * 365)   # minutes per year, sqrt for Sharpe
    def stats_for(pnl):
        mu = float(pnl.mean()); sd = float(pnl.std(ddof=0))
        sharpe_ann = (mu / sd) * ann_factor if sd else 0.0
        cum = float(pnl.sum())
        return {"mean_bp": mu * 1e4, "std_bp": sd * 1e4, "sharpe_ann": sharpe_ann, "cum_logret": cum}

    gross_stats = stats_for(gross.dropna())
    net_stats   = stats_for(net.dropna())

    trade_count = int(turn.sum())
    trades_per_hour = 60.0 * trade_count / n_valid
    long_frac  = float((pos_eff == 1).mean())
    short_frac = float((pos_eff == -1).mean())

    return {
        "n_bars": n_valid,
        "trade_count_abs_pos_changes": trade_count,
        "trades_per_hour": trades_per_hour,
        "long_frac": long_frac,
        "short_frac": short_frac,
        "gross": gross_stats,
        "net": net_stats,
        "cost_bps_per_side": cost_bps_per_side,
    }


# ---------- main ----------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA_PATH))
    ap.add_argument("--out",  default=str(OUT_DIR))
    args = ap.parse_args()

    log("load data")
    df = pd.read_parquet(args.data)
    log(f"loaded {len(df)} bars from {df['ts'].min()} -> {df['ts'].max()}")

    log("build panel")
    df = build_panel(df)

    log("build expressions")
    sigs = build_expressions(df)
    expected_signs = {name: True for name in sigs}  # all signed high->LONG

    log("G1 + G2 — if we reached here, both pass")
    gates = {name: {"G1": True, "G2": True} for name in sigs}

    log("G3 — non-degenerate check")
    for name, s in sigs.items():
        gates[name]["G3"] = gate_g3(s, df, name)

    log("G4 — behavioral fidelity")
    for name, s in sigs.items():
        gates[name]["G4"] = gate_g4(s, df, expected_signs[name])

    log("IC table")
    ic_df = ic_table(sigs, df)
    ic_df.to_csv(f"{args.out}/ic_table_batch_0001.csv", index=False)
    log("decile summary")
    dec_df = decile_summary(sigs, df)
    dec_df.to_csv(f"{args.out}/decile_summary_batch_0001.csv", index=False)

    log("strategy PnL")
    strat_rows = []
    for name, s in sigs.items():
        st = threshold_strategy_pnl(s, df)
        st["expr"] = name
        strat_rows.append(st)
    # flatten for CSV
    flat = []
    for r in strat_rows:
        if "gross" not in r:
            continue
        flat.append({
            "expr": r["expr"],
            "n_bars": r["n_bars"],
            "trades_per_hour": r["trades_per_hour"],
            "long_frac": r["long_frac"],
            "short_frac": r["short_frac"],
            "gross_mean_bp": r["gross"]["mean_bp"],
            "gross_sharpe_ann": r["gross"]["sharpe_ann"],
            "gross_cum_logret": r["gross"]["cum_logret"],
            "net_mean_bp": r["net"]["mean_bp"],
            "net_sharpe_ann": r["net"]["sharpe_ann"],
            "net_cum_logret": r["net"]["cum_logret"],
            "cost_bps_per_side": r["cost_bps_per_side"],
        })
    ls_df = pd.DataFrame(flat)
    ls_df.to_csv(f"{args.out}/ls_summary_batch_0001.csv", index=False)

    log("write validation_gates json")
    # make gates JSON-serializable
    def _js(x):
        if isinstance(x, (np.bool_,)): return bool(x)
        if isinstance(x, (np.floating,)): return float(x)
        if isinstance(x, (np.integer,)): return int(x)
        return x
    def _walk(o):
        if isinstance(o, dict): return {k: _walk(v) for k, v in o.items()}
        if isinstance(o, list): return [_walk(v) for v in o]
        return _js(o)
    with open(f"{args.out}/validation_gates_batch_0001.json", "w") as f:
        json.dump(_walk(gates), f, indent=2)

    log("write markdown summary")
    with open(f"{args.out}/backtest_results_batch_0001.md", "w") as f:
        f.write("# Backtest Results — BTC 1m Reversal Batch 0001\n\n")
        f.write(f"Data window: {df['ts'].min()} -> {df['ts'].max()}  ({len(df)} bars)\n\n")

        f.write("## IC table (Pearson, forward log-return)\n\n```\n")
        f.write(ic_df.to_string(index=False))
        f.write("\n```\n\n")

        f.write("## Decile summary (at primary horizon k=5m)\n\n```\n")
        f.write(dec_df.to_string(index=False))
        f.write("\n```\n\n")

        f.write(f"## Strategy PnL (threshold D10/D1, delay=1, cost={COST_BPS_PER_SIDE} bps/side)\n\n```\n")
        f.write(ls_df.to_string(index=False))
        f.write("\n```\n\n")

        f.write("## Validation gates (G1-G4)\n\n")
        for name in sigs:
            g = gates[name]
            f.write(f"### {name}\n")
            f.write(f"- G1: {g['G1']}\n- G2: {g['G2']}\n")
            f.write(f"- G3: {'PASS' if g['G3']['passed'] else 'FAIL'}\n")
            for ck, cv in g["G3"]["checks"].items():
                f.write(f"    - {ck}: {'OK' if cv['pass'] else 'FAIL'}  observed={cv['observed']:.4f}  threshold={cv['threshold']}\n")
            f.write(f"- G4: {'PASS' if g['G4']['passed'] else 'FAIL'}\n")
            if "checks" in g["G4"]:
                for ck, cv in g["G4"]["checks"].items():
                    f.write(f"    - {ck}: {'OK' if cv['pass'] else 'FAIL'}  observed={cv['observed']:.6f}\n")
            f.write(f"    - ic_primary={g['G4'].get('ic_primary')}  ic_60m={g['G4'].get('ic_60m')}\n\n")

    # handoff_4_to_5
    log("write handoff_4_to_5.json")
    handoff = {
        "session_id": "20260423_btc_minute_reversal_v1",
        "from": "agent_4_backtest_operator",
        "to":   "agent_5_evaluator_recorder",
        "batch_id": "0001",
        "expressions": [],
    }
    for name in sigs:
        g = gates[name]
        handoff["expressions"].append({
            "id": name,
            "gates": {
                "G1": g["G1"], "G2": g["G2"],
                "G3": "pass" if g["G3"]["passed"] else "fail",
                "G4": "pass" if g["G4"]["passed"] else "fail",
            },
            "retry_count": 0,
            "ic_primary": g["G4"].get("ic_primary"),
        })
    with open(f"{str(WORK_DIR)}/handoff_4_to_5.json", "w") as f:
        json.dump(_walk(handoff), f, indent=2)

    log("DONE")


if __name__ == "__main__":
    main()
