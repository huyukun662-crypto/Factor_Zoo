# Expressions · Batch 0001 · Variant A (penalized combine)

**Session**: `20260422_industry_rotation_cn`
**Agent 3** · Alpha Builder · 2026-04-22
**Family**: A — 动量减拥挤罚分,一个分排序 Top-3。

## Common setup

- 面板:`outputs/industry_weekly.parquet`(31 SW L1 行业,周频,2018-01 → 2026-04)
- 输入列:`ret_w`, `turnover_mv_w`, `cum_w`
- 持仓:Top-3 long-only 等权
- 再平衡:每周(周五信号,下周一执行,`delay=1`)
- 成本:单边 5 bps
- 基准:行业等权组合(31 个等权)

## Signal construction

```python
# For each week t, for each industry i:
mom_W[i,t]  = cum[i,t] / cum[i,t-W] - 1             # past W-week return
turn_W[i,t] = mean(turnover_mv[i, t-W+1..t])        # past W-week avg turnover (crowding proxy)
z_x[i,t]    = (x[i,t] - mean_i(x[·,t])) / std_i(x[·,t])  # cross-section z at t

breadth[i,t] = cross-section %above_ma20 (market-wide), same for all i (a gate-like mod)

score[i,t]  = z(mom_W) - lambda * z(turn_W) + mu * breadth
```

Holdings at t are **highest-score Top-3**, rebalanced weekly; execution @ t+1 open.

## 8 specs

| name | mom_W | turn_W | lambda | mu | note |
|---|---|---|---|---|---|
| A1_lam05_m4_t4  | 4w  | 4w | 0.5 | 0.0 | 轻罚分 |
| A2_lam10_m4_t4  | 4w  | 4w | 1.0 | 0.0 | 中罚分(中心网格) |
| A3_lam15_m4_t4  | 4w  | 4w | 1.5 | 0.0 | 重罚分 |
| A4_lam10_m8_t4  | 8w  | 4w | 1.0 | 0.0 | 更长动量 |
| A5_lam10_m12_t4 | 12w | 4w | 1.0 | 0.0 | 季度动量 |
| A6_lam10_m4_t8  | 4w  | 8w | 1.0 | 0.0 | 更平滑拥挤 |
| A7_lam10_m4_t4_b| 4w  | 4w | 1.0 | 0.3 | +市场广度修正 |
| A8_lam00_m4_pure| 4w  | —  | 0.0 | 0.0 | 纯动量基线(对照) |

Handoff → Agent 4 (`handoff_3_to_4_batch_0001.json`).
