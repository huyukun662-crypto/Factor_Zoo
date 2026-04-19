# WorldQuant 5-Agent Workflow Template

## Objective

Research a WorldQuant-style alpha idea from hypothesis to ranked candidate selection.

## Step 1 — Research Librarian

Input:
- idea source
- target market / universe / delay
- target metrics

Do:
- search relevant datasets, operators, prior examples, and optimization notes
- summarize useful evidence
- identify common failure modes

Output:
- `research_brief.md`

## Step 2 — Hypothesis Architect

Do:
- define the main mechanism
- define risk premium source
- define time horizon and market regime
- define the success metrics and failure conditions
- create session metadata

Output:
- `session_metadata.yml`

## Step 3 — Alpha Builder

Do:
- generate exactly 8 expressions
- keep them within the same mechanism family
- annotate each expression with economic intuition

Output:
- `expressions_batch_0001.md`
- draft `round_0001.yml`

## Step 4 — Backtest Operator

Do:
- validate all 8 expressions
- submit one batch backtest
- monitor the job safely
- fetch the results
- record validation or runtime failures

Output:
- `backtest_results_batch_0001.md`
- update `round_0001.yml`

## Step 5 — Evaluator & Recorder

Do:
- compare the 8 candidates
- rank by predictive power, Sharpe, turnover, and stability
- recommend continue / refine / stop
- write round summary and final summary if finished

Output:
- `alpha_ranking.md`
- updated `round_0001.yml`
- `final_summary.md` if completed

## Handoff checklist

Each agent should leave behind:
- a short summary of what it decided
- explicit assumptions
- machine-readable or structured output where possible
- unresolved risks for the next agent
