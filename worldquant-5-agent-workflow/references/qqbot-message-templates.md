# QQBot Message Templates for WorldQuant 5-Agent Workflow

## User -> evaluator

### Start a new workflow

```text
启动一个新的 worldquant workflow

研究主题：analyst sentiment
输入类型：paper_report
输入内容：基于分析师情绪和预期差构建低换手 alpha
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
```

### Continue from an existing expression

```text
继续一个 worldquant workflow

输入类型：alpha_expression
输入内容：
ts_rank(close / ts_mean(close, 20), 10)

目标：
- 降低 turnover
- 提升 sub-universe sharpe
市场：US
股票池：TOP3000
delay：1
```

### Continue the last round

```text
继续上一轮 workflow，从 generator 阶段开始
本轮 focus：
- 保留主机制
- 降低 turnover
- 避免无效线性组合
```

## evaluator -> knowledge

```text
你现在是 WorldQuant workflow 的 Research Librarian。

任务：
基于以下研究目标，输出一份研究检索简报，供后续 planner 使用。

输入：
- research_topic: {研究主题}
- input_type: {economic_logic | alpha_expression | paper_report | improvement_direction}
- input_content:
{输入内容}

约束：
- region: {区域}
- universe: {股票池}
- delay: {delay}
- target_sharpe: {目标}
- target_fitness: {目标}
- target_turnover_max: {目标}
- extra_constraints:
{补充约束}

请输出：
1. 最相关的 1-3 个主机制候选
2. 推荐的数据字段 / dataset / operator
3. 降 turnover 或提升稳健性的注意点
4. 主要风险与 caveat
5. 一个推荐主方向

输出文件目标：
- research_brief.md
- handoff_1_to_2.json
```

## evaluator -> planner

```text
你现在是 WorldQuant workflow 的 Hypothesis Architect。

请基于 knowledge 阶段的研究简报，收敛为一个单一主机制，并形成实验设计。

输入：
- research_brief.md
- handoff_1_to_2.json

要求：
1. 只能选择 1 个 dominant mechanism
2. 给出 3-5 步 causal chain
3. 定义：
   - time horizon
   - market regime
   - risk premium source
   - failure conditions
4. 设定目标指标：
   - sharpe target
   - fitness target
   - turnover range
   - prod corr max
5. 给出建议 neutralization 候选

输出：
- session_metadata.yml
- handoff_2_to_3.json
```

## evaluator -> generator

```text
你现在是 WorldQuant workflow 的 Alpha Builder。

请基于 session_metadata 和 planner handoff，生成一批恰好 8 个表达式。

输入：
- session_metadata.yml
- handoff_2_to_3.json

硬性要求：
1. 必须输出恰好 8 个表达式
2. 8 个表达式必须围绕同一个 dominant mechanism
3. 不允许纯堆砌式线性组合
4. 每个表达式都要附：
   - economic rationale
   - expected turnover direction
   - fragility note

输出：
- expressions_batch_0001.md
- handoff_3_to_4.json
- round_0001.yml 中 expression_generation 部分草稿
```

## evaluator -> backtest

```text
你现在是 WorldQuant workflow 的 Backtest Operator。

请对以下 8 个表达式执行标准回测流程。

输入：
- expressions_batch_0001.md
- handoff_3_to_4.json

硬性要求：
1. 必须先 validate 全部 8 个表达式
2. validate 未全部通过，不得进入提交阶段
3. 若支持，必须使用 visualization=false
4. neutralization 必须从允许选项中选择
5. 不要高频轮询

请输出：
1. validate 结果
2. submission 状态
3. 回测结果表（至少包含 alpha_id / sharpe / fitness / turnover / ic）
4. 若失败，明确区分：
   - syntax/validation failure
   - platform/runtime failure
   - weak performance

输出：
- backtest_results_batch_0001.md
- handoff_4_to_5.json
- round_0001.yml 中 backtest 部分
```

## evaluator self-close

```text
你现在是 Evaluator & Recorder。

请基于 backtest 输出，对 8 个候选进行评估、排名和归档。

输入：
- backtest_results_batch_0001.md
- handoff_4_to_5.json
- round_0001.yml
- session_metadata.yml

要求：
1. 对全部候选按以下维度排序：
   - predictive power
   - sharpe / fitness
   - turnover realism
   - robustness
   - overfitting risk
2. 选出最优 candidate
3. 给出明确决策：
   - continue
   - refine
   - stop
4. 写出下一轮 focus
5. 更新：
   - alpha_ranking.md
   - round_0001.yml
   - run_state.json
6. 若研究结束，生成 final_summary.md
```

## evaluator -> user result templates

### refine

```text
本轮已完成。

结果摘要：
- 最优表达式：#{idx}
- Sharpe：{value}
- Fitness：{value}
- Turnover：{value}
- 结论：主机制成立，但实现仍需优化

下一步建议：
- 降低 turnover
- 改善中性化设置
- 保留当前主机制继续迭代

决策：refine
```

### continue

```text
本轮已完成。

结果摘要：
- 有 1-2 个候选接近目标
- 当前主机制有效
- 建议继续第二轮

下一轮 focus：
- 保留主机制
- 微调表达式结构
- 提升稳健性

决策：continue
```

### stop

```text
本轮已完成。

结果摘要：
- 当前机制在本轮 8 个表达式中未表现出足够信号强度
- 问题更像是机制层，而不是表达式层

结论：
- 建议停止当前方向
- 可以切换到新的机制重新开始

决策：stop
```

## Role-style bot reply guidance

When each bot replies in its own QQ conversation, the message must read like a human work update from that role, not a system notification shell.

Avoid this style:
- `[bot4/backtest] Round 2 Stage 4 detailed summary`
- `Stage complete`
- bare status lines without interpretation

Use this style instead:
- start directly with the role's conclusion
- explain what was done in this stage
- state the most important findings
- explain what looks strong / weak and why
- end with what the next stage should do

Role voice expectations:
- `bot1 / knowledge`: 像研究员在汇报研究发现与主方向建议
- `bot2 / planner`: 像策略规划师在解释为什么收敛到这个主机制、关键约束是什么
- `bot3 / generator`: 像因子生成员在解释这 8 个候选是如何围绕同一主机制展开的
- `bot4 / backtest`: 像回测员在汇报哪些结构最好、哪些最弱、主要差异在哪里
- `bot5 / evaluator`: 像最终评审在做排序、决策与下一轮建议

Recommended structure for every bot DM:
1. opening sentence in natural human voice
2. `本阶段做了什么`
3. `最重要的发现`
4. `风险/不足`
5. `下一步建议`
6. optional artifact/session reference at the bottom

## Per-bot C2C routing for QQBot

When the workflow must make each bot report in its own QQBot DM, use the per-account target mapping file:

- `C:\Users\Hu\.openclaw\workspace-evaluator\config\qqbot-c2c-targets.json`

Resolved mapping in the current environment:

- `bot1` -> `knowledge` -> `qqbot:c2c:D3F01C6F9F4A1F2F627B164B0DABC4A5`
- `bot2` -> `planner` -> `qqbot:c2c:2AE19BA45D83C01D429FC3A88673D264`
- `bot3` -> `generator` -> `qqbot:c2c:CF2DB72518D6F386C9CA2EE543B1440D`
- `bot4` -> `backtest` -> `qqbot:c2c:60396F28A42D29F5BAF88131B12CDD89`
- `bot5` -> `evaluator` -> `qqbot:c2c:1640FDB97DCB2CE312EEFC13771988AE`

Recommended official send pattern:

```text
openclaw message send --channel qqbot --account botX --target qqbot:c2c:<openid> --message "..."
```

Notes:
- Do not use `knowledge/planner/generator/backtest/evaluator` as QQBot account ids in outbound sends.
- Do not use `http://127.0.0.1:19001/send`; it is not a working public send route in this environment.
- For stage-complete notifications, the bot that owns the stage should send the user-facing QQBot DM from its own account.
- If a stage needs host exec approval, that same bot/session should be the one requesting approval.

## Execution discipline

- knowledge 只做检索，不做最终机制拍板。
- planner 只能收敛到一个主机制。
- generator 必须只出 8 个表达式。
- backtest 必须先 validate 再提交。
- evaluator 必须给出 continue / refine / stop。
