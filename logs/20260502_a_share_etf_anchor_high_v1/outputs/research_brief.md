# Research Brief — Anchor / 52W-High Proximity on A-share ETFs

## Mechanism (one paragraph)

Investors anchor on salient reference prices (52-week high, recent peak).
When a security is far below its anchor, holders refuse to realize losses
and buyers wait for "confirmation"; when a security is at or near its
anchor, that resistance has just been overcome and remaining holders are
in profit, so they are willing to let it run. The result is documented
short-horizon underreaction in the breakout names: George & Hwang (2004)
"The 52-Week High and Momentum Investing" finds nearness-to-52w-high
beats price momentum on US single-stocks. The effect should survive on
ETF baskets because the anchor of a basket is collectively salient (it
is published, charted, and quoted), while idiosyncratic news that
normally pollutes single-stock momentum is averaged away.

## Why this could fail in A-share ETFs

- Strong reversal regime: Chinese retail flow chases winners then
  capitulates. Anchor-proximity could become an inverse signal in
  bull-to-bear transitions.
- Heterogeneous universe: 34 ETFs span broad index, sector, thematic,
  and gold. Range scale differs (gold drifts; thematic has 2x range).
  Cross-sectional ranking should normalize, but Z-scoring may help.
- Short window can also pick up momentum tail; need to disentangle.

## Operator suggestions

- `p / max_w(p)` — 52-week-high proximity (G&H canonical form).
- `(p - min_w(p)) / (max_w(p) - min_w(p))` — Williams %R-style range
  position; bounded in [0,1].
- `(p - max_w(p)) / max_w(p)` — drawdown distance (negative).
- Multi-horizon composite: average rank of `p/max_252` and `p/max_60`.
- Regime gate: only go long when benchmark (`510300.SS`) > MA200.
- Sign-flip falsification: confirm that `-p/max_252` underperforms
  (G5 batch-level horizon consistency check).

## Risk catalogue (lessons from common-pitfalls.md)

- Pitfall 1 — execution-delay audit mandatory; default `delay=1`,
  `target_shift = -(1+delay) = -2` for `k=1`, generalize to `k`.
- Pitfall 2 — look-ahead: ensure `max_w` and `min_w` are
  *trailing* windows (`rolling(w).max()`), not centered.
- Pitfall 3 — worst-year floor: anchor factors are notoriously fragile
  in 2018-style drawdowns; A-share has 2022 + 2024-Q1 candidates.
- Pitfall 7 — bull-market LS short-leg destruction: report Q5
  long-only excess alongside LS.
- Pitfall 9 — hidden classic-factor exposure: anchor is heavily loaded
  on momentum; we will residualize against 252-day momentum and report
  the residual Sharpe to confirm the factor is not a momentum clone.
- Pitfall 10 — daily turnover cost trap: prefer monthly rebalance.

## Datasets

- `_shared_cache/etf_daily.parquet` (already fetched 2026-05-02).
  Columns: date, symbol, open, high, low, close, volume, amount.

## References (memory; do not cite verbatim)

- George, T. J., & Hwang, C.-Y. (2004). *The 52-Week High and Momentum
  Investing.* Journal of Finance.
- Driessen, J., Lin, T., & Van Hemert, O. (2012). How the 52-week high
  and low affect option prices.
- Local: `references/common-pitfalls.md`, `references/tvt-split-template.md`,
  `references/execution-delay-audit.md`.
