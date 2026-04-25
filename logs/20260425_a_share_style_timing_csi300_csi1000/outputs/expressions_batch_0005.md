# Expressions Batch 0005 (R5) — Agent 3 (Alpha Builder)

**Mechanism family**: M3_calm_regime_amplified (mirror of R4)
**Declared horizon**: 20 trading days · **Thesis sign**: +1 · **Rule of 8**: ✓
**Construction**: 7 mirror gates of R4 (negate the regime indicator inside tanh) + 1 combo (mirror gate × monthly rebalance).

| # | Name | Construction | Mirror of |
|---|---|---|---|
| 1 | `r5_e1_e4_x_neg_volgate_tanh_t1` | E4 × tanh(−vol_z / 1.0) | R4 E1 |
| 2 | `r5_e2_e4_x_neg_volgate_tanh_t2` | E4 × tanh(−vol_z / 2.0) | R4 E2 |
| 3 | `r5_e3_e4_x_neg_turnoverlevel_tanh` | E4 × tanh(−turnover_z / 1.5) | R4 E3 |
| 4 | `r5_e4_e4_x_neg_volgate_oneside` | E4 × max(0, tanh(−vol_z)) | R4 E4 (calm-only) |
| 5 | `r5_e5_e4_x_neg_composite` | E4 × tanh(−avg(vol, turn) / 1.5) | R4 E5 |
| 6 | `r5_e6_e2_x_neg_volgate_tanh_t1` | E2 × tanh(−vol_z / 1.0) | R4 E6 |
| 7 | `r5_e7_e4_x_neg_market_60d_gate` | E4 × tanh(−mkt60d_z / 1.0) | R4 E8 |
| 8 | `r5_e8_e4_x_neg_volgate_monthly` | E1 × 20d-discretization | R4 E1 + R4 E7 combo |

## Pre-registered honesty bars (session_metadata.yml round_0005)

5th round on the same test window. R5 PROMOTE bar:
- test IC t-stat ≥ **4.5** (vs R4's 4.0)
- worst-year Sharpe ≥ **0.7**
- R5 winner test Sharpe ≥ **+0.78** (R3 E4 +0.58 + 0.2 material improvement)
- all 5 mandatory audits pass
- economic story coherent with R1+R2+R3+R4 findings

## Math: R5 ≈ −R4 (gross), but cost is symmetric

For each i where R5 E_i is a sign-flipped gate of R4 E_i:
- R5_score = base × tanh(−x) = −(base × tanh(x)) = −R4_score
- R5_position = sign(R5_score) = −R4_position
- R5_pnl_gross = R5_position × spread_ret = −R4_pnl_gross
- R5_cost = |Δposition| × cost_rate = R4_cost (same magnitude)
- R5_pnl_net = −R4_pnl_gross − R4_cost = −(R4_pnl_net + 2 × R4_cost)

So R5 train Sharpe should be roughly −R4_train_sharpe with a small cost-adjustment downward. R4 E1 train Sh = −1.17 → R5 E1 train Sh ≈ +1.17 − ε.

E8 (combo) is genuinely new: it adds the 20d discretization on top of the reverse gate, expected to reduce turnover and cost by ~5×.

## Falsification conditions (from session_metadata.yml round_0005)

- TRAIN IC of mirror-gate variants is NOT positive
- R5 test Sharpe does not exceed R3 E4 +0.58 by ≥ +0.2
- 2025 worst-year Sharpe still below 0.5 → audit-3 still fails
- If all 8 R5 mirrors fail bars: M3 is genuinely 2025-broken regardless of regime axis

## Anti-clone

By construction, R5 expressions are tightly correlated with R4 mirrors
(corr ≈ −1) but anti-clone vs R1/R2 inherits from R4 (max |corr| ≤ 0.39
on TRAIN). Verified at runtime.
