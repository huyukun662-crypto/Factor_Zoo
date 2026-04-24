# Objective — A-share Industry ETF Dip-Buy (no safe-haven)

## User request

> 试试制作行业 ETF 抄底,不要黄金等避险资产。

Follow-up to `20260424_a_share_etf_reversal_v2` whose R2 winner was a
55% gold + 45% reversal-ensemble blend. OOS validation showed the gold
leg did 100% of the OOS work; the reversal factor itself had zero OOS
marginal Sharpe. Task is now to construct a PURE industry-ETF dip-buy
factor without any defensive/safe-haven allocation (no gold, no dividend
ETF), and honestly evaluate it under train/val/OOS split from the start.

## Universe

32 A-share thematic/industry ETFs:
  = 34 V7_gold universe
    − 159934.SZ 黄金ETF (safe-haven)
    − 515080.SH 红利ETF (defensive equity)

## TVT split (set before running any backtest)

| Split | Range | n_days approx |
|---|---|---:|
| Train | 2019-01-04 → 2022-12-31 | 970 |
| Val   | 2023-01-01 → 2023-12-31 | 242 |
| OOS   | 2024-01-01 → 2026-04-22 | 556 |

The split anchors are fixed. Hyperparameter selection must be done on
train only; val is used for model comparison; OOS is never used for
any selection and is reported once at the end.

## Success bar

| bar | threshold |
|---|---|
| G1 non-degeneracy | signal nonzero fraction ≥ 0.01 |
| G3 IC at own horizon | ≥ 0.005, |t| ≥ 2.0 |
| G4 Net Sh @5bps train | ≥ 0.5 |
| G4 worst-year train | ≥ 0.0 |
| OOS sanity | OOS Net Sh ≥ 0.3 (at least positive, less strict than train) |
| Promote floor | Val + OOS each Sh ≥ 0.5 AND worst-year ≥ 0 on full sample |

Research-only if any of: G4 train pass but OOS Sh < 0.3, OR val regime
clearly different from train.

## Design principle

R1 and R2 both converged on the same mechanism insight: **the base
reversal signal `-logret_40d` is real in 2019-2022, broke in 2023, and
has not recovered in 2024-2026**. Any new variant must either:
  (a) show improved stability across the three sub-samples, OR
  (b) sharply trade off worse headline for better worst-year AND OOS.

## Non-goals

- No LS strategy (prior R1 showed short leg is -0.8 to -1.0 Sh structural drag).
- No cross-asset blending (gold/bond/cash).
- No industry neutralization (universe IS the industry grid).
- No ensemble with horizons outside [40, 80] — prior horizon scan ruled them out.

## Audits on top candidate

Same five mandatory audits as prior sessions, plus one new:

1. Execution-delay double path
2. Look-ahead within-date randomization
3. Best-year-out ratio ≥ 0.5
4. Falsification probe (`+logret_20d` near zero at k=40)
5. Worst-year Sharpe
6. **NEW: Train-only hyperparameter re-selection** (if any hyperparameter is tuned, re-run the tuning on train alone and report val + OOS under that pick)
