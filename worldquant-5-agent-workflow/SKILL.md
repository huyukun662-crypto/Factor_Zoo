---
name: worldquant-5-agent-workflow
description: Transform the GRD-Chang/worldquant-skill repository into an OpenClaw-compatible multi-agent research workflow for WorldQuant BRAIN. Use when the user wants to run or adapt a quant alpha research pipeline that includes knowledge retrieval, hypothesis formation, expression generation, batch backtesting, evaluation/ranking, and research logging with a 5-agent division of labor.
---

# WorldQuant 5-Agent Workflow

Build and run a 5-agent alpha-research workflow inspired by `GRD-Chang/worldquant-skill`, but adapted for OpenClaw-style orchestration.

## Goal

Turn the original 3-skill design:
- knowledge base search
- factor backtest
- alpha research recorder

into a clearer 5-agent workflow with explicit ownership for each research stage.

## The 5 Agents

### Agent 1: Research Librarian
Own knowledge retrieval.

Responsibilities:
- Search local/reference knowledge about operators, datasets, turnover control, neutralization, and prior examples.
- Distill a short evidence pack for the rest of the workflow.
- Cite exact file paths or source sections when possible.

Inputs:
- research objective
- factor idea / paper / improvement direction
- constraints

Outputs:
- `research_brief.md`
- candidate mechanisms
- operator and dataset suggestions
- risks / caveats

### Agent 2: Hypothesis Architect
Own economic logic and experiment design.

Responsibilities:
- Convert the research brief into one primary mechanism and a narrow testable hypothesis.
- Define market regime, horizon, risk-premium source, and failure conditions.
- Choose the experiment settings that downstream agents should respect.

Outputs:
- `session_metadata.yml`
- experiment assumptions
- evaluation targets
- neutralization rationale candidates

### Agent 3: Alpha Builder
Own expression generation.

Responsibilities:
- Produce exactly 8 candidate expressions per batch.
- Keep expressions aligned to one dominant mechanism.
- Avoid loose linear-combination dumping.
- Attach a one-paragraph economic explanation for each expression.

Hard constraints:
- Produce exactly 8 expressions.
- Keep expressions sufficiently distinct in construction.
- State expected turnover direction and why.

Outputs:
- `expressions_batch_0001.md`
- `round_0001.yml` draft sections for expression generation

### Agent 4: Backtest Operator
Own simulation execution and error handling.

Responsibilities:
- Validate all 8 expressions before submission.
- Run the batch backtest.
- Monitor status conservatively.
- Collect complete outputs and errors.

Hard constraints inherited from the source repository:
- Rule of 8: submit exactly 8 expressions.
- Set `visualization=false` when supported by the target system.
- Use an allowed neutralization mode only.
- Never continue to submission if validation is not fully passed.
- Do not tight-loop polling.

Outputs:
- `backtest_results_batch_0001.json` or `.md`
- `round_0001.yml` backtest section
- failure notes when needed

### Agent 5: Evaluator & Recorder
Own ranking, recommendation, and durable logging.

Responsibilities:
- Evaluate candidates on predictive power, risk-adjusted returns, stability, drawdown, and turnover.
- Rank the candidates.
- Decide whether to continue, refine, or stop.
- Write structured logs and final summary.

Evaluation priorities:
- IC mean / IC stability / IR
- Sharpe / fitness / drawdown trade-off
- turnover realism
- robustness across settings or years when available
- overfitting risk

Outputs:
- `alpha_ranking.md`
- updated `round_0001.yml`
- `final_summary.md` when the study ends

## Shared Workflow Contract

Use this sequence unless the user explicitly asks to skip steps:

1. Research Librarian prepares evidence.
2. Hypothesis Architect defines the economic thesis and constraints.
3. Alpha Builder creates one 8-expression batch.
4. Backtest Operator validates and runs the batch.
5. Evaluator & Recorder ranks results and decides next action.

## Standard Artifacts

Store outputs in a per-session folder like:

```text
logs/
└── YYYYMMDD_topic_model/
    ├── research_brief.md
    ├── session_metadata.yml
    ├── expressions_batch_0001.md
    ├── backtest_results_batch_0001.md
    ├── round_0001.yml
    └── final_summary.md
```

## Mapping from Original Repository

Translate the original repository into this 5-agent split:

- `knowledge_base_search` -> Agent 1 Research Librarian
- planning parts of the README workflow -> Agent 2 Hypothesis Architect
- expression drafting implied by the workflow -> Agent 3 Alpha Builder
- `factor_backtest` -> Agent 4 Backtest Operator
- `alpha-research-recorder` + evaluation step -> Agent 5 Evaluator & Recorder

## Minimal Operating Rules

- Keep one dominant economic mechanism per batch.
- Use exactly 8 expressions per backtest batch.
- Log key decisions immediately; do not rely on memory.
- Prefer one complete batch with clear reasoning over many weak variants.
- If backtests fail due to syntax or invalid operators, fix the expressions before retrying.
- If results are mediocre, explain whether the issue is mechanism weakness, implementation weakness, or parameter mismatch.

## Mandatory audit rules (added after real mistakes — see `references/common-pitfalls.md`)

Never issue a PROMOTE / paper-trading recommendation without:

1. **Execution-delay audit** — physical timeline in prose, invariant
   `target_shift == -(1 + delay)`, future-perturbation test, target-mask
   provenance audit, IC decay by delay chart. Default `delay=1`. See
   `references/execution-delay-audit.md`.
2. **Look-ahead audit** — randomize future bars and confirm past factor
   values are bit-identical. Grep the factor code for any `.where(mask)`
   where `mask` is derivable from `ret.shift(-k)` or any `next_*` variable.
3. **Worst-year floor** — worst year in test window must have Sharpe ≥ 0.5.
   "N of N years positive" is not a substitute — check the distribution.
4. **Best-year-out check** — test Sharpe recomputed without the single best
   year must still be ≥ 50% of the headline Sharpe.
5. **Falsification-first mindset** — before writing the decision, answer:
   "If this Sharpe is wrong by 50%, what is the most likely single cause?"
   and run the test that would prove that cause. Confirmation bias
   accumulates across R1→R2→R3 unless adversarially attacked at each
   round.

If any of the five above fails, the decision is RESEARCH-ONLY, not PROMOTE.

## When to read bundled references

## When to read bundled references

Read `references/repo-summary.md` when you need the source repository summary.

Read `references/workflow-template.md` when you need a ready-to-run human-readable SOP for the 5-agent process.

Read `references/agent-prompts.md` when you want role prompts or handoff contracts for each of the 5 agents.

Read `references/execution-plan.md` when you need the coordinator procedure, session-folder layout, and stage-by-stage validation rules.

Read `references/handoff-schemas.md` when you need machine-readable JSON handoff contracts between agents.

Read `references/openclaw-agent-mapping.md` when the environment already has role-specific OpenClaw agents such as `knowledge`, `planner`, `generator`, `backtest`, and `evaluator`.

Read `references/coordinator-prompt-template.md` when you want a parent orchestrator prompt for real OpenClaw dispatch.

Read `references/coordinator-execution-spec.md` when you want the evaluator session to act as the real coordinator with explicit state transitions and failure handling.

Read `references/sessions-orchestration-spec.md` when you want to orchestrate the workflow through OpenClaw session tools.

Read `references/sessions-send-templates.md` when you want ready-to-send coordinator messages for each role session.

Read `references/sessions-spawn-blueprint.md` when you want blueprint payloads for bootstrapping persistent role sessions.

Read `references/qqbot-message-templates.md` when you want user-facing QQBot conversation templates.

Read `references/qqbot-a1-manual-relay.md` when the user wants each QQBot agent to respond in its own conversation and the workflow should proceed as a visible manual relay across bot1..bot5.

Read `references/openclaw-dispatch-templates.md` when you want short stage dispatch templates for a coordinator.

Read `references/coordinator-pseudocode.md` when you want a full stage-by-stage coordinator logic flow.

Read `references/openclaw-call-examples.md` when you want near-real tool-call examples for `sessions_spawn` and `sessions_send`.

Read `references/automation-approval-strategy.md` when you want to reduce repeated approvals and make run-mode automation smoother in practice.

Read `references/common-pitfalls.md` BEFORE any Stage 4 evaluation. It catalogues the real mistakes that have occurred in past runs (look-ahead masks, mislabeled delay, fake "N/N positive years" validation, A-share limit-day tail asymmetry, confirmation-first research, IC-vs-LS dispersion trap, bull-market short-leg destruction, industry noise eating signal, hidden classic-factor exposure, daily turnover cost trap). Every backtest submission must pass the checks this file describes.

Read `references/execution-delay-audit.md` BEFORE any Stage 4 submission. This is the mandatory pre-submission checklist: physical execution timeline, future-perturbation invariance test, target-mask provenance audit, IC decay by delay, and the standardized delay-aware API. Without this audit, Agent 5 must reject the submission.

Read `references/tvt-split-template.md` whenever the evaluation goes beyond a single-round check. It specifies the Train(1.5-2y) / Validate(1y) / Test(3y+) methodology, the selection rule with stability penalty, the hard floors for PROMOTE decisions (worst-year Sharpe ≥ 0.5, best-year-out Sharpe ≥ 50% of headline, etc.), and the mandatory per-year reporting blocks.

## Operational upgrade

This skill now supports a runnable operating model with:
- an evaluator-coordinator
- five role agents
- fixed handoff files
- a session state file
- deterministic minimum outputs per stage
- OpenClaw sessions-based orchestration
- QQBot-facing message templates

Primary execution path for the current environment:
- **run mode** via one-shot `sessions_spawn(..., mode="run")`

Default automation rule for this skill:
- workflow coordination should run automatically
- file-based artifact generation should run automatically
- approvals should be required only when the agent must execute a host-level file, script, or shell command on the local machine

Secondary/future path:
- session mode via persistent subagent sessions, only when the target fully supports thread-bound subagent sessions

When executing this skill in practice, make the coordinator enforce:
- stage order
- artifact creation
- handoff completeness
- continue/refine/stop decisions after evaluation
- exactly 8 expressions per generation batch
- validation before any backtest submission

## A-share adaptation lessons (from session 20260415_a_share_volprice_alpha)

Hard-won operational rules when running this workflow on A-share data with Tushare:

### Data access
- Tushare free-tier does NOT grant `daily_basic` or `trade_cal` for historical dates. Use per-date `daily` calls with retry, or cache aggressively.
- `stock_basic(fields='industry')` works on free-tier and provides ~110 industry groups — sufficient for neutralization. SW L1 via `index_classify` requires paid tier.
- Always cache to parquet. A full 1500-stock × 8-year panel takes ~15 min to fetch but loads in <2 seconds from cache.

### Factor construction
- Use `amount` (CNY traded) or `vol` (shares traded) instead of `turnover_rate_f` when daily_basic is unavailable for historical periods. The economic signal is equivalent.
- For volume-price factors, **industry neutralization is not optional** — it typically boosts Test Sharpe by 30-40% and halves the train-test overfitting gap (Pitfall 8 in common-pitfalls.md).
- Always compute IC at horizons {1, 5, 10, 20} BEFORE choosing rebalance frequency. If IC increases with horizon, monthly rebalance is optimal, not daily.

### Backtest reporting
- **Always report BOTH long-short AND long-only Q5 excess metrics.** In A-share (no efficient shorting), long-only excess is the deployable metric; LS is for signal validation only.
- In bull-market years, LS Sharpe can collapse to zero even when Q5 long-only excess is +6-9%. This is structural (Pitfall 7), not factor failure.
- After-cost analysis is mandatory. Daily rebalance with rank-based factors typically yields 100%+ daily turnover → after-cost Sharpe negative. Monthly rebalance is usually the sweet spot.

### Decision framework
- If IC t-stat > 3 but LS Sharpe < 0.5 on first mechanism → switch mechanism (new batch), don't tune windows on the same mechanism.
- If raw LS Sharpe > 1.0 but worst-year < 0.5 → try industry neutralization before declaring RESEARCH-ONLY; it often rescues the worst year.
- If residualized LS Sharpe < 50% of raw → the factor is a vehicle for classic factor exposure (usually anti-momentum). Label it honestly and deploy accordingly.
- **Optimal A-share deployment:** monthly-rebalance Q5 long-only (index enhancement), not daily-rebalance dollar-neutral LS.
