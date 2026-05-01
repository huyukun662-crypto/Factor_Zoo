# Research Brief — A-Share ETF Broad-Market Lead-Lag Spillover v1

Owner: Agent 1 (Research Librarian).
Generated: 2026-05-01.

## 1. Problem framing

A-share retail flow concentrates in broad-index ETFs (沪深300 / 中证500 /
中证1000), which absorb information first. Thematic ETFs typically react
with a 1-2 day lag because (a) sector flows follow risk-on/off shifts in
the broad market and (b) thematic ETFs have lower retail attention until
the broad market has moved.

Lo–MacKinlay (1990) and Hou (2007) document the mechanism formally as
slow information diffusion: large/liquid leaders move first, smaller
followers move with a delay. The asymmetry is empirically robust in US
size-sorted portfolios and in international replications.

## 2. Mechanism

### 2.1 Primary signal — beta-projected leader return

For each follower ETF i, leader L (∈ {510300, 510500, 512100}), date t:
1. Compute rolling beta: `β_iL_t = cov(r_i, r_L; 60d) / var(r_L; 60d)`.
2. Compute spillover: `s_iL_t = β_iL_t × r_L_t`.
3. Aggregate over leaders: `signal_i_t = sum_L s_iL_t / 3` (or
   max-beta-weighted, or weighted by leader's own residual).
4. Cross-sectionally rank by signal each day.
5. Long top quintile (highest predicted next-day move),
   short bottom quintile.

Expected sign: **positive** at horizon k=1 (next-day reaction
catches up). Sign should fade by k=3-5 as diffusion completes.

### 2.2 Variants

- **Single-leader**: 510300 only (most-liquid, broadest).
- **Two-step diffusion**: lag {t-1 + t-2} sum.
- **Residualized leader**: leader's own residual to its 20d MA
  (catches surprises, not slow drifts).
- **Vol-scaled**: divide by ETF's own 20d std (size-equalize).
- **Market-orthogonalized**: subtract follower's own contemporaneous
  return → catch the *unexplained* portion of leader move.
- **Sign-only**: `sign(r_L) × |β|` (use direction, ignore magnitude).

## 3. Operator and dataset suggestions

### Data
- Same shared cache as IVOL session: 30 A-share ETFs, 2019-01-02 →
  2026-04-30, daily OHLCV.
- Leaders: 510300 (沪深300, broad cap-weighted),
           510500 (中证500, mid-cap),
           512100 → DROPPED (only 137 bars). Substitute: use 159915
           (创业板) which has full history and represents small-growth
           similarly to 中证1000.
- Effective leaders: {510300.SS, 510500.SS, 159915.SZ}.
- Followers: the remaining 27 ETFs.

### Operators
- Rolling cov/var: `pd.DataFrame.rolling(60).cov() / .var()`.
- Cross-sectional rank: `groupby(date).rank(pct=True)`.
- Quintile cut: `qcut(5)`.

## 4. Prior-art anchors

- Lo, MacKinlay (1990, RFS) — small lags large in size portfolios.
- Hou (2007, JF) — industry lead-lag with explicit information channel.
- Cohen, Frazzini (2008) — economic-link lead-lag.
- Boudoukh et al. (1994) — non-synchronous trading mechanical lead-lag.
- Diether, Lee, Werner (2009) — short-side response asymmetry.

A-share specifics:
- A-share opens at 09:30 Beijing; broad-index ETFs ARB tightly to spot
  index futures; thematic ETFs price-discover from the broad index move.
- Cross-listing of broad ETFs in HK/US night sessions creates evening
  information that re-prices in next-day open — so ETF lead-lag at
  daily horizon is not just intraday.

## 5. Risks and caveats

### 5.1 The cost wall is the binding constraint
- Daily rebalance + 5 bps/side cost ≈ 25 bps/week if we trade quintile
  membership weekly, but daily flips would compound.
- Annual turnover ceiling 1500% — hard floor, not a guideline.
- Before claiming PROMOTE we MUST report net Sharpe at 5 bps explicitly.

### 5.2 Mechanical lead-lag from non-synchronous trading
- Some thematic ETFs are illiquid early in the morning. Using close-to-
  close returns avoids most of this, but the residual mechanical effect
  must be checked by IC at horizon 0 (contemporaneous).
- If IC at k=0 is huge but k=1 is small, the "lead-lag" is just stale
  prices. Ang–Boudoukh adjustment: subtract the contemporaneous IC.

### 5.3 Leader self-trading
- Leaders are also in the cross-section. The signal for a leader vs
  itself is degenerate. Solution: zero out the diagonal so a leader
  never receives its own signal.

### 5.4 Beta sign confusion
- Negative-beta ETFs (gold 518880) flip the spillover sign. The
  mechanism still works (gold goes UP when SHCOMP goes DOWN, with a
  lag), but the sign convention must be consistent. Trust β_iL × r_L
  to handle it correctly — that product already has the right sign.

### 5.5 Win-loser asymmetry in 2020 / 2024
- 2020 had a huge 中证500 / 创业板 lead vs 沪深300 lag (small > large).
- 2024 had the opposite (large > small) under 国家队 buying.
- A 3-leader spillover with equal weights smooths these regimes.

## 6. Key repo references

- `references/validation-gates.md` — G3 net-Sharpe-at-cost is the
  decisive gate for daily rebalance signals.
- `references/common-pitfalls.md` Pitfall 10 — costs wipe the signal.
- `references/execution-delay-audit.md` — daily-rebalance signals are
  highly sensitive to delay convention. `target_shift == -(1+delay)`
  with `delay=1`.

## 7. Next-stage handoff

Agent 2 must:
- Pick primary horizon k=1 (the entire mechanism is short-horizon).
- Pre-commit to net-Sharpe-at-5bps as the headline metric (gross is
  misleading for daily signals).
- State turnover ceiling 1500% / yr.
- Report contemporaneous (k=0) IC alongside k=1 to detect mechanical
  stale-price effect.
