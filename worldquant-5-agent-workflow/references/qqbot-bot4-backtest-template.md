# Bot4 / Backtest Template

Send this to **bot4 / backtest** after bot3 returns Stage 3.

```text
继续 WorldQuant 多 bot 手动接力流程

session_id: 20260408_trial_sentiment_gpt
role: backtest

以下是 generator 阶段输出：
- expressions:
  1. ...
  2. ...
  3. ...
  4. ...
  5. ...
  6. ...
  7. ...
  8. ...

要求：
1. 必须先 validate 全部 8 个表达式
2. validate 未全部通过，不得进入提交
3. 若支持，使用 visualization=false
4. 不要高频轮询
5. 结果里至少返回：
   - alpha_id
   - sharpe
   - fitness
   - turnover
   - ic
6. 若失败，请区分：
   - syntax/validation failure
   - platform/runtime failure
   - weak performance

请输出：
- validate 结果
- backtest 结果摘要
- handoff 给 evaluator 的摘要
```
