# Final Summary — BTC 1m Reversal v1 (Rounds 1 + 2)

**Session:** 20260423_btc_minute_reversal_v1
**Data:** BTC-USD 1m, Coinbase, 2026-02-22 → 2026-04-23 (60 days, 86,380 bars)
**Verdict:** RESEARCH-ONLY. No factor promoted. Session closed after Round 2.

## Two-round summary

| | Round 1 | Round 2 |
|---|---|---|
| Primary horizon | 5 min | 15 min |
| Hold | 1 bar | 15 bars |
| Expressions | 8 (1/5/15m windows) | 8 (15/30/45/60m windows) |
| G3 pass | 5/8 | **0/8** (new net-Sharpe gate fires) |
| G4 pass | 3/8 | 4/8 |
| G5 batch horizon | — (not yet defined) | **PASS, 4/4 peak at k=15m** |
| Best IC t-stat @ k=15m | 3.86 (r1_rev_15m) | 3.86 (r2_rev_15m) — same signal |
| Best gross Sharpe | 8.42 (cost-unviable variant) | 2.54 (r2_rev_60m) |
| Best net Sharpe @ 5bps | -68 (r1_rev_15m) | -12.9 (r2_rev_30m_ema15) |
| Verdict | RESEARCH-ONLY | RESEARCH-ONLY (close) |

## Round 2 detail

## One-paragraph summary (two rounds)

Ran the WorldQuant 5-agent workflow on 60 days of BTC-USD 1-minute bars
testing short-term reversal. Round 1 (k=5m primary, 1-bar hold) found
the mechanism real at k=1m and k=15m but flat at k=5m — horizon was
mis-specified. Round 2 (k=15m primary, 15-bar hold, cost-sensitivity
curve) confirmed the mechanism cleanly: G5 batch-horizon-consistency
passes 100% (all 4 G4-survivors peak at k=15m), best IC t-stat 3.86
(`r2_rev_15m`), gross Sharpe up to 2.54. **But 0 of 8 Round-2 expressions
pass the new G3 net-Sharpe gate.** Breakeven cost is 0.4 bps per side;
realistic spot taker is 5-10 bps — the signal is 30× smaller than the
cost per bar. Mechanism confirmed, deployability structurally blocked
at spot-taker fee levels.

## Key numbers

| | value |
|---|---:|
| bars analyzed | 86,380 |
| coverage vs full 1m grid | 99.98% |
| expressions | 8 |
| passed G1 + G2 + G3 + G4 | 2 |
| best IC (across all horizons) | +0.0131 at k=15m (`r1_rev_15m`) |
| best IC t-stat | 3.86 |
| best GROSS Sharpe ann. | +8.42 (`r1_rev_5m_volscale_hd`, but G3/G4 both fail) |
| best NET Sharpe ann. at 5 bps/side | -68.5 (`r1_rev_15m`) |

## What worked

- Validation-gates funnel correctly intercepted 6/8 failure modes
  before Agent 5. First real dogfood of `validation-gates.md` — it
  earned its keep.
- Execution-delay audit passed (shift = -(1+k) invariant verified).
- Look-ahead audit passed (no future-bar references in any signal).

## What did not work

- Agent 2's primary horizon of 5 minutes was wrong for this window and
  data. IC is meaningfully positive at k=1m and k=15m but flips sign
  at k=5m. This is a crypto microstructure pattern that would not be
  discovered without multi-horizon IC analysis.
- All 8 signals are too weak to survive 5 bps/side cost at minute-level
  rebalance. Gross mean bp per bar is 0.01-0.04 vs cost burden 50+ bps/h.

## Next steps (if user approves Round 2)

1. Re-center on k=15m primary horizon
2. Add 15-bar minimum hold constraint to strategy (not just signal)
3. Test longer reversal windows (15m, 30m, 45m, 60m)
4. Sensitivity chart: net Sharpe at cost ∈ {2, 5, 8, 10} bps/side
5. Optional: add funding-rate data from OKX for a second mechanism

## Files

```
logs/20260423_btc_minute_reversal_v1/
├── inputs/
│   ├── btc_1m.parquet              86,380 bars, 3.7 MB
│   ├── objective.md
│   └── fetch.log
├── scripts/
│   ├── 01_fetch_btc_minute.py      Coinbase REST fetch, 288 chunks
│   └── 02_build_and_backtest.py    Agent 4 with 4-gate funnel
├── outputs/
│   ├── research_brief.md           Agent 1
│   ├── session_metadata.yml        Agent 2
│   ├── expressions_batch_0001.md   Agent 3
│   ├── backtest_results_batch_0001.md   Agent 4
│   ├── ic_table_batch_0001.csv
│   ├── decile_summary_batch_0001.csv
│   ├── ls_summary_batch_0001.csv
│   ├── validation_gates_batch_0001.json
│   ├── alpha_ranking.md            Agent 5
│   └── final_summary.md            (this file)
├── working/
│   ├── handoff_1_to_2.json
│   ├── handoff_2_to_3.json
│   ├── handoff_3_to_4.json
│   └── handoff_4_to_5.json
├── round_0001.yml
└── run_state.json
```
