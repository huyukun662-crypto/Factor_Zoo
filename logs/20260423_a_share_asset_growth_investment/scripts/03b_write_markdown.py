"""Rewrite backtest_results_batch_0001.md using plain-text tables (no tabulate)."""
import json
import pandas as pd

OUT = "/home/user/Factor_Zoo/logs/20260423_a_share_asset_growth_investment/outputs"
ic = pd.read_csv(f"{OUT}/ic_table_batch_0001.csv")
su = pd.read_csv(f"{OUT}/ls_summary_batch_0001.csv")
an = pd.read_csv(f"{OUT}/ls_annual_batch_0001.csv")
audit = json.load(open(f"{OUT}/audit_execution_delay.json"))

def df_pipe_table(df, float_fmt=".4f"):
    s = df.to_string(float_format=lambda x: f"{x:{float_fmt}}")
    return "```\n" + s + "\n```"

lines = []
lines.append("# Backtest Results — Batch 0001\n")
lines.append("Session: 20260423_a_share_asset_growth_investment")
lines.append("Agent: 4 Backtest Operator")
lines.append("Rebalance: monthly (21 trading days); Cost: 5 bps/side; Delay: 1")
lines.append("Panel: 2020-01-02 .. 2025-04-18 (inherited from accruals session)\n")

lines.append("## Execution-delay audit")
lines.append(f"- invariant: {audit['invariant']}")
lines.append(f"- future-perturbation test: **{audit['future_perturbation_test']}**")
lines.append(f"- last-day fwd_ret_1 NaN share: {audit['last_day_fwd_ret_nan_share']:.2f} (expected high — can't observe t+1 close)")
lines.append(f"- panel inherited from: {audit['inherited_panel_from']}\n")

lines.append("## IC by horizon (Spearman rank-IC, full sample)\n")
pv = ic.pivot(index="factor", columns="horizon", values="ic_mean").round(4)
lines.append(df_pipe_table(pv))
lines.append("")
lines.append("### IC t-stat (full sample)\n")
pv2 = ic.pivot(index="factor", columns="horizon", values="ic_tstat").round(2)
lines.append(df_pipe_table(pv2, ".2f"))
lines.append("")

lines.append("## LS + Q5 long-only (monthly rebal, after 5 bps/side)\n")
cols = ["factor","sharpe_ls","ann_ret_ls","sharpe_q5_excess","ann_ret_q5_excess",
        "worst_year_sharpe_ls","worst_year_sharpe_q5_excess","n_years"]
lines.append(df_pipe_table(su[cols].round(3), ".3f"))
lines.append("")

lines.append("## Annual LS Sharpe\n")
pv3 = an.pivot(index="factor", columns="year", values="sharpe_ls").round(2)
lines.append(df_pipe_table(pv3, ".2f"))
lines.append("")

lines.append("## Annual Q5-excess Sharpe\n")
pv4 = an.pivot(index="factor", columns="year", values="sharpe_q5_excess").round(2)
lines.append(df_pipe_table(pv4, ".2f"))
lines.append("")

with open(f"{OUT}/backtest_results_batch_0001.md","w") as f:
    f.write("\n".join(lines))
print("written")
