# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Factor_Zoo is a **factor mining results hub**. Today it contains:

- `README.md` — in Chinese; positions the repo as the sink for factor definitions, IC/backtest results and reports across four factor families (量价 / 基本面 / 趋势-技术 / 另类与跨市场).
- `worldquant-5-agent-workflow/` — a self-contained **Claude Code Skill package** (markdown only, no runtime code). This is the pipeline that is expected to *produce* everything that will later land under `factors/`, `results/`, `figures/`, `reports/` (directories listed in README as TBA; do not assume they exist yet).

There is no build system, test suite, lockfile, or source language here. Do not invent `pnpm`, `pytest`, or similar commands.

## The Skill package (`worldquant-5-agent-workflow/`)

This directory IS a Claude Skill, not a library. Its structure is the contract:

- `SKILL.md` — the entry file. The YAML frontmatter (`name`, `description`) is what lets this skill be discovered by other Claude harnesses. Treat it as load-bearing: don't reword the description without reason, and keep it focused on *when* to trigger (WorldQuant BRAIN alpha research, 5-agent workflow, OpenClaw).
- `references/` — 28 on-demand reference files. `SKILL.md` contains a long "When to read bundled references" section that maps each file to the situation that warrants reading it. Keep that index in sync whenever you add, rename, or delete a file under `references/`.
- `references/README-USE-ORDER.md` — the suggested read order when the skill first activates. Update this if the preferred bootstrap sequence changes.
- `PACKAGING.md` — publishing checklist for re-releasing the skill.

## The 5-agent pipeline (the core abstraction)

Every reference file orbits this pipeline. Understand the roles and handoffs before editing anything under `references/`:

```
Agent 1 Research Librarian  → research_brief.md      + handoff_1_to_2.json
Agent 2 Hypothesis Architect → session_metadata.yml  + handoff_2_to_3.json
Agent 3 Alpha Builder        → expressions_batch_NNNN.md + handoff_3_to_4.json
Agent 4 Backtest Operator    → backtest_results_batch_NNNN + handoff_4_to_5.json
Agent 5 Evaluator & Recorder → alpha_ranking.md / round_NNNN.yml / final_summary.md
```

A session folder is `logs/YYYYMMDD_topic_model/` with `inputs/`, `working/` (handoff JSONs), `outputs/` (artifacts), `round_NNNN.yml`, `run_state.json`. This layout is specified in `references/execution-plan.md` and referenced throughout — don't change it unilaterally.

## Load-bearing operational rules

These rules show up in multiple reference files and in SKILL.md. Preserve them when editing:

- **Rule of 8** — Alpha Builder produces exactly 8 expressions per batch; Backtest Operator submits exactly 8. Deviating breaks the contract the whole skill is built on.
- **Validation before submission** — Agent 4 must not submit if validation fails; fix expressions instead of retrying blindly.
- **Mandatory pre-PROMOTE audits** (listed in `SKILL.md` "Mandatory audit rules" and detailed in `references/common-pitfalls.md`, `references/execution-delay-audit.md`, `references/tvt-split-template.md`):
  1. Execution-delay audit (`target_shift == -(1 + delay)`, default `delay=1`)
  2. Look-ahead audit (randomize future bars, grep for `.where(mask)` derived from `ret.shift(-k)` or `next_*`)
  3. Worst-year Sharpe ≥ 0.5
  4. Best-year-out Sharpe ≥ 50% of headline
  5. Falsification-first adversarial check
  Any failure → decision is RESEARCH-ONLY, never PROMOTE.
- **A-share specifics** (see the "A-share adaptation lessons" block at the end of `SKILL.md`): industry neutralization is not optional for volume-price factors; always report *both* LS and long-only Q5 excess metrics; prefer monthly rebalance after cost analysis.

## Editing guidance

- Before adding a new reference file, check whether its content overlaps an existing one (there are already 28); prefer extending the relevant file.
- When you add a reference, also append an entry to both:
  - the "When to read bundled references" section of `SKILL.md`, and
  - `references/README-USE-ORDER.md` if it belongs in the bootstrap order.
- The README.md's Chinese factor-category section is marketing-facing; keep technical specifics inside the skill package rather than promoting them to README.

## Git workflow

- Default branch is `main`. Past development has happened on `claude/setup-factor-mining-repo-*` branches and landed via PR — keep that pattern unless the user says otherwise.
- GitHub MCP access is scoped to `huyukun662-crypto/Factor_Zoo` only. Cross-repo operations (e.g. re-importing the upstream `worldquant-skill`) must go through a local clone + copy.
