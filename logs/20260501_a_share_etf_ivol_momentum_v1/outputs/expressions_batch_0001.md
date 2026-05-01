# Expressions Batch 0001 — Inverted IVOL Momentum on A-Share ETFs

Owner: Agent 3 (Alpha Builder).
Generated: 2026-05-01.
Mechanism: long-only top-N portfolio of high-IVOL A-share ETFs,
optionally gated by MA50 of 510300.

## Convention

`signal = +IVOL` (NOT negated). Higher signal value → long.

`r_i_t` = log return of ETF i on date t.
`r_M_t` = 510300 return on date t.
`β_i_t = roll_cov(r_i, r_M; 60d) / roll_var(r_M; 60d)` (backward, ≤ t).
`ε_i_t = r_i_t − β_i_t × r_M_t`.
`IVOL_i_t = roll_std(ε_i; 20d) × sqrt(252)`.
`MA50_t = mean(close_510300 over past 50 trading days)` (backward, ≤ t).
`gate_t = (close_510300_t > MA50_t)` evaluated at t, applied to the
position established at close(t+1).

Cross-section ranking is `groupby(date).rank(pct=True)`.

---

## E1 — `m1_ivol_LS_no_gate`  (LS baseline, control)

```
sig = +IVOL_resid_20d
LS = mean(top-quintile fwd return) - mean(bottom-quintile fwd return)
no regime gate
```

- Reproduces the parent session's +0.66 LS sensitivity.
- Provides a control for the "does gating help LS" question.

## E2 — `m2_ivol_top3_no_gate`  (long-only baseline)

```
sig = +IVOL_resid_20d
position = equal-weight top-3 by signal each rebalance
no regime gate
```

- The most concentrated long-only variant. No gate.
- Tests whether long-only top-3 already passes the worst-year floor.

## E3 — `m3_ivol_LS_ma50_gate`  (gated LS)

```
sig = +IVOL_resid_20d
gate_t = close_510300_t > MA50_t  (using only data <= t)
position = LS_q5_q1 × gate_t (zero when gate off)
```

- Gated LS variant. Tests whether the MA50 gate alone (without
  switching to long-only) rescues 2024.

## E4 — `m4_ivol_top3_ma50_gate`  (gated long-only top-3)

```
sig = +IVOL_resid_20d
position = top-3 EW × gate_t (cash when gate off)
```

- The primary deployable candidate. Concentrated, gated, long-only.

## E5 — `m5_ivol_top5_ma50_gate`  (gated long-only top-5)

```
sig = +IVOL_resid_20d
position = top-5 EW × gate_t
```

- Less-concentrated long-only with gate. Top-5 of 30 ≈ 17%
  concentration vs top-3's 10%.

## E6 — `m6_ivol_top5_ma200_gate`  (slow regime gate)

```
sig = +IVOL_resid_20d
gate_t = close_510300_t > MA200_t
position = top-5 EW × gate_t
```

- MA200 spends more time below price than MA50; less aggressive
  gate. Diagnostic: if m6 ≈ m5, gating speed isn't critical; if
  m6 < m5, MA50 specifically captures the right regime.

## E7 — `m7_ivol_top5_ma50_lag5`  (lagged signal sensitivity)

```
sig = +IVOL_resid_20d_t-5  (signal observed 5 days ago)
position = top-5 EW (selected at t using sig at t-5) × gate_t
```

- Tests signal stability. If m7 ≈ m5, the IVOL signal decays slowly
  and our weekly-or-better rebalance is fine. If m7 < m5, IVOL is a
  fast-decay signal needing tighter rebalance.

## E8 — `m8_total_vol_top5_ma50_gate`  (no residualization control)

```
sig = +std(r_i; 20d) × sqrt(252)        # raw vol, no beta residualization
position = top-5 EW × gate_t
```

- Uses raw 20-day std instead of residual std.
- Diagnostic: if m8 ≈ m5, the cross-section's beta-dispersion is
  small enough that residualization isn't doing meaningful work.
  If m8 < m5, the residualization is genuinely informative.

---

## Pre-flight check

| Check | Status |
|---|---|
| Exactly 8 expressions | ✅ E1–E8 |
| All share dominant mechanism (inverted-IVOL) | ✅ |
| Sign convention: high signal = long | ✅ |
| No look-ahead in formulas | ✅ all rolling windows backward; MA50 uses ≤ t |
| Position established at close(t+1) (delay=1) | ✅ |
| Regime gate uses only data ≤ t | ✅ |
| Top-N variants stated | ✅ top-3 (m2, m4) and top-5 (m5, m6, m7, m8) |
| LS baselines included | ✅ m1 (no gate), m3 (gated) |
| Includes residualization-vs-total-vol control | ✅ m8 |
| Includes lag-stability control | ✅ m7 |

## Expected outcomes by question

| Question | Expression | Expected if hypothesis holds |
|---|---|---|
| Does MA50 rescue 2024? | m3 vs m1, m4/m5 vs m2 | gated 2024 Sharpe ≥ 0.5 |
| Top-N better than LS? | m2/m4/m5 vs m1/m3 | top-N excess Sharpe > LS Sharpe |
| Top-3 vs top-5? | m4 vs m5 | top-3 higher gross, top-5 better worst-year |
| MA50 vs MA200? | m6 vs m5 | m5 ≥ m6 (MA50 is the right speed) |
| Residualization needed? | m8 vs m5 | m5 ≥ m8 (residualization adds Sharpe) |
| Signal stable to lag? | m7 vs m5 | m7 ≈ m5 (slow-decay) |
| Orthogonal to V7_gold? | all weekly | |corr| ≤ 0.5 |
