# Alpha Ranking — Round 3 (production-grade phase-averaged)

R3 ran 8 production-grade variants of the anchor / range-position
factor. All 8 use **21-phase ensemble** (1/21 capital deployed each
trading day, 21-day holding) — the deployable form of any monthly
rebalanced strategy.

## R3 results (top-5 long-only excess vs equal-weight benchmark)

| ID | construction                        | net Sharpe | worst yr | test | n_pos/n_total | verdict        |
|----|-------------------------------------|-----------:|---------:|-----:|--------------:|----------------|
| H7 | phase-avg + portfolio vol-target    | **0.71**   | -0.20    | 0.49 | 5/7           | research-only  |
| H6 | phase-avg + top-3                   | 0.63       | -0.04    | 0.49 | 6/7           | research-only  |
| H1 | phase-avg baseline                  | 0.55       | -0.13    | 0.42 | 5/7           | research-only  |
| H3 | phase-avg + inv-vol weighting       | 0.54       | -0.11    | 0.55 | 6/7           | research-only  |
| H5 | phase-avg + 20-ETF core universe    | 0.52       | **+0.09**| 0.53 | **7/7**       | research-only  |
| H2 | phase-avg + MA200 risk-on gate      | 0.48       | -0.27    | 0.51 | 5/7           | reject         |
| H8 | full risk-managed (vol-target+H4)   | 0.35       | -0.40    | 0.55 | 4/7           | reject         |
| H4 | H2 + H3 (gate + inv-vol)            | 0.32       | -0.43    | 0.55 | 5/7           | reject         |

## Findings

1. **H5 is the only variant with positive worst-year** (+0.09).
   Restricting to the 20 ETFs with full 7-year history strips out
   late-listed thematic ETFs that drove 2024 weakness.
2. **H7 has the highest Sharpe** (0.71) — portfolio-level vol-target
   to 10% ann boosts headline by 30 % over baseline.
3. **H2/H4/H8 with regime gate fail** — when bench < MA200, holding
   the broad bench instead of EW universe loses a defensive overlay
   advantage in 2022.
4. **H3 (inv-vol weighting)** marginally improves robustness without
   changing headline.

## R4 design rationale

R3 leaders share three orthogonal improvements:
- top-3 vs top-5 (concentration, +0.08 Sharpe)
- core vs full universe (worst-year fix, +0.21 worst-year)
- vol-target overlay (drawdown control, +0.16 Sharpe)

Combining them should be additive. The key R4 question is whether
the combination crosses the **1.0 ADMITTED floor** from
`factors/README.md`.
