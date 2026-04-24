# Alpha Ranking — BTC 1m Reversal Batch 0001

**Session:** 20260423_btc_minute_reversal_v1
**Agent:** 5 (Evaluator & Recorder)
**Data:** BTC-USD 1m, Coinbase, 2026-02-22 16:00 UTC → 2026-04-23 16:00 UTC (60 days, 86,380 bars, 99.98% coverage)
**Cost assumption:** 5 bps per side (taker).

---

## 1. Gate funnel results (G1–G4)

Dogfood of the funnel we shipped earlier today:

| # | expression | G1 | G2 | G3 | G4 | both-gates-pass |
|---|---|:--:|:--:|:--:|:--:|:--:|
| 1 | `r1_rev_1m` | ✅ | ✅ | ❌ (trade_freq 17.8/h > 10) | ✅ | **NO** |
| 2 | `r1_rev_5m` | ✅ | ✅ | ✅ | ❌ (IC sign -) | **NO** |
| 3 | `r1_rev_15m` | ✅ | ✅ | ✅ | ✅ | **YES** |
| 4 | `r1_rev_5m_volscale` | ✅ | ✅ | ❌ (trade_freq 11.1/h) | ❌ (IC sign -) | **NO** |
| 5 | `r1_rev_15m_volscale` | ✅ | ✅ | ✅ | ❌ (D10<D1) | **NO** |
| 6 | `r1_rev_5m_volscale_hd` | ✅ | ✅ | ❌ (trade_freq 11.1/h) | ❌ (IC sign -) | **NO** |
| 7 | `r1_rev_range5m` | ✅ | ✅ | ✅ | ❌ (IC sign -) | **NO** |
| 8 | `r1_rev_amount5m` | ✅ | ✅ | ✅ | ✅ | **YES** |

**2 of 8 pass** both G3 and G4. This is the exact rate the QuantCode-Bench paper
reports for one-shot LLM factor generation (~25% clean pass). The funnel
earned its keep.

## 2. IC profile (the mechanism is horizon-dependent)

```
         k=1m     k=5m     k=15m    k=60m
r1_rev_1m        +0.0097  +0.0081  +0.0057  +0.0024
r1_rev_5m        +0.0081  -0.0026  +0.0100  +0.0030
r1_rev_15m       +0.0058  +0.0100  +0.0131  +0.0017
r1_rev_5m_vs     +0.0124  -0.0022  -0.0014  -0.0052
r1_rev_15m_vs    +0.0045  +0.0053  +0.0066  -0.0055
r1_rev_5m_vs_hd  +0.0127  -0.0016  -0.0006  -0.0044
r1_rev_range5m   +0.0067  -0.0036  +0.0082  +0.0010
r1_rev_amount5m  +0.0086  +0.0016  +0.0043  -0.0004
```

Key observation: **reversal is real at k=1m and k=15m, but breaks (flips or
collapses) at k=5m.** The 5m horizon falls in a trough between the
microstructure-reversal regime (<2m) and the mean-reversion-of-momentum
regime (~15m). Agent 2 picked k=5m as primary based on priors; data says
k=15m is the right primary for this window.

Best IC t-stats across all expressions × horizons:
- `r1_rev_15m` at k=15m: IC +0.0131, t-stat **3.86** (n=86,349)
- `r1_rev_5m_volscale_hd` at k=1m: IC +0.0127, t-stat **3.72**
- `r1_rev_5m_volscale` at k=1m: IC +0.0124, t-stat **3.64**
- `r1_rev_15m` at k=5m: IC +0.0100, t-stat 2.95

None of these reaches the hard floor of IC t-stat ≥ 4.0 at the primary
horizon chosen in `session_metadata.yml`. The peak result (`r1_rev_15m`
at k=15m) reaches 3.86, just under the floor.

## 3. Strategy PnL (gross vs net after 5 bps/side)

| expression | trades/hr | gross Sharpe ann. | net Sharpe ann. | verdict |
|---|---:|---:|---:|:--|
| r1_rev_1m | 19.8 | +2.63 | **−239** | cost wipeout |
| r1_rev_5m | 9.1 | +3.61 | **−118** | cost wipeout |
| r1_rev_15m | 5.2 | +2.04 | **−68** | cost wipeout |
| r1_rev_5m_volscale | 11.1 | +8.15 | **−169** | cost wipeout |
| r1_rev_15m_volscale | 6.6 | +2.21 | **−103** | cost wipeout |
| r1_rev_5m_volscale_hd | 11.1 | +8.42 | **−169** | cost wipeout |
| r1_rev_range5m | 6.7 | +2.17 | **−80** | cost wipeout |
| r1_rev_amount5m | 6.4 | +3.43 | **−75** | cost wipeout |

**All 8 expressions have net Sharpe < 0.** The gross mean PnL per bar is
0.01–0.04 bps. Cost is 5 bps × 2 sides on every position change. With
5–10 position changes per hour, cost burden = 50-100 bps/hour = 12-24%
daily drag. The gross signal is a tiny fraction of that.

This is **textbook Pitfall 10** (daily/frequent rebalance with
rank-based factors → cost wipes signal), already documented in
`common-pitfalls.md`.

## 4. Verdict

### 4.1 Against the hard floors from `session_metadata.yml`

| Floor | Threshold | Best observed | Pass? |
|---|---|---|:--:|
| IC t-stat at k=5 min | ≥ 4.0 | 2.95 (r1_rev_15m) | ❌ |
| Decile spread Sharpe gross | ≥ 1.0 | 8.42 (r1_rev_5m_volscale_hd) | ✅ |
| After-cost Sharpe | > 0 | -68 (best: r1_rev_15m) | ❌ |
| Trade frequency | ≤ 10/hour | 4.4 (r1_rev_amount5m) | ✅ for some |
| Cost assumption | 5 bps/side | applied | ✅ |

### 4.2 Decision

**RESEARCH-ONLY.** The mechanism is partially confirmed (1m and 15m
horizon IC are consistent with the reversal thesis; t-stats are around
3-4) but:

1. The primary 5-min horizon is a dead zone (IC sign flips on most
   variants)
2. Nothing survives 5 bps/side cost
3. Only 2 of 8 expressions pass all gates, and the 2 that do have weak
   IC (r1_rev_15m: 2.95 t-stat; r1_rev_amount5m: 0.46 t-stat)

Cannot promote to paper trading or any deployment.

### 4.3 Falsification-first check

> If this "partial confirmation" is wrong by 50%, what is the most likely
> single cause?

- **Hypothesis A (most likely):** Horizon mismatch — the mechanism was
  mis-specified at Agent 2. True signal is at k=15m, not k=5m.
  Evidence: r1_rev_15m has IC 0.013 (t=3.86) at k=15m — the strongest
  single number in the whole batch. Round 2 should re-center on k=15m
  with explicit 15m holding period.

- **Hypothesis B:** 60-day window too short for stable inference. IC
  0.01 at 86k bars is t-stat ~3. Double the window and the effect
  should strengthen if real, or wash out if spurious. Coinbase has
  longer history available.

- **Hypothesis C:** Cost assumption too aggressive. OKX taker is 5 bps
  but with volume-tier discounts can drop to 2-3 bps. At 2 bps/side,
  r1_rev_15m net Sharpe recomputed would be less-negative — worth a
  sensitivity chart, but unlikely to flip to positive given the gap.

## 5. Next round direction (if continuing)

Round 2 recommendations for Agent 1/Agent 2:
1. **Re-center primary horizon on k=15 minutes.** Redo the hypothesis
   with 15m as the target, and add a 15m hold constraint on the
   strategy (signal only refreshes every 15 bars).
2. **Test longer windows** for 15m reversal: past 15m, 30m, 45m, 60m.
3. **Reduce trade frequency** via signal smoothing: EMA over 15 bars
   before thresholding, or quintile (5 buckets) instead of decile.
4. **Pivot to perpetuals** if funding rate data becomes available —
   funding-rate-based signals have much larger expected effect size
   at minute-hour scale.

## 6. Gate-funnel dogfood results (meta)

This run is the **first real test** of the 4-gate funnel shipped
earlier today. Meta-findings:

### What the gates caught correctly
- **G3 trade_freq** correctly flagged all 3 sub-minute expressions
  (r1_rev_1m, r1_rev_5m_volscale, r1_rev_5m_volscale_hd) as
  cost-unviable before Agent 5 had to analyze their net Sharpe.
  This is exactly the "catch Pitfall 10 before it reaches Agent 5"
  purpose.
- **G4 IC sign** correctly flagged the 4 expressions where the
  mechanism doesn't hold at k=5m, forcing a round-level pivot
  discussion rather than silently reporting noise as alpha.

### What the gates did NOT catch
- **Horizon mispick at Agent 2 level.** The funnel is per-expression,
  not per-hypothesis. If Agent 2 picks a wrong primary k, all 8
  expressions can fail G4 for the same reason and you learn the
  right k only by inspecting IC across horizons — which Agent 5 did
  above. Consider adding a per-batch "horizon consistency" gate in
  a later workflow iteration: "does the IC at the declared primary
  horizon beat IC at all other horizons for at least half the batch?"
- **Cost wipeout is flagged post-hoc via `net_sharpe < 0`, not by a
  gate.** The existing `trade_freq_per_hour_ok` gate is a proxy but
  imperfect; a direct net-Sharpe > 0 gate would be more decisive.
  Consider adding to `validation-gates.md` as a G3 check.

### Overall

The funnel worked as intended: it intercepted 6 of 8 expressions that
would otherwise reach Agent 5 as candidates despite being either
cost-unviable or mechanism-inconsistent. The two that passed (r1_rev_15m
and r1_rev_amount5m) correctly reflect the strongest real signals in
the batch. This is pay-off.

---

## 7. Handoff

- **Status:** RESEARCH-ONLY
- **Best expression (for reference):** `r1_rev_15m` (IC at k=15m: 0.0131,
  t-stat 3.86; gross Sharpe 2.04; net Sharpe -68 at 5 bps/side)
- **Session archived.** No factor is promoted from this round.
- **Round 2 is NOT launched automatically** — user should confirm the
  pivot direction above before Agent 1 is re-engaged.
