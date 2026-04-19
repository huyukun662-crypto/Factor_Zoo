# OpenClaw Dispatch Templates

## Coordinator dispatch order

1. `knowledge`
2. `planner`
3. `generator`
4. `backtest`
5. `evaluator`

## Stage 1 dispatch template

Send to `knowledge`:

```text
Run Stage 1 of the WorldQuant workflow as Research Librarian.
Read the session objective and constraints.
Return:
- research brief
- top mechanism candidates
- recommended datasets/operators
- main caveats
Write outputs to the agreed session folder.
```

## Stage 2 dispatch template

Send to `planner`:

```text
Run Stage 2 of the WorldQuant workflow as Hypothesis Architect.
Read the research brief and select one dominant mechanism.
Return:
- causal chain
- horizon and regime
- target metrics
- session metadata
Write outputs to the agreed session folder.
```

## Stage 3 dispatch template

Send to `generator`:

```text
Run Stage 3 of the WorldQuant workflow as Alpha Builder.
Use the selected mechanism and session metadata.
Generate exactly 8 expressions.
For each expression include rationale, expected turnover direction, and fragility notes.
Write outputs to the agreed session folder.
```

## Stage 4 dispatch template

Send to `backtest`:

```text
Run Stage 4 of the WorldQuant workflow as Backtest Operator.
Validate the 8 expressions before any submission.
If validation fails, stop and return fixes needed.
If validation passes, submit the batch, monitor conservatively, and return full results.
Write outputs to the agreed session folder.
```

## Stage 5 dispatch template

Send to `evaluator`:

```text
Run Stage 5 of the WorldQuant workflow as Evaluator & Recorder.
Rank the candidate expressions.
Return the best candidate, next-step decision, and round summary.
Decision must be one of:
- continue
- refine
- stop
Write outputs to the agreed session folder.
```

## Coordinator completion checklist

Before closing a round, verify these files exist:
- `research_brief.md`
- `session_metadata.yml`
- `expressions_batch_0001.md`
- `backtest_results_batch_0001.md`
- `alpha_ranking.md`
- `round_0001.yml`
- `run_state.json`
