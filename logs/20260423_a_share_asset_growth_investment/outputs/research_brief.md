# Research Brief — A-share Asset Growth / Investment Anomaly

**Session**: 20260423_a_share_asset_growth_investment
**Agent**: 1 Research Librarian
**Date**: 2026-04-23

## Objective

Mine a robust A-share **fundamental** alpha. Accruals has already been covered (session 20260420); this batch commits to the **investment anomaly** family as the dominant economic mechanism.

## Candidate mechanisms surveyed

| # | Mechanism | Key paper | A-share fit | Data need | Orthogonal to accruals? |
|---|-----------|-----------|-------------|-----------|--------------------------|
| 1 | Asset Growth (AG) | Cooper-Gulen-Schill 2008 JF | **strong** — SOE capex cycle + SPO dilution | `total_assets` (have) | yes |
| 2 | Net Share Issuance (NSI) | Pontiff-Woodgate 2008; Daniel-Titman 2006 | strong — A-share IPO/SPO waves | `total_share` (have) | yes |
| 3 | ROA / profitability | Novy-Marx 2013; Fama-French 5F | moderate (state-owned distortion) | `n_income`, `total_assets` (have) | partly (ROA correlates with accruals sign) |
| 4 | OCF / assets (cash quality) | Sloan 1996 follow-ups | strong | `n_cashflow_act`, `total_assets` (have) | **correlated with accruals** |
| 5 | Sales growth | Lakonishok-Shleifer-Vishny 1994 | moderate | `revenue` (have) | yes |
| 6 | SUE / earnings surprise | Bernard-Thomas 1989 | strong but needs estimate data | need EPS estimates (not cached) | yes |

**Selected mechanism for batch 1: Asset Growth (AG)** — it is the cleanest single-signal investment anomaly, orthogonal to accruals, and all required data is cached.

## Why Asset Growth works (economic logic)

1. **q-theory** (Cochrane 1991, Li-Liu 2018): only firms with low expected returns (low cost of capital) invest heavily. Thus high-AG firms are negative-alpha ex ante.
2. **Managerial overinvestment** (Jensen 1986 free-cash-flow): growing firms overinvest in negative-NPV empire-building projects. Post-investment returns are low.
3. **Dilution channel** (Daniel-Titman 2006): part of AG comes from share issuance; the issuance channel alone explains ~50% of AG's return spread globally.
4. **Limits-to-arbitrage in A-share**: retail-dominated market under-reacts to slow fundamental signals like ΔTA/TA. 4-8 quarter drift typical.

## A-share specific concerns

- **PIT correctness**: use `f_ann_date` (first announcement), not `end_date`. Quarterly reports lag 1-3 months. Convention: data usable `f_ann_date + 1 trading day`.
- **SOE capex distortion**: state-owned enterprises have non-economic capex. Industry neutralization (SW L1, ~31 groups) is **mandatory** to isolate idiosyncratic AG.
- **ST / delisted**: exclude ST/*ST and tickers with less than 6 months history.
- **Small-cap noise**: AG on tiny firms (<5B total_mv) is dominated by M&A shocks. Filter or cap-weight.
- **IPO effect**: firms with less than 2 years listing history have mechanically high AG from IPO proceeds. Exclude or require 2+ years.
- **Survivorship**: use SW L1 map as-of date (historical industry assignment).

## Operator / construction suggestions

- Primary: `AG = -(TA_t - TA_{t-4q}) / TA_{t-4q}` — negate so high-AG → short → low signal, low-AG → long.
- PIT lag: shift by `(f_ann_date - end_date)` per row, then forward-fill to daily trading panel.
- Neutralization: subtract SW L1 industry median (cross-sectional, per date).
- Winsorize at 1%/99% by date to tame tails.
- Rank to N(0,1) via cross-sectional rank → inverse-normal.

## Data paths (Factor_Zoo/.cache/)

- `balancesheet.parquet` — `[ts_code, end_date, ann_date, f_ann_date, total_assets, accounts_receiv, inventories, accounts_pay, total_share]`
- `income.parquet` — `[ts_code, end_date, ann_date, f_ann_date, n_income, revenue]`
- `cashflow.parquet` — `[ts_code, end_date, ann_date, f_ann_date, n_cashflow_act, depr_fa_coga_dpba]`
- `daily.parquet` — `[ts_code, trade_date, open, close, vol, amount]` (2018-01-02 → 2026-04-22)
- `daily_basic.parquet` — `[ts_code, trade_date, total_mv, circ_mv]`
- `sw_l1_map.parquet` — `[ts_code, in_date, out_date, industry_code, industry_name]` (paid SW L1, 5823 stocks)

## Risks / caveats

1. AG is a **slow signal** — expected IC decay at horizon 1, peak at 60-120 trading days. Must evaluate monthly rebalance, not daily.
2. Correlation with size: small-cap firms structurally grow faster. Size neutralization may be needed on top of industry.
3. Correlation with low-volatility: high-AG firms also have high vol post-issuance. Adversarial residualization against vol required in Agent 5 audit.
4. 2020-2021 is a growth bull run — AG short-leg was destroyed (Pitfall 7). Must report per-year breakdown.
5. 2024-2025 contains policy-driven mergers (state-directed "reorganization"). AG signal could be inverted in H2 2024. Worst-year audit critical.

## Handoff to Agent 2

- Dominant mechanism: **Asset Growth (CGS 2008) with PIT-lagged quarterly total_assets**
- Universe: A-share main board + ChiNext + STAR, exclude ST/*ST, require >= 504 trading days listing history
- Horizon hypothesis: monthly rebalance (21-day), best IC at 20-60 day horizon
- Neutralization requirement: SW L1 industry demean is mandatory; size demean optional in later rounds
- Evaluation period: 2020-01 to 2026-04 (quarterly reports from 2018Q4 needed to form AG; first trading date 2020-01-01 after 4-quarter warmup + announcement lag)
- TVT split: Train 2020-2021, Validate 2022, Test 2023-2026-04 (see `references/tvt-split-template.md`)
