# Expressions · Batch 0003 · Variant C (reversal)

**Session**: `20260422_industry_rotation_cn`
**Agent 3** · Alpha Builder · 2026-04-22
**Family**: C — 行业层面短期反转。买跌卖涨 1-4w。

## Signal

```python
mom_W[i,t] = cum[i,t] / cum[i,t-W] - 1
score[i,t] = -mom_W[i,t]              # higher = more reversal candidate
# optional crowd amplifier: score *= 1 + alpha * z(turn_W)
# select top-3 by score (i.e., 3 worst-performing)
```

## 8 specs

| name | W (rev lookback) | amplifier | structure |
|---|---|---|---|
| C1_rev1w        | 1w | — | long bottom-3 |
| C2_rev2w        | 2w | — | long bottom-3 |
| C3_rev3w        | 3w | — | long bottom-3 |
| C4_rev4w        | 4w | — | long bottom-3 |
| C5_rev2w_crowdx | 2w | 0.5·z(turn_2w) | 强化炒作反噬 |
| C6_rev4w_crowdx | 4w | 0.5·z(turn_4w) | 强化炒作反噬 |
| C7_rev2w_long   | 2w | — | long bottom-3(记作主规范之另一基线) |
| C8_rev2w_LS     | 2w | — | long bottom-3, short top-3 (LS) |

Handoff → Agent 4 (`handoff_3_to_4_batch_0003.json`).
