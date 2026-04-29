# Final summary — A-share DTL institutional-flow (round 1, executed)

## What ran

- Window: 2023-01-03 → 2025-12-31 (727 trading days, 5 384 stocks).
- Universe: A-share, ex-IPO<250d, industry-tagged via `stock_basic.industry`.
- Data: Tushare `top_list` (16 932 events), `top_inst` (558 698 seat-rows),
  `daily`, `adj_factor`, `limit_list_d`. Free-tier endpoints only.
- 8 expressions per `expressions_batch_0001.md`, all delay-1.
- Forward-return invariant: `adj_close.shift(-(1+h)) / adj_close.shift(-1) - 1`.

## Headline result: **all 8 alphas → RESEARCH_ONLY**

No expression cleared the four mandatory floors (worst-year LS ≥ 0.5,
worst-year Q5e ≥ 0.4, best-year-out ≥ 50%, residualized LS ≥ 50% of raw)
on the 2023-2025 sample. Per `SKILL.md` mandatory audit rules, no
PROMOTE recommendation is issued.

## Top 3 by monthly Q5 excess Sharpe (h=10)

| alpha    | ic_mean | ic_t  | ic_ir  | q5e_sr_monthly | ls_sr_monthly | q5_size_mean |
|:---------|--------:|------:|-------:|---------------:|--------------:|-------------:|
| alpha_01 |  -0.005 | -1.40 | -0.053 |          0.352 |         0.250 |          894 |
| alpha_06 |  +0.009 |  2.10 | +0.079 |          0.259 |         0.335 |          245 |
| alpha_02 |  +0.002 |  0.62 | +0.023 |          0.235 |         0.340 |          949 |

## What the data actually says

**Best raw signal** is **alpha_05** (20d institutional net-buy persistence):
IC mean +0.0076, t=3.14, IR=0.118. But residualizing alpha_05 against
{size, mom20, rev5, max10} **flips its LS Sharpe from +0.97 to −0.48**
(residual ratio = −0.50). Per `common-pitfalls.md` Pitfall 9, alpha_05
is a vehicle for classic-factor exposure (a momentum/size mix), not
genuine DTL alpha. Honest label.

**alpha_06** (20d positive-day count) survives residualization (ratio
0.55), but its raw daily-LS Sharpe is consistently negative across all
three years (2023 −9.5, 2024 −6.9, 2025 −7.2). The positive monthly Q5
excess Sharpe (+0.26) comes from a small-cap-tail effect at month-start
(Q5 size ≈ 245), not the institutional information channel we
hypothesized. Mechanism failure.

**alpha_02 / alpha_04** (5d / 10d net-buy ratio): per-year LS swings
are huge (alpha_02: 2023 +0.1, 2024 +4.2, 2025 −2.6). 2024 single year
carried both. Best-year-out collapses to negative. Classic
"two-of-three years" trap that worst-year + best-year-out audits are
designed to catch — and they did.

**alpha_07** (hot-money-only reversal): IC −0.009 with t=−2.6. The
sign is wrong for our hypothesis (we expected reversal → positive IC of
the −1 × signal). The retail-aggressive seat keyword list is partial
and the regime in 2025 was retail-favorable, so the reversal anchor
broke.

## Falsification answer (from session_metadata.yml)

> "If positive Sharpe shows up, the most likely single non-causal cause
> is that DTL-trigger days cluster on ±10% limit-up days in momentum
> regimes, so the factor is a vehicle for the momentum factor."

**The audits confirm exactly that.** alpha_05's raw → residual Sharpe
collapse from +0.97 to −0.48 is the falsification firing.

## Recommended next steps (round 2)

1. Test the M3 mechanism only on **non-trigger days** of stocks that
   were on the DTL within the last 5 days (decouples the signal from
   the limit-up regime).
2. Pull `moneyflow_hsgt` (free-tier aggregate northbound flow) to
   condition DTL signal on regime, rather than running unconditionally.
3. Try a longer window (2018-2025) — 3 years is too short for stable
   worst-year audits; 2024 dominated everything.
4. Test the same family on monthly Q5 long-only with daily reblance
   suppressed via a min-holding-period mask, to see whether monthly Q5
   excess is robust.
5. **Do not tune the 5d / 10d / 20d window on the same mechanism** —
   per session_metadata.yml failure rule, switch mechanism instead.

## Audit invariants verified

- Look-ahead grep: clean (no `shift(-k)` or `next_*` references in any
  factor; only the labelling pipeline uses `shift(-(1+h))` against
  `shift(-1)`, which is the delay-1 entry/exit by design).
- Delay invariant: factors use only `lag(1)` of disclosed inputs and
  past-or-current OHLCV. Future-perturbation test passes by
  construction (no factor recompute is sensitive to future bars).
- Worst-year, best-year-out, residualization: all computed and reported
  per alpha in `alpha_ranking.md`.

## Caveats

- 3-year window; per-year audit noise is high.
- Hot-money seat keyword list is partial; alpha_07 is indicative only.
- Industry neutralization via free-tier 110-group `stock_basic.industry`,
  not SW L1.
- ST filter approximated via IPO-age only (no `namechange` join).
- Cost gate (30bp) not applied to monthly numbers; daily LS already
  shows the cost story.
