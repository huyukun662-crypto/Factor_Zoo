# Objective — A-share ETF Reversal v2 (extended universe + horizon scan)

## User request

> 用 worldquant workflow 构建一个 A 股 ETF 抄底/反转因子。
>
> Parameters (confirmed):
> - Universe: 34 thematic A-share ETFs (same as V7_gold)
> - Independent factor + optional V7 fusion comparison
> - 8 expressions covering the transition band between momentum and reversal:
>   - 2 short-horizon falsification probes (1d, 5d) — expected to show momentum sign
>   - 4 medium-horizon horizon scan (20d, 40d, 60d, 80d) — cross-universe validation of prior session's 60d sweet spot
>   - 2 drawdown event-type (dd60 depth + dd60 with 5d recovery confirmation)

## Why this session exists (prior context)

The prior reversal session `20260423_a_share_etf_reversal_v1` on an 18-ETF
universe concluded:

- ≤20d horizon on A-share ETFs is **momentum**, not reversal (Round 1: 7/8 negative IC, Q1>Q5 inverted).
- ~60d horizon is the **reversal sweet spot** — `r2_lt_rev_60d` IC t=+2.35, Net Sh @5bps +0.56, Q5-Q1 monotonic.
- ~120-250d horizon is again **momentum** (long-horizon DeBondt-Thaler does NOT hold here).
- Blocking issue: worst-year 2020 Sharpe = -0.68 on short leg (COVID momentum regime).

Prior closure suggested three Round 3 paths; this session executes a combination of:
- Path #3 (extend universe 18 → 34 thematic) to test whether thicker cross-section sharpens the 60d reversal signal
- Path #1 (long-only variant) to evaluate whether removing the short leg rescues the worst-year floor

## Success / failure definition

Deploy bar is **all five mandatory audits pass** (execution-delay, look-ahead,
worst-year ≥ 0.5, best-year-out ≥ 50% headline, falsification). Research bar
is **G1-G4 pass** with mechanism confirmation. Anything weaker than that is
RESEARCH-ONLY and gets logged for the next round's input.

## Known constraints / lessons to apply

From recent sessions (weekly TQPB R2 lessons):

1. **G1 non-degeneracy gate** — signal must actually trigger; any expression
   with `signal_raw > 0` in < 1% of obs is degenerate and must be rejected
   before IC computation.
2. **Prior-window semantics** — any `ts_max(x, N)` or `rolling().max()` must
   be preceded by `shift(1)` to avoid leaking the current bar into breakout
   comparisons. For pure reversal (`-logret_Nd`) this is not an issue, but
   the drawdown event expressions (`dd60 = (max(close, 60) - close) / max(close, 60)`)
   must use `shift(0)` on max — that is, *include* the current bar (drawdown
   is a current-state feature, not a forward-looking one).
3. **Dense weekly rebalancing** — if the strategy holds zero positions some
   weeks (threshold-based triggers), explicit zero-weight rows each Friday
   avoid the ffill-held-forever bug.
4. **Baseline re-reproduction** — V7_gold on this session's sample window
   will be re-run from source; do not take the published full-sample 1.91
   at face value (V7 alignment produced 1.759 on 377 weeks last session).

## Scope and boundaries

- Session sample: common window where ≥ 10 ETFs are live, ≈ 2019-01 onward
  (aligned to V7 baseline's `2019-01-04` start).
- Rebalance: daily signal, weekly Friday rebalance (held 5 bars), **plus
  monthly rebalance (20 bar hold)** for the k=60/80 horizon candidates where
  prior evidence supports longer holding.
- Cross-sectional neutralization: universe-EW demean per date.
- Transaction cost sensitivity: 0, 5, 10, 15 bps/side.
- Audits: all 5 mandatory (execution-delay, look-ahead randomized future
  bars, worst-year Sharpe, best-year-out, falsification).

## Non-goals for this session

- No industry neutralization beyond universe-EW demean (universe is already
  scoped to thematic/industry ETFs; a second industry neutralization is
  degenerate).
- No model-stacking or ML.
- No optimization over hold period within a single expression — each
  expression declares its hold horizon up front.
