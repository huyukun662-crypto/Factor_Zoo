# Final Summary — Round 2 (Weekly TQPB V7_gold combine)

**Session:** `20260423_a_share_etf_weekly_tqpb_v1` · Round 2
**Universe:** 34 V7_gold ETFs + 14 broad-index ETFs (expanded to 48)
**Sample:** 2019-01 → 2026-04, 377 weeks
**Verdict:** **RESEARCH-ONLY; Round 1 deploy recommendation RETRACTED**

## One-paragraph summary

Round 2 ran the four directions requested by the user (long-only top-3,
signal-level fusion, regime-conditional overlay, extended universe). While
setting up Direction 1, an audit caught a critical bug in Round 1's
`r1_breakout_vol_conf` signal: `max_high_20 = rolling(20).max()` includes
the current bar, so on breakout days `close − max_high_20 = 0` and the
signal is identically zero on all 42,788 observations. Round 1's claimed
Sharpe 1.79 / corr −0.009 / residual Sharpe +0.44 came entirely from
pandas stable-sort tie-breaking on a degenerate signal, i.e., a **ghost
result**. Round 2 re-ran everything with the corrected semantics
(`max_high_20 = shift(1).rolling(20).max()`, strict inequality), which
produces ~4.4% breakout events across the panel. With the corrected
signal, none of the four directions improves V7_gold: long-only top-3 at
5% blend gives Sh 1.71 (−0.05 vs V7 1.76), signal-level fusion variants
all give ≤ 1.75 (worst −0.03), extended 48-ETF universe gives 1.71
(−0.05), and regime-conditional overlay at `breadth_z < −0.25` gives
1.748 (+0.021, within noise). V7_gold stands on its own. The Round 1
deploy recommendation is formally retracted.

## Headline numbers (ALL COMPUTED WITH CORRECTED SIGNAL)

| Direction | Best variant | Sharpe | Δ vs V7 | MaxDD | Notes |
|---|---|---:|---:|---:|---|
| — | V7_gold baseline (reproduced) | **1.759** | — | −9.1% | same sample |
| D1 | 85% V7 + 5% long-only top-3 | 1.714 | −0.045 | −8.9% | dilutive |
| D2 | Fused Leg A (25% breadth + 10% brk_z) | 1.746 | −0.013 | −9.6% | marginal hurt |
| D3 | Regime-cond LS, breadth_z < −0.25, 15% | **1.748** | **+0.021** | −8.4% | within noise |
| D4 | 85% V7 + 5% top-3 on 48 ETFs | 1.711 | −0.048 | −8.9% | universe ext hurts |

*(Round 1 reported 1.79 / +0.06; was ghost. Always-on 15% LS with correct
signal gives 1.693, BELOW V7 baseline.)*

## The Round 1 bug in full

**Intended signal** (per Round 1 expression doc):
> `(close − max_high_20)/std_20d × I[close ≥ max_high_20 AND vol_5/vol_20 > 1.2]`

**What was actually computed:**
```python
df["max_high_20"] = g["close_adj"].apply(lambda s: s.rolling(20, min_periods=10).max())
# rolling().max() includes the CURRENT bar; on local-max days:
#   close == max_high_20  → close - max_high_20 == 0
# on non-max days:
#   close < max_high_20   → close - max_high_20 < 0, clipped to 0 by .clip(lower=0)
# → signal is identically zero on ALL observations
```

**Empirical confirmation:**
- `signal_raw > 0` on **0 / 42,788** observations
- `unique(signal)` = `{0.0}` (literally one value)

**Why it still produced a "PnL":** `pd.qcut` collapsed (hence the `NaN` IC
that was logged as "sparse-trigger artifact"), but the LS portfolio used
`sort_values(ascending=False).head(5)` which returns the first 5 rows by
pandas' stable sort order. With a tied signal, that's essentially ranking
ETFs alphabetically by `ts_code`. The resulting LS book happened to have
corr −0.009 with V7 and a small positive Sharpe from pure noise.

## The Round 2 bug (and fix)

On the first run of Direction 1 with the corrected signal, standalone
MaxDD came out at −24%, vol at 158% annualized — obviously wrong.
Root cause: my `long_only_topn` function used `continue` on weeks with no
breakouts, and the `daily_pnl_from_weekly_weights` function used `ffill`
to propagate weights. Together these held positions indefinitely during
breakout-drought periods. Fix: each Friday must write explicit weights
(including all-zeros for cash weeks) to the dense weekly weights matrix,
so ffill works correctly.

This is also a workflow lesson (see §8.5 of alpha_ranking).

## What we learned

### Quantitatively

1. **V7_gold is already close to the Sharpe ceiling** for the A-share
   thematic ETF opportunity set at weekly frequency. Its `mom_4w`
   captures most of the useful trend information; breadth handles
   regime. The residual noise floor in returns is higher than any
   single-signal weekly alpha can clear.
2. **Breakout-volume-confirmed signals at weekly sampling are a
   trend-coincident redundancy** with V7. They fire in the same
   regimes V7 picks. Correlation after removing the zero-signal bug
   is actually POSITIVE with V7 (~+0.25 on LS pnl), so even residual
   Sharpe is weak.
3. **Extended universe** (34 → 48) does not help because the added
   broad-index ETFs are highly correlated with V7's top picks. Need
   truly cross-asset additions (bond, commodity, HK/US ETFs already
   in 48 but their cross-correlation with V7 is still positive
   during risk-on regimes).
4. **Regime-conditional** at `breadth_z < −0.25` gives a nominal
   +0.021 Sharpe lift. With a t-stat of ~0.4 on 377 weeks, this is
   within noise. Not deployable.

### Workflow-level

1. **Signal-nonzero sanity check** needs to be a G1 gate. An all-zero
   or all-constant signal produces valid-looking PnL via tie-breaking,
   which can survive IC, Sharpe, and correlation checks. Should include:
   `count(signal != 0), count(signal > 0), unique_count(signal)`.
2. **Strict inequality + prior-window semantics** for all
   breakout / reversal / extreme-event signals. `close >= rolling_max`
   is almost never what you want; `close > shift(1).rolling_max` is.
3. **Dense rebalancing** for overlay/combine sessions: every rebalance
   date must write explicit weights for all symbols, including zeros.
   Never `continue` on a rebalance date. Document in
   `execution-plan.md`.
4. **Reproduce baseline from source** on the combine sample. Trusting a
   saved headline Sharpe (1.91) led Round 1 to overstate V7's bar; the
   reproduced baseline on 377 overlapping weeks is 1.76.
5. **Audit probe** for combine sessions: "what happens if I replace the
   new signal's pnl with pure zeros?" Round 1 would have immediately
   flunked this because its "signal" WAS pure zero.

## Recommendation

| Action | Rationale |
|---|---|
| Retract 85% V7 + 15% breakout LS overlay | Built on a degenerate signal |
| Keep V7_gold standalone | Sh 1.76, MaxDD −9.1% stands |
| Do NOT deploy regime-conditional overlay | Δ within noise on 377 weeks |
| Next overlay attempt should use out-of-universe assets | Cross-asset diversification > signal-level |

## Per-year V7 reproduction (sanity; matches published per-year closely)

| year | weeks | Sh (round2 repro) | Sh (published) |
|---:|---:|---:|---:|
| 2019 | 51 | 2.09 | 2.28 |
| 2020 | 52 | 2.21 | 2.56 |
| 2021 | 55 | 1.70 | 1.85 |
| 2022 | 50 | 0.83 | 0.81 |
| 2023 | 50 | 1.60 | 1.70 |
| 2024 | 51 | 1.88 | 2.11 |
| 2025 | 53 | 2.04 | 2.30 |
| 2026 | 15 | 0.93 | 0.91 |

The small differences come from my reproduction computing breadth/turnover
on the same weekly panel but with slightly different `elig` masking near
period boundaries; patterns are identical (2022 is the weakest year).

## Research-log entry (for README)

```
session: 20260423_a_share_etf_weekly_tqpb_v1 (Round 2)
factor_family: trend_technical.breakout_volume_confirmed_weekly_etf
verdict: RESEARCH_ONLY; Round 1 deploy recommendation RETRACTED
directions_tested:
  - long_only_top3:              Sh 1.71 @ 5%   (Δ −0.05 vs V7)
  - signal_level_fusion:         Sh 1.75 max    (Δ −0.01 vs V7)
  - regime_conditional_breadth:  Sh 1.75        (Δ +0.02 vs V7, within noise)
  - extended_universe_48:        Sh 1.71 @ 5%   (Δ −0.05 vs V7)
critical_bug_found:
  round1_breakout_signal_always_zero: max_high_20 included current bar; signal
    was identically 0; "Round 1 Sh 1.79 / corr −0.009 / residual Sh +0.44"
    were artifacts of pandas stable-sort tie-breaking on degenerate signal.
v7_baseline_round2_repro: Sh 1.759 (377w), MaxDD -9.1%
always_on_15pct_LS_overlay_with_correct_signal: Sh 1.693 (BELOW V7)
workflow_gaps_found:
  - G1 should check signal-nonzero / signal-unique
  - common-pitfalls should document prior-window rolling + strict inequality
  - execution-plan should require dense rebalancing with explicit cash weeks
status: RESEARCH_ONLY
```

## Files

```
logs/20260423_a_share_etf_weekly_tqpb_v1/
├── scripts/round2/
│   ├── 01_fetch_broad_index_etfs.py         # 14 broad ETFs via Yahoo
│   ├── 02_directions_1_3_4.py               # D1, D3, D4 combined
│   └── 03_direction_2_v7_fusion.py          # D2 V7 Leg A fusion
├── outputs/round2/
│   ├── alpha_ranking.md                     # Agent 5 Round 2
│   ├── final_summary.md                     # this file
│   ├── directions_1_3_4_results.json        # structured D1/D3/D4
│   ├── d1_top3_grid.csv                     # blend weight grid
│   ├── d1_top3_pnl_weekly.csv
│   ├── d2_signal_fusion_results.json        # variant sweep
│   ├── d2_per_year_compare.csv
│   ├── d2_v7_pnl_series.csv
│   ├── d3_regime_sensitivity.csv
│   ├── d3_ls_top5bot5_pnl_weekly.csv
│   ├── d4_top3_ext48_grid.csv
│   ├── d4_top3_ext48_pnl_weekly.csv
│   ├── etf_daily_broad.parquet              # 14 broad ETFs daily
│   └── etf_universe_broad.csv
├── round_0001.yml                           # (round 1)
├── round_0002.yml                           # round 2 summary
└── run_state.json                           # reopened, verdict updated
```
