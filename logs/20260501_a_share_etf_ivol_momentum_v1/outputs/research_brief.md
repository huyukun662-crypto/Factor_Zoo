# Research Brief — Inverted IVOL Momentum on A-Share ETFs

Owner: Agent 1 (Research Librarian).
Generated: 2026-05-01.

This brief is a continuation of the work in
`logs/20260501_a_share_etf_ivol_reversal_v1`. It does not re-derive the
mechanism — it scopes the three open questions left by that session.

## Origin of the hypothesis

The parent session falsified the classical Ang-Hodrick-Xing-Zhang
(2006) IVOL-reversal anomaly on A-share thematic ETFs. The decile
ordering was inverted:

| Quintile | Description | Annual return |
|---:|---|---:|
| Q1 | high-IVOL ETFs | **+24.6%** |
| Q5 | low-IVOL ETFs |  +6.7% |

The interpretation: thematic ETFs ARE the labeled narrative buckets
that retail flows chase. The lottery-preference channel that
underprices high-vol stocks at the stock level OVERPRICES (or stays
flat-bid) at the basket level, because each high-vol thematic ETF IS
the exposure vehicle for the marginal bid. A future-paper version
would say: at the basket level, lottery preference manifests as
narrative momentum, not as a return discount.

A naive "long high-IVOL, short low-IVOL" portfolio at monthly
rebalance produced LS Sharpe = +0.66, all 7 calendar years positive,
worst-year (2024) = +0.04 — failing the 0.5 floor.

## Three open questions

### Q1. Regime gate

The 2024 worst-year coincided with the Chinese deleveraging regime
(broad-market drawdown, narrative collapse). MA50 of 510300 spent
much of 2024 below price, so a trend filter could flatten exposure
during the bad regime.

The MA50 gate is the same one used by V7_gold
(`logs/20260422_industry_rotation_cn`); it is well-validated on the
A-share thematic-ETF cross-section.

### Q2. Long-only top-N vs LS

Per CLAUDE.md A-share lessons, the deployable A-share metric is
long-only Q5 / top-N excess vs the EW universe. Reasons:

- A-share has limited shorting (margin lending of ETFs requires
  qualification; effective short interest is near-zero for most
  thematic ETFs).
- The high-IVOL Q1 short leg structurally underperforms in the LS
  variant — that's where the +24.6% lives. We don't actually want
  to short it; we want to LONG it.

The mechanism's signal direction (long high-IVOL) is what pays. The
LS variant pays at +0.66 only because the long Q5 leg is high-IVOL.
A long-only top-N variant captures the long-leg directly.

**Top-3 vs top-5**:
- Top-3 of 30 ETFs ≈ top-10% concentration; matches V7_gold spec
  (top-4 in 4-ETF momentum leg).
- Top-5 ≈ top-17%; less concentrated, smoother turnover.

### Q3. Orthogonality vs V7_gold

V7_gold uses 4-week momentum + crowding penalty + breadth + group
rotator + MA50 gate to pick 7 names weekly. Its construction is
return-magnitude based.

Inverted-IVOL is *vol-rank* based — economically distinct from
return-magnitude. Hypothesis: |corr| between the two should be < 0.5.
If they are highly correlated (corr > 0.7), inverted-IVOL is a noisy
proxy for V7's momentum and adds nothing.

V7_gold weekly returns are accessible at
`logs/20260422_industry_rotation_cn/outputs/round8_equity_curves.csv`
(column `V7_gold`).

## Operators / data

- Same shared cache: `logs/_shared_cache/etf_daily.parquet` (30 ETFs).
- Same beta benchmark: 510300.SS.
- New data join: V7_gold weekly equity curve from
  `logs/20260422_industry_rotation_cn/outputs/round8_equity_curves.csv`.

## Risks specific to this round

### R1. Look-ahead in regime gate
- MA50 must be computed at close(t-1) and used as a flag for
  position from close(t+1). If MA50 includes close(t), the gate
  flips on the same day the signal is observed → look-ahead.
- Mitigation: compute `gate_t = (close_510300_t > MA50_510300_t)`
  using only data ≤ t, AND require `delay = 1` so position is
  established at close(t+1).

### R2. Survivorship in 30-ETF universe
- 5 ETFs (159755, 159890, 159869, 159857, 159992) start mid-2021.
- The cross-section grows from ~22 in 2019 to 30 in 2022+. Top-3
  is robust to this; top-5 also.
- Mitigation: report n_universe per day; if < 15, skip date.

### R3. 2024-bad-year cherry-picking
- The MA50 gate is selected *because* it would have rescued 2024.
  This risks overfitting to a single regime.
- Mitigation: report per-year breakdown for ALL years and check the
  gate doesn't kill a good year (e.g., 2020 was a bull run; if MA50
  flagged it down even briefly, performance degrades).

### R4. Concentration → idiosyncratic risk
- Top-3 of 30 ETFs is small. A single ETF blowup dominates.
- Mitigation: show top-3 vs top-5 vs LS side-by-side; if top-3 has
  much higher Sharpe but also much worse worst-year, prefer top-5.

## Prior-art anchors

- Ang, Hodrick, Xing, Zhang (2006) — the original IVOL anomaly
  (which DOES NOT hold here).
- Bali, Cakici, Whitelaw (2011) MAX — companion lottery factor;
  same direction as IVOL on stocks, also expected to invert at
  ETF level.
- Frazzini, Pedersen (2014) BAB — betting-against-beta; orthogonal
  to IVOL but worth noting since high-beta and high-IVOL overlap.
- Asness, Frazzini, Israel, Moskowitz (2018) — quality-minus-junk
  arguments around vol; argue against the lottery-preference channel.
- For A-share thematic ETF momentum: V7_gold session
  `logs/20260422_industry_rotation_cn` — 4-week momentum + group
  rotator at Sharpe 1.91 / MaxDD -8.9%.

## Next-stage handoff

Agent 2 must:
- Lock primary horizon at k=20 (monthly).
- Pre-commit to long-only top-N (top-3 and top-5 both tested) as
  the deployable variant.
- State the V7_gold corr ceiling (|corr| ≤ 0.5).
- Pre-commit to per-year reporting: ALL 7 years; the MA50 gate
  must not destroy any good year while rescuing 2024.
