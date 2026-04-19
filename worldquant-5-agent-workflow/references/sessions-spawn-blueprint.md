# sessions_spawn Blueprint

Use this blueprint when bootstrapping persistent role sessions.

## Spawn knowledge session

```json
{
  "task": "WorldQuant role session bootstrap: Research Librarian. You will receive stage instructions later. Keep outputs artifact-oriented.",
  "label": "worldquant-knowledge",
  "runtime": "subagent",
  "agentId": "knowledge",
  "mode": "session",
  "cleanup": "keep",
  "sandbox": "inherit"
}
```

## Spawn planner session

```json
{
  "task": "WorldQuant role session bootstrap: Hypothesis Architect. You will receive stage instructions later. Keep outputs artifact-oriented.",
  "label": "worldquant-planner",
  "runtime": "subagent",
  "agentId": "planner",
  "mode": "session",
  "cleanup": "keep",
  "sandbox": "inherit"
}
```

## Spawn generator session

```json
{
  "task": "WorldQuant role session bootstrap: Alpha Builder. You will receive stage instructions later. Keep outputs artifact-oriented.",
  "label": "worldquant-generator",
  "runtime": "subagent",
  "agentId": "generator",
  "mode": "session",
  "cleanup": "keep",
  "sandbox": "inherit"
}
```

## Spawn backtest session

```json
{
  "task": "WorldQuant role session bootstrap: Backtest Operator. You will receive stage instructions later. Keep outputs artifact-oriented.",
  "label": "worldquant-backtest",
  "runtime": "subagent",
  "agentId": "backtest",
  "mode": "session",
  "cleanup": "keep",
  "sandbox": "inherit"
}
```

## Notes

- The evaluator remains the parent coordinator session.
- Reuse these sessions across rounds when possible.
- Keep session labels stable so `sessions_send` can target them reliably.
