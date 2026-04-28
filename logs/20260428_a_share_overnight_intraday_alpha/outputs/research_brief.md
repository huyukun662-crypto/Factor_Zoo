# Research Brief — Overnight–Intraday Return Decomposition (A-share)

**Session:** `20260428_a_share_overnight_intraday_alpha`
**Agent:** 1 — Research Librarian
**Date:** 2026-04-28
**Market:** A-share (主板 + 创业板 + 科创板, ex-ST, ex-suspended, ex-北交所)
**Data window:** 2018-01-02 → 2026-04-28 daily (Tushare `daily` + `adj_factor` + `daily_basic`)

---

## 1. Mechanisms surveyed

| Family | Anchor paper(s) | A-share evidence | Already in repo? | Distinct? |
|---|---|---|---|---|
| Short-term reversal | Jegadeesh 1990; Nagel 2012 | Strong (Cheung 2015) | partially absorbed by lottery | medium |
| Idiosyncratic momentum (12-3) | Blitz-Huij-Martens 2011 | Strong | **yes — `idio_12_3_momentum_disp_gated_v1`** | overlap |
| MAX / lottery demand | Bali-Cakici-Whitelaw 2011 | Strong (Liu-Stambaugh-Yuan 2019 CH-3) | **yes — `lottery_idio_max_q5_overlay_v1`** | overlap |
| Turnover anomaly | Lee-Swaminathan 2000 | Strong (retail-driven) | partial (lottery uses turnover as control) | medium |
| Amihud illiquidity | Amihud 2002 | Weak as alpha (risk premium) | no | distinct |
| **Overnight–intraday decomposition** | **Lou-Polk-Skouras 2019 JFE; Aboody-Even-Tov-Lehavy-Trueman 2018 RFS; Berkman-Koch-Tuttle-Zhang 2012** | **Strong + A-share-specific via T+1 channel** | **no** | **distinct** |
| Frog-in-the-pan / information discreteness | Da-Gurun-Warachka 2014 RFS | Mixed A-share (Han et al 2018) | no | distinct |
| Volume shock reversal | Gervais-Kaniel-Mingelgrin 2001 | Weak A-share | no | medium |

## 2. Mechanism selected: Overnight return as informed-flow proxy

### 2.1 Economic logic

In a market with frictions on intraday participation, **information arrives outside
trading hours** (overnight news, earnings, regulatory announcements, foreign-market
moves) and is impounded at the open. The intraday session, by contrast, is dominated
by liquidity shocks, retail attention, and noise trading. Lou, Polk & Skouras (JFE
2019) and Aboody et al (RFS 2018) decompose daily returns into

```
ret_overnight_t = open_t / (close_{t-1} * adj_factor_t / adj_factor_{t-1}) - 1
ret_intraday_t  = close_t / open_t - 1
```

and show that in the US:

- the overnight component **persists** (positive autocorrelation, alpha)
- the intraday component **reverses** (negative autocorrelation, anti-alpha)
- the long-overnight / short-intraday spread earns Sharpe ≈ 1.0 net of size and value.

### 2.2 Why this is especially clean in A-share

1. **T+1 settlement.** A-share investors who buy today cannot sell before T+1.
   Overnight gap risk is borne *only* by holders, so anyone willing to hold
   overnight is selecting on conviction. This sharpens the
   "overnight = informed" interpretation relative to T+0 markets.
2. **No after-hours or pre-market session.** All overnight information is impounded
   in the *single* opening auction, producing a clean discrete jump rather than a
   gradual fade. Empirical jump magnitudes are larger and signal-to-noise is higher.
3. **Retail-dominated intraday flow.** Retail investors are >80% of A-share
   intraday turnover (Liu-Stambaugh-Yuan 2019). Intraday returns therefore
   carry a strong noise-trader component, which the overnight–intraday
   spread isolates.
4. **±10% daily price limits.** Limit-up days terminate intraday trading early.
   The overnight component then absorbs *the next day's* price discovery —
   another structural reason overnight predicts forward returns.
5. **Orthogonality to existing factors in this repo.**
   - `idio_12_3_momentum_disp_gated_v1` operates on a 252-63 cumulative log return
     (close-to-close); it cannot distinguish overnight from intraday.
   - `lottery_idio_max_q5_overlay_v1` uses the daily |return| extreme; the MAX
     of total return is dominated by intraday noise and is empirically
     *anti-correlated* with overnight persistence.

### 2.3 Direction
**Long high cumulative overnight return; short low.** Sign expected positive on IC.

### 2.4 Variants for the Rule of 8
The mechanism gives a natural family — same primitive (`ret_overnight`), differing
in window, normalization, and attention amplification. See Agent 3
`expressions_batch_0001.md`.

## 3. Pitfall index (mapped to `references/common-pitfalls.md`)

| Pitfall | How it could bite | Mitigation in this session |
|---|---|---|
| Look-ahead via `.shift(-k).where()` | mask future bars into past factor | scripts use only `.shift(+k)` and rolling on past windows |
| Mislabeled execution delay | overstated Sharpe | invariant `target_shift = -(1+delay) = -2` enforced + future-perturbation test |
| Survivorship bias | ex-post universe | use `stock_basic(list_status='L'+'D')` so delisted firms remain |
| Hidden classic-factor exposure | factor is just size or short-term reversal | residualize vs `{log_mv, σ_20, ret_5, ret_20, turnover_20}` and report Δ |
| Industry-noise eating signal | sector-driven | industry-demean per date is mandatory (CLAUDE.md A-share rule) |
| LS ≠ deployable in A-share | no efficient shorting | report Q5 long-only excess metrics in addition to LS |
| Daily turnover cost trap | daily rebal blows up turnover | rebalance monthly (20 trading days); 5 bps/side cost |
| ±10% limit truncation | `pct_chg = ±10` rows are masspoint | winsorize log returns at ±10.5%; cross-checked against `open == high == low` (one-side limit days) |
| Adj-factor mismatch on overnight | naïve `open_t / close_{t-1}` ignores split/dividend | use `(open_t * adj_factor_t) / (close_{t-1} * adj_factor_{t-1}) - 1` |
| Stale prices on illiquid days | `vol == 0` → spurious overnight = 0 | drop rows where `vol == 0` from per-stock factor inputs |

## 4. Data requirements (matches existing cache schema)

| Field | Source | Use |
|---|---|---|
| `open`, `close`, `pre_close` | `pro.daily` | overnight + intraday returns |
| `adj_factor` | `pro.adj_factor` | adjusted return computation |
| `vol`, `amount` | `pro.daily` | turnover proxy, attention weight |
| `total_mv`, `circ_mv`, `turnover_rate_f` | `pro.daily_basic` | size control, official turnover |
| `industry` | `pro.stock_basic` | industry neutralization (CITIC L1 proxy) |
| trade calendar | `pro.trade_cal` | rebalance date selection |

Cache lives at `/home/user/Factor_Zoo/.cache/` (gitignored).

## 5. Deliverable for Agent 2

- **Mechanism:** overnight return as informed-flow proxy
- **Direction:** long high cum-overnight; short low
- **Sign:** positive IC expected
- **Neutralization stack (mandatory):** industry (CITIC L1 proxy), cross-sectional zscore per date
- **Residualization stack (audits):** `log_mv`, `σ_20`, `ret_5` (close-to-close), `ret_20`, `turnover_20`
- **8 variants:** share `ret_overnight` primitive; differ in window {5, 20, 60},
  pure-overnight vs overnight-minus-intraday, vol-scaling, attention weighting, frequency vs magnitude
- **TVT split:** train 2018-2022, validate 2023, test 2024 + 2025 + 2026-YTD
- **Cost model:** turnover-aware, 5 bps one-side
- **Rebalance:** monthly (20 trading days) primary; weekly (5d) variant for robustness
- **Sample bar:** US LPS-2019 reports LS Sharpe 0.8-1.2 net of size; A-share with
  T+1 + retail amplification has prior of 0.7-1.3.

## 6. Key references

- Lou, D., Polk, C., Skouras, S. (2019). "A tug of war: Overnight versus intraday
  expected returns." *Journal of Financial Economics*, 134(1), 192-213.
- Aboody, D., Even-Tov, O., Lehavy, R., Trueman, B. (2018). "Overnight returns and
  firm-specific investor sentiment." *Review of Financial Studies*, 31(11), 4242-4272.
- Berkman, H., Koch, P. D., Tuttle, L., Zhang, Y. J. (2012). "Paying attention:
  Overnight returns and the hidden cost of buying at the open." *Journal of
  Financial and Quantitative Analysis*, 47(4), 715-741.
- Liu, J., Stambaugh, R. F., Yuan, Y. (2019). "Size and value in China." *Journal
  of Financial Economics*, 134(1), 48-69.
- Bali, T. G., Cakici, N., Whitelaw, R. F. (2011). "Maxing out: Stocks as
  lotteries and the cross-section of expected returns." *Journal of Financial
  Economics*, 99(2), 427-446. [contrast — the existing lottery factor]
- Gao, X., Lin, T. C. (2015). "Do individual investors treat trading as a
  fun and exciting gambling activity? Evidence from repeated natural experiments."
  *Review of Financial Studies*, 28(7), 2128-2166. [retail-dominance evidence
  that grounds the intraday-noise interpretation in the A-share context]
