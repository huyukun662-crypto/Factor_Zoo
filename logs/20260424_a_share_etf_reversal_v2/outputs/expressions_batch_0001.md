# Expressions — Batch 0001 (Round 1)

**Session:** `20260424_a_share_etf_reversal_v2`
**Agent:** 3 (Alpha Builder)
**Universe:** 34 A-share thematic ETFs
**Execution delay:** 1 bar; target = `log(close_adj[t+1+k]) - log(close_adj[t+1])`
**Neutralization:** universe-EW cross-sectional demean per date (zero-sum)
**Convention:** high signal = long (dip = positive signal)

## 8 expressions (Rule of 8 ✓)

| id | cluster | k | hold | formula (before demean) | rationale |
|---|---|---:|---|---|---|
| `r1_rev_1d`       | short_falsification | 1  | weekly  | `-logret_1d`                                    | Lehmann 1990 style 1-day bounce (expected to invert here — A-share ETF short-horizon is momentum) |
| `r1_rev_5d`       | short_falsification | 5  | weekly  | `-logret_5d`                                    | 5-day reversal (expected inversion; prior 18-ETF evidence) |
| `r1_rev_20d`      | medium_scan         | 20 | monthly | `-logret_20d`                                   | Start of transition band |
| `r1_rev_40d`      | medium_scan         | 40 | monthly | `-logret_40d`                                   | Middle of reversal zone |
| `r1_rev_60d`      | medium_scan         | 60 | monthly | `-logret_60d`                                   | Prior 18-ETF sweet spot — extension test |
| `r1_rev_80d`      | medium_scan         | 80 | monthly | `-logret_80d`                                   | Upper edge — does it still hold? |
| `r1_dd60_raw`     | drawdown_event      | 60 | monthly | `(max_60d(close) − close) / max_60d(close)`     | Current drawdown depth from 60d max (deep dip → long) |
| `r1_dd60_recover` | drawdown_event      | 60 | monthly | `dd60_raw * I[logret_5d > 0]`                   | Conditional: dd60 only when last-5d return is positive (recovery confirmation) |

## Audit probe (outside Rule of 8)

| id | formula | purpose |
|---|---|---|
| `probe_mom_20d_plus` | `+logret_20d` | Pipeline sanity / falsification control. If this has IC ≫ 0 at k=60, momentum leakage; if near 0 or negative, pipeline is clean. |

## Semantics and audit notes

1. `logret_Nd[t] = log(close_adj[t]) − log(close_adj[t−N])`. No shift, past-only.
2. `max_60d(close)[t] = close_adj.shift(0).rolling(60).max()` — **includes** current bar by design. Drawdown is a current-state feature; we are NOT asking "did close exceed the prior 60d max" (which would need `shift(1)`). We are asking "how far below the trailing 60d max is close now." Both interpretations are legal; this session uses the current-state one, same convention as prior session's `r1_dd20`.
3. `I[logret_5d > 0]` is an indicator gate — zeroing out `dd60_raw` when recent momentum is negative. **G1 non-degeneracy check**: before IC computation, verify this signal has `>0` value in ≥ 1% of obs.
4. Target: `target_k[t] = log(close_adj[t+1+k]) − log(close_adj[t+1])`. Execution delay = 1 bar. Signal at `t` is ranked, weights set at `t+1 close`, and realized over `[t+1, t+1+k]`.
5. Universe-EW demean per date: `signal_demean[t,i] = signal[t,i] − mean_over_i(signal[t, live])`. Applied after raw computation, before rank / quintile.
6. New ETF staggered-join: require 60 trading days of history before a symbol is eligible for ranking (avoids tiny-window statistics on fresh listings).
