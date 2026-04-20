# Alpha Ranking — Batch 0001

**Session:** 20260420_fundamental_accruals_alpha
**Agent:** 5 Evaluator & Recorder
**Round decision:** `RESEARCH-ONLY`  (no live runtime → no PROMOTE possible; mandatory 5-audit package cannot close)

---

## 1. Why this is RESEARCH-ONLY, not PROMOTE

Per SKILL.md *"If any of the five above fails, the decision is RESEARCH-ONLY, not PROMOTE"*. In this round:

| Audit | Status |
|-------|--------|
| Execution-delay audit | **specified, not executed** — no numeric future-perturbation test |
| Look-ahead audit | structural pass by construction; **numeric randomization test not executed** |
| Worst-year floor (Sharpe ≥ 0.5) | **cannot assert** — no backtest run |
| Best-year-out check (≥ 50 % of headline) | **cannot assert** — no backtest run |
| Falsification-first check | question defined, test **not executed** |

Three of five audits are numeric and require a runtime. Therefore, the only honest disposition is RESEARCH-ONLY.

## 2. A-priori ranking  (expected, to be validated in Round 1.5)

Ranking is *expected ordering* based on (a) literature, (b) A-share adaptation lessons in SKILL.md, and (c) neutralization theory. Not evidence-based until real numbers exist.

| rank | idx | alpha | why expected high/low |
|------|-----|-------|-----------------------|
| 1 | 8 | sloan_ind_size_double | Industry + size neutralization consistently top in A-share fundamentals |
| 2 | 3 | sloan_ind_neutral | Single-axis neutral; captures 60-70 % of the gain from double-neutralization |
| 3 | 1 | sloan_cfs (baseline) | The reference; healthier than most variants but carries size/industry bias |
| 4 | 4 | cfo_ni_ratio | Equivalent economics, cleaner narrative; potential IC parity with #1 |
| 5 | 6 | acc_vol_weighted | Downweighting noisy firms should help, penalized by universe shrinkage |
| 6 | 5 | dacc_yoy | Change signal — lower t-stat but lower correlation (ensemble utility later) |
| 7 | 2 | bs_wca | A-share restatement noise hurts BS-method |
| 8 | 7 | acc_persist_weighted | Non-linear, interpretability cost, universe shrinkage — needs to beat #1 by >5% |

## 3. Correlation hypothesis  (to verify numerically)

Expected pairwise rank-IC correlations among the 8 alphas:

```
       1    2    3    4    5    6    7    8
1   1.00 0.60 0.85 0.80 0.25 0.75 0.70 0.80
2        1.00 0.55 0.50 0.15 0.45 0.45 0.50
3             1.00 0.70 0.30 0.70 0.65 0.90
4                  1.00 0.20 0.65 0.60 0.65
5                       1.00 0.25 0.30 0.25
6                            1.00 0.65 0.65
7                                 1.00 0.60
8                                      1.00
```

If any off-diagonal pair drops below 0.3, investigate — it may mean the "one dominant mechanism" constraint was weaker than claimed.

## 4. What Round 1.5 (runtime-attached) must deliver

1. IC table at horizons {1, 5, 10, 20, 60} for all 8 alphas, with **IC(delay=0) > IC(delay=1)** verified.
2. Future-bar randomization test: alpha_{1..8}(T) before randomization == alpha_{1..8}(T) after randomization, bitwise on all T ≤ last-train-date.
3. Publication-lag leakage test: rerun alpha_01 using `end_date`-gated TTM (no ann_date lag) and report the gap vs the default; if the leaked version's Sharpe > 150 % of ann_date version, the mechanism is brittle.
4. Annual Sharpe table (train / validate / test) per alpha + cost curve (0 / 5 / 10 / 20 bps).
5. Q5 long-only excess-vs-CSI300 annualized table.
6. Worst-year-floor check (target ≥ 0.5) and best-year-out check (≥ 50 % of headline).

## 5. Round 1 → Round 2 branch rules

- If top alpha (expected: idx 8) passes all 5 audits in Round 1.5 → **PROMOTE to paper trading**, begin out-of-sample live tracking.
- If top alpha fails only worst-year floor → Round 2 adds size-neutralization × bear-year regime filter; same mechanism, not a new one.
- If residual-vs-known-factors Sharpe drops > 50 % → label as "accruals-exposure vehicle" and deprioritize; move to Mechanism B (SUE / PEAD) in next session.
- If LS Sharpe < 0.5 gross but Q5 long-only excess > 4 % → deploy Q5 long-only as index enhancement; LS version is not deployable in A-share short-constrained setting (SKILL.md A-share lesson).

## 6. Continue / refine / stop

**Decision:** `refine` (Round 1.5 required to attach runtime and execute numeric audits). No `stop` because the mechanism is well-supported by literature and the expression batch passes structural validation.
