# Bot2 / Planner Template

Send this to **bot2 / planner** after bot1 returns Stage 1.

```text
继续 WorldQuant 多 bot 手动接力流程

session_id: 20260408_trial_sentiment_gpt
role: planner

以下是 knowledge 阶段结果摘要：
- mechanism candidates:
  1. news surprise / sentiment shock
  2. sentiment dispersion / disagreement
  3. narrative persistence / sentiment trend decay

- 推荐方向：
  优先考虑 company-level timestamped news/headline dataset
  不建议直接使用 raw sentiment level

- caveats:
  - timestamp integrity
  - coverage imbalance
  - label consistency
  - event/regime dependence

请你：
1. 只能选择 1 个 dominant mechanism
2. 给出 causal chain
3. 定义：
   - time horizon
   - market regime
   - risk premium source
   - failure conditions
4. 输出 session metadata 摘要
5. 给出 handoff 给 generator 的摘要
```
