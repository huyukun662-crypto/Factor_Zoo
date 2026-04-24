# Research Brief — A-share ETF Reversal v2

**Agent 1 (Research Librarian) output**
**Session:** `20260424_a_share_etf_reversal_v2`
**Date:** 2026-04-24

## Summary

Reversal / dip-buy alpha family on A-share thematic ETFs. Prior 18-ETF
session localized the reversal payoff to a narrow ~60d window; this session
extends to the 34-ETF V7_gold universe to test whether thicker cross-section
sharpens the signal, scan the 5d → 80d transition band, and evaluate
long-only variants to sidestep the 2020 short-leg worst-year failure.

## Academic / practitioner lineage (3-sentence version)

- **De Bondt-Thaler (1985)** — 3-5-year winner/loser reversal, equity-level. Does not survive on A-share ETFs (prior session: k=120/250 had momentum-sign IC).
- **Jegadeesh (1990)**; **Lehmann (1990)** — 1-week reversal on US stocks. Does not survive on A-share ETFs (prior session: k=10 weekly had 7/8 negative IC).
- **Nagel (2012) vol-scaled reversal** — divides short-term return by volatility. Prior session's `r1_vol_scaled_rev5` also failed at k=10. Retained here only as a control; not re-tested as a headline expression.
- **A-share specific** — reversal payoff localizes at **~60 trading days** (Chen-Chen-Cao 2019 style residual reversal after trend control also fits here). This is the zone to attack.

## Prior-session evidence base (the one input that matters most)

From `logs/20260423_a_share_etf_reversal_v1/outputs/`:

| Horizon | IC sign | G4 pass? | Interpretation |
|---|---|---|---|
| k=10 (weekly) | 7/8 negative | 0/8 | Momentum zone |
| k=20 (monthly-short) | mixed | 1/8 | Transition, very noisy |
| k=60 (monthly) | positive, t=+2.35 | 2/8 | **Reversal sweet spot** |
| k=120 (6-month) | negative | 0/8 | Back to momentum |
| k=250 (1-year) | negative | 0/8 | Long-horizon momentum |

Best Round 2 candidate: `r2_lt_rev_60d` — Net Sharpe @5bps = +0.56,
ICIR = +0.99, Q5-Q1 monotonic, turnover 1363% annual. Blocker: 2020 Sharpe
= −0.68 from short leg (COVID momentum regime where consumer / healthcare
winners stayed winners).

## Open questions this session should answer

1. **Does extending universe 18 → 34 lift the 60d signal's IC and worst-year?**
   Hypothesis: modestly yes — more cross-section = better ranking = more diversified short leg.
2. **Is there a sharper sub-horizon inside [40, 60, 80]?**
   Hypothesis: k=60 is robust but k=40 or k=80 may be equal or better on extended universe.
3. **Does long-only top-3 (instead of LS top-4/bot-4) pass the worst-year ≥ 0.5 floor?**
   Hypothesis: likely yes for k=60, because the long leg earned +11% over the study period while short leg earned −11% (prior session attribution).
4. **Does a drawdown-event trigger (dd60 > 15%) with recovery confirmation (5d ret > 0) produce a higher-conviction but lower-frequency signal with better worst-year?**
   Hypothesis: untested. Potentially yes, but turnover-sensitivity will matter.
5. **Does signal-level fusion into V7_gold (residual after V7 Leg A mom4/turn4) add 0.05-0.10 net Sharpe?**
   Hypothesis: weakly yes — reversal is orthogonal to V7's momentum chassis. But R2 D2 fusion on volume-breakout signal was flat, so this is speculative.

## Universe

34 thematic A-share ETFs. Loaded from
`logs/20260422_industry_rotation_cn/outputs/etf_daily.parquet`. Range
2015-01-05 → 2026-04-22. Many ETFs start mid-2021 (see `etf_universe`
summary inside session_metadata.yml). Common window with ≥ 10 live ETFs is
~2019-01-04 onward (aligns with V7 baseline).

## Concerns (pre-registered)

- **Universe-size gain may be marginal.** 18 → 34 doubles cross-section but
  most new ETFs start post-2021; on the 2020 critical year, cross-section is
  still thin (~20 live).
- **Sample-size risk for drawdown triggers.** A dd60 > 15% trigger may fire
  fewer than 500 obs on this panel; the confidence interval on its IC will
  be wide. Report bootstrap CI on IC for drawdown signals.
- **Baseline re-anchoring.** V7_gold weekly baseline will be pulled from the
  prior session's `d2_v7_pnl_series.csv`; do not rebuild from scratch.

## Recommended batch structure (Agent 2 input)

Exactly 8 expressions, split:

- **2 short (falsification probes)**: `r1_rev_1d`, `r1_rev_5d`
- **4 medium horizon scan**: `r1_rev_20d`, `r1_rev_40d`, `r1_rev_60d`, `r1_rev_80d`
- **2 drawdown event-type**: `r1_dd60_raw`, `r1_dd60_recover`

All expressions are **high-signal = long** (dips positive). All are
universe-EW demeaned per date before ranking. Short and drawdown variants
are also tested as **long-only top-3** strategy in Agent 4.

## Hand-off to Agent 2

Next agent should:
1. Confirm sample window (earliest date with ≥ 10 live symbols).
2. Specify k-horizons (5 / 20 / 60 / 60) and hold periods (1w / 4w / 4w / 4w).
3. Spec strategy wrappers: LS top-4/bot-4 weekly + monthly; long-only top-3 weekly + monthly.
4. Register G1 non-degeneracy threshold (> 1% of obs have non-zero signal).
