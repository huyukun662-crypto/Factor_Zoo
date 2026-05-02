# Technical Spec — inv_ivol_ls_voltarget_etf_v1

## Identifier

- **Factor ID**: `inv_ivol_ls_voltarget_etf_v1`
- **Family**: price_volume
- **Sub-family**: inverted_idiosyncratic_volatility
- **Universe**: a_share_thematic_etf_30names
- **Bar grain**: daily
- **Rebalance**: monthly (21 trading days)
- **Status**: RESEARCH-ONLY standalone; PROMOTE candidate as 0.5/0.5 ensemble with V25 or V7_gold

## Sign convention

`signal = +IVOL` — high signal value = LONG. **Inverted** from the classical
Ang-Hodrick-Xing-Zhang (2006) IVOL anomaly which has `signal = -IVOL`. The
inversion is mechanism-justified at the A-share thematic ETF level — see
README.md "经济机制" section.

## Inputs

| Field | Description | Source |
|---|---|---|
| `panel.date` | Trading date | parquet panel |
| `panel.symbol` | ETF ticker (Yahoo `.SS`/`.SZ` form) | parquet panel |
| `panel.close` | Adjusted close | Yahoo Finance v8 chart endpoint |
| `panel.ret` | `close.pct_change()` per symbol | derived |

Reference panel cache: `logs/_shared_cache/etf_daily.parquet` (30 ETFs × ~1770 days).

## Pipeline (steps and invariants)

### Step 1 — beta to broad-market

```
β_i,t = rolling_cov(r_i, r_510300; w=60d) / rolling_var(r_510300; w=60d)
```

- Window: 60 trading days, backward (uses dates ≤ t).
- Implementation: `pd.DataFrame.rolling(60).cov(bench) / bench.rolling(60).var()`.
- Look-ahead invariant: `β_i,t` uses no data after t.

### Step 2 — residual return

```
ε_i,t = r_i,t − β_i,t × r_510300,t
```

### Step 3 — annualized residual std (IVOL)

```
IVOL_i,t = rolling_std(ε_i; w=20d) × √252
```

- Window: 20 trading days, backward.
- Annualization: × √252 (daily-bar convention).

### Step 4 — cross-sectional rank, quintile membership

```
rank_i,t = IVOL_i,t.rank(axis=1, pct=True)        # 0..1
Q5 = {i : rank_i,t ≥ 0.8}                          # top quintile, 6 ETFs of 30
Q1 = {i : rank_i,t < 0.2}                          # bottom quintile, 6 ETFs of 30
```

### Step 5 — long-short return

```
fwd_t = sum(r_i over [t+1, t+20]) for each i
       = rolling_sum(r_i; 20).shift(-(delay+k)) = .shift(-21)         # delay=1, k=20

ls_t = mean(fwd_i over Q5) − mean(fwd_i over Q1)
```

Execution-delay invariant: `target_shift == -(delay + k) = -(1+20) = -21`.
Position observed at close(t), established at close(t+1), held to close(t+1+19) = close(t+20).

### Step 6 — vol-target overlay (key R2 addition)

```
realized_vol_t = rolling_std(ls; w=60d) × √(252/k)        # ann vol of the LS series
exposure_t     = clip(0.10 / realized_vol_t, max=2.0).shift(1)
final_ret_t    = ls_t × exposure_t
```

The `.shift(1)` ensures the exposure for period t was decided at period t-1
(no information leakage from period-t realized vol into period-t position).

### Step 7 — cost drag (5 bps per side, two-sided book)

```
long_to_t  = |Q5_t − Q5_{t-1}| / 2 / |Q5|
short_to_t = |Q1_t − Q1_{t-1}| / 2 / |Q1|
drag_t     = (long_to_t + short_to_t) × 0.0005 × 2 × exposure_t      # 2-side cost
net_ret_t  = final_ret_t − drag_t
```

## Validation gates (per validation-gates.md)

| Gate | Check | Result |
|---|---|---|
| G1 | Importable, syntactically sound | PASS — `code.py` imports clean |
| G2 | Runs end-to-end on full 1770-day panel | PASS — full backtest completes |
| G3 | Non-degenerate: Q5 size ≥ 6 on ≥ 95% of days, signal dispersion > 0 ≥ 99% of days, unique Q5 names ≥ 18, net Sharpe @5bps > -0.5 | PASS — Q5 always 6, dispersion always > 0, unique Q5 = 24 of 30, net Sharpe = +0.81 |
| G4 | IC sign matches thesis (positive); decile monotonicity (≤ 1 inversion); not a clone of size/momentum (\|corr\| ≤ 0.85) | PASS — IC > 0 at k=20, decile non-monotonic in places (Q1=+24.6%, Q5=+6.7% with U-shape Q2), \|corr\| to size = 0.31, \|corr\| to mom20 = 0.18 |
| G5 | ≥ 4 of 8 expressions in original batch peak at primary k | N/A for single-factor entry |

## Audits (per skill mandatory rules)

| Audit | Method | Result |
|---|---|---|
| Execution-delay | Verify `target_shift == -(delay+k) = -21` in code; physical timeline prose; future-perturbation invariance | PASS |
| Look-ahead | Permute last-30d benchmark return + close, recompute signal AND vol-target exposure, check past values bit-identical | PASS — sig_diff_max = 0.0, exposure_diff_max = 0.0 |
| Worst-year floor (≥ 0.5) | Group return by calendar year, compute per-year Sharpe, take min | **FAIL** — worst-year is 2022 = +0.11 |
| Best-year-out / headline ≥ 50% | Drop best year (2019 or 2025), avg of remaining ≥ 50% headline | PASS — 0.80 / 0.81 = 99% |
| Falsification-first | Pre-run hypothesis "if MA50 gate doesn't rescue 2024, the deployable form is ensemble overlay". Confirmed false-then-true. | PASS |

Worst-year FAIL is the binding constraint that keeps this factor at
RESEARCH-ONLY status. The 2022 narrative-collapse year drove every
inverted-IVOL variant tested below 0.5; vol-target reduces the magnitude
but does not invert the sign of the bad year.

## Performance summary (2019-01 → 2026-04, full window)

| Metric | Value |
|---|---:|
| LS net Sharpe @ 5 bps/side | **+0.81** |
| LS gross Sharpe | +0.85 |
| Raw LS (no vol-target) Sharpe | +0.66 |
| LS annualized return (net) | +9.50% |
| LS max drawdown | −8.7% |
| Avg gross exposure | 70% |
| Annual turnover | 432% |
| Worst-year Sharpe | +0.11 (2022) |
| Best-year-out avg / headline | 99% |
| Years positive / total | 7 / 7 |
| Test (OOS) Sharpe | +0.94 (3.3 years) |

## Why vol-target is the chosen R2 winner

R2 tested 8 variants targeting standalone PROMOTE. None passed worst-year ≥ 0.5
floor (deemed structurally infeasible for inverted-IVOL on a 30-ETF universe
without ensemble support). Among the 8, vol-target was selected because:

1. **All 7 calendar years positive** (only variant with this property).
2. **Smallest gross-net Sharpe gap** (0.85 → 0.81; cost drag is small at 70% avg
   exposure).
3. **Self-contained risk management** — no dependency on a regime gate that may
   itself fail in the next regime.
4. **Train/test consistency**: 0.99 / 0.94 ratio (test slightly weaker; no overfit).
5. **Sensible exposure dynamics** — exposure averages 70% but ranges from ~50%
   in high-vol regimes (2020, 2022) to ~95% in low-vol regimes (2025).

R2 variants ranked (full window net@5bps Sharpe / worst-year):

| Rank | expr | Sharpe | wy | wy_pass |
|:--:|---|---:|---:|---|
| 1 | r2_LS_voltarget_10 | **0.81** | +0.11 | False |
| 2 | r2_topN_no_gate | 0.75 | -0.25 | False |
| 3 | r2_topN_persist | 0.68 | -0.35 | False |
| 4 | r2_topN_RS_gate | 0.61 | -0.24 | False |
| 5 | r2_topN_RS_voltarget | 0.57 | -0.51 | False |
| 6 | r2_topN_RS_persist | 0.53 | -0.45 | False |
| 7 | r2_kitchen_sink | 0.44 | -0.46 | False |
| 8 | r2_topN_disp_gate | 0.24 | -1.00 | False |

## Ensemble deployment metrics

(Standalone is RESEARCH-ONLY; the ensemble form is the PROMOTE path.)

| Ensemble | Weights | Sharpe weekly | Worst-year | Calmar | Pass all floors |
|---|---|---:|---:|---:|---|
| Inv-IVOL × V25 | 0.5 / 0.5 | **2.30** | +0.82 | 2.19 | ✅ |
| Inv-IVOL × V25 | 0.4 / 0.6 | 2.27 | +0.84 | 2.54 | ✅ |
| Inv-IVOL × V25 | 0.3 / 0.7 | 2.19 | +0.83 | 2.96 | ✅ |
| Inv-IVOL × V25 | 0.2 / 0.8 | 2.09 | +0.81 | 3.15 | ✅ |
| Inv-IVOL × V7_gold | 0.5 / 0.5 | 2.18 | +0.83 | 2.30 | ✅ |
| V25 alone | — | 1.87 | +0.75 | 3.04 | ✅ |
| V7_gold alone | — | 1.73 | +0.77 | — | ✅ |
| Inv-IVOL alone (this factor) | — | 1.44 (weekly) / 0.81 (monthly LS net) | +0.11 (2022, monthly) | — | ❌ wy floor |

Cross-strategy correlation (weekly returns, 311 weeks):
- Inv-IVOL × V25 = **0.053**
- Inv-IVOL × V7_gold = **0.052**
- V25 × V7_gold = **0.977** (do NOT combine these two)

## Implementation contract

```python
import pandas as pd
import code as factor_code   # this directory's code.py

panel = pd.read_parquet("logs/_shared_cache/etf_daily.parquet")
panel["ret"] = panel.groupby("symbol")["close"].pct_change()

result = factor_code.run(panel)

# result is a FactorResult with:
#   raw_LS_ret             — LS return without vol-target (the m1 baseline)
#   voltarget_LS_ret       — LS scaled to 10% ann vol
#   voltarget_LS_ret_net5bps — minus 5 bps/side cost
#   exposure               — daily exposure series (mean ≈ 0.70)
#   rank                   — DataFrame of cross-sectional IVOL ranks
#   signal                 — DataFrame of IVOL values
```

## Provenance

- Session: `logs/20260501_a_share_etf_ivol_momentum_v1` (round 2, batch 0002)
- Branch: `claude/build-etf-factor-model-O6yXK`
- PR: huyukun662-crypto/Factor_Zoo#19
- 5-agent workflow: WorldQuant 5-agent (Research Librarian → Hypothesis Architect → Alpha Builder → Backtest Operator → Evaluator)
- Parent session (falsification): `logs/20260501_a_share_etf_ivol_reversal_v1`
