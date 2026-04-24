# Research Brief — BTC 1-minute factor

**Session:** 20260423_btc_minute_reversal_v1
**Agent:** 1 (Research Librarian)
**Objective:** Mine a deployable alpha on BTC-USD 1-minute bars using only OHLCV.
**Sample:** ~60 days of Coinbase BTC-USD 1m (~86,400 bars expected).

---

## 1. Candidate mechanisms (literature + practitioner)

### 1.1 Short-term reversal / liquidity provision (PRIMARY candidate)
- Nagel 2012 "Evaporating Liquidity": at intraday horizons, compensated
  returns to market-makers show up as mean-reversion after liquidity-
  demanding trades.
- Heston & Sadka 2008 variant: return over previous k minutes predicts
  return over next k minutes with a negative sign, scaled by volume.
- In crypto, Baron-Brogaard-Hagströmer-Kirilenko 2019 (HFT market-making
  in FX/crypto futures) show the same sign — aggressive flows get paid.
- **Expected signal direction:** `signal = -past_ret` (high past return
  → short next). Volume-weighted version usually stronger.
- **Expected IC horizon profile:** IC peaks at 1-15 min, decays sharply
  past 60 min (microstructure effect, not persistent alpha).

### 1.2 Realized-vol-scaled reversal
- Raw reversal is noisy because return = vol × noise.
- Divide past return by realized vol of the same window → cleaner signal.
- Well documented in equities (Lehmann 1990); survives in crypto
  per various industry reports.

### 1.3 Range as information proxy (Alizadeh-Brandt-Diebold 2002)
- High-Low range is an informationally efficient volatility estimator.
- Intraday: unusually wide range often signals information arrival;
  after info is absorbed, short-term reversal typically follows.
- **Signal candidate:** `-last_range_zscore` combined with directional
  sign of the candle (`sign(close - open)`).

### 1.4 Volume clustering / abnormal volume
- Gallant-Rossi-Tauchen 1992 volume-volatility relation + Campbell-
  Grossman-Wang 1993 volume-as-information. In crypto minute scale:
  volume spikes in the last k minutes typically precede a short-term
  reversal if the spike was uninformed (panic / liquidation cascade),
  or continuation if informed (listing, regulatory news).
- **Problem:** we can't distinguish informed vs uninformed from OHLCV
  alone. Treat as a sub-signal that requires combination.

### 1.5 Hour-of-day seasonality
- BTC minute returns have clear UTC-hour seasonality (Asian session
  vs US/EU session liquidity). If not removed, it contaminates the
  signal.
- **Not a factor**, but a required demean step (analogous to
  A-share industry neutralization).

### 1.6 Price-vs-VWAP (not tested this round)
- Would require volume-weighted intraday levels over longer windows.
  Leave for a later batch if reversal works.

### 1.7 Funding rate / perp-spot basis (not available)
- Requires separate Binance / OKX perpetuals data. Blocked in this
  environment.

---

## 2. Picked mechanism for Round 1

**Short-term reversal, vol-scaled, hour-of-day-demeaned.**

Rationale:
- Strongest empirical prior in HFT literature
- Implementable with OHLCV only
- Effect size large enough to survive transaction costs if rebalance
  frequency is kept modest (5-15 minute hold)
- Clear sign prior → G4 fidelity gate is easy to specify

---

## 3. Data / operator suggestions

### 3.1 Cache / preprocessing
- Parquet file: `inputs/btc_1m.parquet` with columns
  `[ts, open, high, low, close, volume]`; ts UTC-tz.
- Check coverage vs full minute grid; gaps < 1% acceptable,
  larger gaps → investigate (Coinbase occasional maintenance).
- Log-returns: `r1 = log(close_t) - log(close_{t-1})`. All downstream
  math on `r1`.

### 3.2 Key operators
- `rolling(N).sum()` or `.mean()` for past-return aggregates
- `rolling(N).std()` for realized vol (ddof=0, min_periods=N)
- `rolling(N).max()` - `rolling(N).min()` for range
- `groupby(df.ts.dt.hour).transform("mean")` for hour demean
- `zscore` over the full sample (time-series z) for final scaling

### 3.3 Forward return target
- `r_fwd_k = log(close_{t+k}) - log(close_t)` for k in {1, 5, 15, 60}
- Target is measured on the EXECUTION bar — if signal at close[t] is
  traded at close[t+1] (delay=1), then `target = log(close_{t+k+1}) -
  log(close_{t+1})`. Agent 3 MUST encode this explicitly; default delay=1.

---

## 4. Risks / caveats

- **Small sample (60 days) but high minute count (~86k).** Good
  statistical power for IC, but only ~1-2 bear/flat/bull micro-regimes
  in the window — do NOT extrapolate to multi-year.
- **Liquidity of Coinbase vs Binance:** Coinbase minute volume is
  lower. Factors that rely on volume-spike mechanics will be noisier.
  For this reversal mechanism, volume is a weight, not the signal, so
  effect should still hold.
- **Survivorship not an issue** (only BTC), but regime concentration is.
  One sustained trend (e.g., 3-day rally) can dominate.
- **Transaction costs are real at minute scale.** Coinbase taker fee
  is ~10 bps; Kraken ~15 bps; OKX taker ~5 bps. Use 5 bps per side
  as the hard cost assumption. Strategies that require < 5-minute
  hold will not survive.

---

## 5. Handoff to Agent 2

- **Primary mechanism**: short-term reversal, vol-scaled, hour-demeaned.
- **Target**: 5-minute forward log return at delay=1.
- **Hard floors**: IC t-stat >= 4; decile spread Sharpe >= 1.0 gross;
  after-cost Sharpe > 0 at 5 bps per side.
- **Additional audits**: execution-delay audit (G4 IC sign consistency);
  hour-of-day decomposition; per-week Sharpe stability.

See `working/handoff_1_to_2.json` for machine-readable handoff.
