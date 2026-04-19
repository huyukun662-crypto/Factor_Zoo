# Coordinator Pseudocode

This file gives the evaluator-coordinator a stage-by-stage pseudocode flow.

## Minimal loop

```text
receive user objective
resolve or create session_id
initialize session folder
ensure role sessions exist
run research stage
validate research outputs
run planning stage
validate planning outputs
run generation stage
validate expression count == 8
run backtest stage
validate result artifacts
evaluate locally
write ranking and state
reply to user
```

## Detailed pseudocode

```text
function run_worldquant_round(user_objective):
    session_id = ensure_session(user_objective)
    ensure_session_folder(session_id)
    write_objective(session_id, user_objective)
    ensure_role_sessions()

    send_research_task(session_id)
    wait_for_research_completion(session_id)
    assert_exists(outputs/research_brief.md)
    assert_exists(working/handoff_1_to_2.json)
    notify_stage_complete(stage=1, artifact=outputs/research_brief.md)

    send_planning_task(session_id)
    wait_for_planning_completion(session_id)
    assert_exists(outputs/session_metadata.yml)
    assert_exists(working/handoff_2_to_3.json)
    notify_stage_complete(stage=2, artifact=outputs/session_metadata.yml)

    send_generation_task(session_id)
    wait_for_generation_completion(session_id)
    assert_exists(outputs/expressions_batch_0001.md)
    assert_expression_count(8)
    assert_exists(working/handoff_3_to_4.json)
    notify_stage_complete(stage=3, artifact=outputs/expressions_batch_0001.md)

    send_backtest_task(session_id)
    wait_for_backtest_completion(session_id)
    assert_exists(outputs/backtest_results_batch_0001.md)
    assert_exists(working/handoff_4_to_5.json)
    notify_stage_complete(stage=4, artifact=outputs/backtest_results_batch_0001.md)

    evaluate_round(session_id)
    write_alpha_ranking(session_id)
    update_round_log(session_id)
    update_run_state(session_id)
    notify_stage_complete(stage=5, artifact=outputs/alpha_ranking.md)
    reply_to_user(session_id)
```

## Recovery logic

```text
if research outputs missing:
    resend to knowledge with correction request

if planning outputs missing or mechanism not singular:
    resend to planner with narrowing request

if generation produced not exactly 8 expressions:
    resend to generator with strict count correction

if backtest failed before submission:
    route back to generator or planner depending on failure type

if evaluation says continue or refine:
    create next round or repeat generation with focused changes
```

## Notification helper

```text
function notify_stage_complete(stage, artifact):
    run:
    python C:\Users\Hu\.openclaw\workspace-evaluator\scripts\worldquant_stage_notify.py \
      --stage <stage> \
      --title "Stage <stage> complete" \
      --summary "Validated artifacts are ready for the user." \
      --session-id <session_id> \
      --artifact <artifact>
```

Only call this helper after all required artifact checks for that stage have passed.

## Coordinator invariants

- Never advance without required artifacts.
- Never let generator return fewer or more than 8 expressions.
- Never let backtest submit without validation.
- Always update `run_state.json` after each stage transition.
- Always give the user a visible round summary.
