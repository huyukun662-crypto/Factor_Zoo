"""Generate alpha_ranking.md + final_summary.md from backtest+audit artifacts."""
import json, pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"


def main():
    summ = pd.read_csv(OUT / "ic_ls_summary_batch_0001.csv")
    yearly = pd.read_csv(OUT / "yearly_sharpe_h10.csv")
    audits = json.loads((OUT / "audits.json").read_text())

    # rank by composite score: monthly Q5 excess Sharpe (deployable A-share metric)
    head = summ[summ["h"] == 10].copy()
    head["score"] = head["q5e_sr_monthly"].fillna(-9) + 0.3 * head["ic_ir"].fillna(-9)
    head = head.sort_values("score", ascending=False)

    floors = audits["worst_year_floor"]
    byo = audits["best_year_out"]
    res = audits["residualization"]

    lines = ["# Alpha ranking — batch 0001 (round 1)\n",
             "Universe: CSI All-Share ex-IPO<250d, 2023-01-03 → 2025-12-31, delay=1.\n",
             "Primary horizon h=10. Decision metric: monthly-rebalance Q5 long-only excess Sharpe.\n\n",
             "## Headline (h=10)\n\n",
             head[["alpha", "ic_mean", "ic_t", "ic_ir",
                   "ls_sr_daily", "q5e_sr_daily",
                   "ls_sr_monthly", "q5e_sr_monthly", "q5_size_mean"]].round(3).to_markdown(index=False),
             "\n\n## Per-year h=10 (daily LS / Q5 excess)\n\n",
             yearly.pivot(index="alpha", columns="year", values="ls_sr").round(2).to_markdown(),
             "\n\n## Audit floors\n\n",
             "| alpha | worst_year_LS | worst_year_Q5e | best_year_out_LS | residualized_LS_pct_of_raw |\n",
             "|---|---|---|---|---|\n"]
    for a in [f"alpha_{k:02d}" for k in range(1, 9)]:
        wy = floors.get(a) or {}
        b = byo.get(a) or {}
        r = res.get(a) or {}
        lines.append(
            f"| {a} | {wy.get('worst_year_ls')} | {wy.get('worst_year_q5e')} | "
            f"{b.get('best_year_out_sr')} | {r.get('ratio_resid_to_raw')} |\n")

    lines.append("\n\n## Decision per alpha\n\n")
    for a in [f"alpha_{k:02d}" for k in range(1, 9)]:
        wy = floors.get(a) or {}; b = byo.get(a) or {}; r = res.get(a) or {}
        passes = []
        wls = wy.get("worst_year_ls"); wq = wy.get("worst_year_q5e")
        passes.append(("worst_year_LS>=0.5", (wls is not None) and (wls >= 0.5)))
        passes.append(("worst_year_Q5e>=0.4", (wq is not None) and (wq >= 0.4)))
        ratio = (b.get("ratio_to_headline") if b else None)
        passes.append(("best_year_out>=50%", (ratio is not None) and (ratio >= 0.5)))
        rratio = (r.get("ratio_resid_to_raw") if r else None)
        passes.append(("residualized>=50%", (rratio is not None) and (rratio >= 0.5)))
        all_pass = all(v for _, v in passes)
        decision = "PROMOTE_CANDIDATE" if all_pass else "RESEARCH_ONLY"
        lines.append(f"### {a} → **{decision}**\n\n")
        for k, v in passes: lines.append(f"- {'✓' if v else '✗'} {k}\n")
        lines.append("\n")

    (OUT / "alpha_ranking.md").write_text("".join(lines))
    print("wrote alpha_ranking.md")

    # final summary
    fs = ["# Final summary — A-share DTL inst-flow (round 1)\n\n",
          "## What ran\n\n",
          "- Window: 2023-01-03 → 2025-12-31 (3 trading years, daily).\n",
          "- Universe: A-share ex-IPO<250d, industry-tagged.\n",
          "- 8 expressions per `expressions_batch_0001.md`.\n",
          "- delay=1 enforced via fwd_ret = adj_close.shift(-(1+h))/adj_close.shift(-1) - 1.\n\n",
          "## Top 3 by monthly Q5 excess Sharpe\n\n",
          head.head(3)[["alpha", "ic_mean", "ic_ir",
                        "q5e_sr_monthly", "ls_sr_monthly", "q5_size_mean"]].round(3).to_markdown(index=False),
          "\n\n## Lookahead grep findings\n\n",
          "```\n" + ("\n".join(audits["lookahead_grep_findings"]) or "(clean)") + "\n```\n\n",
          "## Caveats\n\n",
          "- 3y window is short; worst-year/best-year-out audits are noisy.\n",
          "- DTL is event-sparse: Q5 small per day; monthly rebalance preferred.\n",
          "- Hot-money seat keyword list is partial; alpha_07 results are indicative.\n",
          "- Industry neutralization done via stock_basic.industry (~110 groups, free-tier).\n"]
    (OUT / "final_summary.md").write_text("".join(fs))
    print("wrote final_summary.md")


if __name__ == "__main__":
    main()
