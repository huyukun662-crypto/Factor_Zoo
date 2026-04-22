# Follow-on #1 — Is the dispersion gate family-agnostic?

**Session:** `20260422_trend_technical_alpha` (follow-on out of main research loop)
**Scripts:** `scripts/09_followup_disp_gate_lottery_alpha17.py`, `scripts/10_followup_inverse_disp_gate_lottery.py`
**Date:** 2026-04-22

## Motivation

α_35 (dispersion-gated 12-3 idio momentum) passed PROMOTE by adding a
Stivers-Sun (2010 RFS) dispersion-regime overlay to a 12-3 momentum signal
that was previously stuck at worst-year 0.04 (failing the 0.5 floor).

The natural cross-family question: is this gate **a general regime
overlay** that works across factor families? If yes, we could apply it
to lottery α_17 from the prior session (stuck at worst-year -0.27 in 2020)
and rescue it the same way.

## Target factor

α_17 from `logs/20260421_volprice_max_lottery/outputs/panel_round3.parquet`:
- Definition: σ-bucket rank of α_08 (σ-decoupled MAX / idio lottery)
- Ungated performance (monthly, 5 bps/side, industry-neutral):
  - LS full Sharpe **1.68**, test **1.72**, Q5 test **1.03**
  - Max DD **−9.5 %**
  - Worst year **−0.27** in 2020 (the A-share megacap-rally year, which
    destroys lottery-like small-caps)

## Two gate variants tested

1. **Momentum-style gate** (same as α_35): `gate = 1 if disp > 252d median`
2. **Inverse gate** (lottery hypothesis): `gate = 1 if disp < 252d median`

Hypothesis for variant 2: lottery premium is concentrated in *compressed*
cross-sectional dispersion regimes, where speculative capital clusters
in small-cap / MAX-like stocks (Bali-Cakici-Whitelaw 2011 intuition).

## Results

| metric | UNGATED | MOM-GATE | INV-GATE |
|---|---:|---:|---:|
| LS full Sharpe | 1.68 | 0.72 | **1.32** |
| LS test Sharpe | 1.72 | 1.04 | **1.76** |
| Q5 full IR | **1.16** | 0.51 | 0.95 |
| Q5 test IR | 1.03 | 0.46 | **1.96** |
| LS Max DD | −9.5 % | −7.6 % | **−4.4 %** |
| Worst-year LS | −0.27 | −0.08 | −0.47 |
| Worst-year Q5 | −0.28 | 0.00 | −1.01 |
| Gate on-frac | 1.00 | 0.46 | 0.45 |

### Per-year LS Sharpe

| year | UNGATED | MOM-GATE | INV-GATE |
|---:|---:|---:|---:|
| 2018 | 3.63 | 0.00 (cash) | 1.72 |
| 2019 | 1.21 | 0.92 | 0.70 |
| **2020** | **−0.27** | −0.08 | **−0.47** |
| 2021 | 1.63 | 1.03 | 1.02 |
| 2022 | 6.03 | 1.80 | 3.47 |
| 2023 | 1.88 | 1.18 | 1.23 |
| 2024 | 1.58 | 0.99 | 1.95 |

## Interpretation

**The dispersion gate is NOT family-agnostic.**

1. **Momentum-style gate on α_17 destroys the signal.** Full Sharpe halves
   (1.68 → 0.72), Q5 test IR halves (1.03 → 0.46), and worst-year barely
   improves (−0.27 → −0.08, still fails 0.5 floor). The gate turns α_17
   off in exactly the low-dispersion periods where lottery premium
   accrues — backwards.

2. **Inverse gate rescues several metrics but not worst-year.**
   - Max DD cut from −9.5 % to **−4.4 %** (better than α_35's own gate)
   - Q5 test IR nearly doubles (1.03 → **1.96**) — a very strong
     long-only signal when gated on compressed-dispersion regimes
   - LS test Sharpe improves (1.72 → **1.76**)
   - But worst-year LS worsens (−0.27 → −0.47) — **2020 remains the
     structural killer regardless of dispersion conditioning**

3. **2020 A-share megacap rally is invariant to dispersion regime.**
   2020 had both high-dispersion months (mom-gate on, some wins) and
   low-dispersion months (inv-gate on, losses concentrated). Lottery
   premium in 2020 was dead *throughout* the year, not in any particular
   dispersion regime. This is structural to the 2020 tape, not a
   regime-filter failure.

## Takeaway

- **α_35's dispersion gate is specifically a momentum-regime gate.**
  Its effectiveness stems from the Stivers-Sun 2010 mechanism (dispersion
  proxies momentum opportunity set). It does not generalize.

- **Lottery α_17 may still have a deployable form** as INV-GATE + Q5
  long-only: Q5 test IR 1.96, Max DD −4.4 %. But strict worst-year audit
  still fails (Q5 worst-year −1.01 in 2020). Would need a *different*
  regime overlay — e.g., small-cap-vs-large-cap relative strength,
  or a direct bull-market (market cap index return above MA200) filter
  targeted at 2020's tape.

- **Cross-family universal regime overlays don't exist** in this dataset.
  Each factor family has its own favorable regime, and the right gate
  needs to be derived from that family's economic story. Stivers-Sun is
  for momentum; Bali-Cakici-Whitelaw lottery premium has a different
  regime signature.

## Disposition

- **α_35 (trend session PROMOTE) stands.** Gate is correctly tied to its
  own mechanism.
- **α_17 (lottery session RESEARCH-ONLY) stays RESEARCH-ONLY.** The
  follow-on does not unlock deployment. A dedicated lottery-regime
  overlay session would be needed (not queued — cost/benefit unclear).
- **`factors/` catalog unchanged.** No new deployment.

## References

- Stivers, C. T., & Sun, L. (2010). Cross-sectional return dispersions
  and time variation in value and momentum premiums. *JFQA* 45(4):
  987-1014. *(Gate mechanism, momentum-specific.)*
- Bali, T. G., Cakici, N., & Whitelaw, R. F. (2011). Maxing out: Stocks
  as lotteries and the cross-section of expected returns. *JFE* 99(2):
  427-446. *(Lottery premium definition; compressed-dispersion regime
  intuition.)*
- Liu, J., Stambaugh, R. F., & Yuan, Y. (2019). Size and value in China.
  *JFE* 134(1): 48-69. *(A-share 2020 megacap rally backdrop.)*
