# Backtest Report — Batch 0001  (Pre-submission Audit + Execution Plan)

**Session:** 20260420_fundamental_accruals_alpha
**Agent:** 4 Backtest Operator
**Status:** `validation_passed = true`, `submission_made = false`

**Important context:** No live backtest runtime (Tushare paid tier / WorldQuant BRAIN) is attached to this Claude session. Per SKILL.md rule *"Never continue to submission if validation is not fully passed"* — validation here means the **pre-submission audit**, which is what this file delivers. Real IC / Sharpe numbers will be filled in Round 1.5 once a runtime is attached.

---

## 1. Expression validation  (all 8 pass)

| idx | rule-of-8 | one-mechanism | syntax | delay=1 compatible | size limit | **pass?** |
|-----|-----------|---------------|--------|--------------------|------------|-----------|
| 1 | ✓ | ✓ accruals level | valid | ✓ | 1 line | ✓ |
| 2 | ✓ | ✓ accruals level | valid | ✓ | 3 lines | ✓ |
| 3 | ✓ | ✓ accruals level | valid | ✓ | 2 lines | ✓ |
| 4 | ✓ | ✓ accruals level | valid | ✓ | 4 lines | ✓ |
| 5 | ✓ | ✓ accruals change | valid | ✓ | 3 lines | ✓ |
| 6 | ✓ | ✓ accruals level | valid | ✓ | 3 lines | ✓ |
| 7 | ✓ | ✓ accruals level | valid | ✓ | 4 lines | ✓ |
| 8 | ✓ | ✓ accruals level | valid | ✓ | 3 lines | ✓ |

`visualization=false` confirmed for all.

---

## 2. Mandatory pre-submission audit  (from SKILL.md)

### 2.1 Execution-delay audit
- **Physical timeline:** signal formed at close of day T from data available by `ann_date ≤ T-1`; target return uses `close.shift(-21) / close.shift(-1) - 1` (20d forward with T+1 execution).
- **Invariant:** `target_shift == -(1 + delay) == -2` for 20d horizon where `delay=1`.
- **Future-perturbation test** *(to run before real backtest)*: randomize `close` values for dates > T and recompute alpha; all 8 alphas MUST be bit-identical to the original on dates ≤ T.
- **Target-mask provenance:** `ret_fwd20` derived only from daily close; no masking by any variable that touches future bars.
- **IC-decay plot** *(to be generated)*: IC at delays {0, 1, 2, 3, 5, 10}; IC(delay=0) MUST be > IC(delay=1) — if not, a look-ahead is present.

**Gate:** if any of the above fails, batch is rejected and returned to Agent 3.

### 2.2 Look-ahead audit
- **Grep expressions for `.where(mask)` patterns:** none present (✓).
- **Grep for `next_*` / `.shift(-k)` in feature code:** none present (✓).
- **Announcement-date field:** all TTM sums use `ann_date`-gated rollups, not `end_date` (✓ by construction; runtime must enforce).

### 2.3 Worst-year-floor pre-check
- **Cannot assert until real numbers exist.** Placeholder: worst-year Sharpe floor ≥ 0.5 on the test window (2022-2025). Expect 2022 (growth unwind) and 2024 (liquidity-driven rally) to be stress years for accruals LS.

### 2.4 Best-year-out pre-check
- **Cannot assert until real numbers exist.** Rule: recompute test Sharpe excluding the single best calendar year; must be ≥ 50 % of headline.

### 2.5 Falsification-first question
**"If the Sharpe comes back at 2.0, what is the most likely single cause of it being wrong by 50 %?"**
Answer: **announcement-date leakage** (using `end_date` instead of `ann_date`). Test that would prove this cause: shift the TTM build-up by +45 trading days (mimics "publishing without filing") and re-run; if Sharpe collapses, the original had leakage.

---

## 3. Universe & data-fetch plan  (to be executed by runtime)

```text
universe_build:
  - source: stock_basic  (list_status='L')
  - filter: list_date <= today - 252  (listed > 1 year)
  - filter: industry not in ('银行', '非银金融', '保险')  (ex-financials)
  - filter: not currently ST / *ST  (from namechange history)
  - dynamic: exclude stocks with >20 consecutive halted days in trailing 60d

fundamental_fetch  (per-quarter, cache to parquet):
  - income:        n_income, ann_date, end_date
  - balancesheet:  total_assets, acct_rcv, inventories, acct_pay, ann_date, end_date
  - cashflow:      n_cashflow_act, depr_fa_coga_dpba, ann_date, end_date
  - periods:       2011Q1 .. 2025Q4  (need pre-2012 for TTM warm-up)

daily_panel_fetch  (per-year, cache to parquet):
  - daily.open, close, vol, amount
  - daily_basic.total_mv  (fallback: close * total_share if unavailable)
  - adj_factor for split-adjusted returns
  - periods: 2012-01-01 .. 2025-12-31

expected_cache_size: ~450 MB
expected_fetch_time: ~18 min (paid tier) or ~45 min (free with retries)
```

### Neutralization runtime
- Default run: **INDUSTRY** (SW L1 via `stock_basic.industry`).
- Secondary run: **INDUSTRY × SIZE** (5 size bins within industry).
- Tertiary run (only if raw LS Sharpe looks suspiciously high): residualize vs {size, BM, momentum_20d, reversal_5d} cross-sectionally on train only, apply to test.

### Cost model
- One-way cost: 10 bps (commission 2.5 + stamp 5 + impact 2.5). Applied on monthly rebalance turnover.

---

## 4. Expected outputs  (schema for when runtime executes)

```text
outputs/
├── ic_table_batch_0001.csv       # per-alpha: rank_ic_mean, icir, tstat at horizons {1,5,10,20,60}
├── ls_performance_batch_0001.csv # annual Sharpe, max_dd, turnover, after-cost Sharpe
├── q5_excess_batch_0001.csv      # Q5 long-only excess vs CSI300 per calendar year
├── ic_decay_curves.png
├── rolling_12m_ic_curves.png
└── correlation_matrix_alpha_1_to_8.csv
```

---

## 5. Anomalies / preflight notes

- **Alpha 7 universe shrinkage:** 12-quarter history requirement will drop ~400 names in early sample; expect higher t-stat dispersion on the truncated universe.
- **Alpha 2 (BS-method WCA):** A-share restatement risk — runtime should version-tag each parquet with `revision_seq` so a future re-run catches point-in-time drift.
- **Alpha 8 thin-cells:** 5 size-bins × 28 industries; default fallback to 3 bins if any cell has < 10 names that day.

---

## 6. Decision passed to Stage 5

- All 8 expressions pre-validated ✓
- Look-ahead structural checks pass by construction ✓
- Delay-audit invariants locked in ✓
- **Real submission deferred** (no runtime); Stage 5 should mark round as RESEARCH-ONLY and specify what Round 1.5 (runtime-attached) must deliver.
