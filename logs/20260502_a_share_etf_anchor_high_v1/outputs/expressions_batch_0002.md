# Expressions — batch_0002 (Round 2: rescue E3 worst-year)

Round 1 outcome: E3 = `range_pos_252` is the only factor with positive
LS net Sharpe (0.625) and clean train→test (0.67 → 0.75), but its
worst-year LS Sharpe is -0.18 (2024) and -0.11 (2022), failing the
≥ 0.5 PROMOTE floor.

Round 2 hypothesis: the underlying mechanism (cross-sectional range
position) is real but unhedged against (a) regime shifts and (b)
volatility differences across ETFs. Eight variants explore whether
multi-window aggregation, vol-targeting, regime-gating, or
momentum-residualization can rescue the worst year without breaking
the headline.

Universe: 32 ETFs (drop 512800.SS, 515170.SS).
k=20 monthly, delay=1, rebal=21d, cost=5 bps/side.

## F1 — `range_pos_252` baseline (rerun)

```
F1 = (close - rolling_min(close,252)) / (rolling_max(close,252) - rolling_min(close,252))
```

Rerun so all R2 variants are compared to a fresh anchor on the same
codepath. Identical to batch_0001 E3.

## F2 — `range_pos_120` (medium-window range position)

```
F2 = (close - rolling_min(close,120)) / (rolling_max(close,120) - rolling_min(close,120))
```

Hypothesis: 120-day range refreshes faster, so 2024 mid-cap rotation
should reflect into the signal earlier than 252-day.

## F3 — `range_pos_60` (short-window range position)

```
F3 = (close - rolling_min(close,60)) / (rolling_max(close,60) - rolling_min(close,60))
```

Same form, ~3 months. May overfit noise but worth testing.

## F4 — multi-window equal-rank composite

```
F4 = (rank_xs(F1) + rank_xs(F2) + rank_xs(F3)) / 3
```

Average cross-sectional rank across 60/120/252 windows.
Diversifies the window dependency without changing the mechanism.

## F5 — `range_pos_252` × vol-target weight

```
sig_252 = F1
vol_60  = rolling_std(daily_ret, 60) × sqrt(252)
F5      = sig_252 / vol_60     # equivalently: rank by sig_252 / vol_60
```

Down-weights high-vol ETFs (typically thematic) so the signal does
not get drowned by 2024-style high-vol momentum unwinds. Note: this
is a **selection-time** modifier, not portfolio-level vol targeting.

## F6 — `range_pos_252` with bench>MA200 risk-on gate

```
g_t = 1 if close_510300_t > MA200(close_510300)_t else 0
F6  = F1 × g_t   (signal collapses to flat when bench < MA200)
```

When sig collapses to flat (constant across ETFs), the LS portfolio
goes to zero exposure that day — i.e., we step out of the trade
during a bear regime. Distinct from batch_0001 E6 because that gate
was applied to the broken E1, not to E3.

## F7 — `range_pos_252` with momentum residualization

```
mom_252 = rolling_sum(daily_ret, 252)
F7      = F1 - β · mom_252_xs_z   where β fit by daily xs OLS of F1 on mom
```

Strips the 252-day momentum exposure. Tests whether E3's headline
is a pure range-position effect or partly a momentum clone (Pitfall 9).

## F8 — `range_pos_252` rebalanced every 42 days (bi-monthly)

```
F8 = F1 with rebal_days = 42 (instead of 21)
```

Slower rebalance → lower turnover, lower cost. If the per-year shape
is preserved at 42-day rebal, the signal has a long usable horizon
and is a better candidate for production.

---

## Diversity self-check

| | F1 | F2 | F3 | F4 | F5 | F6 | F7 | F8 |
|--|--|--|--|--|--|--|--|--|
|window|252|120|60|60+120+252|252|252|252|252|
|modifier|none|none|none|equal-rank avg|/vol|gate|res-mom|rebal=42|

8 distinct constructions, all anchored to the range-position mechanism.

## Expected behaviors

- F2/F3 should improve 2024 (short-window catches up faster) but may
  hurt 2023 (more noise).
- F4 should compress year-to-year variance.
- F5 should help 2022 (bear/high-vol regime) by avoiding crowded
  thematics.
- F6 should rescue 2022 specifically.
- F7 quantifies the momentum-clone risk; if F7 retains > 50% of F1's
  Sharpe, the factor is genuine.
- F8 tests cost robustness for production.

## What success looks like for R2

PROMOTE candidate iff a single F* achieves:
- Net 5 bps LS Sharpe ≥ 0.5
- Worst-year LS Sharpe ≥ 0.5
- Best-year-out ≥ 50% of headline
- Train Sharpe and Test Sharpe both ≥ 0.4 (no regime collapse)
- Cost-net positive at 10 bps/side
