"""Agent 4 (Backtest Operator) harness.

For each registered factor:
  - run gates G1-G4
  - run audits 1-2 on TRAIN
  - capture train + val metrics
Compute G5 at batch level.
Emit:
  - logs/<session>/outputs/backtest_results_batch_NNNN.md
  - logs/<session>/working/handoff_4_to_5.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ..backtest.audits import (evaluate_expression, gate_g5)
from ..data.panel import load_panel
from ..factors import registry  # noqa: F401  (triggers expression discovery)
from ..factors.base import FACTORS

SESSION_DIR = Path("logs/20260425_a_share_style_timing_csi300_csi1000")


def _fmt_pct(x: float) -> str:
    if x is None or pd.isna(x):
        return "n/a"
    return f"{x*100:+.2f}%"


def _fmt(x, dp=3):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "n/a"
    if isinstance(x, float):
        return f"{x:.{dp}f}"
    return str(x)


def render_md(reports, g5, declared_horizon: int) -> str:
    lines = []
    lines.append("# Backtest Results — Batch 0001")
    lines.append("")
    lines.append("Source: Agent 4 (Backtest Operator) harness `src/cli/run_batch.py`.")
    lines.append("Universe: 3 broad-base ETFs (510300/510500/512100) + 3 indices (000300/000905/000852).")
    lines.append("Splits: TRAIN [2018,2022) · VAL [2022,2024) · TEST [2024,now] frozen.")
    lines.append("Cost assumption: 5 bps per side per leg (10 bps round-trip per leg).")
    lines.append("")
    lines.append("## Per-expression gate + metrics table")
    lines.append("")
    lines.append("| Expr | G1 | G2 | G3 | G4 | Train Sharpe | Val Sharpe | Train Turn | Val Turn | Train MaxDD | Val MaxDD | NonZero% (train) |")
    lines.append("|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in reports:
        gmap = {g.name: g for g in r.gates}
        def cell(g):
            return "✓" if (g and g.passed) else ("✗" if g else "—")
        lines.append("| {n} | {g1} | {g2} | {g3} | {g4} | {ts} | {vs} | {tt} | {vt} | {tdd} | {vdd} | {nz} |".format(
            n=r.name,
            g1=cell(gmap.get("G1_importable")),
            g2=cell(gmap.get("G2_runs_e2e")),
            g3=cell(gmap.get("G3_non_degenerate")),
            g4=cell(gmap.get("G4_behavioral_fidelity")),
            ts=_fmt(r.train_metrics.get("sharpe")),
            vs=_fmt(r.val_metrics.get("sharpe")),
            tt=_fmt(r.train_metrics.get("ann_turnover"), 2),
            vt=_fmt(r.val_metrics.get("ann_turnover"), 2),
            tdd=_fmt_pct(r.train_metrics.get("max_dd")),
            vdd=_fmt_pct(r.val_metrics.get("max_dd")),
            nz=_fmt_pct(r.train_metrics.get("non_zero_frac")),
        ))
    lines.append("")
    lines.append("## G5 — Batch horizon consistency")
    lines.append("")
    lines.append(f"- Declared primary horizon: **{declared_horizon}d**")
    lines.append(f"- Surviving (G1-G4 pass) expressions: {g5.detail.get('survivors')}")
    lines.append(f"- Peak |IC| horizons across survivors: {g5.detail.get('peak_horizons')}")
    lines.append(f"- N at declared horizon: {g5.detail.get('n_at_declared')} (need ≥ 4)")
    lines.append(f"- G5 result: {'**PASS**' if g5.passed else '**FAIL** → escalate to Agent 2 (revise horizon)'}")
    lines.append("")
    lines.append("## Per-expression detail")
    lines.append("")
    for r in reports:
        lines.append(f"### {r.name}")
        lines.append("")
        lines.append(f"- thesis_sign={r.thesis_sign}, declared_horizon={r.horizon}d")
        lines.append("- Gates:")
        for g in r.gates:
            lines.append(f"    - **{g.name}**: {'PASS' if g.passed else 'FAIL'}")
            if g.detail:
                detail_str = json.dumps(g.detail, default=str, ensure_ascii=False)
                if len(detail_str) > 800:
                    detail_str = detail_str[:800] + "...(truncated)"
                lines.append(f"        - detail: `{detail_str}`")
        lines.append("- TRAIN metrics:")
        for k, v in r.train_metrics.items():
            lines.append(f"    - {k}: {_fmt(v, 4)}")
        lines.append("- VAL metrics:")
        for k, v in r.val_metrics.items():
            lines.append(f"    - {k}: {_fmt(v, 4)}")
        lines.append("- Audits:")
        for k, v in r.audits.items():
            lines.append(f"    - **{k}**: {json.dumps(v, default=str, ensure_ascii=False)}")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_handoff(reports, g5, batch_id: str) -> dict:
    return {
        "batch_id": batch_id,
        "validation_passed": g5.passed and all(r.all_gates_pass for r in reports),
        "submission_made": True,
        "results": [
            {
                "expression_idx": i + 1,
                "alpha_id": r.name,
                "sharpe": r.train_metrics.get("sharpe"),
                "fitness": None,
                "turnover": r.train_metrics.get("ann_turnover"),
                "ic": next((g.detail.get("ic_main", {}).get("ic")
                            for g in r.gates if g.name == "G4_behavioral_fidelity" and g.detail), None),
                "status": "completed" if r.all_gates_pass else "failed",
                "error": None if r.all_gates_pass else f"failed gates: {[g.name for g in r.gates if not g.passed]}",
                "val_sharpe": r.val_metrics.get("sharpe"),
                "horizon": r.horizon,
                "thesis_sign": r.thesis_sign,
            }
            for i, r in enumerate(reports)
        ],
        "expressions": [
            {
                "id": r.name,
                "gates": {g.name: ("pass" if g.passed else "fail") for g in r.gates},
                "retry_count": 0,
                "notes": "; ".join(r.notes) if r.notes else "",
            }
            for r in reports
        ],
        "g5": {
            "passed": g5.passed,
            "detail": g5.detail,
        },
        "anomalies": [r.name for r in reports if not r.all_gates_pass],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--horizon", type=int, default=5,
                    help="Declared primary horizon for G5; should match session_metadata.yml")
    ap.add_argument("--deadband", type=float, default=0.5,
                    help="|z|>deadband → take a position; else flat. 0.5 matches Stage 3 z-score convention.")
    args = ap.parse_args()

    panel = load_panel()
    if not FACTORS:
        raise RuntimeError("No factors registered. Did you create files in src/factors/expressions/?")
    print(f"[run_batch] discovered {len(FACTORS)} factors: {list(FACTORS)}")
    if len(FACTORS) != 8:
        print(f"[run_batch] WARNING: Rule of 8 violation — got {len(FACTORS)} expressions")

    reports = []
    for name, f in FACTORS.items():
        print(f"[run_batch] evaluating {name} ...")
        rep = evaluate_expression(f, panel, deadband=args.deadband)
        reports.append(rep)

    g5 = gate_g5(reports, declared_horizon=args.horizon)
    md = render_md(reports, g5, args.horizon)
    handoff = render_handoff(reports, g5, batch_id=f"batch_{args.batch:04d}")

    out_md = SESSION_DIR / "outputs" / f"backtest_results_batch_{args.batch:04d}.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md, encoding="utf-8")
    print(f"[run_batch] wrote {out_md}")

    handoff_path = SESSION_DIR / "working" / "handoff_4_to_5.json"
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(json.dumps(handoff, indent=2, default=str), encoding="utf-8")
    print(f"[run_batch] wrote {handoff_path}")


if __name__ == "__main__":
    main()
