# Final summary (interim — Round 1, design-only)

## Status

This session ran Agents 1–3 of the worldquant-5-agent-workflow to design
an A-share **alternative-data** alpha factor batch around the Dragon-Tiger
List (龙虎榜). Agents 4–5 are **blocked on environment**:

- no `TUSHARE_TOKEN` in this runtime
- `pandas` / `numpy` / `pyarrow` / `tushare` not installed in this Python

Per `references/common-pitfalls.md` and `SKILL.md` mandatory audit rules,
**no PROMOTE recommendation is possible without executed audits**, so this
summary is research-only by construction. No backtest numbers are
fabricated in this folder.

## What was decided (design)

- **Mechanism family:** Dragon-Tiger List institutional-seat informed flow.
  Three sub-mechanisms (M3 net-buy ratio, M4 20d persistence, M2 hot-money
  reversal) plus one ensemble.
- **Primary horizon:** 10 trading days, with grid {1, 5, 10, 20}.
- **Execution delay:** 1 day, invariant `target_shift == -(1+delay)`.
- **Rebalance for decision:** monthly (per A-share lesson — daily
  rebalance on event-triggered factors typically fails the cost gate).
- **Neutralization:** industry demean + cap residualize, mandatory.
- **Universe:** CSI All-Share, ex-ST, ex-IPO < 250 trading days.
- **TVT split:** 2018-2019 / 2020 / 2021-2025.

## Pre-submission self-audit (Agent 3)

All 8 expressions:
- start with `lag(1)` on disclosed inputs (DTL is post-close disclosure)
- contain no `shift(-k)` of returns inside the factor
- use only past-or-same-day prices in any conditional mask (alpha_04)
- use a fixed hot-money-seat list (not data-derived)
- group cross-section ops by date

## Falsification-first hypothesis Agent 5 must test

> If positive Q5-excess Sharpe appears, the leading non-causal explanation
> is that DTL-trigger days cluster on ±10% limit-up days in momentum
> regimes, so the factor is a vehicle for the momentum factor.
> Falsification test: residualize each alpha against {size, 20d-mom,
> 5d-rev, MAX10} and require residualized LS Sharpe ≥ 50% of raw.

## Risks Agent 5 must explicitly check

1. **Q5 size floor.** DTL is event-triggered → most stocks have
   factor=0; daily Q5 may be tiny. Require Q5 size ≥ 30 on ≥ 95% of days.
2. **Limit-day co-occurrence (Pitfall 6).** Re-run alpha_02 vs.
   alpha_04 (which masks limit-up days) and report both worst-year
   numbers; if alpha_04 worst-year ≥ alpha_02 worst-year, prefer
   alpha_04 even at lower headline.
3. **Cost gate (Pitfall 10).** alpha_01 and alpha_07 are likely
   cost-unviable at daily; report only weekly+ for those.
4. **Hot-money seat staleness.** alpha_07 uses a fixed canonical list;
   if the researcher later adds branches based on post-2025 knowledge,
   redo Agent 5 with a forward-bias note.

## Next runtime checklist (hand back to Agent 4)

```
export TUSHARE_TOKEN=...
pip install tushare pandas pyarrow scipy statsmodels
cd logs/20260429_a_share_alt_dtl_inst_flow_opus47
python scripts/00_fetch_data.py
python scripts/00b_fetch_ohlcv.py
python scripts/01_build_panel.py
python scripts/02_compute_alphas.py
python scripts/03_backtest.py
python scripts/04_audits.py
```

Then resume the workflow at Stage 4 with the freshly-cached panel and
re-engage Agent 5 to produce `alpha_ranking.md`.
