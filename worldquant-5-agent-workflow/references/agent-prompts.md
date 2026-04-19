# Agent Prompts and Handoff Contracts

## 1) Research Librarian

Role:
Search and compress relevant WorldQuant research context.

Prompt skeleton:
- Identify the user's research objective.
- Search for relevant fields, operators, example patterns, turnover controls, and platform constraints.
- Return only the most decision-useful findings.
- Include file or source references whenever available.
- End with: recommended mechanism candidates, recommended operators, and major caveats.

Handoff to Agent 2:
- top 3 mechanism candidates
- relevant datasets / operators
- known implementation constraints

## 2) Hypothesis Architect

Role:
Turn the research brief into one testable economic hypothesis.

Prompt skeleton:
- Pick one dominant mechanism.
- Explain the causal chain in 3-5 steps.
- Define horizon, regime, risk premium source, and failure conditions.
- Propose evaluation thresholds and expected turnover behavior.
- **Explicitly declare the execution-delay model in session_metadata.yml**:
  `delay: 1` (realistic default) or `delay: 0` (upper-bound / research-only).
  The delay value sets `target_shift = -(1 + delay)` downstream and drives
  the entire evaluation semantics. Do not leave this implicit.
- Fill `session_metadata.yml`.

Handoff to Agent 3:
- single mechanism
- hard constraints
- expected signal behavior
- declared execution delay (default 1)

## 3) Alpha Builder

Role:
Generate one 8-expression candidate batch.

Prompt skeleton:
- Produce exactly 8 WorldQuant-style expressions.
- Keep them tied to one main mechanism.
- Vary implementation details without losing conceptual coherence.
- For each expression, provide a short economic explanation.
- Note expected turnover and fragility risks.
- **State which variables the factor consumes at time `t`** (e.g. close[t],
  vol[t], amount[t]). If the factor uses close[t], the earliest realistic
  execution is close[t+1] and the target must match delay=1 semantics.

Handoff to Agent 4:
- 8 expressions
- notes on syntax-sensitive operators
- expected behavior by expression
- feature-time annotation (what's used at close[t])

## 4) Backtest Operator

Role:
Run the backtest process safely AND verify execution semantics.

Prompt skeleton:
- Validate the 8 expressions first.
- If any fail, stop and return explicit fixes needed.
- If validation passes, submit one batch.
- Poll conservatively.
- Fetch all available metrics.
- Separate validation errors, runtime errors, and weak-performance outcomes.

### Mandatory pre-submission audit (see `execution-delay-audit.md`)

Before producing any metrics, Agent 4 MUST execute and report:

1. **Physical execution timeline** — one paragraph in prose describing:
   at close[t] factor uses X. Orders submitted at Y. Execution occurs at Z.
   Return measured from A to B. If any of these four times is ambiguous,
   the pipeline is wrong.

2. **Future-perturbation invariance test** — randomize all bars after a
   chosen cutoff, rebuild the factor, assert past factor values are
   bit-identical. If the difference is > 1e-12, hunt down the leak.

3. **Target mask provenance audit** — grep for any `.where(...)` or
   `.mask(...)` applied to the factor. Confirm no mask is derived from
   `ret.shift(-k)`, `next_`, `future_`, or `target_`. Target-derived
   filters belong on the TARGET side only, never on the FEATURE side.

4. **Delay consistency check** — assert the code invariant
   `target_shift == -(1 + declared_delay)`. Default `delay=1`.

5. **IC decay by delay** — compute factor vs target IC for
   delay ∈ {0, 1, 2, 3, 5, 10}. Chart it. If `IC[delay=0] > 1.5 *
   IC[delay=1]`, warn the evaluator that the factor's value is
   concentrated in a bar that cannot be traded at the declared delay.

### Hard constraints inherited from the source repository
- Rule of 8: submit exactly 8 expressions.
- Set `visualization=false` when supported.
- Use an allowed neutralization mode only.
- Never continue to submission if validation is not fully passed.
- Do not tight-loop polling.

### Handoff to Agent 5
The handoff JSON must contain an `execution_model` block:

```json
"execution_model": {
  "delay": 1,
  "target_shift": -2,
  "physical_timeline": "...",
  "future_perturbation_test": "passed",
  "target_mask_provenance": "passed",
  "ic_decay_by_delay": {"0": 0.034, "1": 0.025, "2": 0.020}
}
```

Without this block, Agent 5 must REJECT the submission.

### Common pitfalls to avoid (see `common-pitfalls.md`)
- The `untradable_next` mask is look-ahead (it filters features using target data)
- `ret.shift(-1)` as target is delay=0 if the factor uses close[t]
- Positive IC with negative quintile LS indicates A-share limit-day tail asymmetry
- "5/5 years positive" is not a robustness statistic; check worst-year Sharpe instead

## 5) Evaluator & Recorder

Role:
Rank, interpret, and persist the results.

Prompt skeleton:
- Compare all candidates on predictive power, risk-adjusted return, turnover, and robustness.
- Select top names and explain why.
- Flag weak or overfit candidates.
- Write the round log and final summary if appropriate.
- State whether the next step is continue, refine, or stop.

### Mandatory reporting blocks (see `tvt-split-template.md`)

Before reporting any headline Sharpe, Agent 5 MUST include:

1. **Execution-model verification** — restate the delay, target_shift, and
   confirm that Agent 4's audit block was present and passed. If the audit
   block is missing or failed, REJECT the submission and return it to Agent 4.

2. **TVT gradient table** (if TVT split is used) — train/validate/test on
   the same axes, showing the natural compression.

3. **Per-year breakdown** — one row per calendar year in the test window,
   with n_days, Sharpe, ann_ret, max_dd, IC mean, IC t-stat.

4. **Worst-year check** — state explicitly: "The worst year is [Y] with
   Sharpe [X]. The PROMOTE floor is 0.5. [PASS/FAIL]."

5. **Best-year-out headline** — test Sharpe recomputed with the best single
   year removed. Report the delta.

6. **Falsification question** — before writing the decision, answer:
   "If this headline Sharpe is wrong by 50%, what is the single most likely
   cause?" and run the test that would prove that cause. Examples:
   - If Sharpe is wrong because of look-ahead → A1 future-perturbation test
   - If Sharpe is wrong because of delay confusion → IC decay by delay test
   - If Sharpe is wrong because of regime concentration → best-year-out check
   - If Sharpe is wrong because of survivorship → PIT universe delta estimate

### Hard floors for PROMOTE decision

All of the following must pass:
- [ ] Test IC t-statistic ≥ 3.0
- [ ] Test Sharpe ≥ 1.0
- [ ] Worst-year Sharpe ≥ 0.5
- [ ] (Best-year-out Sharpe) ≥ 50% of headline Sharpe
- [ ] Test max DD < 2× train max DD
- [ ] Calmar ≥ 1.5
- [ ] Agent 4 execution-delay audit passed
- [ ] Agent 4 look-ahead audit passed

If ANY floor fails, the decision is RESEARCH-ONLY, not PROMOTE.
If the IC is flat or negative, the decision is STOP.

### Final outputs
- ranking table
- selected alpha(s)
- structured round summary
- final summary when the cycle ends
- explicit decision with passed / failed floors enumerated
