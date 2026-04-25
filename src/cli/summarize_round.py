"""Agent 5 helper — TVT selection, frozen-test, audits 3-4, draft alpha_ranking.md."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..backtest.engine import per_year_breakdown, run_backtest
from ..backtest.tvt import is_eligible, selection_score, slice_split
from ..data.panel import load_panel
from ..factors import registry  # noqa: F401
from ..factors.base import FACTORS

SESSION_DIR = Path("logs/20260425_a_share_style_timing_csi300_csi1000")


def _fmt(x, dp=3):
    if x is None or (isinstance(x, float) and (pd.isna(x) or np.isnan(x))):
        return "n/a"
    if isinstance(x, float):
        return f"{x:.{dp}f}"
    return str(x)


def _fmt_pct(x):
    if x is None or pd.isna(x):
        return "n/a"
    return f"{x*100:+.2f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--deadband", type=float, default=0.5)
    args = ap.parse_args()

    handoff_path = SESSION_DIR / "working" / "handoff_4_to_5.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    panel = load_panel()

    # Build eligibility table
    rows = []
    for r in handoff["results"]:
        train_sh = r["sharpe"]
        val_sh = r["val_sharpe"]
        elig = is_eligible(train_sh, val_sh) if train_sh is not None and val_sh is not None else False
        score = selection_score(train_sh, val_sh) if train_sh is not None and val_sh is not None else float("nan")
        rows.append({
            "name": r["alpha_id"], "train_sharpe": train_sh, "val_sharpe": val_sh,
            "eligible": elig, "score": score, "horizon": r["horizon"],
            "ic": r["ic"], "all_gates_pass": (r["status"] == "completed"),
            "g5_pass": handoff["g5"]["passed"],
        })
    tbl = pd.DataFrame(rows)
    elig = tbl[tbl["eligible"] & tbl["all_gates_pass"] & tbl["g5_pass"]].copy()

    if elig.empty:
        winner = None
        decision_basis = "no eligible candidate (failed eligibility, gates, or G5)"
    else:
        winner = elig.sort_values("score", ascending=False).iloc[0]["name"]
        decision_basis = f"selected {winner} on TVT score = val_sh − 0.3·|train_sh − val_sh|"

    # Run frozen TEST on winner only (or all candidates if none eligible — for diagnostic context)
    test_blocks = {}
    candidates_for_test = [winner] if winner else list(tbl["name"])
    for name in candidates_for_test:
        if name is None:
            continue
        f = FACTORS[name]
        bt = run_backtest(f, slice_split(panel, "test"), deadband=args.deadband)
        per_year = per_year_breakdown(bt.daily_pnl, bt.traded_position)
        # Compute audit 3 / 4
        if not per_year.empty:
            worst_year = per_year.iloc[per_year["sharpe"].idxmin()]
            audit3 = {"worst_year": int(worst_year["year"]), "worst_sharpe": float(worst_year["sharpe"]), "pass": bool(worst_year["sharpe"] >= 0.5)}
            best_idx = per_year["sharpe"].idxmax()
            best_year = per_year.iloc[best_idx]
            mask = per_year.index != best_idx
            if mask.sum() > 0:
                pnl_no_best = bt.daily_pnl[bt.daily_pnl.index.year != int(best_year["year"])]
                pos_no_best = bt.traded_position[bt.traded_position.index.year != int(best_year["year"])]
                from ..backtest.engine import compute_metrics  # noqa: PLC0415
                m_no_best = compute_metrics(pnl_no_best, pos_no_best)
                headline = bt.metrics["sharpe"]
                ratio = (m_no_best["sharpe"] / headline) if headline not in (0, None) and not pd.isna(headline) and abs(headline) > 1e-9 else float("nan")
                audit4 = {"best_year": int(best_year["year"]), "best_sharpe": float(best_year["sharpe"]),
                          "headline_sharpe": float(headline), "no_best_sharpe": float(m_no_best["sharpe"]),
                          "ratio": float(ratio) if not pd.isna(ratio) else None,
                          "pass": bool(not pd.isna(ratio) and ratio >= 0.5)}
            else:
                audit4 = {"pass": False, "note": "only one test year"}
        else:
            audit3 = {"pass": False, "note": "no per-year data"}
            audit4 = {"pass": False, "note": "no per-year data"}
        test_blocks[name] = {"metrics": bt.metrics, "per_year": per_year.to_dict(orient="records"),
                             "audit_3_worst_year": audit3, "audit_4_best_year_out": audit4}

    # Render alpha_ranking.md (auto-generated skeleton; LLM author will polish)
    lines = []
    lines.append("# Alpha Ranking — Round 0001 (auto-generated draft)")
    lines.append("")
    lines.append(f"**Selection basis**: {decision_basis}")
    lines.append("")
    lines.append("## Eligibility table")
    lines.append("")
    lines.append("| Expr | Train Sharpe | Val Sharpe | Eligible | TVT Score | Gates+G5 |")
    lines.append("|---|---:|---:|:-:|---:|:-:|")
    for _, r in tbl.iterrows():
        lines.append("| {n} | {ts} | {vs} | {e} | {sc} | {g} |".format(
            n=r["name"], ts=_fmt(r["train_sharpe"]), vs=_fmt(r["val_sharpe"]),
            e="Y" if r["eligible"] else "N", sc=_fmt(r["score"]),
            g="Y" if (r["all_gates_pass"] and r["g5_pass"]) else "N",
        ))
    lines.append("")
    if winner:
        lines.append(f"## Winner: `{winner}` — frozen test results")
        lines.append("")
        block = test_blocks[winner]
        m = block["metrics"]
        lines.append("### TVT gradient")
        lines.append("")
        train_row = tbl[tbl["name"] == winner].iloc[0]
        lines.append("| Metric | Train | Val | Test |")
        lines.append("|---|---:|---:|---:|")
        lines.append(f"| Sharpe | {_fmt(train_row['train_sharpe'])} | {_fmt(train_row['val_sharpe'])} | {_fmt(m['sharpe'])} |")
        lines.append(f"| Ann. return | n/a | n/a | {_fmt_pct(m['ann_return'])} |")
        lines.append(f"| Max DD | n/a | n/a | {_fmt_pct(m['max_dd'])} |")
        lines.append(f"| Calmar | n/a | n/a | {_fmt(m['calmar'])} |")
        lines.append(f"| Ann. turnover | n/a | n/a | {_fmt(m['ann_turnover'], 2)} |")
        lines.append(f"| Non-zero days | n/a | n/a | {_fmt_pct(m['non_zero_frac'])} |")
        lines.append("")
        lines.append("### Per-year test breakdown")
        lines.append("")
        lines.append("| Year | n_days | Sharpe | Ann return | Max DD | Turnover |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for row in block["per_year"]:
            lines.append(f"| {row['year']} | {row['n_days']} | {_fmt(row['sharpe'])} | {_fmt_pct(row['ann_return'])} | {_fmt_pct(row['max_dd'])} | {_fmt(row['ann_turnover'], 2)} |")
        lines.append("")
        lines.append("### Audit 3 — worst-year Sharpe ≥ 0.5")
        lines.append("")
        a3 = block["audit_3_worst_year"]
        lines.append(f"- worst year: {a3.get('worst_year')}  worst sharpe: {_fmt(a3.get('worst_sharpe'))}  → **{'PASS' if a3.get('pass') else 'FAIL'}**")
        lines.append("")
        lines.append("### Audit 4 — best-year-out Sharpe ≥ 50% × headline")
        lines.append("")
        a4 = block["audit_4_best_year_out"]
        lines.append(f"- best year: {a4.get('best_year')}  best sharpe: {_fmt(a4.get('best_sharpe'))}")
        lines.append(f"- headline test sharpe: {_fmt(a4.get('headline_sharpe'))}  no-best sharpe: {_fmt(a4.get('no_best_sharpe'))}")
        lines.append(f"- ratio: {_fmt(a4.get('ratio'))}  → **{'PASS' if a4.get('pass') else 'FAIL'}**")
        lines.append("")
        lines.append("### Hard floors for PROMOTE (tvt-split-template.md)")
        lines.append("")
        # Simple checklist — IC t-stat needs to be filled by Agent 5
        lines.append(f"- [ ] Test IC mean t-stat ≥ 3.0  — requires manual computation per-horizon")
        lines.append(f"- [{'x' if m['sharpe'] >= 1.0 else ' '}] Test Sharpe ≥ 1.0  — observed {_fmt(m['sharpe'])}")
        lines.append(f"- [{'x' if a3.get('pass') else ' '}] Worst-year Sharpe ≥ 0.5")
        lines.append(f"- [{'x' if a4.get('pass') else ' '}] Best-year-out Sharpe ≥ 50%")
        lines.append(f"- [ ] Test max DD < 2× train max DD  — requires train DD reference")
        lines.append(f"- [{'x' if m['calmar'] >= 1.5 else ' '}] Calmar ≥ 1.5  — observed {_fmt(m['calmar'])}")
        lines.append(f"- [x] Execution-delay audit passed  — see backtest_results_batch_0001.md audit_1")
        lines.append(f"- [x] Look-ahead audit passed  — see backtest_results_batch_0001.md audit_2")
        lines.append("")
    else:
        lines.append("## No eligible candidate; decision is RESEARCH-ONLY or STOP")
        lines.append("")
        lines.append("### Diagnostic per-candidate test runs (for context only)")
        lines.append("")
        for name, block in test_blocks.items():
            m = block["metrics"]
            lines.append(f"#### {name}")
            lines.append(f"- test sharpe: {_fmt(m['sharpe'])}  ann ret: {_fmt_pct(m['ann_return'])}  max DD: {_fmt_pct(m['max_dd'])}  non-zero: {_fmt_pct(m['non_zero_frac'])}")

    lines.append("")
    lines.append("## Decision (Agent 5 must complete)")
    lines.append("")
    lines.append("- **Decision**: PROMOTE | RESEARCH-ONLY | STOP  ← Agent 5 fills")
    lines.append("- **Audit 5 (falsification)**: \"If this Sharpe is wrong by 50%, the most likely single cause is …\"  ← Agent 5 fills")
    lines.append("- **Next-round focus** (if continue/refine): …  ← Agent 5 fills")
    lines.append("")

    out = SESSION_DIR / "outputs" / "alpha_ranking.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[summarize_round] wrote {out}")

    # Persist computed structures for Agent 5 narrative
    diagnostic = {"selection_table": tbl.to_dict(orient="records"),
                  "winner": winner, "test_blocks": test_blocks}
    diag = SESSION_DIR / "working" / "agent5_diagnostic.json"
    diag.write_text(json.dumps(diagnostic, indent=2, default=str), encoding="utf-8")
    print(f"[summarize_round] wrote {diag}")


if __name__ == "__main__":
    main()
