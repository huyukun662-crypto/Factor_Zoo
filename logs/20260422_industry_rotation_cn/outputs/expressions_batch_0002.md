# Expressions · Batch 0002 · Variant B (layered filter)

**Session**: `20260422_industry_rotation_cn`
**Agent 3** · Alpha Builder · 2026-04-22
**Family**: B — 先动量选主线(Top-K),再拥挤度最低挑 Top-3。

## Signal

```python
# Step 1: momentum filter
mom_W[i,t] = cum[i,t] / cum[i,t-W] - 1
top_K at t = {i : rank_desc(mom_W[·,t]) <= K}

# Step 2: crowding within filter
turn_W[i,t] = mean(turnover_mv[i, t-W+1..t])
selected at t = lowest-3 turn_W among top_K
```

## 8 specs

| name | mom_W | turn_W | K | variant |
|---|---|---|---|---|
| B1_m4_K10_t4   | 4w  | 4w  | 10 | 主规范 |
| B2_m4_K8_t4    | 4w  | 4w  | 8  | 更紧主线 |
| B3_m4_K14_t4   | 4w  | 4w  | 14 | 更宽主线 |
| B4_m8_K10_t4   | 8w  | 4w  | 10 | 中期动量 |
| B5_m12_K10_t4  | 12w | 4w  | 10 | 季度动量 |
| B6_m4_K10_t8   | 4w  | 8w  | 10 | 更平滑拥挤 |
| B7_m4_K10_t4_br| 4w  | 4w+breadth | 10 | 2步排序用 turn−0.3·breadth |
| B8_m4_K10_dturn| 4w  | turn_4w/turn_52w-1 | 10 | 拥挤 *delta*(相对自身历史) |

Handoff → Agent 4 (`handoff_3_to_4_batch_0002.json`).
