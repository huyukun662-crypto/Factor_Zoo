# Expressions Batch 0004 — Deployment-Robustness Round

**Session:** 20260420_fundamental_accruals_alpha
**Agent:** 3 Alpha Builder
**Batch:** 0004  (Round 4 — signal smoothing, turnover control, regime blending)

**Motivation from Round 3 test-set diagnosis**
- The Round 3 cost model applied a flat 20 bps / rebalance regardless of turnover, **over-stating cost by ~10×** relative to the factor's actual ~10 % turnover. Round 4 corrects this (see `backtest_results_batch_0004.md § 1`).
- Test-set diagnostic hinted that `ind × size` beat `ind-only` in 2024-2025 (regime non-stationarity); v5 explicitly tests a blend.
- Fundamental signals update quarterly; daily/monthly cadence of the rebalance wastes potentially turnover. EMA / sticky / bimonthly test whether smoothing adds robustness.

**Mechanism preserved:** median-TTM industry-neutral Sloan CFS accruals (= `alpha_med_ind`). All 8 variants are post-processing of this single signal.

| # | Variant | Construction |
|---|---------|--------------|
| 1 | baseline       | `alpha_med_ind` (reference) |
| 2 | ema20          | per-stock EMA of alpha_med_ind, span 20 |
| 3 | ema60          | per-stock EMA, span 60 |
| 4 | ema120         | per-stock EMA, span 120 (quarterly rhythm) |
| 5 | consensus_ind  | 0.5 × alpha_med_ind + 0.5 × alpha_med_indxsize |
| 6 | sticky_10pct   | baseline signal, but carry prior Q if \|Δrank\| ≤ 0.10 |
| 7 | bimonthly      | baseline signal, rebalance every 40 trading days |
| 8 | horizon_blend  | 0.5 × alpha(t) + 0.5 × alpha(t − 20) |

Rule of 8 and one-mechanism satisfied. Cost model upgraded to turnover-aware: per-rebalance cost = 10 bps × (tov_q5 + tov_q1). Sharpe annualization: 12 × sqrt for monthly, 6 × sqrt for bi-monthly (v7 adjusted after the fact).
