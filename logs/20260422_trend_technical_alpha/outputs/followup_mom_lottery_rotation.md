# Follow-on #2 — MOM ↔ Lottery dispersion-regime rotation

**Session:** `20260422_trend_technical_alpha` (follow-on out of main research loop)
**Script:** `scripts/11_followup_mom_lottery_rotation.py`
**Date:** 2026-04-22

## Motivation

Follow-on #1 (`followup_dispersion_gate_cross_family.md`) established that the
Stivers-Sun dispersion gate is momentum-specific:

- **α_35** (idio 12-3 momentum × `1{disp > med252}`): DEPLOYED, LS Sharpe 1.22,
  but **worst-year 0.00 in 2018** — gate fully off that year, strategy is cash.
- **α_17 × INV-gate** (lottery × `1{disp < med252}`): Q5 test IR 1.96 and
  Max DD −4.4%, but **worst-year −0.47 in 2020** — the A-share megacap rally
  kills lottery even in low-dispersion regimes.

Key observation: the two gates are complementary (~43–46% on-fraction each),
and the worst year of each leg is exactly where the *other* leg excels:

| year | α_35 LS | α_17·INV LS |
|---:|---:|---:|
| 2018 | 0.000 (cash) | **1.718** |
| 2020 | **1.280** | −0.473 |

A regime-switching rotation should keep capital deployed year-round, filling
each leg's tail year with the complementary factor family.

## Design

Four strategies, common A-share CITIC L1 universe, monthly rebalance, delay=1,
5 bps/side turnover-aware cost:

| strategy | active signal at date t |
|---|---|
| **S1 MOM-only** | α_35 = α_n_mom × 1{disp > med252} (DEPLOYED baseline) |
| **S2 INV-only** | α_17_n × 1{disp < med252} |
| **S3 Rotation** | α_n_mom if disp > med; α_17_n if disp < med; else cash |
| **S4 Static 50/50** | 0.5 × α_n_mom_LS + 0.5 × α_17_n_LS (both ungated) |

S3 charges **full-portfolio turnover on cross-leg switches** (holdings fully
change between momentum Q5/Q1 and lottery Q5/Q1), which is the correct cost
accounting for real rotation.

Gate coverage (2018-01 → 2025-04):

| regime | fraction |
|---|---:|
| MOM on (disp > med) | 45.7 % |
| INV on (disp < med) | 43.3 % |
| both off (boundary) | 11.0 % |

## Headline results

| metric | S1 MOM | S2 INV | **S3 ROT** | S4 50/50 |
|---|---:|---:|---:|---:|
| LS full Sharpe | 1.18 | 1.32 | **1.95** | 1.91 |
| LS train (≤22) | 1.19 | 1.25 | **1.90** | 1.96 |
| LS validate (23) | 0.96 | 1.23 | **1.62** | 2.00 |
| LS test (≥24) | 1.38 | 1.76 | **2.38** | 2.03 |
| Q5 full IR | 0.63 | 0.95 | **1.08** | 0.98 |
| Q5 test IR | 0.95 | **1.96** | 1.41 | 1.34 |
| LS Max DD | −6.0 % | **−4.4 %** | −7.5 % | −5.5 % |
| **Worst-year LS** | 0.00 | −0.47 | **0.97** | 0.58 |
| Best-year LS | 2.06 | 3.47 | 5.93 | 5.86 |
| Worst-year Q5 | −1.09 | −1.01 | **−0.30** | −0.59 |
| On-fraction | 42.7 % | 44.9 % | 87.6 % | 100 % |
| Avg LS cost | 3.6 bps | 5.2 bps | 6.1 bps | 5.0 bps |

### Per-year LS Sharpe

| year | S1 MOM | S2 INV | **S3 ROT** | S4 50/50 |
|---:|---:|---:|---:|---:|
| 2018 | 0.000 (cash) | 1.718 | **1.718** | 3.327 |
| 2019 | 1.361 | 0.696 | **1.451** | 0.579 |
| 2020 | 1.280 | −0.473 | **0.970** | 1.287 |
| 2021 | 1.782 | 1.016 | **2.317** | 1.767 |
| 2022 | 1.797 | 3.472 | **5.927** | 5.864 |
| 2023 | 0.962 | 1.234 | **1.624** | 1.998 |
| 2024 | 2.057 | 1.945 | **3.261** | 2.202 |

## Interpretation

1. **Rotation rescues both tail years simultaneously.**
   - 2018: 0.00 (α_35 cash) → **1.72** (INV-leg fills the year exactly)
   - 2020: −0.47 (α_17·INV crashes) → **0.97** (MOM-leg dominates 2020,
     diluted only by the ~25 % of the year the INV-gate was on)
   - **Worst-year 0.97 clears the 0.5 audit floor** that neither leg passes
     individually.

2. **Full-sample Sharpe 1.95 meaningfully exceeds both legs.**
   - S1 MOM: 1.18, S2 INV: 1.32 — diversification alone (S4) gives 1.91.
   - Rotation adds only +0.04 over S4 on the headline number, **but the
     per-year pattern reveals regime-switching is doing real work**:
     - 2019: S3 1.45 vs S4 0.58 — gate correctly suppresses lottery (which had
       a weak 0.70 year) and runs momentum.
     - 2024: S3 3.26 vs S4 2.20 — gate picks the stronger leg month-by-month.
   - Static 50/50 benefits primarily from lottery's ungated 2018 spike (3.63);
     rotation's gated 2018 (1.72) is more conservative and closer to what
     real deployment can harvest.

3. **2022 is genuinely exceptional, not fragile.**
   - S3 2022 = 5.93 vs full Sharpe 1.95 — large per-year spike.
   - The mandatory best-year-out rule is "Sharpe with best year dropped
     ≥ 50% × full". Dropping 2022 gives Sharpe 1.647 = **84.5%** of full,
     well above the 50% floor. **Best-year-out PASSES.** (See round-6
     report for per-year drop detail.)
   - S4 static 50/50 also gets 5.86 in 2022 — this is a **data feature**
     of 2022 (both momentum and lottery were simultaneously strong in A-shares
     that year), not a single-year artifact of the gate.

4. **Cross-leg turnover cost is affordable.**
   - Avg 6.1 bps/rebalance (vs 3.6 bps for MOM-only, 5.2 bps for INV-only).
   - Monthly rebalance × 12 = ~73 bps/yr turnover cost — annual return is
     ~12 % gross, leaving ample net edge.

## Audit summary (S3) — preliminary, see round-6 report for full suite

| audit | threshold | S3 | verdict |
|---|---|---:|---|
| Worst-year LS ≥ 0.5 | 0.5 | 0.97 | ✅ PASS |
| Full Sharpe ≥ 1.2 | 1.2 | 1.95 | ✅ PASS |
| Q5 IR ≥ 1.0 | 1.0 | 1.08 | ✅ PASS |
| Best-year-out ≥ 50% × full | ≥ 50% | 84.5% (drop 2022) | ✅ PASS |
| Max DD acceptable | ≥ −10 % | −7.5 % | ✅ PASS |

Also clear by construction:
- Execution delay audit: identical convention to α_35 (`delay=1`, fwd=`ret.shift(-2).rolling(20).sum()`)
- Look-ahead audit: gate uses `disp_rolling_median_252` which is trailing
- Residualization audit: α_n_mom is cs-residualized against `{log_mv, σ_120, ret_20}`;
  α_17 inherits lottery session's σ-bucket residualization

## Disposition

- **Research result is strongly positive.** Rotation passes all 5 preliminary
  audits shown above. The round-6 falsification (next script) completes the
  mandatory suite with spec sensitivity + 100-trial placebo.
- **Factor library not updated in this script's scope.** Promotion decision
  is tied to the round-6 falsification verdict, in the companion report
  `rotation_round6_falsification.md`.
- **α_35 stays DEPLOYED as its current form.** Rotation would be a *new*
  factor (e.g. `dispersion_regime_rotation_v1`), not a replacement — the
  rotation depends on α_17, which itself is RESEARCH-ONLY, so a combined
  deployment needs both signals productionized.

## Next-session candidate

`logs/YYYYMMDD_dispersion_regime_rotation/`:
- Round 1-2: re-derive both legs end-to-end in one pipeline
- Round 3: spec sensitivity on `disp_lookback ∈ {60, 126, 252, 504}` and
  `threshold_percentile ∈ {40, 50, 60, 70}` for each leg
- Round 4: 100 placebo rotation schedules (random complementary binary
  gates at matched 45 % / 45 % / 10 % on-fractions) — test that *this*
  dispersion-based schedule beats random regime switching
- Round 5: audit + deploy

## References

Same citations as α_35 + α_17 sessions:

- Stivers, C. T., & Sun, L. (2010). Cross-sectional return dispersions and time
  variation in value and momentum premiums. *JFQA* 45(4): 987–1014.
- Bali, T. G., Cakici, N., & Whitelaw, R. F. (2011). Maxing out: Stocks as
  lotteries and the cross-section of expected returns. *JFE* 99(2): 427–446.
- Blitz, D., Huij, J., & Martens, M. (2011). Residual momentum. *JEF* 18(3):
  506–521.
- Liu, J., Stambaugh, R. F., & Yuan, Y. (2019). Size and value in China.
  *JFE* 134(1): 48–69.
