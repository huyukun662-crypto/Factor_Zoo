# Expressions — batch_0003 (Round 3: production-grade engineering)

R2 conclusion: phase-0 numbers were selection-biased; honest
phase-averaged headline of `range_pos_252` is LS 0.24, top-5
long-only excess 0.12. None of the 8 R2 variants survives the
0.5 worst-year floor at any phase, and no variant approaches the
factors/ catalog inclusion threshold of net Sharpe ≥ 1.0.

R3 hypothesis: the mechanism is real but weak on a 32-ETF universe;
the deployable upside is only achievable through proper
phase-rotation ensembling combined with a risk overlay. Eight
variants test combinations of multi-phase ensemble, regime gating,
position sizing, and universe pruning — none of which is
"cherry-picking a phase".

Universe: 32 ETFs (drop 512800.SS, 515170.SS).
k=20 monthly forward, delay=1, rebal=21d, cost=5 bps/side.
**All variants below use 21-phase ensemble** (1/21 capital
deployed each trading day, 21-day holding). Reported metrics are
on the daily-overlap-aggregated portfolio return.

## H1 — F4 phase-averaged top-5 long-only excess (BASELINE)

```
sig_t = (rank_xs(range_pos_60) + rank_xs(range_pos_120) + rank_xs(range_pos_252)) / 3
For each phase p in 0..20:
    every 21 trading days starting at index p, hold equal-weight top-5 by sig
ensemble_return_t = (1/21) * sum over phases of phase_return_t
top5_excess = ensemble_return - equal_weight_universe_return
```

This is the honest deployable form of E3/F4: every day 1/21 of the
book turns over into a fresh top-5 basket sized to 1/21 NAV.

## H2 — H1 with bench MA200 risk-on gate

```
g_t = 1 if close_510300_t > MA200(close_510300)_t else 0
H2_t = g_t * H1_long_return + (1 - g_t) * bench_return_t
H2_excess = H2 - bench
```

When risk-off, the sleeve holds the broad benchmark (no excess but
no negative excess either). Should rescue 2022 specifically.

## H3 — H1 with ETF-level inverse-vol position sizing

```
For each rebalance day, after selecting top-5:
    weight_i = (1/vol_i) / sum_j (1/vol_j)   where vol_i = 60d ann vol of ETF_i
    portfolio_return = sum_i weight_i * fwd_ret_i
```

Down-weights high-vol ETFs (typically thematic that crashed in
2024). Should improve 2024 worst-year.

## H4 — H2 + H3 combined

Both regime gate and inverse-vol sizing applied to H1.

## H5 — H1 on the 20-ETF "core" universe

```
core_universe = 20 ETFs with full 7-year history (drop 14 late-listed)
H5 = H1 restricted to core_universe
```

Removes survivorship-noise from late-listed thematics. Tests
whether the late-listed ETFs are the source of the worst-year
weakness.

## H6 — H1 top-3 (more concentrated)

```
H6 = H1 with n=3 instead of n=5
```

Trade dispersion for higher signal-to-noise on the top end. Risk:
if 2022 worst-year was driven by 1-2 names, H6 makes it worse.

## H7 — H1 portfolio-level vol-target 10 % ann

```
ex_post_vol = rolling_std(H1_daily, 60) * sqrt(252)
H7_t = H1_t * (target_vol=0.10) / max(ex_post_vol, 0.01)
```

Scales the sleeve daily to a target 10 % annualized volatility.
Caps drawdowns in high-vol regimes.

## H8 — H4 + H7 (full risk-managed)

Multi-phase ensemble + regime gate + inverse-vol weighting +
portfolio vol target. The maximally risk-engineered version of
the range-position factor.

---

## What success looks like

For ADMISSION to `factors/price_volume/anchor_range_pos_etf_v1/`:
- Net top-5 long-only excess Sharpe ≥ 1.0 (per factors/README.md
  catalog convention)
- Worst-year ≥ 0 (relaxed from 0.5 since A-share long-only excess
  is the deployable metric per common-pitfalls.md Pitfall 7)
- Phase-rotation robustness already built in by construction
- Test-window Sharpe ≥ 50 % of full-sample
- No look-ahead, exec-delay verified

For ADMITTED-CANDIDATE (per inv_ivol_voltarget_bondrotate_etf_v2
precedent in factors/README.md): net Sharpe ≥ 1.0 + 6/7 years
positive + clean audits, even if formal worst-year floor 0.5 is
missed by < 0.3.

If H1..H8 all fail both bars: close session as RESEARCH-ONLY with
documented ceiling. **Do not run R4+ chasing the headline.**
