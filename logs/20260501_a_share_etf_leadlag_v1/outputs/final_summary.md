# Final Summary — LeadLag Spillover v1

Session: `20260501_a_share_etf_leadlag_v1`
Branch: `claude/build-etf-factor-model-O6yXK`
Status: **STOP** — cost-unviable; better signal lives at k=0 (intra-day, out of scope).

## Headline finding

The broad-ETF lead-lag hypothesis is **partially confirmed but not
deployable** at daily-bar granularity in A-share. The single-leader
510300-only spillover variant has IC t-stat = +2.09 at k=1 (positive,
mechanism-consistent), but:

- All 8 expressions have **negative net Sharpe @ 5 bps/side** (best
  is -0.49 for g2). Daily rebalance with rank-based factors generates
  12,000-18,000% annualized turnover, vastly above the 1500% ceiling.
- Contemporaneous IC@k=0 is **strongly negative** (|t| ≈ 3-4) for
  most variants. The cross-section *overreacts* to the leader's t-1
  move on day t and then partially reverts on t+1. The +2.09 t-stat
  at k=1 is the residual unfinished diffusion, but it's small relative
  to the contemporaneous overreaction.

## Where the signal actually lives

The k=0 IC@-4.10 pattern points to a cleaner deployable signal:
**contrarian intraday entry**. ETFs that have been bid up most
strongly in response to yesterday's broad-market move tend to revert
intraday today. Capturing this requires intraday data and a short-term
mean-reversion harness, which is out of scope for the daily-bar
workflow used here.

## Process notes

- **G5 PASSES** for the first time on the ETF Factor Zoo branch — 7
  of 8 expressions peak IC at the declared primary horizon (k=1).
  The Round 1 hypothesis horizon was correct.
- **G3 fails uniformly on net-Sharpe-at-cost** — Pitfall 10 (cost
  wipes the signal) is the dominant failure mode for daily-rebalance
  ranks on a thin 30-ETF cross-section.

## Audits

| Audit | Result | Notes |
|---|---|---|
| Execution-delay (target_shift = -2 for k=1, delay=1) | PASS | |
| Look-ahead (permute leader 510300 last-30d, check past values) | PASS | max diff = 0.0 |
| Worst-year floor (≥ 0.5) | FAIL | every expression has ≥ 1 negative year |
| Best-year-out (≥ 50% headline) | N/A | headline near zero for most |
| Falsification-first | PASS | pre-run guess "cost wall is the binding constraint"; confirmed |
| Contemporaneous IC@k=0 check | RED FLAG | |t| ≈ 3-4 negative, dominates k=1 by 2x |

## Recommendation

1. STOP this session.
2. Open thread `20260502_a_share_etf_intraday_overreaction_v1`
   (out of scope for this branch — requires intraday data) that
   tests the contemporaneous-overreaction signal as a contrarian
   intraday execution overlay rather than as a daily cross-sectional
   factor.
3. Mark the LeadLag mechanism as **closed** for daily-bar A-share
   ETF research. Lead-lag works on stock-level cross-sections (Hou
   2007, Cohen-Frazzini 2008) but NOT at the ETF basket level
   because each ETF is itself a noisy aggregator that absorbs the
   diffusion process intra-bar.

## Cross-session note

Sibling session `20260501_a_share_etf_ivol_reversal_v1` ran in parallel
on this branch with a different mechanism (IVOL family). Both reach
RESEARCH-ONLY / STOP verdicts but for different reasons: IVOL fails
on directional sign (anomaly inverted in A-share ETFs), LeadLag fails
on cost (turnover ceiling). The two findings are independently
informative about A-share ETF cross-sections:

- **A-share ETFs are narrative buckets** (IVOL inversion → high-vol
  thematic ETFs ARE the marginally-bid lottery tickets).
- **Daily-bar lead-lag at the ETF level is contaminated by intraday
  overreaction-revert** — the cleaner signal is a contrarian intraday
  one, not a cross-sectional daily one.

Both findings should inform any subsequent A-share ETF factor design.
