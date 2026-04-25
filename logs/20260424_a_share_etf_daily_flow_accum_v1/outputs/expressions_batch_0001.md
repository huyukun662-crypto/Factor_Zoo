# Expressions Batch 0001 — Amount-Based PVO Flow Factor

**Agent 3 (Alpha Builder) output.** Exactly 8 expressions (Rule of 8). Single mechanism: amount-based stealth accumulation.

Sign convention: **higher signal value = more bullish forward return.** All signals are cross-sectionally demeaned per date before use. All time-series operations are strictly backward-looking (no `.shift(-k)` with k > 0).

Shared feature building blocks (strictly past-only):
- `log_amount = log(amount)` pointwise
- `ret1d = log_close - log_close.shift(1)` daily log return
- `amount_ma5 = rolling(5).mean() of amount` per symbol
- `amount_ma60 = rolling(60).mean() of amount` per symbol
- `log_amount_5d_mean = log(amount_ma5)`, `log_amount_60d_mean = log(amount_ma60)`
- `z60(x) = (x - rolling(60).mean(x)) / rolling(60).std(x)` per symbol (min_periods=20)
- `z20(x)` analogous with window 20
- `std20(ret1d)` rolling 20d std of daily returns per symbol

---

## e1: abnormal_amount_z60

**Code:** `z60(log(amount))`

**Economic story:** the baseline PVO signal — amount vs its own 60-day normal range. ETFs that have sustained days of anomalous CNY-traded volume relative to their own recent history are candidates for institutional positioning. No price-component subtraction yet — tests whether the raw amount footprint alone predicts returns.

**Expected turnover:** **moderate** (z-score shifts gradually over multiple days; 5-day rebalance further smooths). Rationale: `z60(log_amount)` changes by ~1/σ_amount per day, so ranks in a 30-name universe rotate on a ~10-day timescale.

**Fragility notes:** mechanically log_amount = log_close + log_volume; per-symbol z60 removes the price-level effect within-symbol but residual cross-sectional price-level correlation could remain. Monitored via the corr-vs-20d-momentum check.

---

## e2: abnormal_amount_smoothed_5d

**Code:** `z60(log_amount_5d_mean)`

**Economic story:** same primitive as e1 but smoothed over 5 days before z-scoring. Single-day amount spikes (news drops, ex-dividend distribution, ETF rebalance) are averaged out. Isolates *persistent* abnormal flow, which is what true accumulation looks like.

**Expected turnover:** **lower than e1** — smoothing damps the signal's daily variance so ranks move more slowly.

**Fragility notes:** the 5d mean introduces a small lag vs e1; if flow-to-return is fast, e2 may be weaker than e1. Direct comparison of e1 vs e2 at multiple horizons resolves this.

---

## e3: amount_ratio_5d_60d

**Code:** `log(amount_ma5) - log(amount_ma60)`

**Economic story:** ratio form of flow-surge — `log(ma5 / ma60)`. Robust to scale and regime changes in volume (unlike z60, it does not assume stationary variance). Positive = recent flow exceeds long-term flow; negative = flow drying up. This is the simplest "flow surge" framing and is standard in the PVO literature.

**Expected turnover:** **moderate** — similar to e1 but without the σ-normalization, so more driven by absolute flow changes than relative-to-noise.

**Fragility notes:** no σ-normalization means a name with chronically volatile amount (e.g., thematic names on news cycles) looks similar to a name with stealth accumulation. e1 + e3 paired give us the volatility-normalized vs. scale-normalized comparison.

---

## e4: quiet_day_amount_z60

**Code:** `z60(log(amount)) * indicator(abs(ret1d) < 0.5 * std20(ret1d))`

**Economic story:** **the hypothesis-pure signal.** High amount z-score paired with a *smaller than usual* daily return magnitude. In the Llorente et al. (2002) decomposition, this is the informed-trading regime — someone is trading without moving the price, which is what patient institutional desks do. High-amount with big-price-move is noise-trader or news chase (excluded here).

**Expected turnover:** **sparse-like** — the indicator is 0 on most days for most names, so the factor is dense in rank space but has lots of ties; the ranks move when the indicator flips on/off.

**Fragility notes:** the `0.5 * std20` threshold is a choice; sensitivity to it is checked downstream. The use of `std20(ret1d)` as the threshold is strictly backward-looking.

---

## e5: inverse_amihud_z60

**Code:** `z60(log(amount) - log(abs(ret1d) + 1e-6))`

**Economic story:** Amihud-inverse — amount per unit of return magnitude. High when price moved little despite large amount (resilient, stealth) or when amount is high and return is small. This is the continuous analog of e4 — rather than a binary indicator, it expresses the ratio smoothly. Academically motivated (Amihud 2002 ILLIQ with a minus sign, normalized).

**Expected turnover:** **moderate to high** — ratio signals are noisier than z-scores, and the 1d return in the denominator flips day-to-day.

**Fragility notes:** the 1e-6 floor prevents division-by-zero on a true-zero return day but creates a blow-up sensitivity. Must check that no symbol-day has an explosive value that dominates the rank.

---

## e6: signed_flow_5d

**Code:** `mean_over_last_5d( sign(ret1d) * z60(log(amount)) )`

**Economic story:** directional flow — positive when abnormally-high-amount days were also *up* days over the last 5 trading days. This is the closest thing we can build to an order-imbalance proxy from daily close-bar data. If buyers are dominating the accumulation, upday flow concentrates; if sellers, downday flow does.

**Expected turnover:** **moderate** — smoothed by the 5d rolling window, so ranks decay gradually.

**Fragility notes:** the sign flips often on low-conviction days, but the amount-z-score weighting gives heavy weight only to high-volume days, which usually carry more information. Strong signal if the mechanism is directional.

---

## e7: relative_amount_share_z20

**Code:** `z20( amount / sum_over_universe_on_date(amount) )`

**Economic story:** *relative* flow — what fraction of today's total cross-sectional CNY-traded went to this ETF? Normalizes for market-wide volume regime shifts (festival days, half-days, crisis spikes). Shows where the money is rotating *to* regardless of absolute level.

**Expected turnover:** **moderate** — the share is renormalized daily by the universe total, but persistent high-share names continue to rank high.

**Fragility notes:** highly correlated with e1 in calm regimes (both reflect abnormal amount); differentiates in regime shifts (when the universe-total spikes, e1 spikes broadly but e7 stays in the normal range).

---

## e8: flow_ensemble_rank

**Code:** `cross_sectional_mean( rank(e1), rank(e3), rank(e4), rank(e6) )`

**Economic story:** diversified ensemble across four flow motifs — (1) pure abnormal volume, (3) ratio-based surge, (4) quiet-day filtered, (6) signed directional. Each motif captures a different slice of the stealth-accumulation pattern. The ensemble is what we'd deploy if multiple sub-signals survive validation.

**Expected turnover:** **lowest** — averaging four ranks heavily damps rank fluctuation in a 30-name universe.

**Fragility notes:** the chosen 4-signal subset is a judgment call. Downstream diagnostics report correlation of e8 with its components; if e8 is dominated by one of them, we'll know.

---

## What is NOT in the batch and why

- `z60(raw volume)` — linearly co-moves with `log_amount - log_close`, so conveys the same info as e1 plus a price dependency; rejected.
- `amount × 1d_return` — signed dollar flow without z-scoring; highly variance-unstable across ETFs with different AUM; rejected.
- A second ensemble over e2/e5/e7 — would violate Rule of 8 and risk over-weighting ensemble-style signals.
- Any expression using `shift(-k)`, `next_*`, or cutoff-dependent masks — forbidden by look-ahead audit.

## Expected turnover ordering

`e2 < e8 < e1 ≈ e3 ≈ e6 ≈ e7 < e4 < e5`

## Sign-check prediction table (for Agent 4's G4 gate)

| expr | IC sign expected at primary k=10 | decile monotonicity expected |
|------|----------------------------------|------------------------------|
| e1 | + | Q1 < Q5 |
| e2 | + | Q1 < Q5 |
| e3 | + | Q1 < Q5 |
| e4 | + (strongest if thesis correct) | Q1 < Q5, moderate monotonic |
| e5 | + | Q1 < Q5 |
| e6 | + if directional accumulation dominates; ~0 if not | Q1 < Q5 if signed regime |
| e7 | + | Q1 < Q5 |
| e8 | + by construction of component ranks | Q1 < Q5, strict monotonic |
