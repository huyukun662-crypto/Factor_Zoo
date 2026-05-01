# Final Summary — Inverted IVOL Momentum v1

Session: `20260501_a_share_etf_ivol_momentum_v1`
Branch: `claude/build-etf-factor-model-O6yXK`
Status: **RESEARCH-ONLY** standalone | **PROMOTE candidate** as 50/50 V7_gold ensemble

## Headline finding

Inverted-IVOL (long high-IVOL A-share thematic ETFs at monthly
rebalance) is **research-grade as a standalone factor** (best
variant m1: gross +0.66 LS / net +0.63, all 7 years positive but
worst-year 2024 = +0.04 misses the 0.5 floor) but **becomes a
PROMOTE candidate when combined 50/50 with V7_gold** because the
two signals are nearly orthogonal (weekly correlation 0.05).

The 50/50 weekly ensemble delivers:

| Metric | Value | Floor | Pass |
|---|---:|---:|---|
| Weekly Sharpe (full window) | **2.18** | ≥ 1.0 | ✅ |
| Worst-year Sharpe | **0.83** (2022) | ≥ 0.5 | ✅ |
| Best-year-out / headline | 108% | ≥ 50% | ✅ |
| Years positive | 7 of 7 | — | ✅ |
| V7_gold weekly corr | 0.05 | ≤ 0.5 | ✅ |
| Lift vs V7_gold alone | +26% (1.73 → 2.18) | > 0 | ✅ |

## Open-thread answers (from parent session)

| Q | Result |
|---|---|
| Does MA50 gate rescue 2024? | **NO** — gate made 2024 WORSE in 3 of 4 variants. 2024 was a within-narrative collapse, not a broad-market drawdown. |
| Long-only top-N better than LS? | **NO** at this universe size — LS captures narrative-momentum on long leg AND defensive-underperformance on short leg. Long-only top-3 excess vs EW = +0.13 only. |
| Orthogonal to V7_gold? | **YES** — average |corr| = 0.080 across all 8 expressions. Inverted-IVOL is genuinely independent signal. |

## Mechanism economics — confirmed at the ensemble level

V7_gold is a *return-momentum* signal with explicit MA50 gate and
gold fallback. It handles regime risk well (2024 = +1.64 Sharpe
because the gate caught the deleveraging and the gold fallback
hedged).

Inverted-IVOL is a *vol-rank* signal capturing the lottery-bid
narrative-momentum specific to A-share thematic ETFs. It does NOT
have its own regime gate (every gate variant tested made things
worse).

The ensemble divides labor: V7 = regime-aware base, IVOL = orthogonal
alpha overlay. Their correlation 0.05 is structural — momentum-
magnitude (V7) and vol-rank (IVOL) are economically distinct
characteristics.

## Audits

| Audit | Result |
|---|---|
| Execution-delay (`target_shift = -21` for k=20) | PASS |
| Look-ahead (perturb last-30d bench return + close, check past values bit-identical for signal AND MA50/MA200 gates) | PASS — max diff = 0.0 |
| Worst-year floor standalone | FAIL (every variant) |
| Worst-year floor ensemble | PASS (0.83 in 2022) |
| Best-year-out (50/50 ensemble) | PASS (108%) |
| Falsification-first | PASS — pre-committed gate hypothesis was falsified by data; pre-committed orthogonality fallback delivered the result |
| V7 orthogonality | PASS for all 8 (max 0.10) |

## Recommendation

1. **Adopt the 50/50 weekly ensemble as a PROMOTE candidate.** Move
   to a paper-trading verification step on the 2024-2026 test window.
2. **Document inverted-IVOL standalone** in
   `factors/price_volume/ivol_inverted_etf/` as a researched factor
   with `deployable_when=ensembled_with_v7_gold` flag.
3. **Test ensemble weight sensitivity** (30/70, 70/30) and
   alternative V7 family members (V7_gb_70_30, V7_gb_50_50) to
   ensure robustness.
4. **Close** the inverted-IVOL standalone research thread on this
   branch — the meaningful answer (ensemble) is found.

## Cross-session note

This session is the natural continuation of
`logs/20260501_a_share_etf_ivol_reversal_v1` after the user
instruction "sessionA 继续研究". The parent session falsified the
classical IVOL-reversal hypothesis and identified inverted-IVOL as
the open thread; this session pursued the three open questions
(regime gate, top-N, V7 orthogonality) and delivered a deployable
ensemble.

The sibling session `logs/20260501_a_share_etf_leadlag_v1` remains
RESEARCH-ONLY per user instruction "sessionB 先 research only" — no
further work attempted.
