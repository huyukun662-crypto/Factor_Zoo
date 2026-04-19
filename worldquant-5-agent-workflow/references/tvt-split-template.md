# Train / Validate / Test Methodology Template

Use this template whenever a factor moves past the single-round evaluation
and someone asks "is this real?" or "is this tradable?".

TVT discipline is the standard defense against the subtle overfitting that
builds up across R1→R2→R3 refinement loops. Without it, each round rewards
"make the Sharpe bigger" and silently accumulates confirmation bias.

---

## Standard split

For a typical A-share / equity alpha with 5+ years of data:

| Window | Purpose | Typical span |
|:---|:---|:---|
| **Train** | grid search, parameter selection | 1.5 – 2 years |
| **Validate** | pick the config that generalizes | 1 year |
| **Test (OOS)** | frozen config, reported numbers | 3+ years (never touched) |

Example on 2018-2025 data:
- Train: 2018-01 to 2019-12 (~470 days)
- Validate: 2020-01 to 2020-12 (~243 days)
- Test: 2021-01 to 2025-12 (~1210 days)

**Rule 1: the test window is never touched during tuning.** If any metric
from the test window informs any parameter selection — even once — the
window is compromised and you need to pick a different test period.

---

## Selection rule

```
eligible = {configs | train_sharpe > 0.5 AND validate_sharpe > 0}
score(c) = validate_sharpe(c) − 0.3 × |train_sharpe(c) − validate_sharpe(c)|
best     = argmax(score over eligible)
```

The stability penalty (the 0.3× term) rewards configs whose train and
validate numbers are close — this filters out the "great on train, broken
on validate" over-fitting cases.

### Why 0.3
It's a middle-of-the-road weight. Too low (0.1) and you pick configs that
overfit train. Too high (0.8) and you pick configs that are safe but weak.
0.3 was calibrated in practice — if you want to change it, justify it.

---

## Grid size guidelines

For a single factor family with 3-5 parameters:
- 150-400 configs total is reasonable
- Each parameter should have 3-4 levels max
- Avoid correlated parameters (don't grid both `ret_win` and `decay_win` to
  the same values — they interact)

Beyond ~500 configs, you're no longer tuning — you're data-mining.

---

## Mandatory health checks on the result

After picking the best config on train+validate, BEFORE running it on test,
compute:

1. **Train/validate Sharpe gradient**: `train_sharpe / validate_sharpe`.
   - `1.5 – 3.0`: healthy (train is always stronger in-sample)
   - `> 3.0`: possible overfitting in train
   - `< 1.0`: unusual — validate is stronger than train, possibly a regime
     anomaly or a data quality issue
2. **Grid neighborhood**: what fraction of configs within ±1 parameter step
   of the winner are also eligible? If < 50%, the winner is on a cliff edge.
3. **Best-year-out sensitivity**: recompute `train_sharpe` with the best
   single month removed. If it drops by more than 30%, the train result
   is single-regime.

---

## Running the test (exactly once)

The test evaluation is a one-shot commitment. You run the frozen config
on the test window, record the numbers, and report them. You do not
iterate.

If the test result is disappointing, you do NOT:
- re-tune the parameters on train
- pick a different config from the eligible list
- change the selection rule
- adjust the test window boundaries
- "slightly tweak" the winsor cap

Instead, you write up the result as a RESEARCH-ONLY finding with the
honest numbers, and the next round of research picks a new direction.

---

## Required reporting blocks

The Stage-5 evaluator report must include:

### 1. TVT gradient table

| Metric | Train | Validate | Test |
|:---|---:|---:|---:|
| Days | X | Y | Z |
| Sharpe | ... | ... | ... |
| IC mean | ... | ... | ... |
| Max DD | ... | ... | ... |

### 2. Per-year test breakdown (MANDATORY)

One row per calendar year in the test window. Include:
- n_days, Sharpe, annualized return, max DD, IC mean, IC t-stat

### 3. Worst-year check

State explicitly: "The worst year in the test window is [YEAR] with
Sharpe [X]. The PROMOTE floor is 0.5. [PASS / FAIL]."

### 4. Best-year-out headline

Compute the test Sharpe with the best year removed. State: "Excluding
the best year ([YEAR], Sharpe [X]), the test Sharpe is [Y]."

### 5. Decision

Based on the checks, the decision is one of:
- **PROMOTE to paper-trading** — all floors passed
- **RESEARCH-ONLY** — at least one floor failed but the factor has signal
- **STOP** — IC is flat or negative, no signal to rescue

---

## Hard floors for PROMOTE decision

All must pass:
- [ ] Test IC mean t-statistic ≥ 3.0 (statistical significance)
- [ ] Test Sharpe ≥ 1.0 (economic significance)
- [ ] Worst-year Sharpe ≥ 0.5 (robustness)
- [ ] (Best-year-out Sharpe) ≥ 50% of headline Sharpe (not regime-concentrated)
- [ ] Test max DD < 2× train max DD (no regime shift)
- [ ] Calmar ≥ 1.5 (risk-adjusted)
- [ ] Execution delay audit passed (see references/execution-delay-audit.md)
- [ ] Look-ahead audit passed (see references/common-pitfalls.md)

If any checkbox is unchecked, the decision is NOT PROMOTE.

---

## Lessons from a real run

On a short-horizon reversal factor with 216 configs grid-searched under the
WRONG delay convention (delay=0, i.e. look-ahead), we reported:
- Train Sharpe +3.73, Validate +1.30, Test +2.13
- 5/5 test years positive
- "PROMOTE to paper-trading"

When the delay was corrected to delay=1 and 384 configs re-tuned, the same
factor family gave:
- Train Sharpe +2.43, Validate +1.62, Test **+0.67**
- 4/5 test years Sharpe < 0.5 (one year -0.28)
- RESEARCH-ONLY (floors failed)

The worst-year-Sharpe floor was not checked in the first run. It would
have immediately blocked the PROMOTE decision even under the wrong delay.
It also would have been the first thing to flag when the delay fix dropped
the headline Sharpe by ~1.5 points.

**Always check the floors first, then look at the headline.**
