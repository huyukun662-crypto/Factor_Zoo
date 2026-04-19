# OpenClaw Call Examples

This file shows realistic tool-call patterns the evaluator-coordinator can follow.

## 1. Spawn persistent role sessions

### Spawn knowledge

```json
{
  "tool": "sessions_spawn",
  "arguments": {
    "task": "WorldQuant role session bootstrap: Research Librarian. You will receive stage instructions later. Keep outputs artifact-oriented.",
    "label": "worldquant-knowledge",
    "runtime": "subagent",
    "agentId": "knowledge",
    "mode": "session",
    "cleanup": "keep",
    "sandbox": "inherit"
  }
}
```

### Spawn planner

```json
{
  "tool": "sessions_spawn",
  "arguments": {
    "task": "WorldQuant role session bootstrap: Hypothesis Architect. You will receive stage instructions later. Keep outputs artifact-oriented.",
    "label": "worldquant-planner",
    "runtime": "subagent",
    "agentId": "planner",
    "mode": "session",
    "cleanup": "keep",
    "sandbox": "inherit"
  }
}
```

### Spawn generator

```json
{
  "tool": "sessions_spawn",
  "arguments": {
    "task": "WorldQuant role session bootstrap: Alpha Builder. You will receive stage instructions later. Keep outputs artifact-oriented.",
    "label": "worldquant-generator",
    "runtime": "subagent",
    "agentId": "generator",
    "mode": "session",
    "cleanup": "keep",
    "sandbox": "inherit"
  }
}
```

### Spawn backtest

```json
{
  "tool": "sessions_spawn",
  "arguments": {
    "task": "WorldQuant role session bootstrap: Backtest Operator. You will receive stage instructions later. Keep outputs artifact-oriented.",
    "label": "worldquant-backtest",
    "runtime": "subagent",
    "agentId": "backtest",
    "mode": "session",
    "cleanup": "keep",
    "sandbox": "inherit"
  }
}
```

## 2. Send a research-stage message

```json
{
  "tool": "sessions_send",
  "arguments": {
    "label": "worldquant-knowledge",
    "message": "Run Stage 1 as Research Librarian. Read logs/{session_id}/inputs/objective.md. Write outputs/research_brief.md and working/handoff_1_to_2.json. Return 1-3 mechanism candidates, recommended datasets/operators, and caveats."
  }
}
```

## 3. Send a planning-stage message

```json
{
  "tool": "sessions_send",
  "arguments": {
    "label": "worldquant-planner",
    "message": "Run Stage 2 as Hypothesis Architect. Read outputs/research_brief.md and working/handoff_1_to_2.json. Write outputs/session_metadata.yml and working/handoff_2_to_3.json. Choose exactly one dominant mechanism and define target metrics."
  }
}
```

## 4. Send a generation-stage message

```json
{
  "tool": "sessions_send",
  "arguments": {
    "label": "worldquant-generator",
    "message": "Run Stage 3 as Alpha Builder. Read outputs/session_metadata.yml and working/handoff_2_to_3.json. Write outputs/expressions_batch_0001.md and working/handoff_3_to_4.json. Produce exactly 8 expressions with rationale and expected turnover direction."
  }
}
```

## 5. Send a backtest-stage message

```json
{
  "tool": "sessions_send",
  "arguments": {
    "label": "worldquant-backtest",
    "message": "Run Stage 4 as Backtest Operator. Read outputs/expressions_batch_0001.md and working/handoff_3_to_4.json. Validate before any submission. Write outputs/backtest_results_batch_0001.md and working/handoff_4_to_5.json."
  }
}
```

## 6. Evaluate locally in the current evaluator session

```text
Read:
- outputs/backtest_results_batch_0001.md
- working/handoff_4_to_5.json
- outputs/session_metadata.yml
- round_0001.yml

Then:
- rank candidates
- select best alpha
- decide continue / refine / stop
- write alpha_ranking.md
- update round_0001.yml
- update run_state.json
```

## 7. Artifact checks

Typical coordinator checks:

```text
read outputs/research_brief.md
read working/handoff_1_to_2.json
read outputs/session_metadata.yml
read outputs/expressions_batch_0001.md
read outputs/backtest_results_batch_0001.md
```

If a required artifact is missing or malformed, send a corrective follow-up instead of advancing.
