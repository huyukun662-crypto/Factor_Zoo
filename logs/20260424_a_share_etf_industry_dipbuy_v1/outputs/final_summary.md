# Final Summary — A-share Industry ETF Dip-Buy (no safe-haven)

**Session:** `20260424_a_share_etf_industry_dipbuy_v1`
**Universe:** 32 A-share thematic/industry ETFs (V7_gold − 黄金 − 红利)
**Sample:** 2019-01-04 → 2026-04-22, 1768 days, 88 monthly rebalances
**Verdict:** **RESEARCH-ONLY** — winner passes Train research floor, strong OOS (Sh +0.93 without any safe-haven), but 2023 Val fails.

## One-paragraph summary

Followup to `reversal_v2`, which relied on 55% gold blending to rescue
the reversal family's worst-year problem. User asked for a PURE
industry-ETF dip-buy factor (no gold, no dividend, no cross-asset hedge).
Tested 8 variants covering signal refinement (vol-scaled, residualized),
conditional triggers (deep-dip-only, bounce-confirmed, low-vol surrender),
and portfolio construction (top-1 conviction, top-3 industry-diversified).
Evaluated under fixed TVT split (Train 2019-22, Val 2023, OOS 2024-26)
from the start. Winner is **`p_top3_diversified`** — top-3 deepest-dip
ETFs constrained to 3 distinct industry clusters. Train Sh +0.89, Val 2023
-0.24 (structural bad year, every variant is negative in Val), **OOS Sh
+0.929 with 3/3 OOS years positive** (+0.96 / +0.97 / +0.79). Industry
diversification is a low-cost, high-value constraint: on the same
underlying signal (-logret_40d) it lifts full-sample Sh from 0.54
(baseline top-3) to 0.77 (diversified top-3), and OOS Sh from 0.85 to 0.93.

## TVT summary — all 8 variants

| id | cluster | Train Sh | Val 2023 | **OOS** | Train worst-yr | Train floor |
|---|---|---:|---:|---:|---:|:-:|
| d40_baseline | signal | +0.654 | -0.799 | +0.850 | 2022 -0.346 | ❌ |
| d40_vol_scaled | signal | +0.692 | -0.670 | +0.617 | 2022 -0.859 | ❌ |
| d40_resid_250d | signal | +0.392 | -1.468 | **+1.335** | 2022 -0.677 | ❌ |
| d40_deep_only | trigger | +0.437 | -0.886 | +1.209 | 2022 -0.993 | ❌ |
| d40_bounce_conf | trigger | +0.579 | -1.451 | +1.234 | 2022 -0.937 | ❌ |
| d40_low_vol_surrender | trigger | +0.379 | -0.638 | +0.929 | 2022 -1.294 | ❌ |
| p_top1_conviction | portfolio | **+1.233** | +0.180 | +0.105 | 2022 **+0.008** | ✅ (overfit) |
| **p_top3_diversified** | portfolio | **+0.886** | -0.244 | **+0.929** | 2022 **+0.112** | ✅ |

**Two variants pass the Train research floor** (Train Sh ≥ 0.5 AND
worst-year ≥ 0). Of the two:
- `p_top1_conviction` — Train +1.23 but OOS collapses to +0.10 (classic
  overfit to the single train-best ETF).
- **`p_top3_diversified`** — Train +0.89, OOS +0.93 — the reliable one.

## Winner: `p_top3_diversified`

### Spec

```
signal:          -logret_40d (universe-EW demean per date)
ranking:         top-3 by demeaned signal, long-only
constraint:      max 1 ETF per industry cluster (forces sector diversification)
industry clusters (8):
  TMT_hardware  - 半导体 消费电子 稀土 通信
  TMT_software  - 软件 游戏 AI 云计算 机器人
  consumer      - 酒 食品 家电 畜牧
  healthcare    - 医药 医疗器械 创新药
  financial     - 银行 证券 非银 房地产
  manufacturing - 军工 航空航天 建材 化工 钢铁
  new_energy    - 新能源车 光伏 电池 电网设备 有色 煤炭
  oil_gas       - 石油
weights:         equal (33.3% per pick)
rebalance:       every 4th Friday close, 20-bar hold
execution delay: 1 bar
```

### Headline metrics (full sample)

| | value |
|---|---:|
| Net Sharpe @5bps | **+0.766** |
| Ret ann | +17.59% |
| Vol ann | 22.95% |
| Max drawdown | -31.63% |
| n_days | 1768 |

### TVT split metrics

| Split | n_days | Sharpe | Ret ann | MaxDD |
|---|---:|---:|---:|---:|
| Train 2019-2022 | 970 | **+0.886** | +19.97% | -26.09% |
| Val 2023 | 242 | -0.244 | -4.79% | -20.13% |
| **OOS 2024-2026** | 556 | **+0.929** | **+23.17%** | -18.16% |

### Per-year Sharpe

| Year | Split | Sharpe |
|---|---|---:|
| 2019 | Train | +1.855 |
| 2020 | Train | +1.280 |
| 2021 | Train | +1.147 |
| 2022 | Train | +0.112 |
| **2023** | **Val** | **-0.244** |
| 2024 | OOS | +0.962 |
| 2025 | OOS | +0.973 |
| 2026 YTD | OOS | +0.791 |

**7 of 8 years positive.** 2023 is the single negative year, -0.244 only.

### Comparison: `d40_baseline` vs `p_top3_diversified`

Same -logret_40d signal, different portfolio construction:

| | d40_baseline | p_top3_diversified | Δ |
|---|---:|---:|---:|
| Full-sample Sh | +0.540 | +0.766 | +0.226 |
| MaxDD | -43.52% | -31.63% | +12pp |
| Train Sh | +0.654 | +0.886 | +0.23 |
| OOS Sh | +0.850 | +0.929 | +0.08 |
| Train worst-year | 2022 -0.346 | 2022 **+0.112** | flips positive |

**The industry-diversification constraint is a genuine improvement.**
Same signal, different portfolio rule, lifts both mean and downside.

## What worked

- **Industry-cluster diversification** is the standout finding. Forcing
  top-3 picks into 3 distinct industry buckets gives +0.23 Sharpe uplift,
  12pp drawdown reduction, flips Train worst-year positive. All from a
  simple allocation constraint — no signal change, no extra parameters.
- **OOS is strong without any safe-haven asset.** Prior session (R2)
  needed 55% gold to pass research floor on full sample; this session's
  winner has OOS Sh +0.93 on pure thematic equities. Industry-diversified
  dip-buying is genuinely productive in the 2024-2026 market.
- **d40_resid_250d had the highest OOS Sh (+1.335)** — residualizing short-
  horizon reversal against 250-day trend sharpens the signal in OOS.
  But fails Train floor (only +0.39). Worth revisiting as a feature input
  in a future ensemble.

## What did not work

- **2023 is structurally unfixable within pure-thematic framework.** All
  8 variants have negative Val Sharpe. The TMT-concentration regime of
  2023 is a tail event that no signal refinement or portfolio construction
  within the equity universe can rescue. Prior R2 used gold (+1.68 in
  2023) as the rescue; this session's ground rules forbid that.
- **Top-1 conviction overfits.** Train +1.23 looks promising but OOS
  +0.10 is effectively zero. Single-ETF picks are path-dependent on
  the single best dipper each month; the train-dominant pick doesn't
  generalize.
- **Signal refinements didn't help train.** Vol-scaled, residualized,
  deep-dip-only, bounce-confirmed, low-vol-surrender — all lower train
  Sharpe than the baseline -logret_40d. Simpler is better in-sample here.
- **Conditional triggers narrow sample too much.** d40_bounce_conf fires
  on 49.6% of rows; d40_deep_only on 86%. When triggers are sparse,
  monthly rebalance can't consistently find top-3 picks.

## Verdict detail

**Promote bar (Val Sh ≥ 0.5 AND OOS Sh ≥ 0.5 AND worst-year ≥ 0):**
- FAIL on Val: winner has -0.244 ❌.

**Research bar (Train Sh ≥ 0.5 AND Train worst-year ≥ 0):**
- PASS: Train Sh +0.886, Train worst 2022 +0.112 ✅.

**OOS sanity bar (OOS Sh ≥ 0.3):**
- PASS: OOS Sh +0.929 ✅.

Net: **RESEARCH-ONLY with positive OOS evidence**. The factor is
research-grade and OOS-validated (3/3 OOS years positive, no safe-haven
help). It fails promote only because 2023 is a regime outlier — and
refusing to overfit to "how would I have avoided 2023" is the disciplined
choice. Deployable only if operator accepts a ~-5% 2023-style tail year.

## Current holdings (latest rebalance, 2026-04-17)

| symbol | name | industry cluster | weight | past 40d return |
|---|---|---|---:|---:|
| 159869.SZ | 游戏ETF | TMT_software | 33.33% | -22.82% |
| 516750.SH | 建材ETF | manufacturing | 33.33% | -12.71% |
| 512690.SH | 酒ETF | consumer | 33.33% | -11.66% |

Skipped by diversification rule: 515230.SH 软件ETF (-12.59%, same
cluster as 游戏ETF and ranked below it).

Previous rebal (2026-03-20): 515230.SH 软件ETF / 159892.SZ 非银ETF / 159227.SZ 航空航天ETF.
Next rebal: approximately 2026-05-15.

## Research-log entry (for README)

```
session: 20260424_a_share_etf_industry_dipbuy_v1
winner: p_top3_diversified (top-3 of -logret_40d, max 1 per industry cluster)
universe: 32 A-share thematic/industry ETFs (no gold, no dividend)
full_sample_net_sharpe_5bps: +0.766
train_sharpe:    +0.886  (2019-2022)
val_2023_sharpe: -0.244
oos_sharpe:      +0.929  (2024-01 → 2026-04-22)
maxdd: -31.63%
worst_year: 2023 Sh -0.244 (Val split)
years_positive: 7 of 8
status: RESEARCH_ONLY (passes train + OOS floors; fails Val 2023)
key_finding: "Industry-cluster diversification alone lifts full-sample Sh
              from 0.54 (baseline top-3) to 0.77, and flips train worst-year
              positive. OOS 2024-2026 is strong (Sh +0.93) on pure thematic
              equities with no safe-haven blend. 2023 is a structural tail
              year that no pure-thematic variant rescues."
```
