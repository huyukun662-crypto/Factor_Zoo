# Handoff Schemas

Use these lightweight JSON contracts between agents.

## handoff_1_to_2.json

```json
{
  "objective": "string",
  "mechanism_candidates": [
    {
      "name": "string",
      "why": "string",
      "supporting_evidence": ["string"],
      "datasets": ["string"],
      "operators": ["string"],
      "caveats": ["string"]
    }
  ],
  "recommended_focus": "string"
}
```

## handoff_2_to_3.json

```json
{
  "selected_mechanism": "string",
  "causal_chain": ["string", "string", "string"],
  "time_horizon": "string",
  "market_regime": "string",
  "risk_premium_sources": ["string"],
  "constraints": {
    "dataset_id": "string",
    "region": "string",
    "universe": "string",
    "delay": 1,
    "turnover_range": [0.0, 0.7],
    "sharpe_target": 1.25,
    "fitness_target": 1.0,
    "prod_corr_max": 0.7
  },
  "neutralization_candidates": ["SLOW", "FAST"]
}
```

## handoff_3_to_4.json

```json
{
  "batch_id": "batch_0001",
  "selected_mechanism": "string",
  "expressions": [
    {
      "idx": 1,
      "code": "string",
      "rationale": "string",
      "expected_turnover_direction": "lower|neutral|higher",
      "fragility_notes": ["string"]
    }
  ]
}
```

## handoff_4_to_5.json

```json
{
  "batch_id": "batch_0001",
  "validation_passed": true,
  "submission_made": true,
  "results": [
    {
      "expression_idx": 1,
      "alpha_id": "string",
      "sharpe": 0.0,
      "fitness": 0.0,
      "turnover": 0.0,
      "ic": 0.0,
      "status": "completed|failed",
      "error": null
    }
  ],
  "anomalies": ["string"]
}
```

## Evaluator decision block

Append this structure into `run_state.json` after each round:

```json
{
  "round": 1,
  "decision": "continue|refine|stop",
  "best_expression_idx": 3,
  "best_alpha_id": "A12345",
  "why": "string",
  "next_round_focus": ["string"]
}
```
