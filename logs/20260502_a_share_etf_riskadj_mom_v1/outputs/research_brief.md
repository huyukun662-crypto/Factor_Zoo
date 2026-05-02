# Research Brief — A-Share ETF Risk-Adjusted Momentum v1

**Agent 1 (Research Librarian)** — 2026-05-02

## 1. Mechanism family

Risk-adjusted momentum: rank assets by `r_k / σ_k` instead of plain
`r_k`. The intuition is that two assets with the same trailing return
but very different realized volatility do not have the same
information content; the lower-vol mover is showing a more
*persistent* trend, which has historically translated into stronger
forward returns per unit of risk.

Closest published references the librarian flags as relevant:

- Asness (1994), *"Variables That Explain Stock Returns"*, PhD thesis,
  University of Chicago — risk-adjusted momentum factor in equity
  cross-section.
- Frazzini & Pedersen (2014), *"Betting Against Beta"*, JFE — formal
  treatment of vol-deflated long-short construction; the mechanism
  by which vol-deflation reduces the cost of leverage and stabilises
  rank.
- Faber (2007), *"A Quantitative Approach to Tactical Asset
  Allocation"*, JoWM — moving-average / momentum applied to broad
  ETFs (US sectors). Establishes that monthly rebalance + simple
  trend on ETFs is implementable.
- Moskowitz, Ooi, Pedersen (2012), *"Time Series Momentum"*, JFE —
  documents that ETF / index trend persistence is robust at 1-12
  month horizons.

## 2. Prior internal evidence (Factor_Zoo logs)

### Confirming evidence (same direction)

- `logs/20260422_industry_rotation_cn` — V7_gold momentum: top-3
  60-day return inside industry-rotation framing, monthly, gives
  Sharpe > 1 net of cost on the same 30-ETF universe. **Plain
  momentum already works** at horizon 60d.
- `logs/20260501_a_share_etf_ivol_momentum_v1` — IVOL momentum
  (residualized) is *inverted* in A-share ETFs: long-high-IVOL gives
  + LS Sharpe but worst-year fails 0.5 floor. Implication: **vol
  is informative**, but as part of a composite (return + vol) rather
  than residual-vol alone.

### Disconfirming evidence

- `logs/20260423_a_share_etf_reversal_v1` — short-window (5d) reversal
  fails worst-year floor. Argues against the m4 fast-lookback variant
  but does not falsify slower 60-120d momentum.

### Operational lessons inherited

From CLAUDE.md A-share lessons:

- Daily rebalance with rank-based factors → 100%+ daily turnover →
  net Sharpe negative. **Use monthly rebalance.**
- Always report *both* LS and long-only Q5/top-N excess. **Long-only
  top-N is the deployable metric.**
- Industry/sector neutralization is mandatory for *cross-sectional
  stock* factors but not strictly required at the ETF level (each ETF
  is already a pre-aggregated industry); we report excess vs EW
  universe instead.
- 5 bps/side cost is the realistic A-share retail-broker level.

## 3. Operator and data suggestions

- **Lookback window k**: test 20 / 60 / 120. The literature consensus
  for "intermediate-term momentum" is 60-252d on equities; for ETFs
  60-126d. We anchor on 60d and probe 20 / 120 as sensitivities.
- **Vol estimator**: simple historical std of log-returns; do *not*
  use EWMA — it introduces extra parameter overhead with no
  documented benefit at this universe size.
- **Rank**: cross-sectional rank then top-N selection. Monotone
  transform is rank, not z-score, because the 30-ETF universe has
  fat-tailed signal distributions (theme spikes).
- **Target return**: forward 21d log return, computed as
  `log(close[t+22]) - log(close[t+1])` to respect a 1-day execution
  delay (signal date t, trade at close[t+1], hold to close[t+22]).
- **Cost model**: 5 bps × turnover. Turnover at month-end =
  Σ |w_new − w_old| / 2.

## 4. Risks and caveats

- **Universe size 30 is small.** Top-5 is 17% of the universe; top-3
  is 10%. Selection error can be a meaningful fraction of total
  variance. We mitigate by reporting per-year stability.
- **Survivorship**: the 30 tickers were chosen as those with ≥ 1300
  bars at the time of fetch; ETFs that delisted are excluded. Bias
  is mild but not zero. Document explicitly.
- **A-share thematic ETFs cluster on a small number of macro themes
  (semis, dividends, gold, healthcare).** Top-3 in a thematic
  drawdown can become a single-theme bet. Per-year breakdown is
  required.
- **Look-ahead** is the standard concern. Signal is built on
  `close[t]` only; trade is placed at `close[t+1]`; return is
  measured `close[t+1] → close[t+22]`. Future-perturbation test
  required (Audit 2).
- **Best-year-out** is the most likely failure mode for a 7-year
  test on a small ETF universe. Must report explicitly.

## 5. Candidate mechanism summary

| Variant | Lookback | Vol normalization | Selection | Rationale |
|---|---|---|---|---|
| m1 | 60d / 60d | std(log r) | top-5 | Baseline |
| m2 | 60d / 60d | std(log r) | top-3 | Concentration |
| m3 | 120d / 120d | std(log r) | top-5 | Slower trend |
| m4 | 20d / 20d | std(log r) | top-5 | Faster trend |
| m5 | 60d / 60d | std(log r) | top-5 + MA50 | Regime gate |
| m6 | 60-skip5 / 60d | std(log r) | top-5 | JT-skip |
| m7 | 60d / — | none | top-5 | Plain-mom control |
| m8 | 60d / 60d-DSV | downside std | top-5 | Sortino-style |

Sources cited above; full files cached to `_shared_cache` (data) and
`worldquant-5-agent-workflow/references/` (skill).
