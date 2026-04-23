# Research Brief — A-Share ETF Dip-Buy / Reversal v1

**Agent 1: Research Librarian**
**Session:** `20260423_a_share_etf_reversal_v1`
**Date:** 2026-04-23

---

## 1. The thesis in one paragraph

Short-term reversal (1-2 week horizon) is one of the most widely replicated
return anomalies on equities; it is weaker on broad indices (most
idiosyncratic noise diversified away) and stronger on narrower baskets
(single stocks or industry/thematic ETFs). On A-shares the literature
documents a large short-horizon reversal in single stocks (Pan–Tang–Xu
2016; Guo–Kong–Shi 2018) but much of it is eaten by 10 bps/side round-trip
cost plus stamp duty. ETFs sidestep stamp duty, cut bid-ask to 1-2 bps on
the top names, and let a factor trade the cross-section of 20 liquid
baskets rather than 5,000 noisy stocks. This session asks whether a
rank-based reversal / dip-buy signal on a 20-ETF universe at weekly or
monthly rebalance clears the 0.5 net-Sharpe floor at 5 bps/side.

## 2. Literature grounding (short)

### Core reversal findings

- **Lehmann (1990) "Fads, martingales and market efficiency"** — weekly
  reversal on NYSE stocks, before-cost Sharpe ~0.9 at 1-week hold.
  Post-cost survivable only on liquid large caps.
- **Jegadeesh (1990) "Evidence of predictable behavior of security
  returns"** — 1-month reversal, −0.025 monthly alpha per unit std of
  past-month return.
- **Nagel (2012) "Evaporating liquidity"** — short-term reversal is a
  **compensation for liquidity provision**. On days of high market
  volatility the reversal premium spikes. Implication: reversal signal
  is stronger in stressed regimes; equal-weight combinations with a vol
  signal are natural.
- **De Bondt & Thaler (1985)** — long-horizon (3-5 year) reversal.
  Different mechanism (overreaction correction); not what this session
  targets.

### A-share specifics

- **Pan, Tang, Xu (2016)** — large short-horizon reversal on A-share
  stocks; in-sample Sharpe > 2, but 5-10 bps round-trip cost cuts Sharpe
  by ~60%.
- **Guo, Kong, Shi (2018)** — monthly reversal on A-share small caps
  strongest; large caps have weaker reversal but higher liquidity
  (exactly the ETF story).
- **Empirical observation from `logs/20260421_volprice_max_lottery/`** —
  on single A-share stocks, once volatility and 20d reversal are
  residualized out, MAX / skewness / jump-count residuals have IC < 0.02.
  The baseline reversal itself (pre-residualization) is the big signal.

### ETF-specific reversal

- **Madhavan, Sobczyk (2016) "Price dynamics and liquidity of ETFs"** —
  index ETFs show intraday mean reversion around NAV but weak day-to-day
  reversal. Sector ETFs show stronger multi-day reversal.
- **Barberis, Shleifer (2003)** — noise traders cluster in thematic /
  industry ETFs, which creates the reversal opportunity.
- **China ETF market observation (2020-2025)** — thematic ETFs (芯片,
  军工, 新能源车) had 40-60% annualized volatility vs 18-25% for broad
  indices; if the reversal mechanism is vol-proportional, thematic ETFs
  should carry most of the factor payoff.

## 3. Why this might work on A-share ETFs specifically

1. **No stamp duty** — single-stock A-share round-trip cost is 5-10 bps
   baseline stamp + 3-5 bps commission + 5-15 bps impact. ETFs remove
   the stamp duty floor, dropping cost to ~4-8 bps round-trip.
2. **High noise-trader concentration in thematic ETFs** — retail flows
   into 芯片 / 新能源车 / 军工 are well-documented sources of momentum
   that later reverses.
3. **Large-enough universe for cross-sectional ranking** — 20 ETFs is
   thin for quintiles but adequate for quartiles or threshold strategies.
4. **Daily data is high-quality and widely adjusted** — survivorship
   bias is near zero (only 2 delistings in the target universe since
   2020), splits are cleanly handled by Yahoo's adjusted close.

## 4. Why this might NOT work (preregistered concerns)

1. **The 20-ETF cross-section is too thin for traditional Q5 Sharpe
   stability.** The 20260421 MAX-lottery session confirmed that ~30 names
   is the floor for Q5 noise to be tolerable. Here Q5 = 4 names; a
   single ETF can drive the Q5 return. Workaround: threshold strategy
   (long if signal ≥ 60th pct, short if ≤ 40th pct) OR long-only top-3.
2. **2020 was an index momentum year.** If reversal is the mechanism and
   2020 was momentum-dominated, worst-year Sharpe may fail. Mitigation:
   per-year breakdown required in Agent 4 output.
3. **Transaction costs on less-liquid thematic ETFs may be worse than
   5 bps/side.** 512980 传媒 has daily volume 10x smaller than 510300
   沪深300; 5 bps/side may understate impact on the thematic names.
   Mitigation: report cost curve {2, 5, 8} and liquidity-weighted
   alternative.
4. **Regime break around 2024-Q3 small-cap rally and 2025 tariffs**
   could generate worst-year destruction similar to the Asset Growth
   session. Mitigation: TVT split (train 2020-2022, validate 2023-2024,
   test 2025-2026) plus worst-year floor.
5. **Reversal on ETFs may be too correlated to a universe-EW return.**
   If all 20 ETFs rally together then reversal just picks the laggard,
   which is very close to a short-beta factor. Mitigation: G4 correlation
   check against universe EW.

## 5. Handoff to Agent 2 — what Agent 2 should lock in metadata

- **Primary horizon k_min = 10 trading days** (2 weeks). Test grid
  {5, 10, 20}.
- **Rebalance cadence**: weekly (every Wednesday) as primary; monthly
  (last trading day) as robustness check.
- **Cost**: 5 bps/side baseline; curve {2, 5, 8}.
- **Universe**: 20 ETFs named above. Because |universe| = 20, use
  **threshold strategy** (top-4 long, bottom-4 short, long-only top-3
  as aux) rather than Q5/Q1.
- **Neutralization**: hour-of-day not applicable; use universe-EW demean
  (zero-sum across the 20 ETFs per day) as the base neutralization to
  avoid factor picking up market beta.
- **Hard floors already set in `inputs/objective.md`.**

## 6. References consulted (external, not opened in this session)

- Lehmann (1990) QJE vol 105, pp.1-28
- Jegadeesh (1990) J. Finance vol 45, pp.881-898
- Nagel (2012) RFS vol 25, pp.2005-2039
- De Bondt, Thaler (1985) J. Finance vol 40, pp.793-805
- Pan, Tang, Xu (2016) J. Banking & Finance vol 66, pp.47-59
- Guo, Kong, Shi (2018) Pacific-Basin Finance J. vol 51, pp.61-78
- Madhavan, Sobczyk (2016) J. Investment Management vol 14, pp.86-102

## 7. Handoff file

See `working/handoff_1_to_2.json` for structured fields.
