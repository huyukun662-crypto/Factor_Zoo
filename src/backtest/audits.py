"""Validation gates G1-G5 + mandatory pre-PROMOTE audits.

Adapted from worldquant-5-agent-workflow/references/validation-gates.md
and SKILL.md "Mandatory audit rules". Three-asset adaptation of G3
documented in the approved plan.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from ..factors.base import Factor
from .engine import (ANNUALIZER, COST_BPS_PER_SIDE, DELAY, run_backtest,
                     spread_returns)
from .tvt import slice_split


# G3 thresholds (adapted)
G3_NONZERO_FRAC_MIN = 0.30
G3_TURNOVER_MIN = 0.10
G3_TURNOVER_MAX = 20.0  # 2000% annualized
G3_NET_SHARPE_FLOOR = -0.5

# G4 thresholds
G4_PEAK_HORIZONS = [1, 5, 10, 20]
G4_CLASSIC_CORR_MAX = 0.85
G4_MONOTONIC_INVERSIONS_MAX = 1


@dataclass
class GateResult:
    name: str
    passed: bool
    detail: dict = field(default_factory=dict)


@dataclass
class ExpressionReport:
    name: str
    thesis_sign: int
    horizon: int
    train_metrics: dict
    val_metrics: dict
    gates: list[GateResult]
    audits: dict
    notes: list[str] = field(default_factory=list)

    @property
    def all_gates_pass(self) -> bool:
        return all(g.passed for g in self.gates)


# ----------------------------- helpers -----------------------------

def forward_spread_return(panel: pd.DataFrame, horizon: int, delay: int = DELAY) -> pd.Series:
    """Return r_{t+delay → t+delay+h} of (idx300 - idx1000) close-to-close."""
    sret = spread_returns(panel)
    rolling = sret.rolling(horizon).sum()  # sum of next-h log-approx daily simple returns
    # we want the FORWARD h-day sum, executed starting at t+delay
    return rolling.shift(-(horizon + delay - 1))


def ic_at_horizon(score: pd.Series, panel: pd.DataFrame, horizon: int, delay: int = DELAY) -> dict:
    fwd = forward_spread_return(panel, horizon, delay=delay)
    df = pd.DataFrame({"s": score, "f": fwd}).dropna()
    if len(df) < 30 or df["s"].std(ddof=1) == 0 or df["f"].std(ddof=1) == 0:
        return {"horizon": horizon, "ic": float("nan"), "t_stat": float("nan"), "n": int(len(df))}
    r, _ = stats.pearsonr(df["s"], df["f"])
    n = len(df)
    if abs(r) >= 1 - 1e-9:
        t = float("inf")
    else:
        t = r * np.sqrt(n - 2) / np.sqrt(1 - r ** 2)
    return {"horizon": horizon, "ic": float(r), "t_stat": float(t), "n": int(n)}


def quintile_monotonic(score: pd.Series, panel: pd.DataFrame, horizon: int, delay: int = DELAY) -> dict:
    fwd = forward_spread_return(panel, horizon, delay=delay)
    df = pd.DataFrame({"s": score, "f": fwd}).dropna()
    if len(df) < 100 or df["s"].std(ddof=1) == 0:
        return {"means": [], "inversions": -1}
    try:
        df["q"] = pd.qcut(df["s"], 5, labels=False, duplicates="drop")
    except ValueError:
        return {"means": [], "inversions": -1}
    means = df.groupby("q")["f"].mean().sort_index().tolist()
    inversions = sum(1 for a, b in zip(means, means[1:]) if a > b)
    return {"means": [float(x) for x in means], "inversions": int(inversions)}


def classic_factor_clone(score: pd.Series, panel: pd.DataFrame) -> dict:
    """|corr| with the trivial 20d momentum of (idx300 - idx1000)."""
    sret = spread_returns(panel)
    mom20 = sret.rolling(20).sum()
    df = pd.DataFrame({"s": score, "m": mom20}).dropna()
    if len(df) < 30 or df["s"].std(ddof=1) == 0 or df["m"].std(ddof=1) == 0:
        return {"corr_mom20": float("nan")}
    return {"corr_mom20": float(df["s"].corr(df["m"]))}


# ----------------------------- gates -----------------------------

def gate_g1(factor: Factor, panel: pd.DataFrame) -> GateResult:
    try:
        s = factor.generate(panel)
        ok = isinstance(s, pd.Series) and len(s) > 0
        return GateResult("G1_importable", ok, {"score_len": int(len(s))})
    except Exception as exc:
        return GateResult("G1_importable", False, {"exception": repr(exc)})


def gate_g2(factor: Factor, panel: pd.DataFrame, deadband: float = 0.0) -> GateResult:
    try:
        bt = run_backtest(factor, panel, deadband=deadband)
        return GateResult("G2_runs_e2e", True, {"n_days": bt.metrics["n_days"]})
    except Exception as exc:
        return GateResult("G2_runs_e2e", False, {"exception": repr(exc)})


def gate_g3(factor: Factor, panel_train: pd.DataFrame, deadband: float = 0.0) -> GateResult:
    """Adapted G3 for the 3-asset timing setting.

    - non-zero position ≥ 30% of train days
    - annual turnover ∈ [10%, 2000%]
    - signal std > 0
    - net Sharpe @ 5bps/side > -0.5
    """
    bt = run_backtest(factor, panel_train, deadband=deadband)
    m = bt.metrics
    score_std = float(bt.score.dropna().std(ddof=1)) if bt.score.dropna().size > 1 else 0.0
    checks = {
        "non_zero_frac": (m["non_zero_frac"], G3_NONZERO_FRAC_MIN, m["non_zero_frac"] >= G3_NONZERO_FRAC_MIN),
        "ann_turnover": (m["ann_turnover"], (G3_TURNOVER_MIN, G3_TURNOVER_MAX),
                         G3_TURNOVER_MIN <= m["ann_turnover"] <= G3_TURNOVER_MAX),
        "signal_std": (score_std, 0.0, score_std > 0.0),
        "net_sharpe_train": (m["sharpe"], G3_NET_SHARPE_FLOOR, m["sharpe"] > G3_NET_SHARPE_FLOOR),
    }
    passed = all(v[2] for v in checks.values())
    return GateResult("G3_non_degenerate", passed, {k: {"observed": v[0], "threshold": v[1], "pass": v[2]} for k, v in checks.items()})


def gate_g4(factor: Factor, panel_train: pd.DataFrame, deadband: float = 0.0) -> GateResult:
    """Behavioral fidelity on TRAIN.

    - IC sign at declared horizon matches thesis_sign
    - quintile fwd-return monotonicity (≤ 1 inversion)
    - peak |IC| at declared horizon among {1, 5, 10, 20}
    - |corr| with 20d (idx300 - idx1000) momentum < 0.85
    """
    bt = run_backtest(factor, panel_train, deadband=deadband)
    score = bt.score
    ic_main = ic_at_horizon(score, panel_train, factor.horizon)
    ic_sign_ok = (np.sign(ic_main["ic"]) == factor.thesis_sign) if not np.isnan(ic_main["ic"]) else False
    mono = quintile_monotonic(score, panel_train, factor.horizon)
    mono_ok = (0 <= mono["inversions"] <= G4_MONOTONIC_INVERSIONS_MAX)
    ic_table = {h: ic_at_horizon(score, panel_train, h) for h in G4_PEAK_HORIZONS}
    abs_ic = {h: abs(v["ic"]) for h, v in ic_table.items() if not np.isnan(v["ic"])}
    peak_h = max(abs_ic, key=abs_ic.get) if abs_ic else None
    horizon_ok = (peak_h == factor.horizon) if peak_h is not None else False
    classic = classic_factor_clone(score, panel_train)
    classic_ok = (not np.isnan(classic["corr_mom20"])) and abs(classic["corr_mom20"]) < G4_CLASSIC_CORR_MAX
    detail = {
        "ic_main": ic_main,
        "ic_sign_match_thesis": ic_sign_ok,
        "quintile_means": mono["means"],
        "monotonic_inversions": mono["inversions"],
        "ic_by_horizon": ic_table,
        "peak_horizon": peak_h,
        "horizon_match_declared": horizon_ok,
        "corr_with_mom20": classic["corr_mom20"],
        "classic_clone_check_pass": classic_ok,
    }
    passed = bool(ic_sign_ok and mono_ok and horizon_ok and classic_ok)
    return GateResult("G4_behavioral_fidelity", passed, detail)


def gate_g5(reports: list[ExpressionReport], declared_horizon: int) -> GateResult:
    """Batch-level horizon consistency.

    Pass if ≥ 4 of the surviving G1-G4 expressions have peak |IC| at the
    declared primary horizon.
    """
    survivors = [r for r in reports if r.all_gates_pass]
    peaks = []
    for r in survivors:
        g4 = next((g for g in r.gates if g.name == "G4_behavioral_fidelity"), None)
        if g4 is None:
            continue
        peaks.append(g4.detail.get("peak_horizon"))
    n_at_declared = sum(1 for p in peaks if p == declared_horizon)
    return GateResult(
        "G5_batch_horizon_consistency",
        n_at_declared >= 4,
        {"survivors": len(survivors), "peak_horizons": peaks, "n_at_declared": n_at_declared, "declared": declared_horizon},
    )


# ----------------------------- audits -----------------------------

def audit_execution_delay(factor: Factor, panel: pd.DataFrame, sample_days: int = 30, seed: int = 42) -> dict:
    """Audit 1.

    a) Engine invariant: target_shift == -(1+delay).
    b) Future-perturbation: randomize bars after sample date t and confirm
       position_t (which uses the delayed signal) is unchanged.
    """
    rng = np.random.default_rng(seed)
    bt = run_backtest(factor, panel)
    invariant = bt.invariant_check
    target_shift_ok = (invariant["target_shift"] == -(1 + DELAY))

    # Future-perturbation
    n = len(panel)
    if n < 100:
        return {"target_shift_ok": target_shift_ok, "future_perturbation": "skipped (panel too short)"}
    sample_idx = rng.choice(np.arange(50, n - 50), size=min(sample_days, n - 100), replace=False)
    sample_idx.sort()
    mismatches = 0
    checked = 0
    panel_arr = panel.copy()
    for t_pos in sample_idx:
        # perturb columns AFTER index t_pos for index price columns
        perturbed = panel_arr.copy()
        cols_to_perturb = [c for c in perturbed.columns if c.endswith("_close") or c.endswith("_open")
                           or c.endswith("_high") or c.endswith("_low") or c.endswith("_vol")
                           or c.endswith("_amount")]
        for c in cols_to_perturb:
            arr = perturbed[c].to_numpy(copy=True)
            mask = np.arange(len(arr)) > t_pos
            noise = rng.normal(loc=1.0, scale=0.05, size=mask.sum())
            arr[mask] = arr[mask] * noise
            perturbed[c] = arr
        s_orig = factor.generate(panel_arr)
        s_pert = factor.generate(perturbed)
        # signal at the SAMPLE date t_pos must be identical
        idx = panel_arr.index[t_pos]
        v_orig = s_orig.loc[idx] if idx in s_orig.index else np.nan
        v_pert = s_pert.loc[idx] if idx in s_pert.index else np.nan
        checked += 1
        if not (np.isnan(v_orig) and np.isnan(v_pert)):
            if not np.isclose(v_orig, v_pert, rtol=0, atol=1e-12, equal_nan=True):
                mismatches += 1
    return {
        "target_shift_ok": bool(target_shift_ok),
        "future_perturbation_checked": int(checked),
        "future_perturbation_mismatches": int(mismatches),
        "future_perturbation_pass": bool(mismatches == 0),
    }


def audit_lookahead(factor: Factor, panel: pd.DataFrame, sample_days: int = 30, seed: int = 1337) -> dict:
    """Audit 2: identical to future-perturbation invariant of audit_execution_delay
    but with a stronger randomization (full reshuffle of post-t bars, not just multiplicative noise)
    on a SAMPLE of dates. Bit-identical past factor values required.
    """
    rng = np.random.default_rng(seed)
    n = len(panel)
    if n < 100:
        return {"lookahead_check": "skipped"}
    sample_idx = rng.choice(np.arange(50, n - 50), size=min(sample_days, n - 100), replace=False)
    sample_idx.sort()
    mismatches = 0
    checked = 0
    cols_to_perturb = [c for c in panel.columns if any(c.endswith(suf) for suf in
                       ("_close", "_open", "_high", "_low", "_vol", "_amount"))]
    for t_pos in sample_idx:
        perturbed = panel.copy()
        for c in cols_to_perturb:
            arr = perturbed[c].to_numpy(copy=True)
            future = arr[t_pos + 1 :]
            shuffled = future.copy()
            rng.shuffle(shuffled)
            arr[t_pos + 1 :] = shuffled
            perturbed[c] = arr
        s_orig = factor.generate(panel)
        s_pert = factor.generate(perturbed)
        idx = panel.index[t_pos]
        v_orig = s_orig.loc[idx]
        v_pert = s_pert.loc[idx]
        checked += 1
        if not (pd.isna(v_orig) and pd.isna(v_pert)):
            if not np.isclose(v_orig, v_pert, rtol=0, atol=1e-12, equal_nan=True):
                mismatches += 1
    return {
        "checked": int(checked),
        "mismatches": int(mismatches),
        "pass": bool(mismatches == 0),
    }


# ----------------------------- per-expression driver -----------------------------

def evaluate_expression(factor: Factor, panel: pd.DataFrame, deadband: float = 0.5) -> ExpressionReport:
    """Run all gates + train/val backtests + audits 1-2 for one factor.

    deadband: applied uniformly so z-scored signals translate to a {-1,0,+1}
    position only when |z| > deadband. Default 0.5 matches the Stage 3
    convention that all expressions output a 252d-rolling z-score.
    """
    panel_train = slice_split(panel, "train")
    panel_val = slice_split(panel, "val")

    gates: list[GateResult] = []
    g1 = gate_g1(factor, panel_train)
    gates.append(g1)
    if not g1.passed:
        return ExpressionReport(factor.name, factor.thesis_sign, factor.horizon, {}, {}, gates, {}, ["aborted at G1"])
    g2 = gate_g2(factor, panel_train, deadband=deadband)
    gates.append(g2)
    if not g2.passed:
        return ExpressionReport(factor.name, factor.thesis_sign, factor.horizon, {}, {}, gates, {}, ["aborted at G2"])
    g3 = gate_g3(factor, panel_train, deadband=deadband)
    gates.append(g3)
    g4 = gate_g4(factor, panel_train, deadband=deadband)
    gates.append(g4)

    bt_train = run_backtest(factor, panel_train, deadband=deadband)
    bt_val = run_backtest(factor, panel_val, deadband=deadband)

    audits: dict[str, Any] = {}
    audits["audit_1_execution_delay"] = audit_execution_delay(factor, panel_train)
    audits["audit_2_lookahead"] = audit_lookahead(factor, panel_train)

    return ExpressionReport(
        name=factor.name, thesis_sign=factor.thesis_sign, horizon=factor.horizon,
        train_metrics=bt_train.metrics, val_metrics=bt_val.metrics,
        gates=gates, audits=audits,
    )
