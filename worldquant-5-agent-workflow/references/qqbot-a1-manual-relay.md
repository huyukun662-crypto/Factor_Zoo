# QQBot A1 Manual Relay Mode

Use this mode when the user wants each QQBot agent to respond in its own conversation thread or DM, and a fully automatic cross-bot push model is not required.

## What A1 means

A1 is a **manual relay** workflow.

- The user speaks to each bot in sequence.
- Each bot performs only its own role.
- The user carries forward the structured summary to the next bot.
- A shared `session_id` keeps the round coherent.

## Bot role mapping

- `bot1` -> `knowledge`
- `bot2` -> `planner`
- `bot3` -> `generator`
- `bot4` -> `backtest`
- `bot5` -> `evaluator`

## Shared session rule

Every step must include the same `session_id`.

Example:

```text
session_id: 20260408_trial_sentiment_gpt
```

## Relay order

1. bot1 / knowledge
2. bot2 / planner
3. bot3 / generator
4. bot4 / backtest
5. bot5 / evaluator

## Step 1 — bot1 / knowledge

User should ask for:
- research brief
- 1-3 mechanism candidates
- recommended datasets/operators
- caveats
- planner handoff summary

Carry forward to bot2:
- mechanism candidates
- recommended direction
- caveats

## Step 2 — bot2 / planner

User should ask for:
- one dominant mechanism only
- causal chain
- horizon / regime
- target metrics
- generator handoff summary

Carry forward to bot3:
- dominant mechanism
- causal chain
- target metrics
- failure conditions

## Step 3 — bot3 / generator

User should ask for:
- exactly 8 expressions
- rationale for each expression
- expected turnover direction
- fragility notes
- backtest handoff summary

Carry forward to bot4:
- 8 expressions
- backtest constraints
- risk notes

## Step 4 — bot4 / backtest

User should ask for:
- validation result
- backtest submission/result summary
- error classification
- evaluator handoff summary

Carry forward to bot5:
- result table summary
- validation status
- error summary

## Step 5 — bot5 / evaluator

User should ask for:
- ranking
- best candidate
- continue / refine / stop
- next-round focus
- user-facing recommendation

## Why use A1

Use A1 when:
- each bot should visibly speak in its own QQBot conversation
- session mode is unavailable or unreliable
- the user prefers transparency over hidden coordination
- cross-bot automatic push is not yet implemented

## Limitations

- the user must manually relay summaries
- message flow is slower than a single-entry coordinator model
- consistency depends on keeping the same `session_id`

## Best practices

- relay structured summaries, not giant raw transcripts
- keep the same `session_id` throughout the round
- do not let planner choose multiple mechanisms
- do not let generator output anything other than exactly 8 expressions
- do not let backtest skip validation
- always end at evaluator for the round decision
