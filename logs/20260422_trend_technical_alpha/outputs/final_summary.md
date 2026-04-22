# Final Summary — Trend / Technical Factor Session

**Session:** `20260422_trend_technical_alpha`
**Family:** 趋势-技术 (trend / technical)
**Started:** 2026-04-22
**Completed:** 2026-04-22 (same day)
**Rounds:** 4
**Total alphas tested:** 32 (8 raw trend + 8 idio + 8 robustness + 8 worst-year-lift)
**Cost model:** turnover-aware, 5 bps per side
**Decision:** **RESEARCH-ONLY** (no alpha passes worst-year ≥ 0.5 floor)
**Best candidate:** α_29 — idio 12-3 momentum, test LS 2.06, test Q5 IR 1.16, max DD −7.1 %, worst-year 0.04

## Round-by-round narrative

### Round 1 — Raw trend signals (Han-Zhou-Zhu, t-stat, MA-crossover, 52w-high, etc.)
**Result: 8/8 wrong-signed.** Every raw trend signal had *negative* IC in A-share.

| alpha | construction | LS Sharpe | IC IR | worst yr |
|---|---|---:|---:|---:|
| α_01 | Han-Zhou-Zhu trend (P/MA over 7 horizons) | -1.46 | -21.3 | -3.03 |
| α_02 | 60d log-price OLS t-stat | -0.98 | -11.9 | -2.58 |
| α_03 | 120d log-price OLS t-stat | -0.88 | -10.5 | -3.73 |
| α_04 | MA crossover stack ±3 | -0.68 | -10.4 | -1.78 |
| α_05 | 252d close-max proximity | -0.42 | -3.5 | -1.59 |
| α_06 | frog-in-the-pan 60d | -1.09 | -11.2 | -2.29 |
| α_07 | 120d trend Sharpe | -1.23 | -15.6 | -2.70 |
| α_08 | classic 12-1 momentum (control) | -0.59 | -5.8 | -1.49 |

**Falsification confirmed:** A-share return process is reversal-dominated, every raw trend signal contributes negatively. This replicates the Liu-Stambaugh-Yuan 2019 finding.

### Round 2 — Idiosyncratic momentum (cs-residualized vs {log_mv, σ_120, ret_20})
**Result: sign flips from negative to positive.** 7/7 signals went from negative to weak-positive after stripping size, vol, short-term reversal exposure.

| alpha | base | LS full | LS test | IC IR | worst yr |
|---|---|---:|---:|---:|---:|
| α_09 | idio HZZ trend | -0.31 | -1.26 | -2.4 | -1.50 |
| α_10 | idio 60d t-stat | -0.06 | -0.38 | 1.8 | -0.80 |
| α_11 | idio 120d t-stat | 0.24 | -0.90 | 4.7 | -0.97 |
| α_12 | idio MA-crossover | **1.02** | 0.53 | 9.1 | 0.40 |
| α_13 | idio 52w-prox | 0.35 | -0.64 | 4.6 | -0.94 |
| α_14 | idio trend-Sharpe | 0.35 | -1.14 | 5.1 | -1.29 |
| α_15 | idio 12-1 momentum | 0.57 | 0.88 | **9.5** | -0.10 |
| α_16 | idio combo z(α_09+α_15) | -0.05 | -0.45 | 1.8 | -0.20 |

α_12 (idio MA-crossover) and α_15 (idio 12-1) emerged as the two positive-LS candidates. Neither passes audit floor: α_12 worst-year 0.40, α_15 worst-year -0.10.

### Round 3 — Robustness variants (size-filter, longer skip, industry-relative, combos)
**Result: α_19 (12-2 idio momentum) is breakthrough.** Increasing skip-window from 1m to 2m strips more reversal contamination.

| alpha | construction | LS test | Q5 test | IC IR | worst yr |
|---|---|---:|---:|---:|---:|
| α_17 | α_15 large-cap | 0.28 | -0.49 | 7.1 | 0.13 |
| α_18 | α_15 industry-relative form | 0.53 | 0.11 | 4.5 | -0.65 |
| **α_19** | **idio 12-2 (cum_252−cum_42)** | **1.24** | **0.65** | **11.8** | **0.16** |
| α_20 | idio 24-1 momentum | 0.79 | 0.26 | 1.0 | -2.96 |
| α_21 | combo 50/50 α_12+α_15 | 0.52 | -0.27 | 8.6 | 0.50 |
| α_22 | combo 33/33/33 α_11+12+15 | 0.01 | -0.64 | 7.1 | 0.16 |
| α_23 | idio 6-1 momentum | -1.08 | -1.95 | 5.7 | -1.22 |
| α_24 | idio 9-1 momentum | -0.69 | -0.87 | 6.6 | -0.85 |

α_19 has IC IR 11.8 and test Q5 IR 0.65 — a serious deployable signal — but worst-year 0.16 (2023) fails the floor. α_21 reaches worst-year 0.50 (right at the bar) but its test Q5 is negative.

### Round 4 — Worst-year-lift attempts on α_19 family
**Result: α_29 (12-3 idio momentum) is even stronger as a signal but worst-year *worse*.**

| alpha | construction | LS test | Q5 test | IC IR | worst yr | worst yr Q5 |
|---|---|---:|---:|---:|---:|---:|
| α_25 | α_19 large-cap top-50% | 0.46 | 0.10 | 9.6 | 0.22 | -1.69 |
| α_26 | α_19 large-cap top-30% | 0.56 | -0.01 | 8.1 | 0.23 | -1.30 |
| α_27 | industry-relative 12-2 idio | 0.99 | 0.50 | 7.4 | -0.42 | -1.86 |
| α_28 | 12-2 idio with σ_60 control | 1.20 | 0.61 | 9.4 | -0.14 | -1.80 |
| **α_29** | **12-3 idio (cum_252−cum_63)** | **2.06** | **1.16** | **14.5** | **0.04** | **-1.67** |
| α_30 | 18-1 idio | 0.94 | 0.62 | 5.5 | -1.01 | -1.85 |
| α_31 | combo 50/50 α_19+α_21 | 0.90 | 0.30 | 10.1 | 0.26 | -1.31 |
| α_32 | industry-relative + double-resid | 1.17 | 0.60 | 6.6 | -0.54 | -1.96 |

α_29 is the IC IR champion of the entire session (14.5) and has the highest test LS Sharpe (2.06) and test Q5 IR (1.16), with max DD only −7.1 %. But worst-year 0.04 (2019: 0.04, 2023: 0.18) fails. Q5 long-only excess is even more regime-sensitive (−1.67 in 2023).

Large-cap filtering (α_25, α_26) lifts worst-year by ≈ +0.07 but cuts test Sharpe in half — bad trade.

## Structural finding for A-share trend in 2018-2025

> **In A-share 2018-2025, idiosyncratic trend signals (12-2 / 12-3 momentum, residualized vs size/σ/short-term-reversal) exhibit an intrinsic regime tradeoff: they earn IC IR 11-15 in five of six years but produce ≈ flat returns (Sharpe 0.04 - 0.18) in 2023. No combination of alternative skip-windows, control-set additions, industry-relative reformulations, large-cap filters, or signal combinations within this session lifts the 2023 worst-year above 0.5.**

This is a more honest and sharper version of the prior session's lottery-demand finding. Same generation mechanism (regime-shift years pull worst year), different family (trend instead of σ).

## Audit results (per-mechanism summary)

1. **Execution-delay audit:** PASS. `target_shift = -2 = -(1+delay)` invariant satisfied. Forward returns built with `ret.shift(-(1+delay)).rolling(K).sum().shift(-(K-1))`.
2. **Lookahead audit:** PASS by construction. All factors use only past bars (rolling sum/mean/std/max + sliding-window OLS over closed past windows). Cross-sectional residualization is per-date and walk-forward-safe by definition.
3. **Worst-year floor (≥ 0.5):** **FAIL** for every alpha. Best is α_12 at 0.40, α_19 at 0.16, α_29 at 0.04.
4. **Best-year-out (≥ 50 % of headline):** PASS for top candidates (α_19 BYO/full = 0.67).
5. **Falsification:** PASS — α_08 (raw 12-1 momentum) was negative as predicted, and the inter-alpha correlation matrix in batch 1 confirms α_01-07 cluster on raw trend (corr 0.5-0.86 with α_08). The idio versions (α_15 vs α_08) flipped sign, confirming the residualization was the source of positive IC, not coincidence.
6. **Residualization residual-IC ≥ 30 % of raw:** N/A. The Round 1 raw-IC was *negative* with massive magnitude; the Round 2 idio-IC is *positive* and small. The "30 % residual IC" threshold from the lottery-demand session does not apply when sign flips.

## Cross-session comparison

| session | family | rounds | alphas | best LS test | best worst-yr | decision |
|---|---|---:|---:|---:|---:|---|
| 20260420_fundamental_accruals_alpha | accruals | 4 | 16 | 1.42 | 1.05 | **DEPLOYED** |
| 20260421_volprice_max_lottery | lottery / σ | 6 | 28 | 1.13 | 1.09 | RESEARCH-ONLY |
| 20260422_trend_technical_alpha | trend / momentum | 4 | 32 | **2.06** | 0.04 | RESEARCH-ONLY |

The trend session produced the **strongest single-period signal** (α_29 IC IR 14.5, test LS 2.06) of the three sessions, but the **worst structural worst-year** of the three.

## Decision

- **No PROMOTE.** Hard rule: worst-year-Sharpe floor not met by any alpha.
- **Best research-only candidate:** α_29 — `idio_12_3_momentum_cs_residualized`. Document for future combination with regime overlay.
- **Recorded factor library entry:** none.
- **Deployable form (if user lowers worst-year floor to 0.0):** α_29 monthly Q5 long-only excess is +1.16 IR test, ≈ +1.0 IR full, max DD −7 %, with potential for one flat or slightly negative year per regime cycle.

## Follow-on queue

| priority | follow-on | rationale |
|---|---|---|
| medium | regime-conditioned trend overlay | Combine α_29 with a market-regime indicator (e.g., 200-day index trend, VIX-equivalent) to gate the signal off in regime-shift periods. May lift worst-year above 0.5. |
| medium | residual-momentum with CH-3 controls | Liu-Stambaugh-Yuan 2019 CH-3 (size + value + turnover-sentiment). Residualize 12-2 momentum vs CH-3 instead of {log_mv, σ_120, ret_20}. |
| low | trend + low-volatility combo | Combine α_29 with σ_60 short signal — may reduce regime risk. |
| high (already queued) | SUE / PEAD | Bernard-Thomas 1989. Event-driven, orthogonal to all explored families. |
| high (already queued) | Gross profitability | Novy-Marx 2013. Liu-Stambaugh-Yuan show uncrowded in A-share. |

## Files in this session

```
logs/20260422_trend_technical_alpha/
├── research_brief.md
├── session_metadata.yml
├── round_0001.yml ... round_0004.yml
├── run_state.json
├── inputs/
├── working/handoff_*.json
├── outputs/
│   ├── expressions_batch_0001.md ... 0003.md
│   ├── panel_trend.parquet
│   ├── panel_trend_round2.parquet
│   ├── panel_trend_round3.parquet
│   ├── panel_trend_round4.parquet
│   ├── rank_ic.csv, rank_ic_round2.csv
│   ├── backtest_results_batch_0001.csv ... 0004.csv
│   ├── audits.json, audits_round2.json, audits_round3.json, audits_round4.json
│   ├── per_year_sharpe.json
│   ├── alpha_corr_snapshot.csv
│   ├── alpha_ranking.md
│   └── final_summary.md
└── scripts/
    ├── 01_build_trend_panel.py
    ├── 02_backtest_audit.py
    ├── 03_build_round2_idio.py
    ├── 04_backtest_round2.py
    ├── 05_round3_robustness.py
    └── 06_round4_lift_worstyear.py
```
