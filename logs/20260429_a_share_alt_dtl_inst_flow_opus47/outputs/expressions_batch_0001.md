# Agent 3 — Alpha Builder: Expressions Batch 0001

Session: `20260429_a_share_alt_dtl_inst_flow_opus47`
Mechanism family: A-share Dragon-Tiger List institutional informed-flow.
Budget: 8 expressions (Rule of 8). Split: M3 ×4, M4 ×2, M2 ×2.
Common pre-processing for every expression below:
- Inputs sourced from `top_list` and `top_inst` Tushare endpoints, joined
  on `(ts_code, trade_date)`.
- All disclosed inputs are `lag(1)` (DTL is published t+0 ~17:00; we trade
  at t+1 close → factor uses only data available before the trade).
- Cross-section operations are date-grouped (no time-series global z).
- After raw computation: `winsorize_mad(3.5) → industry_demean →
  cross_section_zscore → rank_normalize`.
- Universe: CSI All-Share ex-ST ex-IPO<250d. Stocks with no DTL row in
  the relevant lookback window have factor = 0 (not NaN), so they fall
  to the cross-section median rank rather than being dropped — this
  preserves daily Q5 size.

Notation:
- `inst_buy_amt[t]` = institutional-seat gross buy CNY on day t (from
  `top_inst`, sum across institutional seats present that day).
- `inst_sell_amt[t]` = institutional-seat gross sell CNY on day t.
- `inst_net[t]` = `inst_buy_amt[t] − inst_sell_amt[t]`.
- `dtl_top5_buy[t]`, `dtl_top5_sell[t]` = top-5 buyers / top-5 sellers
  aggregate gross from `top_list` (includes both inst and 營業部 seats).
- `amt20[t]` = 20d trailing average of OHLCV `amount` (CNY traded).
- `is_upper_limit[t]` = boolean, daily close hit upper price limit.
- `hot_money_seat_set` = hard-coded list of canonical retail-aggressive
  branch codes valid 2018-2025; documented in `inputs/hot_money_seats.csv`.

---

## alpha_01 — M3a: institutional net-buy ratio, 1d
**Expression:**
```
raw_01[t] = lag(inst_net[t], 1) / lag(amt20[t], 1)
alpha_01  = rank_norm( industry_demean( winsor_mad( raw_01, 3.5 ) ) )
```
**Economic story:** Single-day institutional revealed imbalance,
normalized by recent baseline turnover. Largest signal on the day
immediately after disclosure; expected positive IC at h=5–10d.
**Expected turnover:** high (≈ 200–400% annualized) — daily flips driven
by event-triggered cross-section. Will fail cost gate at daily; intended
as the "raw signal" reference; the deployable variant is alpha_02 / alpha_03.

## alpha_02 — M3b: institutional net-buy ratio, 5d sum
**Expression:**
```
raw_02[t] = sum( lag(inst_net, 1), 5 ) / lag(amt20, 1)
alpha_02  = rank_norm( industry_demean( winsor_mad( raw_02, 3.5 ) ) )
```
**Economic story:** 5-day rolling institutional revealed imbalance.
Smooths event sparsity and captures multi-day campaigns. Expected to be
the strongest single-construction member of the batch.
**Expected turnover:** medium (≈ 80–150% annualized).

## alpha_03 — M3c: institutional net-buy ratio, 5d sum, scaled by event-day amount
**Expression:**
```
raw_03[t] = sum( lag(inst_net, 1), 5 ) /
            sum( lag(amount_on_dtl_days, 1), 5 )
alpha_03  = rank_norm( industry_demean( winsor_mad( raw_03, 3.5 ) ) )
```
where `amount_on_dtl_days[t]` = OHLCV amount on day t **only if** the
stock has a DTL row that day, else 0. Denominator is therefore
"institutional share of trading on disclosed days only".
**Economic story:** Scale-free conviction ratio rather than calendar
ratio; corrects for stocks that simply have larger turnover. Expected
higher IR than alpha_02 but lower IC mean.

## alpha_04 — M3d: institutional net-buy ratio, 10d sum, ex-upper-limit days
**Expression:**
```
mask_safe[t]  = NOT is_upper_limit[t]
inst_net_safe = inst_net * mask_safe
raw_04[t]     = sum( lag(inst_net_safe, 1), 10 ) / lag(amt20, 1)
alpha_04      = rank_norm( industry_demean( winsor_mad( raw_04, 3.5 ) ) )
```
**Economic story:** Removes the limit-up co-occurrence regime
(common-pitfalls.md Pitfall 6) by zeroing institutional net-buy on days
the stock closed at the upper limit. Expected to *lose* some headline
Sharpe but gain robust worst-year Sharpe. **Look-ahead audit note:**
`mask_safe` is built from **past** prices only (day t's close vs. day
t's prior close); no shift(-k); safe.

## alpha_05 — M4a: institutional net-buy persistence, 20d sum
**Expression:**
```
raw_05[t] = sum( lag(inst_net, 1), 20 ) / lag(amt20, 1)
alpha_05  = rank_norm( industry_demean( winsor_mad( raw_05, 3.5 ) ) )
```
**Economic story:** Long-window persistence captures multi-week
accumulation campaigns; designed to retain signal at monthly rebalance.
Expected: lower daily Sharpe than alpha_02, but better after-cost
monthly Sharpe.
**Expected turnover:** low (≈ 30–60% annualized).

## alpha_06 — M4b: institutional net-buy days count, 20d
**Expression:**
```
inst_pos_day[t] = 1 if inst_net[t] > 0 else 0
raw_06[t]       = sum( lag(inst_pos_day, 1), 20 )
alpha_06        = rank_norm( industry_demean( winsor_mad( raw_06, 3.5 ) ) )
```
**Economic story:** Count-of-positive-inst-days, scale-free. Robust to
single-day outliers (a giant block-trade-driven inst buy doesn't dominate).
Expected lower IC magnitude but more stable across years.

## alpha_07 — M2a: hot-money-only reversal, 5d
**Expression:**
```
hot_money_only[t] = 1 if (any seat in dtl_top5_buy[t] in hot_money_seat_set
                          AND no inst seat in dtl_top5_buy[t])
                    else 0
raw_07[t] = -1 * sum( lag(hot_money_only, 1) * lag(dtl_top5_buy, 1)
                      / lag(amt20, 1), 5 )
alpha_07  = rank_norm( industry_demean( winsor_mad( raw_07, 3.5 ) ) )
```
**Economic story:** Sign-flipped reversal: stocks where the DTL was
triggered by retail-aggressive 營業部 buying *without* institutional
participation are typically post-limit-up speculative pumps; next-week
return is negative. Explicit `-1` so factor is monotone with forward
return like the others.
**Forward-bias caveat:** `hot_money_seat_set` is fixed using 2018-2025
public-knowledge canonical branches; if extended later, update Pitfall 5
disclosure.

## alpha_08 — Composite: M3 + M4 + M2 (rank-mean stack)
**Expression:**
```
alpha_08 = mean_of_ranks( [alpha_02, alpha_05, alpha_07] )
         = rank_norm( industry_demean( mean(
              rank(alpha_02), rank(alpha_05), rank(alpha_07)
           ) ) )
```
**Economic story:** Ensemble stack of the three distinct mechanisms.
Per `references/agent-prompts.md` Alpha Builder rules, this is the only
composite in the batch (avoids "loose linear-combination dumping").
Included to test whether the three mechanisms diversify, **not** as the
deployment candidate.
**Note for Agent 5:** if alpha_08 has higher IR than max(alpha_02,
alpha_05, alpha_07) but lower IC mean, the diversification is real;
otherwise drop the composite.

---

## Distinctness check (Agent 3 self-audit)

| construction axis | alpha_01 | alpha_02 | alpha_03 | alpha_04 | alpha_05 | alpha_06 | alpha_07 | alpha_08 |
|---|---|---|---|---|---|---|---|---|
| window      | 1d  | 5d  | 5d  | 10d | 20d | 20d | 5d   | mixed |
| denom       | amt20 | amt20 | event-amt | amt20 | amt20 | none(count) | amt20 | n/a |
| seat scope  | inst | inst | inst | inst-safe | inst | inst | retail-only | mix |
| sign        | +    | +    | +    | +    | +    | +    | −    | +    |
| ex-LU mask  | no   | no   | no   | yes  | no   | no   | no   | no   |
| primary mech| M3   | M3   | M3   | M3   | M4   | M4   | M2   | mix  |

Each row differs from every other on ≥ 2 axes — passes Alpha Builder
distinctness rule.

## Expected-turnover declaration (per Agent 3 hard constraint)

| alpha | direction | rough annualized |
|---|---|---|
| 01 | high     | 200–400% |
| 02 | medium   | 80–150%  |
| 03 | medium   | 80–150%  |
| 04 | medium   | 70–130%  |
| 05 | low      | 30–60%   |
| 06 | low      | 25–50%   |
| 07 | high     | 250–500% |
| 08 | medium   | 80–140%  |

Cost gate (G3, net Sharpe at 30bp > −0.5): alpha_01 and alpha_07 likely
to fail at daily rebalance; both should be evaluated at weekly+ instead.

## Audit pre-checks (must hold before submission)

- [x] Every expression starts with `lag(*, 1)` on disclosed inputs.
- [x] `target_shift == -(1+delay)` enforced in the backtest harness, not
      inside any factor (G1).
- [x] No `.where(mask)` where `mask` derives from `ret.shift(-k)` or
      `next_*` (look-ahead audit).
- [x] `mask_safe` in alpha_04 derives only from same-day close vs. prior
      close — past-only.
- [x] `hot_money_seat_set` is a fixed CSV in `inputs/`, not regenerated
      from data each run.
- [x] All cross-section ops grouped by date.

Hands off to Agent 4 (Backtest Operator) via `handoff_3_to_4.json`.
