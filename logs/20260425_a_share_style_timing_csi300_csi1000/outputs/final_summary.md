# Final Summary — A-share broad-base ETF style-timing factor (R1 + R2)

Session: `20260425_a_share_style_timing_csi300_csi1000`
Run mode: two rounds executed (R1 = M1 vol-regime, R2 = M2 turnover divergence).

## TL;DR

> **No deployable factor produced.** Decision = RESEARCH-ONLY.
>
> The volatility-regime mechanism family (M1) was tested in two
> directions on a 4y train / 2y val / 2.3y test split. The original
> "high vol-spread → flight-to-quality, favour CSI300" thesis was
> **falsified** by the data: all 8 expressions had IC sign opposite to
> the thesis on TRAIN. After hypothesis revision to the contrarian
> M1' direction ("high vol-spread → small-cap mean-reversion, favour
> CSI1000") and per-source negation, the IC sign matched on 8/8 but
> only 1/8 (E1) passed all G4 sub-checks, and **no expression in the
> batch was TVT-eligible** (the `train_sharpe > 0.5` floor was never
> cleared). The strongest expression (E1) shows a +0.14 test Sharpe
> driven almost entirely by a single year (2025).

## Headline numbers (E1, only G4 survivor)

| Window | Days | Sharpe |
|---|---:|---:|
| Train [2018-01, 2022-01) | 906 | +0.14 |
| Val [2022-01, 2024-01)   | 484 | +1.06 |
| Test [2024-01, today]    | 558 | +0.14 |

Per-year test (E1): 2024 +0.01, 2025 +0.75, 2026 (partial) −1.15.

## Audits

- 1 execution-delay: PASS
- 2 look-ahead: PASS
- 3 worst-year Sharpe ≥ 0.5: FAIL
- 4 best-year-out ≥ 50% headline: FAIL
- 5 falsification ("if Sharpe is wrong by 50%, the most likely cause is"):
  partial-2026 sample drag + cost assumption sensitivity (see
  `outputs/alpha_ranking.md` "Audit 5").

## Honest readings

1. The original M1 "vol-spike triggers flight-to-quality" thesis is wrong
   for A-share broad-base 300/1000 over 2018-2025. The data says the
   opposite: vol-spread spikes signal short-term small-cap
   mean-reversion (recoveries), consistent with capitulation-low
   dynamics in retail-driven small-caps.
2. Even with the corrected direction, the signal is too weak (max IC
   t≈1.93) and too regime-concentrated to clear PROMOTE floors. The
   conclusion is *not* that there is no signal — it is that any signal
   is below the noise floor of a 2.3y test window with 5 bps/side cost
   and only 3 deployable assets.
3. The expression with the most stable per-year behaviour (E4, faster
   10d window) is *not* the one with the highest train Sharpe. R2
   should weigh per-year stability higher than headline Sharpe.

## Acknowledged plan-level deviations

Per the approved plan §"Acknowledged deviations":

- Test window 2.3y < TVT template's 3y+ floor — floors *not* loosened.
  If anything, this is the most likely contributor to the RESEARCH-ONLY
  outcome (see Audit 5).
- G3 was adapted for the 3-asset universe (`non-zero position fraction`
  + `signal std > 0` + `net Sharpe > −0.5` + `turnover ∈ [10%, 2000%]`
  in lieu of `Q5 size ≥ 30 stocks`). Documented in
  `src/backtest/audits.py` and the v1/v2 result MDs.
- Industry neutralization N/A on a 3-index universe — skipped per plan
  §"Acknowledged deviations" #3.
- BRAIN / OpenClaw / QQBot integrations not used — plan §4.

## What's in the session folder

```
logs/20260425_a_share_style_timing_csi300_csi1000/
├── inputs/
│   └── objective.md
├── working/
│   ├── handoff_1_to_2.json
│   ├── handoff_2_to_3.json
│   ├── handoff_3_to_4.json
│   ├── handoff_4_to_5.json                  # v2 (post-revision)
│   ├── handoff_4_to_5_v1_falsified.json     # v1 audit trail
│   └── agent5_diagnostic.json
├── outputs/
│   ├── research_brief.md
│   ├── session_metadata.yml                 # includes Agent-2 v2 revision block
│   ├── expressions_batch_0001.md
│   ├── backtest_results_batch_0001.md       # v2
│   ├── backtest_results_batch_0001_v1_falsified.md
│   ├── alpha_ranking.md
│   └── final_summary.md                     # this file
├── round_0001.yml
└── run_state.json
```

The Python harness lives at `src/` and is reusable for R2.

## Round 2 — M2 turnover divergence (executed)

Same TVT split, same audits, same Rule of 8. Pivot was clean
(M2 was Agent-1 candidate #2 in `research_brief.md` and was identified
BEFORE any R1 test metric was touched, so the test window remains
honest for M2).

| Stage | Outcome |
|---|---|
| Stage 4 | 2/8 G4 PASS (E1, E8 — level cluster). E3 acceleration shows TRAIN IC = **−0.196 with t = −5.93** in the *anti-thesis* direction. G5 still fails (2 < 4). 0/8 TVT-eligible. |
| Stage 5 | val-strong candidates (E1/E8 val Sh +1.7) **fail to generalize** to test (Sh −0.36). Decision **RESEARCH-ONLY**. |

### R2 headline numbers (E1, val-strongest G4-pass)

| Window | Days | Sharpe |
|---|---:|---:|
| Train [2018-01, 2022-01) | 907 | +0.16 |
| Val [2022-01, 2024-01)   | 484 | +1.69 |
| Test [2024-01, today]    | 558 | **−0.36** |

Per-year test (E1): 2024 −0.38, 2025 −0.85, 2026 partial +4.34
(75 days, dominated by 1-2 spread moves).

### R2 audits

- 1 execution-delay: PASS
- 2 look-ahead: PASS
- 3 worst-year Sharpe ≥ 0.5: FAIL
- 4 best-year-out ≥ 50% headline: FAIL
- 5 falsification: completed — most likely cause of val-test
  divergence is that val Sharpe was carried by a small number of
  large directional bets in 2022-2023, not consistent edge
  (val IC ≈ +0.005, t < 0.2). See `outputs/alpha_ranking_r2.md`.

### R2 honest readings

1. M2-level thesis (E1/E8/E5 cluster) is val-favorable but
   **disconfirmed** out-of-sample on test. The 2022-2023 val window
   was a regime where small-cap-amount-share led style rotation;
   that regime did not persist into 2024-2026.
2. M2-acceleration sub-cluster (E3 strongly, E6 weakly) shows
   **anti-thesis IC** with high statistical significance (E3
   t = −5.93). This is the **strongest single signal** found in
   either round. Read it as: when small-cap turnover accelerates,
   small-cap *continues* to outperform for ~5 trading days
   (momentum, not mean-reversion). This contradicts the M2-level
   thesis but is internally consistent with A-share micro-cap
   surge dynamics (e.g. 2024-Q4).
3. Effective batch size in R2 was 7, not 8: E1 ≈ E8 by response
   despite distinct construction (TRAIN z-score corr 1.00).

## Session-level decision

**RESEARCH-ONLY for both rounds.** The strict TVT + 5-audit framework
correctly rejected (a) the M1 thesis (R1, falsified by sign flip then
weak in revised direction) and (b) the M2-level thesis (R2,
val-favorable but test-failed). The framework worked as designed.

The session is **not** "no signal found":
- E3 inverted (turnover-acceleration as momentum) is a clean R3
  hypothesis with a much stronger pre-test IC than anything in R1 or
  R2 level signals.
- E4 from R1 (per-year-stable, 10d vol-spread) remains a vol-state
  conditioning candidate.
- A regime-conditional combination of M1+M2 has not been tested.

## R3 hand-off (recommended)

Top R3 lead — execute as a clean new round with these constraints:

1. **Mechanism**: small-cap turnover *acceleration* as a MOMENTUM
   signal on the spread.
2. **Direction**: invert E3-class signals at source (Agent-3 negation
   per `validation-gates.md:140`); thesis_sign stays +1 by convention.
3. **8 expressions**: vary MA windows {5/20, 5/60, 10/60, 5/120},
   acceleration spread vs single-leg, volume-derived vs amount-derived,
   regime-conditioning by R1 vol-spread state.
4. **Anti-clone**: enforce `|corr| < 0.85` vs both R1 vol-spread AND
   R2-level expressions.
5. **Same TVT split** — test stays untouched.

R3 was not executed in this session pass.
