# Expressions Batch 0001 — BTC 1m short-term reversal

**Session**: 20260423_btc_minute_reversal_v1
**Agent**: 3 (Alpha Builder)
**Mechanism**: short-term reversal, vol-scaled, hour-of-day demeaned
**Sign prior**: all 8 expressions signed so that **high value → LONG** next bar.

Symbol definitions (computed on the 1m bar series, all at bar `t`):

```
r1_t        = log(close_t) - log(close_{t-1})                   # 1-min log return
rN_t        = log(close_t) - log(close_{t-N})                   # N-min log return
rvN_t       = std(r1, window=N)                                 # realized vol over last N min
rangeN_t    = (max(high, window=N) - min(low, window=N)) / close_{t-N}
amountN_t   = sum(volume * close, window=N)                     # USD traded last N min
bodyN_t     = sum(|close - open| / close, window=N)             # candle-body sum
hour_t      = ts_t.hour (UTC)
ts_z(x)     = (x - mean(x)) / std(x)                            # time-series z over full sample
hd(x)       = x - mean(x | hour=hour_t)                         # hour-of-day demean
```

All signs constructed so that **higher signal → expected LONG**.

## 8 expressions (Rule of 8)

| # | name | formula (one line) | distinguishing axis | expected IC sign |
|---|------|--------------------|----------------------|------------------|
| 1 | `r1_rev_1m` | `-ts_z(r1_t)` | baseline 1-min reversal, no vol scale | + |
| 2 | `r1_rev_5m` | `-ts_z(r5_t)` | 5-min lookback, raw | + |
| 3 | `r1_rev_15m` | `-ts_z(r15_t)` | 15-min lookback, raw | + |
| 4 | `r1_rev_5m_volscale` | `-ts_z(r5_t / rv5_t)` | vol-scaled 5m reversal (PRIMARY) | + |
| 5 | `r1_rev_15m_volscale` | `-ts_z(r15_t / rv15_t)` | vol-scaled 15m | + |
| 6 | `r1_rev_5m_volscale_hd` | `-ts_z(hd(r5_t / rv5_t))` | vol-scaled 5m, hour-demeaned | + |
| 7 | `r1_rev_range5m` | `-ts_z(sign(r5_t) * range5_t)` | signed-range reversal (captures "wide move" intensity) | + |
| 8 | `r1_rev_amount5m` | `-ts_z(sign(r5_t) * log(amount5_t))` | amount-weighted 5m reversal | + |

## Construction pseudocode (canonical)

```python
# INPUT: df with [ts, open, high, low, close, volume], sorted by ts ascending
df["r1"]  = np.log(df["close"]).diff()
for n in [5, 15, 60]:
    df[f"r{n}"]     = np.log(df["close"]) - np.log(df["close"].shift(n))
    df[f"rv{n}"]    = df["r1"].rolling(n, min_periods=n).std(ddof=0)
    df[f"range{n}"] = (df["high"].rolling(n).max() - df["low"].rolling(n).min()) / df["close"].shift(n)
    df[f"amount{n}"]= (df["volume"] * df["close"]).rolling(n, min_periods=n).sum()

df["hour"] = df["ts"].dt.hour

def ts_z(s):
    mu, sd = s.mean(), s.std(ddof=0)
    return (s - mu) / sd if sd and not np.isnan(sd) else s * 0

def hd(s):
    # hour-of-day demean
    return s - df.groupby("hour")[s.name].transform("mean")

# Expressions (named after table above)
e1 = -ts_z(df["r1"])
e2 = -ts_z(df["r5"])
e3 = -ts_z(df["r15"])

vs5  = df["r5"]  / df["rv5"].replace(0, np.nan)
vs15 = df["r15"] / df["rv15"].replace(0, np.nan)

e4 = -ts_z(vs5)
e5 = -ts_z(vs15)

vs5_named = vs5.rename("vs5_hd_src")
# hd() broadcasts by df["hour"], so we do it inline
hd_vs5 = vs5 - df.assign(_vs5=vs5).groupby("hour")["_vs5"].transform("mean")
e6 = -ts_z(hd_vs5)

signed_range5  = np.sign(df["r5"]) * df["range5"]
signed_amount5 = np.sign(df["r5"]) * np.log(df["amount5"].replace(0, np.nan))
e7 = -ts_z(signed_range5)
e8 = -ts_z(signed_amount5)
```

## Target construction (PIT-safe; delay=1)

```python
K_PRIMARY = 5  # minutes
DELAY     = 1

# execution-delay-aware target per SKILL.md audit 1
# at close[t]: signal observed; trade fill at close[t+1]; P&L captured over [close[t+1], close[t+1+K]]
df["fwd_ret_k"] = np.log(df["close"]).shift(-(DELAY + K_PRIMARY)) - np.log(df["close"]).shift(-DELAY)
```

For aux horizons k in {1, 15, 60}, repeat with `shift(-(DELAY + k))`.

## Hard constraints met

- [x] Exactly 8 expressions
- [x] One dominant mechanism (short-term reversal)
- [x] Each expression distinct (lookback length × vol scale × path metric × hour demean)
- [x] Economic note attached (see table "distinguishing axis")
- [x] Sign pre-specified (high signal → LONG, all 8)
- [x] Target uses delay=1 (`shift(-(1+k))`), no future bars in signal
- [x] Winsor/z operations guarded against std=0 (uses `ts_z` helper)

## G4 behavioral prediction (for Agent 4 to verify)

- **IC sign at k=5**: positive for ALL 8. If any is negative, Agent 4
  should enter repair loop (likely a sign-flip bug in that expression).
- **IC t-stat at k=5**: expected > 4 for #4 and #6 (primary candidates),
  > 2 for #1 and #2 (raw baselines), possibly noisier for #7/#8.
- **IC horizon profile**: IC should be highest at k=5 for #4, decay at
  k=60. A monotonically increasing IC in horizon would falsify the
  reversal thesis.
- **Decile spread**: D10 (top decile of signal) should have positive
  average forward return; D1 bottom. D10-D1 > 0 is necessary.

## Handoff to Agent 4

- Script entrypoint: `scripts/02_build_and_backtest.py`
- Required outputs:
  - `outputs/backtest_results_batch_0001.md`
  - `outputs/ic_table_batch_0001.csv` (IC per expression × horizon)
  - `outputs/decile_summary_batch_0001.csv` (D1..D10 mean fwd_ret per expression)
  - `outputs/ls_summary_batch_0001.csv` (strategy PnL stats per expression)
  - `outputs/validation_gates_batch_0001.json` (G1-G4 results)
  - `working/handoff_3_to_4.json`
