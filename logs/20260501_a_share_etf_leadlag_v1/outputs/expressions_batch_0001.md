# Expressions Batch 0001 — Broad-Market Lead-Lag Spillover v1

Owner: Agent 3 (Alpha Builder).
Generated: 2026-05-01.
Mechanism: cross-sectional rank of beta-projected lagged broad-ETF
return.

## Convention

`r_i_t` = log return of ETF i on date t.
`L = {510300.SS, 510500.SS, 159915.SZ}` = leader set.
`β_iL_t = cov(r_i, r_L; 60d) / var(r_L; 60d)` (backward, ends at t).
For leaders the diagonal is masked: leader L gets signal 0 from itself.

All formulas use `r_L_(t-lag)` — leader return at the past, never at t+1.

Cross-section ranking is `groupby(date).rank(pct=True)`.
**Higher signal → long.**

---

## E1 — `g1_spillover_3leader_lag1`  (headline)

```
for each leader L in {510300, 510500, 159915}:
    beta_iL = roll_cov(r_i, r_L, 60) / roll_var(r_L, 60)
    s_iL = beta_iL * shift(r_L, 1)         # t-1 leader return
signal = mean over L of s_iL
mask diagonal: signal[L_self] = 0
```

- 3-leader equal-weight, lag 1, beta-projected.
- Expected: positive IC at k=1 (next-day diffusion), decaying by k=3.
- Expected turnover: high (~800-1200%/yr) — daily rebalance with rank-
  based factor on a moving leader signal.

## E2 — `g2_spillover_510300only_lag1`  (single-leader control)

```
beta_i = roll_cov(r_i, r_510300, 60) / roll_var(r_510300, 60)
signal = beta_i * shift(r_510300, 1)
mask diagonal
```

- Single-leader. Diagnostic: if E2 IC ≈ E1 IC, the multi-leader
  aggregation isn't adding value (likely because leaders are themselves
  ~80% correlated).
- Expected turnover: similar to E1.

## E3 — `g3_spillover_3leader_lag1to2_decay`  (cumulative diffusion)

```
for each leader L:
    beta_iL = roll_cov(r_i, r_L, 60) / roll_var(r_L, 60)
    s_iL = beta_iL * (0.7 * shift(r_L, 1) + 0.3 * shift(r_L, 2))
signal = mean over L of s_iL
mask diagonal
```

- Two-step diffusion with exponential-ish decay weights.
- Tests whether 2-day-old leader info still has value.

## E4 — `g4_spillover_residual_leader_lag1`  (clean-leader)

```
leader_resid_L_t = r_L_t - mean(r_L over past 20d)   # leader's surprise vs MA
for each leader L:
    beta_iL = roll_cov(r_i, r_L, 60) / roll_var(r_L, 60)
    s_iL = beta_iL * shift(leader_resid_L, 1)
signal = mean over L of s_iL
mask diagonal
```

- Use leader's *surprise* (residual to its own 20d MA) instead of raw
  leader return. Filters slow-drift information.
- Expected: cleaner short-horizon predictor.

## E5 — `g5_spillover_3leader_lag1_volscaled`  (vol-scaled)

```
for each leader L:
    beta_iL = roll_cov(r_i, r_L, 60) / roll_var(r_L, 60)
    s_iL = beta_iL * shift(r_L, 1)
raw = mean over L of s_iL
signal = raw / roll_std(r_i, 20)            # scale by follower vol
mask diagonal
```

- Vol-scaling: equalize signal magnitude across high-vol and low-vol
  followers so the cross-section isn't dominated by gold (518880, low
  vol) or 半导体 (high vol).

## E6 — `g6_spillover_3leader_orthogonalized`  (subtract own contemp)

```
for each leader L:
    beta_iL = roll_cov(r_i, r_L, 60) / roll_var(r_L, 60)
    s_iL = beta_iL * shift(r_L, 1)
raw = mean over L of s_iL
follower_resid_at_t1 = shift(r_i, 1) - raw  # follower's t-1 return minus what beta predicts
signal = raw - follower_resid_at_t1         # net "info not yet absorbed"
mask diagonal
```

- Subtract the part of the leader move that the follower has already
  absorbed at t-1. Picks up the *unfinished* portion of diffusion.

## E7 — `g7_spillover_signonly_3leader`  (sign-only / magnitude-free)

```
for each leader L:
    beta_iL = roll_cov(r_i, r_L, 60) / roll_var(r_L, 60)
    s_iL = sign(shift(r_L, 1)) * |beta_iL|
signal = mean over L of s_iL
mask diagonal
```

- Direction-only variant. Robust to leader vol regime shifts but loses
  magnitude information.

## E8 — `g8_kitchen_sink_rank`  (composite)

```
signal = mean_rank([
    rank(g1_spillover_3leader_lag1),
    rank(g4_spillover_residual_leader_lag1),
    rank(g5_spillover_3leader_lag1_volscaled),
    rank(g7_spillover_signonly_3leader)
])
```

- Cross-sectional rank composite of the four most-distinct lead-lag
  flavors.

---

## Pre-flight check

| Check | Status |
|---|---|
| Exactly 8 expressions | ✅ E1-E8 |
| All share dominant mechanism (lead-lag spillover) | ✅ all use lagged leader return × beta |
| Sign convention "high signal = long" | ✅ |
| No look-ahead | ✅ all use shift(r_L, 1) or earlier |
| Self-signal masked | ✅ diagonal zeroed where leader == follower |
| Inputs in shared cache | ✅ |
| No identical formulas | ✅ varies on aggregation, lag-decay, residualization, scaling, sign-only |
