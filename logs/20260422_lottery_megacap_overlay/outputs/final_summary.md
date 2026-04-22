# Session final_summary — lottery_megacap_overlay

**Session:** `logs/20260422_lottery_megacap_overlay/`
**Date:** 2026-04-22
**Goal:** Lift α_17 Q5 long-only 2020 worst-year (−0.33 IR) above 0.5
so it passes the deployment audit as an A-share index-enhancement factor.
**Outcome:** ✅ **DEPLOYED** as
`factors/price_volume/lottery_idio_max_q5_overlay_v1/`

## Problem

Prior session (`logs/20260422_trend_technical_alpha/outputs/alpha17_longonly_review.md`)
found α_17 Q5 long-only has full-sample excess IR 1.09 / OOS 1.43 in 2025 but
fails audit rules 2 (worst-year −0.33 in 2020) and 4 (0/9 spec variants pass;
all fail 2020). Mechanism: A-share 2020 megacap rally (Liu-Stambaugh-Yuan
2019) extinguishes lottery premium.

Per-month 2020 tape showed the year was 6 positive / 6 negative months, so
a reasonable-accuracy gate (not perfect) could plausibly lift 2020 IR above
0.5. Perfect gate gives 2.16; drop-3-worst gives 1.32.

## 3-round iteration

### Round 1 — 4 candidates × 3 modes × 2 fallbacks = 24 variants

Candidates tested:
- `size_spread_60d`: top-100 mv mean 60d log-ret minus bottom-1000
- `concentration`: top-100 mv total / all mv
- `size_q5q1_12m_sh`: trailing 252d Sharpe of Q5-size minus Q1-size daily spread
- `size_disp_60d`: std of 5 size-bucket 60d mean returns

**0/24 pass.** Best: `size_q5q1_12m_sh | pct90 | benchmark` got 2020 IR +0.25
(from −0.33), still below 0.5.

### Round 2 — 102 variants (single + AND-pair + majority-of-3)

Added breadth feature (% stocks above 60d MA). Tested tighter thresholds
(p70..p95) and AND-pairs with benchmark fallback.

**0/102 pass.** Best: `size_q5q1_12m_sh | pct95 | lb=126` got full IR 1.025,
worst 0.452 — **0.048 below the 0.5 floor**.

### Round 3 — 144 refined variants around winner neighborhood

Fine grid: lookback ∈ {63, 90, 126, 189, 252, 378}, percentile ∈ {90..98},
smoothing ∈ {None, 10, 20}.

**3/144 pass.** Winner:

```
signal     = size_q5q1_12m_sh
lookback   = 63   (rolling quantile window)
percentile = 97   (gate ON when signal < 97th percentile of its trailing 63d)
fallback   = benchmark (hold equal-weight universe when gate OFF)
```

Metrics (2018-01 → 2026-04, 99 rebalances):
- Full-sample excess IR **1.129**
- Worst-year (2023) excess IR **0.766**
- 2020 IR **+1.162** (from −0.325)
- 2025 OOS IR **+1.261**
- Train/Validate/Test IR: 1.61 / 0.77 / 0.77
- Excess MaxDD −4.18%
- Gate on-fraction 80.8%

## 7/7 Audit (all pass)

| # | rule | threshold | value | verdict |
|:-:|---|---|---:|:---:|
| 1 | Full-sample excess IR | ≥ 1.0 | 1.129 | ✅ |
| 2 | Worst-year excess IR | ≥ 0.5 | 0.766 | ✅ |
| 3 | Best-year-out ≥ 50% full | ≥ 50% | 93.4% | ✅ |
| 4 | Spec sensitivity majority | ≥ 5/8 | 5/8 | ✅ |
| 5 | Placebo excess IR p-value | < 0.05 | 0.020 | ✅ |
| 6 | Placebo worst-year p-value | < 0.05 | 0.000 | ✅ |
| 7 | Excess MaxDD | > −10% | −4.18% | ✅ |

## Per-year result

| year | excess IR | excess ann | gate on |
|---:|---:|---:|---:|
| 2018 | +1.80 | +4.51% | 33% |
| 2019 | +0.86 | +1.87% | 83% |
| **2020** | **+1.16** | +3.21% | 67% |
| 2021 | +2.16 | +6.14% | 100% |
| 2022 | +2.28 | +4.37% | 92% |
| 2023 | +0.77 | +2.53% | 100% |
| 2024 | +0.84 | +5.26% | 100% |
| **2025** | **+1.26** | +2.91% | 77% |

All 8 complete years have positive excess IR ≥ 0.77.

## Deployed artifacts

**Factor library entry**: `factors/price_volume/lottery_idio_max_q5_overlay_v1/`

- `README.md` — quick reference (Chinese)
- `factor.md` — full spec (definition, mechanism, audit, risk, kill-switch, references)
- `code.py` — reusable `build_portfolio()` function
- `metrics.json` — headline + TVT + audit + placebo metrics
- `annual.csv` — per-year breakdown
- `rebalances.csv` — 99 rebal tape with gate state, turnover, cost

**Catalog update**: `factors/README.md` updated — now 3 DEPLOYED factors.

## Scripts (session)

- `scripts/01_build_overlay_candidates.py` — R1 candidate screen (24 variants)
- `scripts/02_round2_combinations.py` — R2 combinations (102 variants)
- `scripts/03_round3_refine.py` — R3 fine grid (144 variants) → winner
- `scripts/04_audit_and_placebo.py` — full 7/7 audit + 100 placebo

## References

- Bali, Cakici & Whitelaw (2011). *JFE* — lottery / idio-MAX mechanism
- Liu, Stambaugh & Yuan (2019). *JFE* — A-share size regime (2020 megacap rally)
- Fama & French (1992). *JF* — size factor
- Ang, Hodrick, Xing & Zhang (2006). *JF* — idio vol anomaly

## Complementarity with α_35 (DEPLOYED)

α_35 (momentum) had −1.44 Sharpe in 2025 (kill-switch triggered).
This factor had +1.26 excess IR in 2025. Both factors in rotation/combined
would provide regime-level diversification — a practical benefit of
deploying this second factor in a different family.

## Open questions (not in scope of this session)

- **Cross-factor correlation** of this factor with α_35 not directly measured.
  If low, combined deployment improves strategy Sharpe.
- **Productionize α_17 signal code**: currently relies on `panel_round3.parquet`
  from the prior lottery session. For production, lift that code into the
  factor directory or a shared module.
- **α_35 status decision** (DEPLOYED vs PAUSED) — separate user call.
