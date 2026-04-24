# Out-of-Sample Validation — R2 Winner

**Session:** `20260424_a_share_etf_reversal_v2` Round 2
**Winner:** k=40 ⊕ k=80 long-only top-3 monthly ensemble + 55% gold blend
**Date:** 2026-04-24

## TVT split

| Split | Range | n_days | Years |
|---|---|---:|---|
| Train | 2019-01-04 → 2022-12-31 | 970 | 4 |
| Val | 2023-01-01 → 2023-12-31 | 242 | 1 |
| OOS | 2024-01-01 → 2026-04-22 | 556 | 2.3 |

## Q1. Winner (gold_weight = 0.55 full-sample) per split

| Split | Net Sh @5bps | Ret ann | MaxDD | n_days |
|---|---:|---:|---:|---:|
| Train | +1.318 | +17.17% | -11.7% | 970 |
| Val 2023 | +0.250 | +2.59% | -9.5% | 242 |
| **OOS** | **+1.646** | **+28.90%** | -18.7% | 556 |

**Reading:** OOS Sharpe is HIGHER than train — the recipe is not curve-fit.
Val 2023 is the known bad year and shows Sh +0.25 (rescued from -0.58 of
the reversal-only baseline by the gold blend). All 8 calendar years are
positive under this hyperparameter.

## Q2. Train-only gold-weight re-selection (true OOS honesty)

Using only train data (2019-2022), we grid-search gold_weight from 0.00
to 0.95 in 0.05 steps. The "train-optimal" is the highest-train-Sharpe
weight subject to train worst-year ≥ 0.

| Selection path | gw | Train Sh | Val 2023 Sh | OOS Sh |
|---|---:|---:|---:|---:|
| Train-only pick | **0.45** | +1.339 | -0.040 | +1.515 |
| Full-sample pick ("winner") | 0.55 | +1.318 | +0.250 | +1.646 |

The train-only pick (0.45) has essentially identical train Sharpe
(+1.339 vs +1.318), but **fails val** (-0.040 — slightly negative) and
still gives strong OOS (+1.515). The +0.10 extra gold weight in the
full-sample pick was tuned with 2023's hindsight in mind; without that
hindsight, we would have picked 0.45 and val would have been slightly
negative.

Grid stability across [0.40, 0.55]: all five weights give train Sh ≥ 1.3
and OOS Sh ≥ 1.4. Selection is robust; it is NOT a sharp overfit.

## Q3. Decomposition: who is generating the OOS Sharpe?

Gold ETF (159934.SZ) standalone Sharpe per split:

| Split | Gold-only Sh | Ret ann | n_days |
|---|---:|---:|---:|
| Train | +0.662 | +9.56% | 970 |
| Val 2023 | +1.685 | +16.36% | 242 |
| **OOS** | **+1.691** | **+37.33%** | 556 |

Attribution (Winner Sharpe − Gold-only Sharpe):

| Split | Gold-only | Winner | Reversal-leg marginal |
|---|---:|---:|---:|
| Train | +0.662 | +1.318 | **+0.656** (reversal adds value) |
| Val 2023 | +1.685 | +0.250 | **-1.435** (reversal destroys value) |
| **OOS** | **+1.691** | **+1.646** | **-0.045** (reversal is null / slightly negative) |

**Key finding.** The reversal factor's OOS (2024-2026) contribution is
essentially zero. The winner's +1.65 OOS Sharpe is attributable to gold's
+1.69 standalone Sharpe during the 2024-2026 gold rally; the reversal
overlay neither helps nor significantly hurts.

## Life-cycle of the reversal signal

| Window | Reversal-leg Sh | Mechanism state |
|---|---:|---|
| 2019-2022 | +0.66 above gold | Working — classic 40-80d reversal zone productive |
| 2023 | -1.44 below gold | Inverted — TMT concentration regime, losers kept losing |
| 2024-2026 | -0.05 ≈ 0 | Dormant — correlation flat, neither inverted nor productive |

The factor has not recovered since its 2023 break. The OOS window provides
no evidence that the reversal signal is currently a live alpha.

## Verdict update

**R2 winner (55% gold + 45% reversal ensemble) in OOS:**

1. **Headline OOS Sharpe +1.646** — mechanically correct, passes the 0.5 promote bar on OOS alone.
2. **OOS attribution: ~100% gold, ~0% reversal.** The 45% reversal allocation is dead weight in OOS.
3. **A 55% gold + 45% cash portfolio would have produced essentially the same OOS Sharpe** (≈ gold's +1.69, because unlevered cash contributes zero).
4. **For deployment:** 55% gold / 45% cash (or 55% gold / 45% broad-index defensive) would be a more honest positioning. The reversal overlay is a latent-optionality trade — if the 2019-2022 regime returns, it re-adds value; but OOS says no evidence yet.

**Status:** RESEARCH-ONLY is reaffirmed. Earlier narrative that "the 55%
gold blend passes the research floor" remains correct mechanically, but
the OOS dissection shows this rescue was executed by gold, not by the
factor. The factor itself has no current OOS alpha signal.

## Implications for the workflow

- **Always do per-split component attribution for blend wins.** A blend that
  works in train but has zero-marginal-over-gold in OOS should be flagged
  as gold-backed, not factor-backed.
- **"Train-only hyperparameter re-selection" is a cheap discipline.** Run
  the grid on train alone, report val and OOS under that pick. If the
  full-sample pick has a materially different weight, the extra delta is
  hindsight-informed.
- **Add to `references/tvt-split-template.md`:** when gold/cash blends are
  used as worst-year rescue, the deployable claim is only valid if the
  factor leg has independent positive marginal Sharpe in OOS, not just
  in train.
