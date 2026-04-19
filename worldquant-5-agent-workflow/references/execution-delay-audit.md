# Execution Delay Audit — Mandatory Pre-Submission Checklist

Purpose: prevent the specific class of mistakes where a pipeline claims
"delay=k" in comments / documentation but implements delay=k−1 (or 0) in
code. These mistakes compound silently and can inflate reported Sharpe by
multiple points.

Every backtest submission in this workflow must pass this checklist before
Agent 5 (Evaluator) accepts the results.

---

## Step 1 — Write the physical timeline in prose

Agent 4 produces a short paragraph in the backtest report stating, in order:

1. **Feature availability time** — "At close[t] (15:00 local), the factor is
   computed using data X, Y, Z observed up to and including close[t]."
2. **Order submission time** — "Orders are submitted at [time] using the
   signal from close[t]."
3. **Execution time** — "Orders fill at [time]. The earned return begins
   accruing from this instant."
4. **Exit / measurement time** — "The return is measured from [time A] to
   [time B]."

If any of these four times is ambiguous or impossible, the pipeline is wrong.

### Example (correct, delay=1, daily close-to-close)

    At close[t] the factor is computed from close[t] and volume[t]. After 15:00,
    Market-on-Close orders are submitted for day t+1 execution. At close[t+1],
    orders fill at the printed close. Positions are rebalanced at close[t+2],
    so the realized per-period return is close[t+2] / close[t+1] − 1.

The implication: `target(t) = ret[t+2] = ret_w.shift(-2)[t]`.

### Example (wrong — delay=0 mislabeled as delay=1)

    At close[t] the factor uses close[t]. Target is close[t+1] / close[t] − 1.

Problem: the target requires execution at close[t], but the factor only
became known at 15:00 of day t. You cannot both observe close[t] AND trade
at close[t] — you just received the print. This is the delay=0 case, which
is look-ahead if the factor uses close[t] data.

---

## Step 2 — Verify the code invariant

Compute:

```python
target_shift = -(1 + delay)
assert target_matrix is ret_w.shift(target_shift)
```

For delay=1: `target_shift == -2`. For delay=0: `target_shift == -1`
(and this is look-ahead if the factor uses close[t] data).

Grep the codebase for `shift(-1)`, `shift(-2)`. Every hit must have a
comment explaining which delay semantics it corresponds to.

---

## Step 3 — Future-perturbation invariance test

Randomize all bars after a chosen cutoff date. Rebuild the factor from
the perturbed data. Compare the factor values on dates ≤ cutoff between
the original and perturbed runs.

```python
cutoff = pick_any_date_in_middle_of_sample
bars_perturbed = bars.copy()
mask = bars_perturbed["trade_date"] > cutoff
bars_perturbed.loc[mask, "close"] *= rng.uniform(0.5, 1.5, size=mask.sum())
bars_perturbed.loc[mask, "vol"]   *= rng.uniform(0.5, 2.0, size=mask.sum())

fac_original  = build_factor(bars)
fac_perturbed = build_factor(bars_perturbed)

diff = (fac_original - fac_perturbed).loc[:cutoff].abs().max().max()
assert diff < 1e-12, f"factor leaks future info: {diff}"
```

If the past values of the factor change when the future is perturbed,
something leaks. Hunt it down before submission.

---

## Step 4 — IC decay by delay

Compute cross-sectional IC of the factor against target shifted by
delay ∈ {0, 1, 2, 3, 5, 10}. Report as a table and ideally a chart.

Interpretation:
- **delay=0 IC** is what the pipeline is IMPLICITLY measuring if it uses
  `ret.shift(-1)` with a factor built from close[t] data. This is the
  look-ahead / physically-impossible case.
- **delay=1 IC** is the realistic tradable IC.
- **delay ≥ 2** shows how the signal decays if execution slips further.

If `IC[delay=0] > 1.5 × IC[delay=1]`, the factor concentrates its value in
a bar you cannot trade. Treat the delay=0 number as the upper bound and the
delay=1 number as reality.

Example output from an actual run:

    delay=0   IC=+0.0342  t=+19.16
    delay=1   IC=+0.0246  t=+14.68    (-28% from delay=0)
    delay=2   IC=+0.0198  t=+12.51
    delay=5   IC=+0.0123  t=+8.57
    delay=10  IC=+0.0098  t=+7.28

This specific shape — IC halving within 5 trading days — is characteristic
of short-horizon reversal factors. It is also why such factors look great
at delay=0 and underwhelming at delay=1.

---

## Step 5 — Target mask provenance audit

Any boolean matrix used to filter the factor cross-section must be derived
from data available AT OR BEFORE date t. Grep for these patterns in the
filter expressions:

- `next_`, `future_`, `_next` — usually next-day/future references
- `shift(-1)`, `shift(-2)` — future shifts
- `target_`, `_target` — may leak target information

For each hit, confirm the expression's data dependency. Any variable
derived from `ret.shift(-k)` for `k > 0` is FORBIDDEN inside a factor
filter expression.

Applied to the target side, `ret.shift(-k)` is correct (target is allowed
to be forward). Applied to the feature side, it is look-ahead.

---

## Step 6 — Standardized delay-aware API

The factor library MUST accept `delay` as an explicit parameter in the
matrix-building function. Example:

```python
def build_base_matrices(bars, adj, universe_codes, *, delay=1):
    ...
    target_shift = -(1 + delay)
    target_raw = ret_w.shift(target_shift)
    return {..., "target_raw": target_raw, "delay": delay}
```

Default `delay=1` (not 0). This is the realistic case. Any caller passing
`delay=0` must explicitly acknowledge they are measuring an upper bound,
not a tradable return.

---

## Step 7 — Sign-off gate

The Backtest Operator's handoff JSON must contain the following block:

```json
"execution_model": {
  "delay": 1,
  "target_shift": -2,
  "physical_timeline": "factor at close[t], MOC submit, fill close[t+1], exit close[t+2], return = close[t+2]/close[t+1]-1",
  "future_perturbation_test": "passed (max_diff=0.0)",
  "target_mask_provenance": "passed (no future-derived filters on factor)",
  "ic_decay_by_delay": {
    "delay_0": 0.0342,
    "delay_1": 0.0246,
    "delay_2": 0.0198
  }
}
```

Without this block, Agent 5 must REJECT the submission and return it to
Agent 4 for rework.
