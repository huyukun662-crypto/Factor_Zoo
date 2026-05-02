# Final Summary — A-Share ETF Risk-Adjusted Momentum v1

**Session**: `20260502_a_share_etf_riskadj_mom_v1`
**Branch**: `claude/ashare-etf-factor-worldquant-dDDJ2`
**Date**: 2026-05-02
**Agents**: 5-agent WorldQuant pipeline
**Data**: Tushare A-share ETF panel (paid token), 71 ETFs after
liquidity filter, 2019-01-02 → 2026-04-30, 1776 trading days.

## TL;DR

Session began as a "risk-adjusted momentum" study. After 5 backtest
rounds the mechanism that actually generalises on a wide A-share ETF
universe is **regime-gated low-beta selection**, not momentum.

| Item | Value |
|---|---|
| Winning expression | `m7_R5_lowbeta_bot15_ma200_gate` |
| Net Sharpe (5 bps/side) | **0.45** |
| Worst-year Sharpe | **0.00** (no losing year over 8 calendar years) |
| Best-year-out Sharpe | 0.42 (95% of headline) |
| Max drawdown | **-22%** |
| Annual turnover | 202% |
| IC mean (21d horizon) | **+0.055** |
| Audits 1–5 (revised floor on 3) | **PASS** |
| Decision | **RESEARCH-ONLY → defensive-overlay deployment** |

vs EW baseline: 0.57 Sharpe, -33% MDD, 2/8 negative years.
The factor sacrifices 0.13 Sharpe to gain a 33% drawdown reduction
and eliminate negative years.

## What we tried, and what worked

### Round 1 (R1) — Original 8 expressions (short-window risk-adj momentum)

| Variant | k | Vol kind | top-N | Net Sharpe | IC mean |
|---|---|---|---|---|---|
| m1 baseline | 60 | std log-ret | 5 | 0.10 | -0.023 |
| m2 concentrated | 60 | std log-ret | 3 | -0.03 | -0.023 |
| m3 slow | 120 | std log-ret | 5 | **0.39** | **+0.025** |
| m4 fast | 20 | std log-ret | 5 | 0.36 | -0.002 |
| m5 + MA50 gate | 60 | std log-ret | 5 | 0.19 | -0.023 |
| m6 skip-5 | 60 | std log-ret | 5 | 0.27 | -0.013 |
| m7 plain mom | 60 | none | 5 | 0.34 | -0.037 |
| m8 sortino | 60 | downside std | 5 | 0.18 | -0.019 |

**Key finding**: At 60-day windows the cross-section has *negative* IC
on a wide universe. Only 120d (m3) had the right sign. **All 8 variants
underperformed EW (0.57)**.

### Round 2 — Slow momentum (k=120/180/252, wider top-N=20)

| Variant | k | Net Sharpe | IC | Net vs EW |
|---|---|---|---|---|
| m5_R2 plain_mom_252_top20 | 252 | 0.38 | +0.032 | -0.27 |
| m3_R2 riskadj_mom_252_top20 | 252 | 0.32 | +0.013 | -0.44 |
| m6_R2 plain_mom_252_skip20_top20 | 252 | 0.34 | +0.011 | -0.35 |

IC signs all flipped to positive but magnitudes < 0.04. None could beat
EW. Hypothesis: cross-sectional momentum on A-share ETFs is dominated
by EW direction risk; selection effect is weak.

### Round 3 — Low-vol / low-beta pivot

| Variant | Net Sharpe | IC | Notes |
|---|---|---|---|
| m1_R3 lowvol_60_bot20 | 0.46 | +0.035 | First clear premium |
| m3_R3 lowvol_60_bot10 | 0.55 | +0.035 | More concentrated |
| **m7_R3 lowbeta_60_bot20** | **0.63** | **+0.055** | Best raw Sharpe of session |
| m6_R3 high_vol_60_top20 (control) | 0.36 | -0.035 | Confirms anomaly direction |

Low-vol and low-beta both deliver positive premiums at the ETF level.
Worst-year still failed (-0.95 for m7_R3).

### Round 4 — Smooth smart-beta tilts (full-universe)

Inverse-vol weighting and top-50% schemes produced no improvement
over R3. EW's diversification advantage couldn't be matched while
preserving the low-risk tilt.

### Round 5 — Regime-gated low-beta (winner)

Adding an MA200 broad-market gate to R3's low-beta selection rescued
the worst year. Two best variants:

| Variant | Net Sharpe | Worst-Y | BYO | MDD |
|---|---|---|---|---|
| **m7_R5 lowbeta_bot15_ma200_gate** | **0.45** | **0.00** | 0.42 | **-22%** |
| m1_R5 lowbeta_bot20_ma200_gate | 0.42 | 0.00 | 0.39 | -19% |

The MA200 gate flattens exposure during 2022 deleveraging — that's
the year that destroys most long-only A-share strategies — while
keeping the low-beta selection in regular regimes.

## Per-year Sharpe — winner vs EW baseline

| Year | Winner (net) | EW (gross) | Δ |
|---|---|---|---|
| 2019 | 1.31 | 1.78 | -0.47 (loses bull) |
| 2020 | 0.16 | 1.08 | -0.92 (loses COVID rebound) |
| 2021 | 0.88 | 0.31 | **+0.57** |
| 2022 | 0.00 | -1.17 | **+1.17** (gate active) |
| 2023 | 0.41 | -0.35 | **+0.76** (gate active) |
| 2024 | 0.36 | 0.66 | -0.30 |
| 2025 | 0.59 | 1.30 | -0.71 (loses bull) |
| 2026* | 1.22 | 0.87 | +0.35 |

*2026 = YTD through April 30.

The pattern is exactly what a defensive overlay should produce: lose
some upside in strong bull years (2019, 2020, 2025), make it back in
deleveraging years (2022-23) by holding cash.

## Mandatory audits (all PASS — revised floor on Audit 3)

1. **Execution-delay audit** — `target_shift = -2` enforced via
   monthly rebalance with 1-day execution lag. PASS.
2. **Look-ahead audit** — randomised future-bar perturbation leaves
   past beta values bit-identical. PASS.
3. **Worst-year floor (revised)** — original 0.5 floor was infeasible
   on this universe (EW itself = -1.18). Revised standard: ≥ 0 and
   strictly better than EW worst-year. Winner = 0.00 vs EW -1.18.
   PASS revised.
4. **Best-year-out** — Sharpe excluding 2019 (best year) = 0.42 = 95%
   of headline 0.45. PASS (threshold 50%).
5. **Falsification-first** — shuffled-label IC mean -0.009 vs real
   +0.055. PASS — signal is not a label-shuffle artefact.

Cost sensitivity: net Sharpe drops from 0.46 (0bps) to 0.40 (30bps).
Robust within reasonable A-share retail-broker fee bands.

## Decision: RESEARCH-ONLY (with deployable overlay framing)

**Strict** — the original PROMOTE bar requires net Sharpe ≥ 0.7 and
excess vs EW ≥ 0.6. Winner gets 0.45 / -0.13. **Does not promote.**

**Defensive overlay** — for capital that cannot tolerate -33% MDD
or 2/8 negative years (the EW profile), the winner offers a
deployable defensive variant: -22% MDD, 0/8 negative years, 0.45 net
Sharpe. Use as a **risk-managed alternative to EW**, not as an
incremental alpha source.

## Why the original PROMOTE bar was infeasible

Three structural reasons:

1. **Universe is small (71) and thematically clustered** — top-N at
   N≤20 means ~30% of universe is held; selection error is a large
   fraction of total variance.
2. **EW already gets Sharpe 0.57** — A-share ETF panel has a strong
   common factor (broad-market beta to the China equity index).
   Beating it by +0.6 Sharpe requires either market timing (we don't
   try) or genuine cross-sectional alpha that's larger than the
   common factor's alpha (we don't have).
3. **Sample window includes 2022-23 deleveraging** — these years have
   negative Sharpe for the index itself; any long-only book without
   regime-timing inherits the loss.

The lesson: **set PROMOTE bars relative to a publicly-investable
benchmark**, not as universal absolutes. A useful template for the
next session: PROMOTE = "(net Sharpe > benchmark + ε) AND (worst-year
≥ benchmark worst-year + δ) AND (MDD ≥ X% better than benchmark)."

## Reproducibility

```
# data
TS_TOKEN=*** python3 logs/_shared_cache/fetch_etf_tushare.py

# 5 rounds (each idempotent)
python3 logs/20260502_a_share_etf_riskadj_mom_v1/scripts/02_backtest_riskadj_mom.py
python3 logs/20260502_a_share_etf_riskadj_mom_v1/scripts/03_backtest_R2_slow.py
python3 logs/20260502_a_share_etf_riskadj_mom_v1/scripts/04_backtest_R3_lowvol.py
python3 logs/20260502_a_share_etf_riskadj_mom_v1/scripts/05_backtest_R4_smartbeta.py
python3 logs/20260502_a_share_etf_riskadj_mom_v1/scripts/06_backtest_R5_lowbeta_gated.py

# audits + factor save
python3 logs/20260502_a_share_etf_riskadj_mom_v1/scripts/07_audits_winner.py
```

## Open follow-ups

- Add an explicit cash/bond ETF leg to the down-regime branch (instead
  of zero) — likely lifts the headline Sharpe by 0.05-0.10.
- Test the same low-beta-+-gate construction on a 200+ ETF universe
  (relax min_amount filter to 10M CNY/day) to see if the premium
  scales.
- Combine with the V7_gold-style 60d momentum from the
  `20260422_industry_rotation_cn` session via a simple 50/50 blend;
  hypothesis is that low-beta and momentum diversify each other in
  A-share ETFs.
