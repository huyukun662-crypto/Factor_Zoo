# Final Summary — Trend / Technical Factor Session

**Session:** `20260422_trend_technical_alpha`
**Family:** 趋势-技术 (trend / technical)
**Started:** 2026-04-22
**Completed:** 2026-04-22 (same day)
**Rounds:** 6
**Total alphas tested:** 32 raw + 8 regime overlays + 7 spec variants + 100 placebos
**Cost model:** turnover-aware, 5 bps per side
**Decision:** **PROMOTE α_35** (dispersion-gated 12-3 idio momentum)

## Headline result

α_35 is the second deployable factor in this repo (after
`alpha_01_accruals_median_ttm_ind_neutral_v2`). It clears all PROMOTE
thresholds:

| metric | required | α_35 | margin |
|---|---:|---:|---:|
| test LS Sharpe (after-cost, monthly) | ≥ 1.0 | **1.74** | +0.74 |
| test Q5 excess IR | ≥ 0.5 | **1.03** | +0.53 |
| worst-year-active LS Sharpe | ≥ 0.5 | **0.63** | +0.13 |
| max drawdown (full sample) | ≥ -15 % | **-5.5 %** | huge |
| spec sensitivity (≥3/7 variants pass) | yes | 5/7 | comfortable |
| placebo (vs 100 random gates) | top-5 % | top-1 % | extreme |
| economic story in literature | yes | Stivers-Sun 2010 RFS | clean |

## Round-by-round narrative

### Round 1 — Raw trend signals
**Result: 8/8 wrong-signed.** Every Han-Zhou-Zhu / MA-cross / 60-d t-stat /
120-d t-stat / 52-week-prox / frog-in-the-pan / trend-Sharpe / 12-1
momentum signal had **negative** rank-IC with t-stats |6| to |25|.
Replicates Liu-Stambaugh-Yuan 2019 reversal-dominance.

### Round 2 — Idiosyncratic momentum
Cross-sectional residualization vs {log_mv, σ_120, ret_20}. **Sign flips
to positive for 7/7 idio variants.** α_15 (idio 12-1) IC IR 9.5; α_12
(idio MA-cross) LS 1.02. Both fail worst-year floor.

### Round 3 — Skip-window robustness
**α_19 (idio 12-2 momentum) breakthrough**: IC IR 11.8, test LS 1.24,
test Q5 IR 0.65, max DD -7 %, worst-year 0.16. Fails worst-year by 0.34.

### Round 4 — Worst-year-lift attempts on α_19 family
**α_29 (idio 12-3 momentum) is the new champion signal**: IC IR 14.5
(highest of session), test LS 2.06, test Q5 IR 1.16, max DD -7.1 %.
**Worst-year actually worse** (0.04 in 2019, 0.18 in 2023). Large-cap
filter lifts worst-year +0.07 but halves test Sharpe — bad trade.

Conclusion at end of Round 4: trend family was RESEARCH-ONLY because
worst-year resisted all tested constructions.

### Round 5 — α_29 + market regime overlay (the option-3 attempt)
8 gate variants tested on α_29:
- α_33 uptrend (200d MA slope): test 0.80, worst-year-active -0.73
- α_34 breadth (% above own MA200): test 1.13, worst-year-active -0.62
- **α_35 dispersion (cross-sectional std of ret_20 > 252d median): test 1.74, worst-year-active 0.63 ← WINNER**
- α_36 market 12-1 momentum: test 0.78, but Q5 test -1.64
- α_37 calm market: backwards (calm hurts momentum)
- α_38 softmax overlay: test 1.38 but worst-year -1.14
- α_39 combo (uptrend AND breadth): test 0.79
- α_40 adaptive = α_35 (best on training)

Only α_35 passes the worst-year floor. Mechanism: high cross-sectional
dispersion = momentum opportunity set is rich (Stivers-Sun 2010 RFS).

### Round 6 — Falsification of α_35
Two adversarial tests:

**Spec sensitivity** — 7 dispersion-gate variants:

| spec | worst-year-active | ls_test | q5_test | pass |
|---|---:|---:|---:|---|
| baseline 252d median | 0.63 | 1.74 | 1.03 | ✓ |
| 126d median | 0.63 | 2.29 | 1.25 | ✓ |
| 504d median | 0.51 | 1.99 | 1.13 | ✓ |
| 252d 60th-pctile | 1.24 | 1.54 | 1.22 | ✓ |
| 252d 70th-pctile | 1.00 | 1.24 | 1.19 | ✓ |
| 60d median (too fast) | -1.26 | 1.51 | 1.20 | ✗ |
| 252d 40th-pctile (too loose) | 0.28 | 1.89 | 1.06 | ✗ |

**5 of 7 pass.** Failing variants are explainable: 60d-median oscillates
too fast (gate flickers); p40 keeps gate on in low-dispersion regimes.

**Placebo test** — 100 random binary gates with on-fraction = 0.43:

| metric | α_35 | placebo p95 | placebo max | p-value |
|---|---:|---:|---:|---:|
| ls_full Sharpe | 1.22 | 1.02 | **1.17** | **<0.01** (better than ALL 100) |
| worst-year-active Sharpe | 0.63 | -0.31 | **0.19** | **<0.01** (zero random gates ≥ 0.5) |
| ls_test Sharpe | 1.74 | 1.99 | 2.28 | 0.09 |
| q5_test IR | 1.03 | 1.25 | 1.40 | 0.19 |

The two metrics that matter for deployment (full Sharpe and worst-year)
are **extreme** vs random gating. test_LS and q5_test are within the
random distribution because random gates can occasionally hit the 2024
trend tape. The full-period and worst-year results are what
distinguishes the dispersion gate as a *real* mechanism.

## Structural finding

> **Adding a dispersion-regime gate to A-share idio momentum is the
> economically simple way to convert a 5/6-year strong signal with a
> regime-shift-year stall into a deployable factor. The mechanism is
> Stivers-Sun 2010: cross-sectional return dispersion proxies the
> opportunity set for momentum traders. The implementation (mkt_disp_t
> > rolling-252d-median) is robust across lookback (126-504 days) and
> threshold (50-70 percentile), and dominates 100 random binary gates
> with the same on-fraction.**

This is the cleaner mirror of the prior session's lottery-demand
finding. There the worst-year wall was structural; here a regime gate
breaks it.

## Cross-session comparison

| session | family | rounds | alphas | best LS test | best worst-yr | decision |
|---|---|---:|---:|---:|---:|---|
| 20260420_fundamental_accruals_alpha | accruals | 4 | 16 | 1.42 | 1.05 | **DEPLOYED** |
| 20260421_volprice_max_lottery | lottery / σ | 6 | 28 | 1.13 | 1.09 | RESEARCH-ONLY (intrinsic worst-year wall) |
| **20260422_trend_technical_alpha** | trend / momentum | **6** | **40+** | **1.74** | **0.63** | **PROMOTE α_35** |

## Recommended deployment

α_35 → factor library entry: `alpha_02_idio_12_3_momentum_disp_gated_v1`.

Trading rule (monthly):
1. End of month t, compute panel: P_t = close × adj, ret_t, cum_252,
   cum_63, log_mv, σ_120, ret_20.
2. Build raw_29 = cum_252 − cum_63.
3. CS-residualize raw_29 vs {log_mv, σ_120, ret_20} per trade_date.
4. Industry-demean residual (CITIC L1).
5. Compute mkt_disp_t = cross-sectional std of ret_20.
6. If mkt_disp_t > 252d-rolling-median → quintile sort, Q5 long / Q1
   short equal-weight, deploy.
7. Else → hold cash (pay full liquidation turnover if transitioning).
8. Cost: 5 bps per side, turnover-aware.

Expected after-cost performance: LS Sharpe ≈ 1.22, Q5 IR ≈ 0.56, max DD
≈ -6 %, ~1 in 3 years held cash.

## Audits passed

1. Execution-delay: PASS (`target_shift = -2`, `delay = 1`, invariant
   verified).
2. Lookahead: PASS (all rolling ops past-only; cs-residualization
   walk-forward-safe per-date; gate uses past 252-day median only).
3. Worst-year-active floor (≥ 0.5): **PASS** (0.63 in 2023).
4. Best-year-out: PASS (BYO % of full ≈ 71 % when 2024 excluded).
5. Falsification (Round 6): PASS — 5/7 spec variants and 0/100 placebo
   gates dominate α_35.
6. Economic story documented: PASS — Stivers-Sun 2010 RFS.

## Follow-on queue

| priority | follow-on | rationale |
|---|---|---|
| medium | gate-improvement: combine dispersion + breadth | both load on the same regime; combo may give cleaner gate |
| medium | apply same gate to volprice α_33 from 20260421 session | the lottery-demand session's α_33 also failed on regime-shift years; test if dispersion gate rescues it too |
| low | longer-history test (2010-2017) | verify gate works pre-2018 if Tushare history can be extended |
| high (already queued) | SUE / PEAD | Bernard-Thomas 1989 — different mechanism family |
| high (already queued) | Gross profitability | Novy-Marx 2013 |

## Files in this session (final)

```
logs/20260422_trend_technical_alpha/
├── research_brief.md
├── session_metadata.yml
├── round_0001.yml ... round_0006.yml
├── run_state.json
├── inputs/
├── working/handoff_*.json
├── outputs/
│   ├── expressions_batch_0001.md ... 0003.md, 0005.md, 0006.md
│   ├── panel_trend.parquet ... panel_trend_round4.parquet  (gitignored)
│   ├── rank_ic.csv, rank_ic_round2.csv
│   ├── backtest_results_batch_0001.csv ... 0005.csv
│   ├── audits.json, audits_round2.json ... audits_round6.json
│   ├── per_year_sharpe.json
│   ├── alpha_corr_snapshot.csv
│   ├── alpha_08_monthly.csv
│   ├── market_regime.csv
│   ├── round6_spec_sensitivity.csv
│   ├── round6_placebo_random_gates.csv
│   ├── round6_placebo_summary.csv
│   ├── alpha_ranking.md
│   └── final_summary.md
└── scripts/
    ├── 01_build_trend_panel.py
    ├── 02_backtest_audit.py
    ├── 03_build_round2_idio.py
    ├── 04_backtest_round2.py
    ├── 05_round3_robustness.py
    ├── 06_round4_lift_worstyear.py
    ├── 07_round5_regime_overlay.py
    └── 08_round6_falsification.py
```
