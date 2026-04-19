# Bot1 / Knowledge Template

Send this to **bot1 / knowledge** to start Stage 1.

```text
启动 WorldQuant 多 bot 手动接力流程

session_id: 20260408_trial_sentiment_gpt
role: knowledge

研究主题：trial sentiment alpha
输入类型：paper_report
输入内容：基于分析师情绪、预期差和市场消化滞后构建低换手 alpha
市场：US
股票池：TOP3000
delay：1
目标：
- sharpe >= 1.25
- fitness >= 1.0
- turnover <= 0.45
补充约束：
- 优先低换手
- 避免过强 crowding
- 一轮先只做 8 个表达式

请输出：
- research brief
- 1~3 个 mechanism candidates
- 推荐 datasets/operators
- 关键 caveats
- handoff 给 planner 的摘要
```
