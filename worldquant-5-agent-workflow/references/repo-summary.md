# Repository Summary: GRD-Chang/worldquant-skill

## What the source repository provides

The source repository is a WorldQuant BRAIN research workflow built around 3 skills:

1. **knowledge_base_search**
   - Search dataset fields, optimization notes, good examples, and platform mechanism notes.
   - Intended as the retrieval layer.

2. **factor_backtest**
   - Run one batch of exactly 8 alpha expressions.
   - Enforce validation before submission.
   - Monitor backtest progress and fetch results.
   - Emphasize `visualization=false` and constrained neutralization choices.

3. **alpha-research-recorder**
   - Persist the research process using templates.
   - Write session metadata, per-round logs, and a final summary.

## Core design idea in the source repository

The repository separates:
- knowledge retrieval
- backtesting execution
- persistent logging

This is already close to a workflow, but several responsibilities remain bundled together. In particular:
- economic hypothesis design is implicit rather than isolated
- expression generation is implied rather than defined as a separate role
- evaluation/ranking is mentioned but not separated as a dedicated agent

## Why convert it into 5 agents

A 5-agent design makes the pipeline clearer:
- one agent searches
- one agent frames the hypothesis
- one agent builds the expressions
- one agent executes the backtests
- one agent evaluates and records

This reduces role-mixing and creates cleaner handoffs.

## Artifacts inherited from the source repository

Useful artifacts from the cloned repo:
- `worldquant-skill/README.md`
- `worldquant-skill/skills/alpha-research-recorder/SKILL.md`
- `worldquant-skill/skills/alpha-research-recorder/templates/session_metadata.yml.template`
- `worldquant-skill/skills/alpha-research-recorder/templates/round_NNNN.yml.template`
- `worldquant-skill/skills/alpha-research-recorder/templates/final_summary.md.template`
- `worldquant-skill/skills/factor_backtest/SKILL.md`
- `worldquant-skill/skills/knowledge_base_search/SKILL.md`

## Practical adaptation notes for OpenClaw

The original repository is skill-oriented, not agent-orchestrator-oriented.

For OpenClaw adaptation:
- keep the templates and structural discipline
- rewrite the workflow around role ownership and handoffs
- preserve the batch-of-8 backtest rule
- preserve durable logging
- add an explicit evaluation/ranking stage
