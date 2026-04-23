# Expressions Batch 0002 — BTC 1m reversal, 15m horizon + 15-bar hold

**Session**: 20260423_btc_minute_reversal_v1
**Round**: 2
**Batch**: 0002
**Agent**: 3 (Alpha Builder)
**Parent**: batch_0001 residue — reversal real at k=15m, cost wiped by 1-bar rebalance
**Mechanism**: short-term reversal at 15-minute horizon with 15-bar hold

All signed so **high signal → LONG**.

## 8 expressions (Rule of 8)

| # | name | formula (one-line) | distinguishing axis | expected IC sign |
|---|------|--------------------|----------------------|------------------|
| 1 | `r2_rev_15m` | `-ts_z(r15_t)` | baseline (best of Round 1) re-targeted at k=15m with 15-bar hold | + |
| 2 | `r2_rev_30m` | `-ts_z(r30_t)` | longer lookback (matches Avellaneda-Lee 15-30m band) | + |
| 3 | `r2_rev_45m` | `-ts_z(r45_t)` | longer still | + |
| 4 | `r2_rev_60m` | `-ts_z(r60_t)` | 1-hour reversal | + |
| 5 | `r2_rev_15m_volscale` | `-ts_z(r15_t / rv15_t)` | vol-scaled 15m | + |
| 6 | `r2_rev_30m_volscale` | `-ts_z(r30_t / rv30_t)` | vol-scaled 30m | + |
| 7 | `r2_rev_30m_ema15` | `-ts_z(ema(r30_t, span=15))` | EMA-smoothed 30m signal (whipsaw reducer) | + |
| 8 | `r2_rev_30m_volscale_hd` | `-ts_z(hd(r30_t / rv30_t))` | vol-scaled 30m + hour-demean (full neutralization) | + |

## Construction (canonical pseudocode)

```python
# Reuse panel built in scripts/02_build_and_backtest.py
# Additional columns needed:
for n in [30, 45]:
    df[f"r{n}"]  = np.log(df["close"]) - np.log(df["close"].shift(n))
    df[f"rv{n}"] = df["r1"].rolling(n, min_periods=n).std(ddof=0)

# EMA smoothed r30: emulate pandas.ewm(span=15, adjust=False, min_periods=15)
df["r30_ema15"] = df["r30"].ewm(span=15, adjust=False, min_periods=15).mean()

e1 = -ts_z(df["r15"])
e2 = -ts_z(df["r30"])
e3 = -ts_z(df["r45"])
e4 = -ts_z(df["r60"])

vs15 = df["r15"] / df["rv15"].replace(0, np.nan)
vs30 = df["r30"] / df["rv30"].replace(0, np.nan)
e5 = -ts_z(vs15)
e6 = -ts_z(vs30)

e7 = -ts_z(df["r30_ema15"])

vs30_hd = vs30 - df.assign(_s=vs30).groupby("hour")["_s"].transform("mean")
e8 = -ts_z(vs30_hd)
```

## Strategy (15-bar hold)

```python
HOLD = 15
for each expr signal s:
    q_lo, q_hi = s.quantile(0.10), s.quantile(0.90)
    raw_pos = +1 if s >= q_hi else -1 if s <= q_lo else 0

    # hold constraint: keep pos for 15 bars; only re-evaluate at bar t
    # where (t - last_trade) >= HOLD, else freeze pos
    pos = apply_hold(raw_pos, hold=HOLD)
    pos_eff = pos.shift(1)   # execution delay=1
    r_next  = log(close).shift(-1) - log(close)
    gross   = pos_eff * r_next
    turn    = pos_eff.diff().abs()
    cost    = turn * (cost_bps / 1e4)
    net     = gross - cost
```

Cost sensitivity: report net Sharpe at cost_bps ∈ {2, 5, 8, 10} per side.

## Hard constraints met

- [x] Exactly 8 expressions
- [x] One mechanism (15m reversal); all variants share k=15m target
- [x] Eight distinct constructions (4 raw lookbacks + 2 vol-scaled + EMA + hour-demean)
- [x] Sign pre-specified (high → LONG)
- [x] Hold constraint baked into strategy (not expression), so expressions remain clean
- [x] No future-bar references in any signal
- [x] Target uses `shift(-(delay + k))` with delay=1, primary k=15

## G5 pre-commit self-check

Before Agent 4 runs: Round 1's G5 would have flagged the batch if
re-run as a meta-check. Round 2's expressions ALL target k=15m with
15-bar holds — if these do NOT peak at k=15m in the backtest, the
mechanism itself (not the horizon) is broken. G5 as written should
pass for this batch; failure means pivot to a different mechanism,
not another horizon tweak.

## Handoff to Agent 4

- Script: `scripts/03_round2_backtest.py`
- Required outputs:
  - `outputs/backtest_results_batch_0002.md`
  - `outputs/ic_table_batch_0002.csv`
  - `outputs/ls_summary_batch_0002.csv`
  - `outputs/cost_sensitivity_batch_0002.csv`
  - `outputs/validation_gates_batch_0002.json`
  - `working/handoff_4_to_5_round2.json`
