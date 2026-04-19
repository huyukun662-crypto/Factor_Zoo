# Bot3 / Generator Template

Send this to **bot3 / generator** after bot2 returns Stage 2.

```text
继续 WorldQuant 多 bot 手动接力流程

session_id: 20260408_trial_sentiment_gpt
role: generator

以下是 planner 阶段输出摘要：
- dominant mechanism: {唯一主机制}
- causal chain: {3-5步因果链}
- time horizon: {时间尺度}
- market regime: {适用市场环境}
- target:
  - sharpe >= 1.25
  - fitness >= 1.0
  - turnover <= 0.45

硬性要求：
1. 必须生成恰好 8 个表达式
2. 所有表达式必须围绕同一个 dominant mechanism
3. 不允许纯堆砌式线性组合
4. 每个表达式都附：
   - economic rationale
   - expected turnover direction
   - fragility note

请输出：
- expressions 1~8
- 每个表达式的解释
- handoff 给 backtest 的摘要
```
