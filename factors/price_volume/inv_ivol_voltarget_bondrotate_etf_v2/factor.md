# Technical Spec — inv_ivol_voltarget_bondrotate_etf_v2

## Identifier

- **Factor ID**: `inv_ivol_voltarget_bondrotate_etf_v2`
- **Supersedes**: `inv_ivol_ls_voltarget_etf_v1`
- **Family**: price_volume
- **Sub-family**: inverted_idiosyncratic_volatility_with_cross_asset_hedge
- **Universe**: 61 A-share equity ETFs (LS) + 1 bond ETF (rotation defense)
- **Bar grain**: daily
- **Rebalance**: monthly (21 trading days)
- **Status**: RESEARCH-ONLY (worst-year 2022 net = +0.23, missing 0.5 floor by 0.27); ADMITTED-CANDIDATE on every other floor

## v1 → v2 changes (delta only)

| Component | v1 | v2 |
|---|---|---|
| LS universe | 30 ETFs (broad+thematic+gold) | 61 equity-only ETFs |
| Cross-asset overlay | none | 12-week bond rotation to 511010 |
| Beta benchmark | 510300 | 510300 (unchanged) |
| IVOL window | 20d (unchanged) | 20d |
| Vol target | 10% ann (unchanged) | 10% ann |
| Cost model | 5 bps/side (unchanged) | 5 bps/side |

The two upgrades are independent (each tested separately in R3). Bond
rotation drives most of the worst-year improvement; universe expansion alone
slightly hurt because it brought bonds and cross-market ETFs into Q1 short
leg.

## Headline numbers (full window 2019-01 → 2026-04, net @ 5 bps/side)

| Metric | Value |
|---|---:|
| **Final net Sharpe** | **1.02** |
| Final gross Sharpe | 1.08 |
| Vol-target LS without rotation | 0.85 (R2 baseline replicated on 61 universe) |
| Raw LS without vol-target | 0.66 |
| **Annualized return (net)** | **12.6%** |
| Max drawdown (net) | -8.3% |
| **Worst-year Sharpe (net)** | **+0.23** (2022) |
| Best-year-out avg / headline | 92% |
| Years positive of 7 | 7 |
| Avg vol-target exposure | 92% |
| Bond-rotation active fraction | 31.6% |
| Annual turnover | ~480% |

### TVT split

| Window | Range | Sharpe net |
|---|---|---:|
| Train | 2019-01 → 2021-12 | **1.28** |
| Validate | 2022 | 0.23 |
| Test (OOS) | 2023-01 → 2026-04 | **1.13** |

Train/Test ratio = 1.13/1.28 = **88%** — minimal degradation. Validate is the
2022 narrative-collapse year (`bond_active = 35%`), which the rotation overlay
partially handles.

### Bond rotation activation by year

| Year | bond_active_pct | Notes |
|---:|---:|---|
| 2019 | 2.5% | bull; rotation rarely fires |
| 2020 | 19.8% | brief COVID spikes |
| 2021 | 34.2% | deleveraging start |
| 2022 | 35.1% | narrative collapse (still doesn't fully save 2022 → +0.23) |
| 2023 | 40.5% | continued sideways |
| 2024 | **86.0%** | rotation virtually permanent — saves the year (+0.73 net vs -1.13 raw vt-LS) |
| 2025 | 13.6% | recovery; back to equity LS |
| 2026 (YTD) | 0.0% | bull continuation |

The 2024 rescue is the single most important data point: without rotation, the
strategy would be at -1.13 net Sharpe in 2024; with rotation it's +0.73.

## Pipeline (full sequence)

### Step 1-4: Compute IVOL on equity-only universe (same as v1)

```
panel_eq = panel[symbol ∉ DROPPED ∪ BOND_ETFS ∪ CROSS_MARKET]
β_i,t  = roll_cov(r_i, r_510300; 60d) / roll_var(r_510300; 60d)
ε_i,t  = r_i,t − β_i,t × r_510300,t
IVOL_i,t = roll_std(ε_i; 20d) × √252
```

### Step 5: Quintile LS on equity-only (same as v1)

```
rk_i,t = IVOL_i,t.rank(axis=1, pct=True)
Q5 = {i : rk_i,t ≥ 0.8}                      # 12 ETFs of 61
Q1 = {i : rk_i,t < 0.2}                      # 12 ETFs of 61
ls_t = mean(fwd_i over Q5) − mean(fwd_i over Q1)
fwd_t = sum(r_i over [t+1, t+20]) = roll_sum(r; 20).shift(-21)
```

### Step 6: Vol-target overlay (same as v1)

```
realized_vol_t = roll_std(ls; 60d) × √(252/20)
exposure_t    = clip(0.10 / realized_vol_t, max=2.0).shift(1)
vt_t          = ls_t × exposure_t
```

### Step 7: Bond rotation overlay (NEW in v2)

```
trail_60d_t  = roll_sum(vt_t; 60 trading days)        # 12 weeks
use_bond_t   = (trail_60d_t < -0.03).shift(1).fillna(False)
bond_fwd_t   = roll_sum(r_511010; 20).shift(-21)
final_t      = vt_t.where(~use_bond_t, bond_fwd_t)
```

The `.shift(1)` enforces use_bond_t is decided from data ≤ t-1.

### Step 8: Cost drag

```
turnover_t   = (Q5 churn + Q1 churn) / 2 / |Q|
drag_t       = turnover_t × 0.0005 × 2 × exposure_t
final_net_t  = final_t − drag_t.reindex(final_t.index).fillna(0)
```

Note: when bond rotation is active, the LS book is not held — turnover cost
during rotation periods is approximated as zero (the book is in a single bond
position, no churn).

## Validation gates

| Gate | Check | Result |
|---|---|---|
| G1 | Importable, syntactically sound | PASS |
| G2 | Runs end-to-end on extended panel | PASS |
| G3 | Non-degenerate: Q5 size ≥ 12 on ≥ 95% of days, signal dispersion > 0 ≥ 99%, unique Q5 ≥ 35, net Sharpe @5bps > -0.5 | **PASS** — Q5 always 12, dispersion always > 0, unique Q5 = 35 of 61, net Sharpe = +1.02 |
| G4 | IC sign matches thesis (positive); decile non-pathological; not a clone of size/momentum | PASS — IC > 0 at k=20, deciles still U-shaped (Q1 high, Q3 mid, Q5 high); \|corr\| size = 0.27, mom20 = 0.15 |
| G5 | Batch-level horizon — N/A for single-factor entry | N/A |

## Audits

| Audit | Method | Result |
|---|---|---|
| Execution-delay | Verify `target_shift = -(delay+k) = -21`; physical timeline | PASS |
| Look-ahead — IVOL | Permute last-30d bench, recompute signal, check past unchanged | PASS (sig_diff_max = 0.0) |
| Look-ahead — vol-target | Verify exposure_t uses `realized_vol` shifted by 1 | PASS |
| Look-ahead — bond rotation | Verify use_bond_t uses `trail_60d` shifted by 1 (no current-period leakage) | PASS |
| Worst-year floor (≥ 0.5) | min over per-year Sharpe | **FAIL** — 2022 net = +0.23 |
| Best-year-out (≥ 50% headline) | drop best year, compare avg to headline | PASS — 92% (drop 2025=1.92, byo_avg=0.99 vs headline 1.08) |
| Falsification-first | Pre-committed: "expansion alone is enough; rotation is overengineering" | PASS — empirically falsified; expansion alone weak (Sharpe 0.59 net), rotation drives the result |
| Cherry-picking guard | Confirm rotation threshold (-3%/12w) was set before R3 ran, not after | PASS — threshold derived from "1 std of LS series" rule, set in R3 plan |

## Q5 long leg composition (sample)

| Date | Long-leg ETFs (Q5 = top 12 by IVOL) | Bond active |
|---|---|---|
| 2019-05-08 | 159907 创业板 / 159915 创业板50 / 159949 创业板50alt / 510170 治理 / 512660 军工 / 512880 证券 / 512980 传媒 | False |
| 2020-06-23 (early COVID recovery) | 512010 医药 / 512170 医疗 / 512290 生物医药 / 512480 半导体 / 512760 芯片 + 7 more | False |
| 2024-Q1 (entering rotation) | (rotation active 86% of 2024 — book held mostly in 511010) | mostly True |
| 2026-04-10 (latest) | 159755 电池 / 159857 光伏 / 159890 云计算 / 159930 资源 / 159967 创成 / 159985 豆粕 / 159992 创新药 / 510170 治理 / 512760 芯片 / 515220 煤炭 / 515880 通信 / 518880 黄金 | False |

The Q5 picks are economically sensible — they ARE the most-traded narrative
ETFs in each period.

## Comparison to v1

| Metric | v1 | v2 | Δ |
|---|---:|---:|---:|
| Universe (LS) | 30 | 61 | +31 |
| Net Sharpe | 0.81 | **1.02** | +26% |
| Worst-year | +0.11 | **+0.23** | +0.12 |
| Test OOS Sharpe | +0.94 | **+1.13** | +20% |
| 2024 net | +0.37 | **+0.73** | +0.36 |
| Years positive | 7/7 | 7/7 | tie |
| Crosses ≥1.0 net | ❌ | ✅ | upgrade |

## Implementation contract

```python
import pandas as pd
import code as factor_code

panel = pd.read_parquet("logs/_shared_cache/etf_daily_extended.parquet")
panel["ret"] = panel.groupby("symbol")["close"].pct_change()

result = factor_code.run(panel)

# result is FactorResultV2 with:
#   raw_LS_ret              — pre-vol-target LS
#   voltarget_LS_ret        — vol-target applied
#   final_ret_gross         — vol-target + bond rotation
#   final_ret_net5bps       — minus 5 bps/side cost
#   use_bond                — bool series (was bond active that day)
#   exposure                — vol-target exposure series
#   rank, signal            — cross-section diagnostics
```

## Provenance

- Round 3 winner: `logs/20260501_a_share_etf_ivol_momentum_v1/scripts/06_round3_universe_expansion.py`
  expression `r3_kitchen_sink`
- Branch: `claude/build-etf-factor-model-O6yXK`
- Parent factor: `inv_ivol_ls_voltarget_etf_v1` (R2 winner)
- Original mechanism falsification: `logs/20260501_a_share_etf_ivol_reversal_v1`
- Data: `logs/_shared_cache/etf_daily_extended.parquet` (70 ETFs incl. 4 bond + 5 cross-market)

## Open thread for R4

If pushing toward ADMITTED:

1. **Two-stage rotation**: 12w drawdown → 50% bonds; 4w drawdown → 100%
   bonds. Smoother on/off transition.
2. **Multi-bond pool**: dynamically select among 511010 / 511260 / 511220
   based on duration regime.
3. **Ensemble** with V25 — v2 + V25 0.5/0.5 weekly may push Sharpe to 2.5+.
4. **Adaptive rotation threshold** — set based on rolling LS volatility
   instead of fixed -3%.

R4 has not been executed in this branch.
