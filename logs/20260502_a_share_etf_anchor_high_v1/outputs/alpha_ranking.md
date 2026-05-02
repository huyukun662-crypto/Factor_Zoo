# Alpha Ranking — batch_0001

Session: 20260502_a_share_etf_anchor_high_v1
Universe: 32 A-share ETFs | k=20 monthly rebal | delay=1 | 5 bps/side

## Ranking (best → worst)

| Rank | id  | label              | LS net5 | top-3 net5 | top-5 net5 | worst yr LS | TVT (Train/Val/Test) | verdict             |
|------|-----|--------------------|---------|------------|------------|-------------|----------------------|---------------------|
| 1    | E3  | range_pos_252      | **0.62**| 0.31       | **0.49**   | -0.18       | 0.67 / -0.11 / 0.75  | RESEARCH-ONLY (lead)|
| 2    | E4  | max60/max252       | -0.11   | 0.30       | **0.33**   | -0.46       | -0.29 / -0.46 / 0.12 | research-only       |
| 3    | E2  | p/max_60           |  0.19   | -0.005     | 0.02       | -1.01       |  0.82 / -0.37 / -0.27| reject (TT split)   |
| 4    | E5  | z(e1)+z(e2)        | -0.12   | 0.24       | 0.15       | -0.82       | -0.43 / -0.82 / 0.24 | reject              |
| 5    | E1  | p/max_252          | -0.04   | 0.09       | 0.05       | -0.61       | -0.29 / -0.61 / 0.35 | reject (zero signal)|
| 6    | E6  | e1·MA200_gate      | -0.09   | 0.005      | -0.006     |  0.24       | -0.02 / NaN  / -0.16 | reject              |
| 7    | E8  | -e1 (falsifier)    | -0.08   | 0.31       | -0.07      | -0.64       | -0.33 / 0.41 / -0.04 | reject (asymmetric) |
| 8    | E7  | e1.shift(21) (lag) | -0.50   | -0.58      | -0.49      | -1.72       | -0.67 / -0.53 / -0.32| reject (decayed)    |

## Headline conclusion

**The canonical 52-week-high proximity factor (E1, p/max_252) does NOT
work on this 32-ETF A-share universe** — its LS Sharpe is essentially
zero, and the sign-flip (E8) does not underperform meaningfully. This
is a clean falsification of the literal George-Hwang hypothesis on
A-share ETFs.

**The Williams-style range-position factor (E3) does work**, with a
distinct economic interpretation: rather than "near-the-high"
anchoring alone, the signal is *position within trailing range*.
ETFs at the high end of their 52-week min-max range outperform those
at the low end. The factor is robust on TVT (Train 0.67 / Test 0.75),
worst-year is mild (-0.18 in 2024), and net-of-cost top-5 long-only
excess Sharpe is **0.49**.

## Per-year detail for E3

|              | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|--------------|------|------|------|------|------|------|
| LS Sharpe    | 1.09 | 0.92 | -0.11| 1.46 | -0.18| 1.09 |
| top-3 excess | 0.41 | 1.10 | -0.84| 1.16 | -0.86| 0.51 |
| top-5 excess | 1.60 | 1.21 | -0.13| 0.79 | -0.40| 0.08 |

Two negative years (2022 bear, 2024 mid-cap rotation). Worst-year
floor (≥0.5) fails on LS Sharpe. **Best-year-out** check (drop 2023,
the best year): residual LS Sharpe = 0.41 = 65% of headline 0.63 →
passes 50% threshold.

## Why other anchor variants fail

- **E1 / E2** (raw p/max ratios): cross-sectional ranking of
  p/max_w is dominated by long-run drift differences across ETFs
  (gold drifts up, niche thematic drifts down). After ranking, the
  signal collapses to "ETFs that have rallied recently" — i.e.
  pure momentum. With 252d momentum xs-rank correlation of 0.38,
  E1 is mostly a momentum clone.
- **E3 works** because the *normalization by min* counteracts the
  long-run drift: an ETF at 95% of its 52-week range is bullish
  *relative to its own history*, not just relative to other ETFs'
  drifts.
- **E4 (max60/max252)** confirms that "recent 60d window contains
  the all-time high" carries some information for top-N long-only
  selection (top-5 excess 0.33 net), but its LS leg is destroyed by
  the structural feature that ETFs whose recent peak ≠ multi-year
  peak include both fading themes (negative) AND defensive baskets
  in a sideways regime (zero/mixed) — short leg has no clean signal.
- **E6 (regime gate)** kills too much exposure; the gate is on for
  ~60% of days and the on/off cycles destroy the rebalance pattern,
  not fixing the worst-year problem.
- **E7 (21-day lag)** confirms the signal decays on this universe;
  applicable signal lifetime is < 1 month.

## Combined / next-round suggestion (do NOT promote without re-running)

E3 + E4 (top-5 long-only) average rank could plausibly improve the
worst-year (E4 is positive in 2025 when E3 is flat for top-5; E3 is
positive in 2020-2021 when E4 is mixed). This belongs in batch_0002
as a single dedicated round, not as an ad-hoc combination here.
