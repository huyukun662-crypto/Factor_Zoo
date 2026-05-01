# Research Brief — A-Share ETF IVOL-Reversal v1

Owner: Agent 1 (Research Librarian).
Generated: 2026-05-01.

## 1. Problem framing

A-share thematic ETFs trade on narrative-driven flows (新能源车 / 半导体 /
医药 / 军工). Even after stripping market beta, residual returns carry
substantial idiosyncratic volatility. The question is whether
*cross-sectional rank of that idiosyncratic volatility* is a
return predictor at the 5-day (weekly) horizon.

The Ang–Hodrick–Xing–Zhang (AHXZ) IVOL anomaly is one of the most
replicated equity puzzles: high-IVOL stocks underperform on average.
The mechanism is debated (lottery preference of retail investors,
arbitrage limits, mispricing of skewness) but the empirical fact is
robust to neutralization choice and country.

## 2. Mechanisms

### 2.1 Primary mechanism — IVOL as cross-sectional return predictor (negative)

For each ETF i and each date t:
1. Run a 60-day rolling univariate OLS: `r_i = a + β_i × r_M + ε_i`
   where `r_M` is the broad-market return (510300).
2. Compute `IVOL_i_t = std(ε_i over the past 20d)`.
3. Cross-sectionally rank by `-IVOL_i_t` (high IVOL → low rank = short).
4. Long bottom-quintile (low IVOL), short top-quintile (high IVOL).

Expected sign: **positive long-short return** (low-IVOL > high-IVOL).

### 2.2 Variants worth testing

- **Total volatility** (no residualization) — to check if the IVOL
  decomposition matters or if raw vol works.
- **Residual-amplitude** instead of std (mean absolute residual).
- **Window**: 10d (weekly), 20d (monthly), 40d (two-monthly).
- **Lag**: t (most recent) vs t-5 (lagged) — does the signal decay
  monotonically?
- **Vol-of-vol**: IVOL itself ranked by its 20d trend — accelerating
  vol may be more predictive than absolute level.

## 3. Operator and dataset suggestions

### Data
- Daily OHLCV from Yahoo Finance v8 chart endpoint.
- Universe: 30 A-share ETFs (broad index 8 + thematic 21 + commodity 1)
  after dropping 4 truncated tickers (512100, 515050, 515170, 512800
  with only 137 bars from 2025-10).
- Window: 2019-01-02 → 2026-04-30 (~7 years).
- Benchmark: 510300.SS for beta residualization.

### Operators
- Rolling regression: `pd.DataFrame.rolling(60).cov(r_M) /
  rolling(60).var(r_M)`.
- Residual: `r_i - β_i × r_M`.
- IVOL: `residual.rolling(20).std() * sqrt(252)`.
- Cross-sectional rank: `df.groupby('date')['signal'].rank(pct=True)`.
- Quintile membership: `pd.qcut(rank, 5, labels=False)`.

### Neutralization
- ETFs already aggregate stocks → no industry neutralization needed at
  the ETF level. The cross-section IS the industries.
- Vol-target neutralization considered; rank-based factors get a free
  pass (rank already vol-equalizes).

## 4. Prior-art anchors

- Ang, Hodrick, Xing, Zhang (2006) — "The Cross-Section of Volatility
  and Expected Returns", JF: high IVOL → low future return on US stocks.
- Ang, Hodrick, Xing, Zhang (2009) — international replication.
- Bali, Cakici, Whitelaw (2011) MAX — companion lottery anomaly.
- Han, Lesmond (2011) — IVOL liquidity-bias correction.
- Cao, Han (2016) — IVOL × arbitrage limits (more relevant for ETFs).

For A-share specifically:
- Liu, Shu, Wei (2017, JFE) — confirms IVOL anomaly on Shanghai/Shenzhen
  individual stocks; weaker but present at portfolio level.
- No prior study on A-share *ETF* IVOL specifically — this is the new
  contribution.

## 5. Risks and caveats

### 5.1 ETF universe is small (30 names)
- Q5 size = ceil(30 × 0.2) = 6. The G3 floor of 30 stocks/quintile is
  written for stock universes, not ETFs. We adopt **Q5 ≥ 6 ETFs** as
  the ETF-adapted floor (consistent with the prior ETF sessions).

### 5.2 Beta instability
- 60-day rolling beta is the standard but is noisy on short series and
  during regime breaks (e.g., 2020 COVID, 2022 deleveraging).
- Sensitivity test: rerun with 90-day beta to confirm.

### 5.3 The 4-bar / NA problem
- 5 ETFs start mid-window (159755 from 2021-06, 159890 from 2021-03,
  etc.). Cross-section size grows from ~20 in 2019 to 30 in 2022+.
- Mitigation: enforce ≥ 25 valid signals per day; drop earlier dates
  if needed. Report coverage explicitly.

### 5.4 Cost realism
- Weekly rebalance, 5 bps/side. Annual turnover budget ≤ 600%.
- For a 30-ETF universe with quintile membership, full-rotation
  turnover ≈ 200%/yr — comfortable margin.

### 5.5 Bull-market short-leg risk (Pitfall 7)
- The IVOL short leg holds *high-IVOL* ETFs. In a pure-narrative bull
  year (e.g., 2020 半导体 / 新能源车), high-IVOL CAN be the winners.
- This is the single largest risk to the worst-year floor.
- Mitigation: report long-only Q5 excess separately; if LS fails the
  worst-year floor but long-only excess is positive, flag as deployable
  long-only.

### 5.6 Lookahead in the residual computation
- Beta computed from `r_i, r_M` at dates ≤ t.
- IVOL computed from residuals at dates ≤ t.
- Signal observed at close(t), executed at close(t+1) — delay=1.
- The execution-delay-audit must verify `target_shift == -(1 + delay)`.

## 6. Key references in this repo

- `worldquant-5-agent-workflow/references/validation-gates.md` — G1–G5
  funnel.
- `worldquant-5-agent-workflow/references/tvt-split-template.md` —
  Train/Validate/Test methodology, 0.3-stability-penalty selection.
- `worldquant-5-agent-workflow/references/execution-delay-audit.md` —
  mandatory pre-submission audit.
- `worldquant-5-agent-workflow/references/common-pitfalls.md` Pitfall 7
  — bull-market short-leg destruction.
- `logs/20260423_a_share_etf_reversal_v1/outputs/final_summary.md` —
  worst-year-2020 failure case study (don't repeat).

## 7. Next-stage handoff

Agent 2 must:
- Pick ONE primary horizon (recommend k=5 weekly).
- Pick ONE residualization choice for the headline (recommend
  60d-rolling-beta IVOL, 20d window).
- State the worst-year floor in `session_metadata.yml` explicitly.
- Pre-commit to long-only Q5 excess as the deployable metric (bull-market
  short-leg insurance).
