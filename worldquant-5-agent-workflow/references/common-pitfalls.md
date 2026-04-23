# Common Pitfalls — Real Mistakes from Past Runs

This document records concrete mistakes that occurred during actual execution
of this workflow, the Sharpe-point impact of each, and the exact test that
would have caught them. Treat this as a mandatory pre-flight checklist for
Agent 4 (Backtest Operator) and Agent 5 (Evaluator & Recorder).

---

## Pitfall 1 — Target-derived masks on the FEATURE matrix (look-ahead)

### Symptom
Code like:

```python
untradable_next = next_ret.abs() >= 0.098       # uses day t+1 info
fac = fac.where(~untradable_next)               # applied at day t
```

or any variant where a boolean computed from `next_ret` / `target` / `shift(-k)`
is used to FILTER the factor cross-section before ranking.

### Why it looks innocent
"I'm just dropping names that can't be traded next day" — feels like good
hygiene, same as dropping suspended / ST / NaN names.

### Why it is look-ahead
At time `t`, you do not yet know the `ret(t+1)` value. Using `next_ret` to
decide which names enter the day-`t` ranking leaks future information.

### Economic impact (measured)
On the A-share CSI1000 reversal × volume factor, this pitfall inflated the
quintile long-short Sharpe from roughly **−0.94** (honest) to **+3.63**
(biased) — a 4-point swing. The mask systematically dropped the days where
the reversal bet went WRONG (stocks continuing in the original direction to
hit the daily limit), which are exactly the worst-P&L days.

### How to catch
1. **Future-perturbation test** (audit A1): randomize all bars after a cutoff
   date, recompute the factor on PAST dates, assert max absolute difference
   is zero. If it isn't, something leaks.
2. **Mask provenance audit**: every boolean applied to `fac` with `.where(...)`
   or `.mask(...)` must be derivable from data available AT OR BEFORE date `t`.
   Grep for `shift(-`, `next_`, `future_`, `target_` in mask expressions.
3. **IC-vs-LS discrepancy**: if IC is strongly positive but quintile LS is
   negative under honest evaluation, suspect the opposite — that the masked
   version was hiding tail losses.

### Fix
Target filters belong on the TARGET, not on the FEATURE. If you must exclude
limit-day returns from the evaluation, do it on `next_ret_masked`, never on
the factor matrix itself. Better: use `winsorize(next_ret, ±cap)` as a
risk-management constraint, which is the same economic idea (vol-targeted
position limits) and is honest.

---

## Pitfall 2 — "Delay=1" in comments, delay=0 in code

### Symptom
```python
# Delay: 1 trading day
target = ret.shift(-1)    # close[t+1] / close[t] - 1
```

The comment claims 1-day delay. The code uses day-`t` data to compute the
factor and a target that is earnable from close[t] to close[t+1]. Since the
factor sees close[t] (available at 15:00 day t), execution at close[t] is
impossible — you just got the print.

### Correct semantics
If factor at `t` uses close[t] and vol[t], the earliest realistic execution
is close[t+1], and the earned return is close[t+2]/close[t+1] − 1. That is
`ret.shift(-2)[t]`, not `ret.shift(-1)[t]`.

Physical timeline:

    Close[t]        factor(t) computed from close[t], vol[t]
    15:00+ day t    orders submitted (MOC)
    Close[t+1]      orders fill
    Close[t+2]      rebalance; realized return = close[t+2]/close[t+1] − 1

### Economic impact (measured)
On the A-share CSI1000 factor (same as above), the apparent Sharpe dropped
from **+2.13** (delay=0 mislabeled) to **+0.67** (delay=1 correct) on the OOS
test window. This is because most of the reversal signal lives in the FIRST
24 hours after close[t] — by the time you can actually trade, 28% of the IC
is already gone.

### How to catch
1. **Write the physical timeline in prose**. Agent 4 MUST produce a short
   paragraph in the backtest report describing: "at close[t], the factor uses
   X. Orders are submitted at Y. Execution occurs at Z. Return measured is W."
   If the timeline doesn't survive a 30-second read, it's wrong.
2. **Verify the invariant** `target.shift == -(1 + delay)` in code.
3. **Measure IC decay by delay**: compute IC for delay ∈ {0, 1, 2, 3, 5, 10}
   and chart it. The delay=0 bar is what the pipeline is IMPLICITLY measuring.
   If IC at delay=0 is much higher than at delay=1, the factor's value is
   concentrated in a bar you can't actually trade, and "delay=1 claimed"
   numbers are wrong.

### Fix
Make `delay` an explicit parameter in `build_base_matrices`. Compute:

```python
target_shift = -(1 + delay)
target_raw = ret_w.shift(target_shift)
```

Default to `delay=1`. Never let the code use `shift(-1)` without a comment
explaining that this is equivalent to `delay=0` and is look-ahead for any
factor that uses close[t] data.

---

## Pitfall 3 — "5 of 5 years positive" is not a validation

### Symptom
Agent 5 reports "5/5 test years positive Sharpe" or "6/6 years positive"
as a primary justification for PROMOTE.

### Why it's misleading
Count-of-positive-years is a lossy statistic. It does not distinguish between:
- 5 years at Sharpe 2 (genuinely robust)
- 4 years at Sharpe 0.1 and 1 year at Sharpe 2.9 (single-regime)
- 5 years all barely positive with huge drawdowns (fragile)

In one actual run, "5/5 positive" decomposed on inspection as:
    2021: +0.27  2022: -0.28  2023: +0.33  2024: +0.11  2025: +2.91

Four of the five years were Sharpe ≤ 0.33, and 2022 was literally negative
when re-measured under honest delay. The single 2025 year carried the
headline. That is a regime-concentrated alpha, not a robust signal.

### How to catch
Agent 5 MUST report, in this order:
1. **Worst-year Sharpe** (not the average or sum)
2. **Count of years with Sharpe ≥ 0.5** (substantive threshold, not ≥ 0)
3. **Decomposition: headline Sharpe with best year removed** — if this drops
   by more than 1.0, the factor is regime-concentrated
4. **Then** the full per-year table

### Fix — mandatory floors before any PROMOTE decision
- worst-year test Sharpe ≥ 0.5 (hard floor)
- (headline Sharpe − best year contribution) ≥ 50% of headline Sharpe
- no year with max DD exceeding 2× the full-window max DD

If any floor is violated, the decision is RESEARCH-ONLY, not PROMOTE.

---

## Pitfall 4 — IC positive, quintile LS negative: limit-day tail asymmetry

### Symptom
Under honest (unmasked) evaluation, Spearman IC is positive and significant
(e.g., +0.034, t-stat 16), but the top-minus-bottom quintile long-short has
NEGATIVE Sharpe.

### Why this happens in A-share
A-share's ±10% daily limits create a tail asymmetry:
- On limit-up, a winner continues UP +9.8%. If the factor placed it in the
  SHORT leg (reversal bet), the short leg loses 9.8%.
- On limit-down, a loser continues DOWN −9.8%. If the factor placed it in
  the LONG leg (reversal bet), the long leg loses 9.8%.

These events are rare but their magnitude (~±10%) dwarfs normal daily moves
(~±2%). For a reversal factor, limit-day names are disproportionately in the
tail quintiles (they're recent extreme movers), so the tails are poisoned.

Spearman IC stays positive because the RANK ordering is still correct —
most of the distribution reverts. But the MEAN of the extreme quintiles
is dragged negative by the limit-day tails.

### How to catch
- Always report IC and quintile LS Sharpe SIDE BY SIDE. A gap indicates
  tail asymmetry.
- Test decile vs quintile — if decile LS > quintile LS substantially,
  confirm tail concentration.
- Test winsorized target — if Sharpe becomes positive under `target.clip(±5%)`,
  the issue is pure tail risk.

### Fix
Use decile (n=10) instead of quintile (n=5) for group-based LS — dilutes tail
concentration. Apply a realistic position-sizing cap (winsor target at
±3% to ±5%) which is defensible as vol-targeted risk management.

---

## Pitfall 5 — Confirmation-friendly research vs. falsification-first research

### Symptom
Each round of the workflow proves its hypothesis more strongly, until a
later audit finds a methodological flaw that destroys the result.

### Why it happens
The research pipeline naturally selects for configurations that look good.
Each iteration rewards "make the Sharpe bigger" over "break the result".
By the time you have 3 rounds of refinement, you have 3 rounds of
confirmation bias baked in.

### Fix — add an adversarial stage
Before declaring any Stage-5 decision, Agent 5 MUST attempt to FALSIFY its
own conclusion with the question:

> "If this factor's reported Sharpe is wrong by 50%, what is the most likely
> single cause?"

Then run the test that would prove that cause. Examples:
- "If the Sharpe is wrong because of look-ahead, running on shuffled future
  data should give the same result" → A1 future-perturbation test.
- "If the Sharpe is wrong because of hidden delay=0, IC at delay=1 should
  be materially lower" → IC decay by delay test.
- "If the Sharpe is wrong because of regime concentration, removing the
  best year should halve the headline" → best-year-out recomputation.
- "If the Sharpe is wrong because of survivorship, running on a point-in-time
  universe should weaken the result" → PIT universe test (or at least a
  survivorship delta estimate).

If ANY of these tests show a discrepancy greater than 30% relative Sharpe,
the factor goes to RESEARCH-ONLY regardless of headline numbers.

---

## Pitfall 6 — IC significant but LS Sharpe insufficient: the dispersion trap

### Symptom
All 8 expressions have IC t-stat > 3 (sometimes > 6), but quintile
long-short Sharpe stays below 0.6 on the test window.

### Why it happens
IC measures rank-order accuracy across the entire cross-section. LS Sharpe
requires the TOP and BOTTOM quintiles to have a meaningful RETURN SPREAD.
In low-dispersion environments (e.g., 2025 A-share bull market where
cross-sectional daily return std ≈ 0.023), the factor correctly RANKS stocks
but the absolute gap between Q5 and Q1 is too small to generate portfolio
profit.

### Economic impact (measured)
In session `20260415_a_share_volprice_alpha` Batch 1 (abnormal amount
z-score), 8 expressions all had IC t-stat 3.7–8.9 on the test window
(2021-2025). But the best LS Sharpe was only 0.585 (alpha_03). The
mechanism was real (attention → reversal) but too weak to generate
tradeable portfolio returns.

### How to catch
1. **Always report IC and LS Sharpe side by side.** A large gap (IC t > 5
   but LS Sharpe < 0.5) signals the dispersion trap.
2. **Check cross-sectional return dispersion per year**: if `target.std(axis=1)`
   is shrinking, the factor's ECONOMIC alpha is declining even if its
   STATISTICAL alpha (IC) is stable.
3. **Don't stop at one mechanism.** If Batch 1 hits this trap, switch to a
   structurally different mechanism for Batch 2 rather than tuning windows.

### Fix
When IC is strong but LS is weak, the factor's value is as a **sub-signal
in a multi-factor ensemble**, not as a standalone alpha. Mark it
RESEARCH-ONLY and test it as an input to a composite model. Alternatively,
apply industry neutralization — it often boosts LS by removing cross-industry
noise that dilutes the within-industry signal (see Pitfall 8).

---

## Pitfall 7 — Long-short Sharpe collapses in bull markets: the short-leg problem

### Symptom
A factor has LS Sharpe > 1.0 over the full test period, but in individual
bull-market years (e.g., 2025 A-share rally +33% equal-weight) the LS
Sharpe drops below 0.5 or goes negative.

### Why it happens
In a strong bull market, even the worst-ranked stocks rise significantly.
The short leg of a LS portfolio bleeds as "bad stocks" still appreciate
20-40%. The factor's RANKING is still correct (Q5 > Q1), but the absolute
spread Q5−Q1 shrinks to near-zero because Q1 is being lifted by the
market tide.

### Economic impact (measured)
In session `20260415_a_share_volprice_alpha`, alpha_05 (volume-price
divergence, industry-neutral):
- 2022 (bear): LS ann = +18.2%, LS Sharpe = 2.66
- 2023 (flat): LS ann = +11.3%, LS Sharpe = 1.58
- 2024 (mild bull): LS ann = +11.7%, LS Sharpe = 1.19
- **2025 (strong bull)**: LS ann = **+0.0%**, LS Sharpe = **0.00**

Meanwhile, Q5 long-only excess (vs benchmark) in 2025 was **+6.8%** with
Sharpe 1.71. The factor was working perfectly on the long side; only the
short leg was destroyed by the bull tide.

### How to catch
1. **Always report per-year LS AND per-year long-only excess.** A factor
   that appears to "fail" in a bull year on LS may be perfectly fine on
   the long side.
2. **Compute Q1 absolute return per year.** If Q1 earns > +20% in any year,
   the short leg is contributing negative alpha regardless of ranking
   accuracy.
3. **Test long-only Q5 excess as the primary metric for bull-market years.**

### Fix — match the strategy to the market structure
A-share has no efficient short-selling mechanism (high borrow cost, limited
supply). The correct deployment for A-share factors is almost always
**long-only excess** (index enhancement) or **long-biased** (130/30),
not dollar-neutral LS. Report both LS and long-only metrics; use LS
for signal validation but long-only for live trading decisions.

For monthly rebalance Q5 long-only, the 2025 excess was +9.3% (cumulative)
vs 0.0% for LS — the strategy was generating alpha that LS masked.

---

## Pitfall 8 — Industry noise eats 30-40% of factor signal

### Symptom
A factor has Test Sharpe ~1.0 (raw) but the train-test Sharpe gap is
> 0.5, flagging overfitting risk.

### Why it happens
Volume-price factors (turnover, amount, vol) have very different baseline
distributions across industries. Banks trade with low turnover and tight
spreads; ChiNext tech stocks trade with high turnover and wide spreads.
Without industry neutralization, the factor is partly capturing
**cross-industry structural differences** rather than within-industry
stock-picking signals. These structural patterns are less stable across
time → larger train-test gap.

### Economic impact (measured)
alpha_05 (volume-price divergence), session `20260415_a_share_volprice_alpha`:

| Metric | Raw | Industry-neutral | Delta |
|--------|-----|-------------------|-------|
| Test Sharpe | 1.011 | **1.447** | **+43%** |
| Train-Test gap | 0.681 | **0.314** | **-54%** |
| Worst-year Sharpe | 0.306 (FAIL) | **0.574 (PASS)** | — |
| IC t-stat | 10.3 | **14.2** | **+38%** |
| Promote floors | 3/5 pass | **5/5 pass** | — |

Industry neutralization turned a RESEARCH-ONLY factor into a PROMOTE
candidate by removing the cross-industry noise that was both inflating
train-period signal and deflating test-period signal.

### How to catch
Agent 4 MUST run industry-neutralized variants for every factor that
uses volume, turnover, or amount data. Compare raw vs neutral test
Sharpe and train-test gap. If neutralization improves BOTH, the raw
factor contains industry leakage.

### Fix
For volume-price factors, always use **industry-demeaned** factor values
as the primary version. Report the raw version as a diagnostic, not as
the headline. The neutralization should be applied BEFORE cross-sectional
ranking: `rank(factor − industry_mean(factor))`.

---

## Pitfall 9 — Orthogonalized IC alive but LS dead: hidden factor exposure

### Symptom
After residualizing the factor against classic factors (size + momentum),
IC t-stat remains significant (e.g., 8.4) but LS Sharpe collapses from
1.0 to ~0.1.

### Why it happens
The factor has a genuine, statistically significant RANKING ability that
is independent of size and momentum. But the PORTFOLIO-LEVEL returns are
largely delivered through a systematic exposure to another factor (e.g.,
anti-momentum). Residualization removes the exposure → removes the returns,
even though the pure ranking signal survives.

### Economic impact (measured)
alpha_05 had Spearman correlation of **−0.41** with 20-day momentum.
- Raw: Test LS Sharpe = 1.01, IC t = 10.3
- Residualized (−size, −mom_20): LS Sharpe = **0.10**, IC t = **8.4**

The IC signal is real (independent ranking power). But 90% of the LS
return came from the anti-momentum tilt, not from pure stock selection.

### How to catch
1. **Always compute factor correlation with size and momentum BEFORE
   celebrating LS Sharpe.** If |corr| > 0.3 with any classic factor,
   residualize and report both versions.
2. **If residualized LS Sharpe < 50% of raw LS Sharpe, the factor is
   primarily a VEHICLE for classic factor exposure**, not an independent
   alpha source.

### Fix — honest labeling and appropriate deployment
This is not necessarily a problem — anti-momentum in A-share has been a
persistent premium. But label the factor honestly:
- "Conditional anti-momentum factor" (not "volume-price alpha")
- Deploy in a portfolio that WANTS anti-momentum exposure
- Do NOT combine it with a momentum factor expecting diversification —
  they will cancel each other

If you want pure residual alpha, you need a factor where BOTH residualized
IC AND residualized LS Sharpe are significant.

---

## Pitfall 10 — Daily rebalance looks great, but after-cost Sharpe is negative

### Symptom
Daily LS Sharpe is 1.4+, but estimated daily one-way turnover is > 100%.
At 15 bps one-way cost, after-cost Sharpe is deeply negative.

### Why it happens
Rank-based factors in a 1500-stock universe have high daily cross-sectional
rank changes. Each day, 30-50% of stocks change quintile → enormous
portfolio turnover. The factor SIGNAL is real, but the signal-to-cost
ratio at daily frequency is negative.

### Economic impact (measured)
alpha_05 daily rebalance:
- Raw LS Sharpe: **1.447** (industry-neutral)
- Estimated daily turnover: **134%** one-way
- After-cost Sharpe at 15 bps: **−6.6** (deeply negative)

But at monthly rebalance (20-day hold):
- LS Sharpe: **1.316**
- Q5 excess Sharpe: **1.428**
- Turnover: ~5× per year (practical)

### How to catch
**Always compute one-way turnover.** If daily turnover > 50%, the factor
cannot be traded at daily frequency regardless of gross Sharpe. Test at
weekly (5d) and monthly (20d) hold periods.

### IC horizon check
If `IC(horizon=20) > IC(horizon=1)`, the factor is BETTER at longer
horizons and daily rebalance is actively harmful. In this case:
- 1d IC = 0.035
- 5d IC = 0.048
- 20d IC = 0.053

The factor's predictive power INCREASES with horizon → monthly rebalance
is not a compromise, it's the OPTIMAL frequency.

### Fix — match rebalance frequency to IC decay profile
Before running any LS backtest, compute IC at horizons {1, 5, 10, 20}.
If IC is flat or increasing, default to monthly rebalance and skip
the daily LS entirely — it's misleading. Report "monthly Q5 long-only
excess" as the PRIMARY metric and "daily LS" as a diagnostic only.

---

## Pitfall 11 — Silent zero-signal backtest (script runs, strategy doesn't)

### Symptom
The backtest completes without exception, numbers appear in the output,
but on inspection:
- Q5 has 3 stocks per day instead of 100
- The same 5 stocks fill Q5 for 800 consecutive trading days
- Signal cross-section std is 0 on 40% of days
- Turnover is 2% annualized (essentially buy-and-hold on a few names)

The headline Sharpe may still print a plausible number (e.g., 0.7) because
Sharpe is well-defined on any non-degenerate return series — but the
"strategy" is actually a near-static basket of whatever few stocks
survived the filters.

### Why it happens
This is the LLM-quant failure class recently quantified by QuantCode-Bench:
roughly 17.8% of one-shot generated backtests run to completion but
produce economically degenerate portfolios. Typical causes:
- Staleness filter too tight (e.g., `staleness_days ≤ 30` when annual
  reports publish at 90-180 day intervals → most stocks drop out)
- Multiple `and`-chained filters where each is reasonable but the
  intersection is empty (e.g., "total_mv > median AND turnover > median
  AND ST-excluded AND has-8q-history" can leave < 100 stocks)
- Neutralization against an industry with only 3 stocks makes the
  within-industry z-score undefined → entire industry drops
- Winsor-then-cross-section-z with an all-equal input produces 0/0 → NaN
  cascades

### Economic impact
Worse than a negative result: a zero-signal backtest with plausible
headline numbers actively wastes the next round. Agent 5 builds a
decision on noise, Agent 1 next round starts from a phantom mechanism.

### How to catch
**Use `references/validation-gates.md` Gate G3.** Non-negotiable
invariants:
- Q5 membership size ≥ 30 on ≥ 95% of days
- Unique names ever in Q5 ≥ 3× portfolio size
- Signal cross-section std > 0 on ≥ 99% of days
- Annual turnover between 10% and 2000%

Plot the Q5 vs Q1 cumulative line. If Q5-Q1 is flat or noisy across the
full window while headline Sharpe prints 0.5+, you are in zero-signal
territory regardless of the numbers.

### Fix
- Relax filters in dependency order: start from the universe, remove one
  filter at a time, re-measure Q5 size, keep going until Q5 size ≥ 30.
- If the signal has structural zeros (e.g., no report for a stock), use
  `merge_asof(direction="backward")` with a bounded staleness, not a
  strict equality join.
- Never rank a cross-section with < 30 non-NaN values — use the previous
  valid date's ranking or mark the day as "no trade" explicitly.

---

## Pitfall 12 — Panel-pandas semantic traps (framework-specific gotchas)

### Symptom
The code looks right to a Python reader but does the wrong thing at the
panel level. The backtest runs, the numbers are different from what the
author intended, and the bug is invisible without explicit verification.

### The specific traps

#### 12.1 `shift(-k)` is the FUTURE, `shift(+k)` is the PAST
- `ret.shift(-1)` at date `t` is `ret[t+1]` — uses information from
  tomorrow to fill today's row. This is the standard way to build a
  target, and the standard way to accidentally create look-ahead on
  features. See Pitfall 2.

#### 12.2 `merge_asof(direction=...)` sign convention
- `direction="backward"` (default) matches the latest LEFT key ≤ RIGHT
  key. For PIT fundamentals: use backward with `by="ts_code"`.
- `direction="forward"` matches the earliest LEFT key ≥ RIGHT key —
  this is look-ahead for fundamentals joins.
- `direction="nearest"` will silently pick future data if it's closer
  in time than past data. Never use `nearest` for PIT joins.

#### 12.3 `groupby().transform()` vs `apply()`
- `transform` broadcasts back to the original index shape; use for
  "demean within industry per date".
- `apply` can return aggregated (one row per group) or broadcast
  (one row per input row) — the difference silently changes the result
  shape. For cross-sectional demean, `transform` is always correct.

#### 12.4 `rolling(window).mean()` with `min_periods=None`
- Default `min_periods = window` — first `window-1` rows are NaN.
- Setting `min_periods=1` fills early periods with partial windows,
  which is usually WHAT YOU WANT for a signal but WHAT YOU DON'T WANT
  for an IC decay chart (the partial windows have different statistical
  properties).
- Be explicit in both cases; never rely on the default.

#### 12.5 `np.polyfit` with NaN inputs
- Returns `array([nan, nan])` silently, then your residualization returns
  all-NaN, then winsor-then-zscore returns all-zero, then your "signal"
  is a constant. Always `dropna()` before `polyfit` and handle the
  "not enough points" case explicitly (see `build_signal` in
  `factors/fundamental/ag_orth_nsi_2y_v1/code.py` for an example).

#### 12.6 Winsorize at `quantile(0.01, 0.99)` on all-equal input
- Produces `lo == hi`, then `clip(lo, hi)` collapses everything to a
  constant, then z-score divides by zero → NaN everywhere. Always
  check `std > 0` before z-scoring.

#### 12.7 Timezone-naive vs timezone-aware timestamps
- `pd.Timestamp("2025-04-01")` is naive. Mixing with timezone-aware
  timestamps from some Tushare endpoints raises TypeError in `merge_asof`
  or silently misaligns in join operations. Normalize both sides
  with `.tz_localize(None)` at the boundary.

#### 12.8 Industry column dtype
- If industry has both `"银行"` (string) and `nan` (float) values,
  `groupby("industry")` drops the NaN rows silently. For neutralization,
  this means stocks with missing industry are dropped from the cross
  section entirely — check coverage explicitly before groupby.

### How to catch
- Every panel-pandas bug in the list above passes G1 and G2 but fails
  G3 or G4 in `validation-gates.md`. Run those gates.
- Keep a "panel diff" unit: feed the expression the same panel, flip one
  assumption (e.g., `shift(+1)` vs `shift(-1)`), and check the sign of
  the IC flips. If it doesn't, either the signal is symmetric (rare) or
  one of your shifts is silently no-op.

### Fix
- Use `merge_asof(direction="backward", by="ts_code")` as the default
  PIT join; add a staleness filter as a separate step.
- Use `groupby.transform("median")` for cross-sectional demeans.
- Explicitly set `min_periods` on every `rolling()`.
- Always wrap winsor+z in a guard: if `std == 0 or sample < 30`, return
  the input unchanged (or NaN) rather than producing a fake signal.
- Normalize timestamps at the cache boundary, not at the backtest boundary.
