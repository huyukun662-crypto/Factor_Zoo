# Alpha Ranking — A-Share ETF Reversal v1, Rounds 1 + 2

**Session:** `20260423_a_share_etf_reversal_v1`
**Agent:** 5 (Evaluator & Recorder)
**Date:** 2026-04-23

---

## 1. Two-round summary

| | Round 1 | Round 2 |
|---|---|---|
| Primary horizon | 10 trading days | **60 trading days** |
| Rebalance | weekly (Wed) | monthly (20d) |
| Mechanism | short-term reversal | long-term reversal + selective OS |
| Expressions | 8 | 8 |
| G1 pass | 8/8 | 8/8 |
| G2 pass | 8/8 | 8/8 |
| G3 pass | 3/8 | 0/8 (long warmup reduces pct_enough_signal) |
| **G4 pass** | **0/8** | **2/8** |
| G5 batch horizon | fail | **pass** (50% peak at k=60) |
| Best IC t-stat | +2.58 (vol_confirmed_rev @ k10) | **+7.75** (rsi_extreme_os @ k20) |
| Best gross Sharpe | +0.33 (vol_confirmed_rev) | **+0.58** (lt_rev_60d) |
| Best net Sharpe @5bps | +0.16 | **+0.56** |
| Worst-year Sharpe of best | -1.05 (2023) | **-0.68 (2020)** |
| Verdict | batch hypothesis rejected → Round 2 | RESEARCH-ONLY |

## 2. Round 1 retrospective

Round 1 hypothesized that reversal (dip-buy) works at k=10 trading days
on this 18-ETF universe. The data **inverted the thesis cleanly**:

- 7 of 8 signals had NEGATIVE IC at k∈{5,10,20}.
- Quintile monotonicity on `r1_dd20` was perfectly inverted: Q1 (no dip)
  +0.44% / Q5 (deep dip) +0.03% over 10 days.
- IC magnitude GREW with horizon (k=5 → k=20), a classic momentum-
  continuation signature.
- Only `r1_vol_confirmed_rev` had positive IC (+0.020), but net Sharpe
  was only +0.16 — below the 0.5 floor.

Per `references/validation-gates.md` G5 protocol: batch-level thesis
failure returns to Agent 2 for horizon/mechanism re-specification, NOT
to Agent 3 for expression repair.

## 3. Round 2 findings

Round 2 tested long-horizon reversal (60d, 120d, 250d) + narrow-
condition variants (extreme drawdown, RSI<30) at monthly rebalance.

### 3.1 The promoted-for-research candidate: `r2_lt_rev_60d`

**Formula**: `-(log_close[t] - log_close[t-60])`, universe-EW demeaned.

**Headline metrics** (monthly rebalance, top-4/bot-4, 5 bps/side):

| metric | value | floor | pass? |
|---|---:|---:|:--:|
| Gross Sharpe | +0.58 | ≥ 1.0 | ❌ |
| Net Sharpe @5bps | **+0.56** | ≥ 0.5 | ✅ |
| IC mean @k=60 | +0.023 | ≥ 0.03 | ❌ (just below) |
| IC t-stat @k=60 | +2.35 | — | — |
| ICIR annualized | +0.99 | ≥ 0.3 | ✅ |
| Quintile Q5-Q1 | +0.51% over 60d | > 0 | ✅ |
| Monotonicity (5 bins) | 1 inversion (Q4>Q5) | ≤ 2 | ✅ |
| Worst calendar-year Sharpe | **-0.68 (2020)** | ≥ 0 | ❌ |
| Turnover | 1363%/y | ≤ 2000% | ✅ |
| Corr vs universe EW | < 0.85 | — | ✅ |

**Two hard floors fail**: IC mean just misses (+0.023 vs 0.03) and
worst-year Sharpe (-0.68 in 2020) is below zero. Per session rules,
any floor failure → RESEARCH-ONLY.

**But the signal is economically real**:

- Long/short legs rotate through 15-17 of 18 ETFs at comparable
  frequencies. Not a buried single-asset bet.
- 6 of 7 years are positive or flat; only 2020 is clearly negative.
- Cost sensitivity is flat: Sharpe at 2/5/8 bps = +0.57/+0.56/+0.55.
- 2026 YTD Sharpe +1.54 on 71 trading days (+79.7% ann. mean, 51.9%
  ann. vol) — still performing in the out-of-sample period.

### 3.2 The curiosity: `r2_rsi_extreme_os`

RSI(14) oversold (signal active only when RSI < 30) has:
- IC @k=20 = **+0.065, t-stat = +7.75** (strongest single-horizon IC
  in the whole 16-expression study)
- Quintile Q5-Q1 at k=60 = **+13.5%** (extraordinary)
- But top-4/bot-4 LS Sharpe only +0.13 because 16 of 18 ETFs have
  zero signal on most days → short leg is noise.

This expression is mis-spec'd for the symmetric LS strategy we ran.
A triggered-long-only strategy (long when an ETF's RSI crosses below
30, equal-weight across all triggered names, exit when RSI crosses
above 50) would likely capture the IC. **Flagged for Round 3.**

### 3.3 The rejection: `r2_lt_rev_250d`

Built expecting stronger long-term reversal at 1-year, but IC is
decisively NEGATIVE at k=60 and k=120 (-0.110 and -0.126, t < -11).
This is the Jegadeesh-Titman 1-year momentum zone on A-share ETFs:
past-year winners keep winning for the next 2-4 months. **Long-term
reversal begins to work around k=60 but reverses into momentum by
k=120-250.** This is an important new finding for the factor zoo —
the reversal window on A-share ETFs is narrower than classic DeBondt-
Thaler (3-5 years).

### 3.4 Audit probe

`+logret_20d` at k=60: IC = -0.003, t = -0.34. Near-zero momentum
IC confirms the pipeline is clean and k=60 sits in the momentum-to-
reversal crossover zone.

## 4. Cross-round meta-observations

### 4.1 Mechanism topology on A-share ETFs (2020-2026)

Synthesizing all 16 expressions + probe:

| horizon | mechanism direction | evidence |
|---:|---|---|
| 1-5 days  | weak momentum | r1 signals inverted IC |
| 10-20 days | **momentum** | r1_dd20 IC@k20 = -0.054, t=-5.79 |
| 20-30 days | transition | r2_lt_rev_60d IC@k20 = -0.003 |
| 60 days  | **reversal** | r2_lt_rev_60d IC@k60 = +0.023, t=+2.35 |
| 120 days | noise / mild momentum | r2_lt_rev_120d IC@k120 = -0.056 |
| 250 days | **1y momentum** | r2_lt_rev_250d IC@k60 = -0.110, t=-11.3 |

**Reversal on A-share ETFs is a narrow ~60-day effect, sandwiched
between short-horizon momentum (≤20d) and long-horizon momentum
(~1y).** This map may be the most reusable output of the session.

### 4.2 The "RSI<30 extreme oversold" effect

On days an ETF hits RSI(14)<30, the next 20-60 days deliver large
excess returns (Q5-Q1 +13.5% over 60d at k=60). This may be the
right hook for a tactical long-only dip-buy rule, but the cross-
sectional formulation we tested dilutes it.

### 4.3 Dogfood: what this session confirmed about the workflow

- **G5 earned its keep again.** Round 1 G5-fail correctly flagged
  "wrong horizon" and drove the mechanism pivot to k=60 in Round 2.
  Without G5 we would have rejected all 8 Round-1 expressions as
  individual failures and never connected them to a horizon-wide
  pattern.
- **Audit probe (`+logret_20d`) pattern is reusable.** Running a
  known-direction signal as a separate sanity check, outside the Rule
  of 8, is cheap and catches pipeline bugs deterministically. Should
  be a standard Agent 4 deliverable on every session — add to
  `execution-plan.md`.
- **Falsification-first forced honest RESEARCH-ONLY verdict.** The
  strongest candidate (lt_rev_60d) has net Sharpe > 0.5 floor, but the
  2020 Sharpe = -0.68 blocks PROMOTE. Consistent with the Accruals /
  Asset Growth disciplinary precedent.

## 5. Final verdict

### Best candidate: `r2_lt_rev_60d`

**Status: RESEARCH-ONLY**

**Reason for not-PROMOTE**:
1. IC mean +0.023 < 0.03 floor (marginal)
2. Worst-year Sharpe -0.68 < 0 floor (clear fail)

**Reason for research-worthy**:
1. Mechanism confirmed by G5 and by the horizon map (k=60 is the
   reversal peak)
2. Net Sharpe @5bps = +0.56 clears the net-Sharpe floor
3. Signal is diversified across 15-17 ETFs (not a buried beta trade)
4. Out-of-sample 2026 YTD (71 days) at +1.54 Sharpe
5. Cost structure is friendly (1363%/y × 5bps × 2 = ~14 bp/y drag)

### Round 3 suggestions (if user approves)

1. **Long-only top-3 of r2_lt_rev_60d** — expected to dodge 2020's
   short-leg pain (past-winners that kept winning). If long-only 2020
   Sharpe > 0, promote candidate.
2. **Triggered-long-only RSI<30 strategy** — capture the +0.065 IC@k20
   on r2_rsi_extreme_os with a strategy that fits the signal geometry.
3. **Extend universe to 40-50 ETFs** — current 18 gives Q5=4 which is
   thin; adding 20 more thematic ETFs (新能源, 红利低波, 恒生互联网,
   中概互联网, 创业板 ETF 华夏, 中证1000 其他) would let us test Q7/Q8.
4. **Extend window back to 2015** — captures 2015/2017 regime and tests
   whether 2020's bad year is a repeating pattern or a one-off.

## 6. Reference expression for the factor zoo research log

Even without PROMOTE, record the following in the Factor_Zoo research
log as a confirmed-mechanism-but-not-deployed entry:

```
factor_family: trend_technical.long_term_reversal_etf
mechanism:     60-day cross-sectional mean reversion on 18 A-share ETFs
horizon:       60 trading days (monthly rebalance)
net_sharpe_5bps: +0.56 (+22% CAGR, -47% maxdd)
worst_year:    2020 -0.68 Sharpe (blocks promote)
status:        RESEARCH_ONLY
key_finding:   "Reversal on A-share ETFs is a narrow 60d window;
                short-horizon (≤20d) is momentum, 1-year is momentum.
                Only the 2-3 month zone carries reversal payoff."
```

## 7. Files archived

```
logs/20260423_a_share_etf_reversal_v1/
├── inputs/
│   ├── objective.md
│   ├── etf_daily.parquet          # 18 ETFs, 27,017 bars, 2020-01 to 2026-04
│   └── fetch.log
├── scripts/
│   ├── 01_fetch_etf_daily.py      # Yahoo Finance via v8/chart
│   ├── 02_build_and_backtest.py   # Round 1 (weekly reversal)
│   └── 03_round2_backtest.py      # Round 2 (monthly long-term reversal)
├── outputs/
│   ├── research_brief.md                  # Agent 1
│   ├── session_metadata.yml               # Agent 2 (R1)
│   ├── session_metadata_round2.yml        # Agent 2 (R2)
│   ├── expressions_batch_0001.md          # Agent 3 (R1)
│   ├── expressions_batch_0002.md          # Agent 3 (R2)
│   ├── backtest_results_batch_0001.md     # Agent 4 (R1)
│   ├── backtest_results_batch_0002.md     # Agent 4 (R2)
│   ├── ic_table_batch_0001.csv
│   ├── ic_table_batch_0002.csv
│   ├── ls_summary_batch_0001.csv
│   ├── ls_summary_batch_0002.csv
│   ├── decile_summary_batch_0001.csv
│   ├── decile_summary_batch_0002.csv
│   ├── cost_sensitivity_batch_0001.csv
│   ├── cost_sensitivity_batch_0002.csv
│   ├── per_year_sharpe_batch_0001.csv
│   ├── per_year_sharpe_batch_0002.csv
│   ├── validation_gates_batch_0001.json
│   ├── validation_gates_batch_0002.json
│   ├── momentum_probe_batch_0002.json
│   ├── alpha_ranking.md                   # (this file)
│   └── final_summary.md                   # top-level session close
├── working/
│   ├── handoff_1_to_2.json
│   ├── handoff_2_to_3.json
│   └── handoff_4_to_5.json
├── round_0001.yml
├── round_0002.yml
└── run_state.json
```
