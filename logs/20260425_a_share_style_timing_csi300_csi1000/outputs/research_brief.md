# Research Brief — Agent 1 (Research Librarian)

Session: `20260425_a_share_style_timing_csi300_csi1000`
Objective: see `inputs/objective.md`.

## Knowledge sources surveyed

This round is constrained to information that is either (a) from the in-repo
skill references or (b) widely-known A-share style-rotation empirical
patterns. No external paper retrieval was performed; the skill's
`references/repo-summary.md` notes the original repo's knowledge base focused
on operator/dataset advice, not style-rotation literature.

Relevant constraints brought forward from skill references:

- `SKILL.md:297-321` "A-share adaptation lessons" — for cross-sectional
  alphas. **Most do not bind here** (industry neutralization N/A on
  indices), but two transfer:
  - "always report BOTH long-short AND long-only excess metrics"
    → degenerate in our setting (only one spread); we report Sharpe of the
    +1/0/-1 position and also an asymmetric long-only-300 variant in audit.
  - "After-cost analysis is mandatory" — we apply 5 bps/side from the
    start, not after the fact.
- `validation-gates.md:118-126` G3 thresholds — adapted in
  `src/backtest/audits.py` per the approved plan; 3-asset universe means
  Q5-size and unique-name checks become "non-zero position fraction" and
  "annual turnover within budget".
- `tvt-split-template.md:138-149` PROMOTE floors — applied unchanged.

## Mechanism candidates

We list five candidate mechanisms; Agent 2 will pick exactly one to drive
the 8-expression batch.

### M1 — Volatility-regime / risk-off rotation

**Story.** When realized volatility of small-cap (CSI1000) spikes
relative to large-cap (CSI300), institutional risk-parity rebalances cut
risk → small-cap selling pressure persists for a few days → CSI300
outperforms CSI1000 over the next ~5 trading days. Vol-regime signals
revert on a 1-2 week horizon, then a slower mean-reversion ("recovery
rally") favours small-cap on a 1-2 month horizon — outside our R1
horizon.

**Direction.** `vol_spread = vol(1000) − vol(300)` high → favour 300
(thesis sign of IC vs forward spread = +1).

**Why it can work in A-share:** small-cap names are heavily retail-held,
panic-vol spreads compress small-caps faster than large-caps; this is
asymmetric and persistent on short horizons.

**Why it might fail:** if our 2018-2025 sample is dominated by long calm
regimes (2019, 2021, 2023), the rare vol-spike sample is too sparse for
stable estimation; "spikes" become regime-driven outliers driving most of
the Sharpe and audit 4 (best-year-out) flags it.

**Datasets / operators needed:** index daily close, std/var rolling,
ratio, log, z-score over rolling window.

### M2 — Volume / turnover divergence (retail euphoria)

**Story.** Small-cap turnover spikes (relative to large-cap) flag retail
euphoria → mean-reversion within ~5 trading days → favour CSI300.
Symmetrically, abnormally LOW small-cap turnover signals retail
disinterest → potential rebound → favour CSI1000.

**Direction.** `turnover_spread_1000_300` high → favour 300 (sign +1).

**Why it can work:** A-share's retail share of trading is structurally
high; turnover is a more direct retail-attention proxy than e.g. price
momentum.

**Why it might fail:** turnover is highly correlated with vol; M2 may be
a noisier proxy for M1.

### M3 — Cross-sectional dispersion / vol-of-vol

**Story.** When dispersion within small-cap basket is high (CSI1000
intraday range / cross-section spread is wide), idiosyncratic noise
dominates ETF-level returns → stock-pickers do well, ETF lags. Favour
broad-index 300 over CSI1000 ETF until dispersion contracts.

**Why it can work:** captures the regime when "small-cap as a basket"
underperforms even though individual small-caps are alive.

**Why it might fail:** without constituent data, we approximate
dispersion with a (high-low)/close range; this is only weakly correlated
with true cross-sectional dispersion.

### M4 — Momentum continuation/reversal of the style spread

**Story.** Style rotation regimes are persistent at 60-120d (continuation)
but mean-revert at 5-10d (short-term reversal). A short-window reversal
signal on the 300-1000 return spread should predict short-horizon flips.

**Why it can fail:** classic-factor clone risk — directly trades a
momentum signal that is collinear with size, momentum, and EW-return per
the G4 anti-clone check.

### M5 — Market-regime defensive switch

**Story.** Bear markets favour large-cap (defensive); bull markets favour
small-cap (beta). A 60-120d trailing return of a market proxy
(CSI300 itself) acts as a regime indicator.

**Why it can fail:** highly trend-following → overfits to the specific
2018-2022 bear market and 2024-25 micro-cap rally; likely to fail
worst-year audit.

## Recommended focus for Agent 2

Pick **M1 (volatility-regime / risk-off rotation)** for the following
reasons:

1. **Distinct from classic factors.** vol-spread is mechanically separated
   from the size/momentum/EW-return cluster that G4's anti-clone check
   targets.
2. **Cleanly 8-expressionable.** Variants on (vol window, weighting,
   downside vs total vol, raw vs ratio vs log, with vs without
   regime-relative z-score) give 8 economically distinct probes of the
   same mechanism.
3. **Clear falsification.** If `corr(vol_spread, fwd_spread_5d)` is not
   reliably positive on TRAIN, the mechanism is dead — no parameter
   tuning will save it.
4. **A-share fit.** Vol regimes have been particularly violent in
   A-share since 2018 (2018Q4 trade war, 2020Q1 COVID, 2024 Q1 micro-cap
   panic) — sample is rich enough to test, but also concentrated enough
   to make audit 4 (best-year-out) a meaningful gate.

Agent 2 should declare **horizon = 5 trading days** and confirm via G5
batch consistency that ≥ 4 of 8 expressions peak |IC| at h=5.

## Risks / caveats

- **Sample-period concentration risk**: vol regimes cluster in time;
  PROMOTE Sharpe could come almost entirely from one panic episode.
  Audit 3 (worst-year-Sharpe) and audit 4 (best-year-out) are exactly
  the gates that catch this.
- **Anti-clone risk**: vol-spread can become highly correlated with
  20d-momentum if the recent regime is trending. G4 enforces
  `|corr| < 0.85`.
- **Test-window sufficiency**: 2.3y test window covers (a) the early-2024
  micro-cap panic, (b) the 2024-Q4 to 2025-Q1 small-cap rally, and (c)
  partial 2026. This is regime-rich but short — PROMOTE Sharpe needs to
  be very strong to clear floors over only ~2.3y.
- **Overfit-by-mechanism-search risk**: we are choosing M1 partly because
  it makes 8 clean expressions; if M1 fails, R2 should pivot to M2 or
  M3, not tune M1 windows.
