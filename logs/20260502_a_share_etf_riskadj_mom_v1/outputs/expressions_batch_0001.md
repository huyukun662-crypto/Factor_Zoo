# Expressions Batch 0001 — Risk-Adjusted Momentum on A-Share ETFs

**Agent 3 (Alpha Builder)** — 2026-05-02

Mechanism: cross-sectional Sharpe-style risk-adjusted momentum.
Universe: 30-ETF A-share thematic panel.
Rebalance: monthly (last trading day of each calendar month).
Delay: signal at `close[t]`, executed at `close[t+1]`,
held to `close[t+22]`.
Target invariant: `target_shift = -(1 + delay) = -2`.
Cost: 5 bps per side at rebalance.

All expressions use `panel.pivot(index='date', columns='symbol', values='close')`
as the price matrix `P`, then build `log_ret = log(P).diff()`.

## Notation

```
mom_k(t)   = log(P[t]) - log(P[t-k])           # cumulative log return
vol_k(t)   = std(log_ret[t-k+1 : t])           # daily realized vol
dvol_k(t)  = std(min(log_ret[t-k+1 : t], 0))   # downside std (Sortino numerator vol)
ma_n(t)    = mean(close_510300[t-n+1 : t])
gate_ma50(t) = 1 if close_510300[t] > ma_50(t) else 0
rank_xs(s, t) = cross-sectional rank of s across symbols at t (0..1)
top_N(s, t)  = 1 if rank_xs(s, t) >= 1 - N/U  (U = #valid symbols at t)
```

Eight expressions follow.

---

### m1 — `riskadj_mom_60_top5`  (BASELINE)

```
signal_m1(i, t) = mom_60(i, t) / max(vol_60(i, t), 1e-6)
weight_m1(i, t) = top_5(signal_m1, t) / 5            # equal weight inside top 5
```

Rebalance monthly. Long-only. Expected turnover direction: moderate
(top-5 changes by 1-2 names per month at this universe size →
~120-300% annual turnover).

**Economic story.** k=60 captures 3-month price persistence; vol-deflation
penalises ETFs whose return came from one or two limit-up days (cheap
beta). This is the classical Asness 1994 risk-adjusted momentum applied
at ETF level.

---

### m2 — `riskadj_mom_60_top3`

```
signal_m2(i, t) = mom_60(i, t) / max(vol_60(i, t), 1e-6)
weight_m2(i, t) = top_3(signal_m2, t) / 3
```

Same signal as m1 but more concentrated. Tests whether selection
sharpens or whether top-3 is too narrow given thematic clustering.

Expected turnover: higher than m1 (~250-500% annual).

---

### m3 — `riskadj_mom_120_top5`

```
signal_m3(i, t) = mom_120(i, t) / max(vol_120(i, t), 1e-6)
weight_m3(i, t) = top_5(signal_m3, t) / 5
```

Slower lookback (~6 months). Tests whether the mechanism strengthens
at intermediate-term horizons (Moskowitz-Ooi-Pedersen 2012 favours
6-12 month windows for indices).

Expected turnover: lower than m1 (~80-200% annual).

---

### m4 — `riskadj_mom_20_top5`

```
signal_m4(i, t) = mom_20(i, t) / max(vol_20(i, t), 1e-6)
weight_m4(i, t) = top_5(signal_m4, t) / 5
```

Faster 1-month window. Probable failure mode: at 20d the mechanism
overlaps with short-term reversal (Jegadeesh 1990). If m4 underperforms
m1, this is the expected reading and confirms 60d is in the
right horizon band.

Expected turnover: high (~400-700% annual).

---

### m5 — `riskadj_mom_60_top5_ma50_gate`

```
signal_m5(i, t) = mom_60(i, t) / max(vol_60(i, t), 1e-6)
weight_raw_m5(i, t) = top_5(signal_m5, t) / 5
weight_m5(i, t)     = weight_raw_m5(i, t) * gate_ma50(t)   # cash when 510300 < MA50
```

m1 plus a broad-market trend filter. Expected to rescue worst-year by
flattening exposure during 2024-style deleveraging regimes.

Expected turnover: m1 turnover plus 1-2 extra entries/exits per
gate flip per year.

---

### m6 — `riskadj_mom_60_skip5_top5`

```
mom_60_skip5(i, t) = log(P[t-5]) - log(P[t-65])
signal_m6(i, t) = mom_60_skip5(i, t) / max(vol_60(i, t), 1e-6)
weight_m6(i, t) = top_5(signal_m6, t) / 5
```

Jegadeesh-Titman style "skip the most recent week" — designed to
isolate intermediate-term momentum from 1-week reversal. If m6 > m1,
short-term mean-reversion is contaminating m1's signal.

Expected turnover: similar to m1.

---

### m7 — `plain_mom_60_top5`  (CONTROL — no vol deflation)

```
signal_m7(i, t) = mom_60(i, t)
weight_m7(i, t) = top_5(signal_m7, t) / 5
```

The non-risk-adjusted control. If m1 ≈ m7 (within 0.1 Sharpe), then
vol-deflation is doing no real work and the mechanism is just plain
momentum. We expect m1 to beat m7 modestly (0.1-0.3 Sharpe).

Expected turnover: similar to m1.

---

### m8 — `sortino_mom_60_top5`

```
dvol_60(i, t) = std( clip(log_ret_i[t-59:t], max=0) )    # only negative days
signal_m8(i, t) = mom_60(i, t) / max(dvol_60(i, t), 1e-6)
weight_m8(i, t) = top_5(signal_m8, t) / 5
```

Sortino-flavoured. Replaces full-vol with downside vol only. Tests
whether the operative element of m1 is *risk* normalisation generally
or *downside-risk* normalisation specifically.

Expected turnover: similar to m1.

---

## Distinctness check

| pair | shared element | distinguishing element |
|---|---|---|
| m1–m2 | signal | top-N (5 vs 3) |
| m1–m3 | mechanism | lookback (60 vs 120) |
| m1–m4 | mechanism | lookback (60 vs 20) |
| m1–m5 | signal | regime gate (none vs MA50) |
| m1–m6 | mechanism | skip-5 lag |
| m1–m7 | top-N | vol deflation (yes vs no) |
| m1–m8 | mechanism | vol kind (full vs downside) |

All 8 are sufficiently distinct constructions; none is a
linear-combination dump.

## Rule-of-8 acknowledged

Exactly 8 expressions in this batch. Agent 4 must validate G1–G4
(import → run → non-degenerate → fidelity) before any submission.
