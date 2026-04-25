# Final Summary — A-share broad-base ETF style-timing factor (R1)

Session: `20260425_a_share_style_timing_csi300_csi1000`
Run mode: single-round (R1), no R2 launched.

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

## R2 hand-off (if research continues)

See `outputs/alpha_ranking.md` §"Next-round (R2) focus" for the four
candidate directions. Top recommendation: pivot to M2 turnover
divergence with the same TVT discipline; preserve M1 v2 results as
priors / regime-conditioning inputs rather than as a standalone factor.
