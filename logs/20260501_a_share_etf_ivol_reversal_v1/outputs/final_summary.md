# Final Summary — IVOL-Reversal v1

Session: `20260501_a_share_etf_ivol_reversal_v1`
Branch: `claude/build-etf-factor-model-O6yXK`
Status: **STOP** original hypothesis | **RESEARCH-ONLY** open thread for inverted variant

## Headline finding

The Ang-Hodrick-Xing-Zhang IVOL anomaly does **not** hold on
A-share thematic ETFs (2019-2026, 30-ETF universe). The decile
ordering is inverted: high-IVOL ETFs (Q1 in our long-low convention)
earn ~24% ann return, low-IVOL ETFs (Q5) earn ~7%. The original
long-low-IVOL / short-high-IVOL portfolio loses ~18%/yr gross.

The **inverted variant** (long high-IVOL, short low-IVOL — i.e.,
IVOL-MOMENTUM not reversal) generates +0.66 LS Sharpe at monthly
rebalance with all 7 calendar years positive, but worst-year 2024
Sharpe = +0.04 misses the 0.5 floor → RESEARCH-ONLY.

## Mechanism economics

A-share thematic ETFs are *labeled narrative buckets*. Retail flow
chases the active narrative (新能源车 2020-21, 半导体 / 创新药 / AI in
2023-24). The ETFs that bear the narrative ARE the high-vol ETFs,
because they get the marginal retail bid AND the marginal selling
pressure on a daily basis. The lottery-preference channel that
PRODUCES the IVOL anomaly in stock-level US data is the same channel
that REVERSES it at the A-share ETF level — because at the ETF level
the lottery preference manifests as persistent narrative momentum,
not as overpriced expected returns.

This is the "ETFs are the narrative buckets" interpretation: the
classical IVOL anomaly works on stocks because high-IVOL stocks
inside a basket get squeezed out; at the basket level, the bucket
that contains the narrative IS the bucket that the basket
represents — there's no within-basket redistribution to harvest.

## Process notes

- **Round 1**: Declared primary horizon k=5 (weekly). G5 batch-level
  gate failed — all 8 expressions peaked IC at k=1, not k=5. Per
  workflow contract this is an Agent-2 issue; metadata revised in
  `session_metadata_round2.yml`.
- **Round 2**: Re-evaluated at k=1 daily rebalance. LS Sharpe still
  negative (-0.29 to -0.67) because the issue isn't horizon, it's
  decile non-monotonicity (G4 fail in retrospect — caught here, not
  by G4 because G4 only checks "≤1 inversion in deciles" which
  technically passed; the real diagnostic is the magnitude of Q1 vs Q5).
- **Sensitivity**: Sign-flipped run on f1 generated the inverted-IVOL
  result.

## Audits

| Audit | Result | Notes |
|---|---|---|
| Execution-delay invariant `target_shift == -(1+delay)` | PASS | Verified for k=1 (-2) and k=5 (-6). |
| Look-ahead (permute last-30d bench return, check past values bit-identical) | PASS | Max diff = 0.0 for dates < cutoff. |
| Worst-year floor (≥ 0.5) | FAIL | Both signs, all expressions. |
| Best-year-out floor (≥ 50% headline) | Borderline (inverted only) | 0.61 vs 0.66 → 92%, passes if you trust the headline. |
| Falsification-first | PASS | Pre-run answer: bull-market short-leg destruction. Confirmed: Q1 (high-IVOL short leg) earned +24.6% — the bull-market thesis was the correct falsifier. |

## Recommendation

1. STOP this session's hypothesis.
2. Open a new session `20260502_a_share_etf_ivol_momentum_v1` (out of
   scope for this branch) that:
   - Tests inverted IVOL with a regime gate (MA50 / broad-market trend
     filter) to rescue 2024.
   - Tests long-only top-3 instead of LS (A-share deployment is
     long-only enhancement, not LS — see CLAUDE.md A-share lessons).
   - Checks corr vs V7_gold momentum factor — if too high, no
     incremental signal.
3. Add the **inverted-IVOL** finding to the Factor Zoo
   `factors/price_volume/` index as a documented but not-yet-deployable
   factor.

## Cross-session note

This session ran in parallel with `20260501_a_share_etf_leadlag_v1`
on the same branch. The two are independent mechanisms; the LeadLag
session reaches a similar RESEARCH-ONLY / STOP verdict but for a
different reason (cost wall, not sign-flip).
