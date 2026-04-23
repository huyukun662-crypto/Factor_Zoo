# Research Brief — Round 2 (BTC 1m reversal re-center)

**Session:** 20260423_btc_minute_reversal_v1
**Round:** 2
**Agent:** 1 (Research Librarian)
**Parent:** Round 1 (2 of 8 passed gates; best IC t-stat 3.86 at k=15m)

---

## 1. Round 1 residue

What Round 1 established:
- Reversal mechanism is real at k ∈ {1m, 15m}, t-stat 3-4
- Mechanism breaks at k=5m (likely an inflection between microstructure
  reversal and slower mean-reversion regimes)
- Every expression failed net-Sharpe > 0 at 5 bps/side due to high
  trade frequency — Pitfall 10 (not a factor problem, a deployment
  problem)
- Best Round 1 expression: `r1_rev_15m` (IC 0.0131 / t-stat 3.86 at k=15m,
  gross Sharpe 2.04, trade freq 5.2/hour)

New G5 meta-gate (added today) would flag this batch: 3 of the 8
expressions peaked at k=15m (not the declared k=5m). This IS the
horizon-mismatch signature.

## 2. Round 2 pivots

1. **Primary horizon = 15 minutes** (was 5)
2. **Hold constraint = 15 bars** (was 1). Signal refreshes every 15
   bars, cutting trade count ~15×. This is the primary lever to fight
   Pitfall 10.
3. **Reversal windows focused on 15-60m** (was 1-15m). Round 1's k=1m
   peak is too cost-sensitive to deploy; drop it.
4. **Cost sensitivity curve** at {2, 5, 8, 10} bps/side — Coinbase
   Pro is ~10 bps taker, OKX taker ~5 bps with tier discount to ~2 bps.
5. **Add EMA-smoothed variant** — replace the raw signal with an EMA
   over 15 bars before thresholding; reduces whipsaw without changing
   the underlying signal.

## 3. Literature / mechanism check

Short-term reversal at 15m scale:
- Lehmann 1990 "Fads, martingales, and market efficiency" — at weekly
  horizon, reversal was 3 std. In modern HFT era, the horizon has
  compressed to minute-hour scale.
- Nagel 2012 "Evaporating Liquidity" — reversal strengthens in low-
  liquidity regimes. Crypto overnight (US night / Asia day) is a low-
  liquidity regime where the effect should be enhanced.
- Avellaneda-Lee 2010 "Statistical Arbitrage in the US Equities Market"
  — their intraday reversal strategy holds 15-30 minutes with similar
  mechanics (z-score against a moving average). This is the exact
  horizon we're now targeting.

Expected IC at k=15m with 15-bar hold: 0.01-0.02 (matches Round 1
observation).

Expected net Sharpe at 5 bps/side with 15m hold:
- Trade freq ~1-2 per hour (vs 5-10 in Round 1)
- Cost burden ~10-20 bps/hour (vs 50-100)
- If gross Sharpe stays at 2.0, cost ratio should give net ~0.3-0.8

## 4. Non-goals

- NOT testing momentum / continuation (different mechanism — future
  batch)
- NOT testing funding rate (still no perp data access)
- NOT re-testing k=1m (cost-unviable regardless of smoothing)

## 5. Handoff to Agent 2

- Primary mechanism: **short-term reversal at 15m horizon with 15-bar hold**
- 8 new expressions focused on 15m family with EMA smoothing variants
- Hard floors: same as Round 1 but re-anchored on k=15m
- Explicit cost sensitivity reporting required
