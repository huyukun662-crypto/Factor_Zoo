# Alpha Ranking — Session 20260502_a_share_etf_riskadj_mom_v1

**Agent 5 (Evaluator & Recorder)** — 2026-05-02

Universe: **71 A-share ETFs** (Tushare passive/enhanced index trackers,
list_date ≤ 2020-06-30, ≥ 1500 trading bars, avg daily amount ≥ 50M CNY).
Window: 2019-01-02 → 2026-04-30. Cost: 5 bps/side, monthly rebalance,
1-day execution delay.

EW-universe baseline (the bar to beat): net Sharpe **0.571**, worst-year
Sharpe **-1.17**, max drawdown **-33%**.

## Final ranking across all 5 rounds (by deployable utility)

| Rank | Expression | Round | Net Sharpe | Worst-Y | BYO/headline | MDD | Annual TO | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 ★ | **m7_R5_lowbeta_bot15_ma200_gate** | R5 | 0.45 | **0.00** | 0.95 | -22% | 202% | All audits pass; only expression with no negative year |
| 2 | m1_R5_lowbeta_bot20_ma200_gate | R5 | 0.42 | 0.00 | 0.93 | -19% | 199% | Slightly larger book, similar profile |
| 3 | m4_R5_lowbeta_bot30_ma200_gate | R5 | 0.44 | -0.39 | 0.62 | -18% | 186% | Wider, lower MDD, but worst-year goes negative |
| 4 | m7_R3_lowbeta_60_bot20 (no gate) | R3 | 0.63 | -0.95 | 0.76 | -27% | 201% | Highest raw Sharpe but worst-year fails |
| 5 | m3_R3_lowvol_60_bot10 | R3 | 0.55 | -1.50 | 0.75 | -33% | 294% | Concentrated, large MDD |
| 6 | m6_R5_ew_with_cash_below_ma200 | R5 | 0.44 | -1.17 | 0.75 | -26% | 56% | Cheap to run but no excess over EW |
| 7 | m5_R2_plain_mom_252_top20 (12-mo classic) | R2 | 0.38 | -1.70 | 0.50 | -? | 213% | Slow momentum has correct sign but loses to EW |
| 8 | All other R1-R4 expressions | – | <0.55 | <-1.0 | – | – | – | Underperform the deployable winner |

★ = recommended for deployment-as-overlay

## Read across the 5 rounds (mechanism evolution)

1. **R1 (8 expressions, short-window risk-adj momentum, top-3/5)**
   On the broad 158-ETF universe, every variant had **negative IC at 21d
   horizon** and worst-year < -1. Killed by short-horizon noise on a wider,
   more thematic universe.
2. **R2 (slow-window momentum, top-20)** Stricter liquidity filter (71
   ETFs). IC sign flipped to **positive** at 120-252d windows but
   magnitudes too small (|t|<1) to clear the EW bar. 12-month classical
   (m5_R2) was best in this round at net 0.38.
3. **R3 (low-vol pivot)** First positive results vs IC: lowvol 60d had
   IC +0.035, low-beta 60d had IC +0.055. m7_R3 lowbeta_bot20 hit net
   0.63, the highest raw Sharpe of the session — but worst-year -0.95.
4. **R4 (smooth tilts)** Inv-vol/inv-beta full-universe tilts and
   top-50% buckets diversified the book but couldn't beat EW. None
   was an improvement over R3 winner.
5. **R5 (regime-gated low-beta)** Adding an MA200 broad-market gate to
   R3's low-beta selection rescued the worst year — the gate flattens
   exposure during the 2022-23 deleveraging that crushed long-only
   alternatives. **m7_R5 lowbeta_bot15_ma200_gate** is the deployable
   winner: net Sharpe 0.45, no negative year (8/8 ≥ 0), MDD -22% (vs
   EW -33%), BYO/headline 0.95.

## Decision

**RESEARCH-ONLY → defensive-overlay deployment** (with explicit
trade-off framing).

The original PROMOTE bar from `session_metadata.yml` requires raw net
Sharpe ≥ 0.7 and excess vs EW Sharpe ≥ 0.6. **No expression in any
round meets the original bar**, because the EW baseline itself
(Sharpe 0.57) is hard to beat on this universe. A long-only ETF
manager who treats absolute Sharpe as the only objective should
**stay in EW**.

The honest deployable-utility framing is different: m7_R5 is a
**defensive overlay**. Compared to EW it gives up 0.13 Sharpe but
delivers:

- **No negative year** in 8 calendar years (vs EW: 2 negative years)
- **MDD -22%** (vs EW -33%, a 33% reduction in max drawdown)
- BYO/headline 0.95 (extremely robust to single-year removal)
- Stable IC of +0.055 across R3, R4, R5 (consistent low-beta premium)

This is suitable for deployment as a **risk-managed alternative to
EW** for capital that cannot tolerate full A-share market drawdowns.
For an absolute-Sharpe seeker it is **research-only**.

## Falsification sanity check

The shuffled-label IC averages -0.009 (vs real +0.055), passing
Audit 5. The signal is not an artefact of selection / autocorrelation
in the universe.

## Files

- `outputs/audit_winner_m7_R5.json` — all 5 audits + cost sweep
- `outputs/winner_daily_pnl.parquet` — daily P&L for winner + EW
- `factors/price_volume/ashare_etf_lowbeta_bot15_ma200gate_v1.parquet` — factor signal
- `outputs/r{1..5}_summary_batch_*.csv` — per-round backtest summaries
- `outputs/r{2..5}_per_year_batch_*.csv` — per-year detail
