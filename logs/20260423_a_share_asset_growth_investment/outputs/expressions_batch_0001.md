# Expressions Batch 0001 — Asset Growth variants

**Session**: 20260423_a_share_asset_growth_investment
**Agent**: 3 Alpha Builder
**Dominant mechanism**: Asset Growth (q-theory / investment anomaly)
**Count**: 8 (Rule of 8 enforced)

All formulas use **PIT-lagged** quarterly `total_assets` (from `balancesheet.parquet`), lookup key `f_ann_date + 1 trading day`. All are **signed so that high value → long**.

| # | name | formula (pseudocode) | neutralization | horizon | expected turnover (ann.) | expected IC sign | economic note |
|---|------|----------------------|----------------|---------|--------------------------|------------------|---------------|
| 1 | `ag_yoy_raw` | `-(TA_t - TA_{t-4q}) / TA_{t-4q}` | none | 21d | ~120% | + | Pure CGS 2008 replica, benchmark; expected size-proxy |
| 2 | `ag_yoy_ind` | `ag_yoy_raw - median_{SW_L1}(ag_yoy_raw)` | SW L1 industry median | 21d | ~140% | + | Primary candidate; removes SOE capex-cycle & industry beta |
| 3 | `ag_yoy_ind_size` | `ag_yoy_ind - median_{size quintile}(ag_yoy_ind)` | SW L1 + size quintile | 21d | ~150% | + | Double-demean; isolates idiosyncratic AG |
| 4 | `ag_log_yoy_ind` | `-log(TA_t / TA_{t-4q})` then industry-demean | SW L1 industry | 21d | ~130% | + | Log stabilizes tails; less M&A-jump-sensitive |
| 5 | `ag_2y_ind` | `-(TA_t - TA_{t-8q}) / TA_{t-8q}`, industry-demean | SW L1 industry | 42d | ~80% | + | Slower signal, lower turnover, captures cumulative overinvestment |
| 6 | `ag_qoq_ind` | `-(TA_t - TA_{t-1q}) / TA_{t-1q}`, industry-demean | SW L1 industry | 10d | ~280% | + | Faster signal; captures single-quarter capex shocks (seasonal) |
| 7 | `ag_rank_ind` | `-rank_cs(TA_t / TA_{t-4q})` then industry-demean | SW L1 industry | 21d | ~110% | + | Cross-sectional rank; outlier-immune, should be most stable |
| 8 | `ag_composite` | `0.5 * z(ag_yoy_ind) + 0.5 * z(ag_log_yoy_ind)` | SW L1 industry (inherited) | 21d | ~130% | + | Average of two different transforms of same mechanism; diversification boost |

## Construction pseudocode (canonical, same for all 8 up to the last step)

```python
# INPUTS
bs = load_parquet(".cache/balancesheet.parquet")  # ts_code, end_date, f_ann_date, total_assets
daily = load_parquet(".cache/daily.parquet")     # ts_code, trade_date, close
sw = load_parquet(".cache/sw_l1_map.parquet")    # ts_code, in_date, out_date, industry_code

# STEP 1: clean quarterly BS, keep max(ann_date, f_ann_date) per (ts_code, end_date)
bs = bs.sort_values(["ts_code","end_date","f_ann_date"]).groupby(["ts_code","end_date"]).last()

# STEP 2: build lagged total_assets (1q, 4q, 8q lags by quarterly index)
bs["ta_lag_1q"] = bs.groupby("ts_code")["total_assets"].shift(1)
bs["ta_lag_4q"] = bs.groupby("ts_code")["total_assets"].shift(4)
bs["ta_lag_8q"] = bs.groupby("ts_code")["total_assets"].shift(8)

# STEP 3: compute raw signal
bs["ag_yoy_raw"] = -(bs["total_assets"] - bs["ta_lag_4q"]) / bs["ta_lag_4q"]
# ... (repeat for log / 2y / qoq variants)

# STEP 4: PIT-lag — map to trading-day panel using f_ann_date
#   each (ts_code, end_date) record becomes valid on next trading day >= f_ann_date + 1
panel = daily[["ts_code","trade_date"]].copy()
panel = panel.merge_asof(bs.reset_index(), left_on="trade_date", right_on="f_ann_date",
                          by="ts_code", direction="backward")
# shift +1 day to be safe against intraday announcements
panel = panel.groupby("ts_code").shift(1)

# STEP 5: universe filter — exclude ST/*ST, require 504 trading days history, price >= 2
panel = apply_universe_filter(panel, daily, min_history=504, min_price=2)

# STEP 6: neutralization — merge SW L1 industry (PIT via in_date/out_date), demean per (trade_date, industry)
panel = merge_sw_l1_pit(panel, sw)
panel["ag_yoy_ind"] = panel.groupby(["trade_date","industry_code"])["ag_yoy_raw"].transform(lambda s: s - s.median())

# STEP 7: winsorize + z-score per date
for col in factor_cols:
    panel[col] = winsorize_cs(panel[col], p=0.01)
    panel[col] = zscore_cs(panel[col])
```

## Expected turnover direction and why

Monthly-rebalance AG signal changes **only** when new quarterly report is filed (4 times a year). Between reports,
the signal drifts via denominator/rank churn. Expected annual turnover:
- **Raw / industry-demean / composite**: 120-150% (moderate)
- **2y lag**: 80% (slowest — 8q denominator smooths more)
- **QoQ**: 280% (fastest — seasonal jumps every quarter)
- **Rank**: 110% (rank stability gives lowest turnover among transforms)

## Hard constraints met

- [x] Exactly 8 expressions
- [x] One dominant mechanism (Asset Growth)
- [x] Expressions differ in construction (3 neutralization variants, 3 window variants, 2 transform variants + 1 composite)
- [x] Every expression has economic note
- [x] PIT rule embedded (f_ann_date + 1)
- [x] Universe filter specified

## Handoff to Agent 4

- Run all 8 in one Python script (`scripts/03_build_and_backtest.py`).
- Submit to backtest with `delay=1` (T+1 execution), `visualization=false`.
- Return IC table + LS summary + annual LS + annual Q5 long-only excess for each.
- Run execution-delay audit BEFORE writing any result as canonical.
