# Research origin — session `20260502_a_share_etf_anchor_high_v1`

Full 4-round audit trail lives in:

```
logs/20260502_a_share_etf_anchor_high_v1/
├── inputs/objective.md
├── outputs/
│   ├── research_brief.md            # Agent 1
│   ├── session_metadata.yml          # Agent 2
│   ├── expressions_batch_0001.md    # R1
│   ├── expressions_batch_0002.md    # R2
│   ├── expressions_batch_0003.md    # R3
│   ├── alpha_ranking{,_r2,_r3,_r4}.md
│   ├── final_summary.md
│   ├── summary_batch_0001.csv
│   ├── r2_summary_batch_0002.csv
│   ├── r2_phase_rotation_summary.json
│   ├── r3_summary_batch_0003.csv
│   ├── r4_summary_batch_0004.csv
│   ├── audit_execution_delay.json
│   ├── audit_lookahead_batch_0001.json
│   ├── audit_floors_batch_0001.json
│   └── audit_falsification_batch_0001.json
├── working/handoff_{1_to_2,2_to_3,3_to_4{,_r2},4_to_5{,_r2}}.json
├── scripts/
│   ├── 02_backtest_anchor_high.py        # R1
│   ├── 03_backtest_r2.py                 # R2 variants
│   ├── 04_phase_rotation_audit.py        # R2 phase audit
│   ├── 05_backtest_r3.py                 # R3
│   └── 06_backtest_r4.py                 # R4 (admission)
├── round_{0001,0002,0003,0004}.yml
└── run_state.json
```

## R1 — initial 8 expressions

E1 to E8 covered raw `p/max_w` ratios at 60 / 252 windows, the
Williams-style range position (E3), drawdown distance, multi-window
composite, regime gate, lag, and sign-flip falsifier.

**Key finding**: literal G&H 52-week-high proximity (E1) was falsified
on this universe — LS Sharpe ≈ 0; sign-flip E8 only 0.04 worse.
The variant that worked was E3 (range_pos_252) at single-phase LS
Sharpe 0.628.

## R2 — phase-rotation adversarial audit

The R1 lead's headline was tested across all 21 possible rebalance
phase offsets. Result: R1 picked the single-best phase out of 21.

| metric | R1 reported | R2 phase-averaged |
|---|---|---|
| LS Sharpe | 0.628 | 0.239 ± 0.245 |
| top-5 long excess | 0.486 | 0.121 |
| worst year LS | -0.18 | median -0.84 |

**This pitfall is not in `worldquant-5-agent-workflow/references/common-pitfalls.md`**.
Recommended addition as Pitfall #13 + G6 validation gate.

The R3+ work uses 21-phase ensemble by construction so the bias
cannot recur.

## R3 — production-grade variants

8 variants combined phase-averaging with various risk overlays.
Best single variant: H7 (vol-target) at 0.71 net excess Sharpe.
Three orthogonal levers identified for R4 combination:
- top-3 vs top-5 (concentration, +0.08)
- core vs full universe (worst-year fix, +0.21)
- vol-target overlay (drawdown control, +0.16)

## R4 — admission run

Combined R3 levers and tested an extended 4-window signal
(60/120/252/500). K5 reached **net excess Sharpe 1.007**, with:
- Train 1.088 / Validate 0.844 / Test 1.003 (no overfitting)
- 6/7 positive years
- Max DD -13.5 %
- 2022 Sharpe +0.84 (strong in the bear that hurt every other catalog factor)
- 2024 Sharpe -0.13 (-1.4 % cum excess; only negative year)

K5 is the deployable form encoded in this package.
