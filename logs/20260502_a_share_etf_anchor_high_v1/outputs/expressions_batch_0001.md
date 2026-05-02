# Expressions — batch_0001 (Anchor / 52W-High Proximity, A-share ETFs)

Universe: 32 A-share ETFs (drop 512800.SS, 515170.SS).
Forward horizon k=20 (monthly), delay=1, rebalance=21d, cost=5 bps/side.
All factors are evaluated cross-sectionally; ranks computed per date.

## E1 — `p_over_max_252` (canonical 52w-high proximity, raw)

```
e1 = close_t / rolling_max(close, 252)_t
```

Higher = closer to 52-week high → expected long. Mechanism: George &
Hwang anchoring. Expected turnover: low-to-medium (proximity changes
slowly).

## E2 — `p_over_max_60` (short-window anchor)

```
e2 = close_t / rolling_max(close, 60)_t
```

Same form, ~3-month horizon. Tests whether the anchor effect is
present at quarterly scale. Expected turnover: higher than E1.

## E3 — `range_pos_252` (Williams %R-style position in range)

```
e3 = (close_t - rolling_min(close, 252)_t)
     / (rolling_max(close, 252)_t - rolling_min(close, 252)_t + eps)
```

Bounded in [0,1]. Distinct from E1 because it co-uses the trailing
low, which downweights ETFs that have rallied off a deep drawdown.

## E4 — `max60_over_max252` (recent peak vs long-term peak)

```
e4 = rolling_max(close, 60)_t / rolling_max(close, 252)_t
```

Bounded in [0,1]. e4=1 iff the 60-day window contains the 252-day
peak (i.e., the security recently confirmed an all-time-high regime).
Distinct from `p/max_252` because it does NOT depend on the current
close — it isolates "recent breakouts" from "currently near high".
Note: original draft used `(close-max60)/max60` but that is monotone
in `close/max60` and produces identical cross-sectional ranks to E2;
replaced after Agent 4 self-check.

## E5 — `composite_z_60_252` (multi-horizon anchor)

```
z_a = zscore_cross_section( p / max_252 )_t
z_b = zscore_cross_section( p / max_60  )_t
e5  = 0.5 * z_a + 0.5 * z_b
```

Combines long-anchor and short-anchor signals; should reduce noise
without changing the dominant mechanism.

## E6 — `regime_gated_p_over_max_252` (defensive overlay)

```
g_t = 1 if close_bench_t > MA200(close_bench)_t else 0
e6_t = (p / max_252)_t * g_t   # signal zeroed when regime off
```

When the broad benchmark is below its 200-day MA, do not take
exposure (signal collapses to flat → equal-weight or cash). Tests
whether the mechanism is conditional on a risk-on regime.

## E7 — `lagged_p_over_max_252` (signal-decay test)

```
e7 = (p / max_252)_{t - 21}
```

Same factor evaluated 21 trading days earlier. If forward returns
still load on the lagged signal, the anchor effect has slow decay
and is implementable; if not, the headline IC is short-horizon
microstructure rather than anchoring.

## E8 — `neg_p_over_max_252` (sign-flip falsification)

```
e8 = -(p / max_252)
```

Pure sign flip of E1. MUST underperform E1; if it instead beats E1,
the mechanism is the *opposite* (reversal, not anchoring) and the
batch should be re-architected at Agent 2.

---

## Diversity self-check

| | E1 | E2 | E3 | E4 | E5 | E6 | E7 | E8 |
|--|--|--|--|--|--|--|--|--|
|core operator|p/max|p/max|range|dd|z-comp|p/max·gate|p/max(lag)|-(p/max)|
|window|252|60|252|60|60+252|252|252|252|
|expected sign|+|+|+|+|+|+|+|−|

Distinct constructions: 3 windows, 4 functional forms (proximity,
range, drawdown, composite), 1 regime gate, 1 lag, 1 sign-flip
falsifier. No two expressions are linear copies.

## Expected turnover direction

E1, E3, E7: low (anchors move slowly).
E2, E4, E5: medium (60-day window).
E6: bursty (regime switches).
E8: identical magnitude to E1 (sign flip).

## Output format expected from Agent 4

For each of E1..E8 and for selection mode in {LS Q5, top-3 long
excess, top-5 long excess}, return:

- IC mean / IC stability / IR at k ∈ {5, 10, 20}
- Annualized Sharpe (gross and net at 5 bps/side)
- Per-year Sharpe table
- Annualized turnover
- Worst-year and best-year-out Sharpe
- Q5/top-N long-only excess vs equal-weight benchmark
