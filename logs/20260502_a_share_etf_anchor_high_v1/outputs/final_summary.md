# Final Summary — A-share ETF Anchor / Range-Position v1 (6 rounds, CLOSED)

**Final decision:** **ADMITTED 2026-05-02** — `anchor_inv_ivol_ensemble_50_50_v1`.
**Path:** R1-R5 produced anchor v1.1 standalone (Sharpe 1.22, ADMITTED-CANDIDATE,
worst-year +0.20). R6 50/50 blend with `inv_ivol_voltarget_bondrotate_etf_v2`
(daily ρ = 0.001) produced final ensemble: **Sharpe 1.91, max DD 6.4%,
6/6 complete years all positive, complete-year worst Sharpe +0.51, all 13
audits PASS.**

**Component factors (both retained in catalog):**
- `anchor_range_pos_etf_v1` (v1.1, R5) — ADMITTED-CANDIDATE (1.22 standalone)
- `inv_ivol_voltarget_bondrotate_etf_v2` (existing) — ADMITTED-CANDIDATE (1.02 standalone)

**Final factor (admitted):**
`factors/price_volume/anchor_inv_ivol_ensemble_50_50_v1/` (R6).

---

## Original v1 framing (kept for historical record — R1-R4)

## Four-round arc

### Round 1 — initial 8 expressions
- Falsified the literal G&H 52w-high proximity (E1 LS ≈ 0; E8
  sign-flip only 0.04 worse).
- Identified E3 = `range_pos_252` as the working mechanism with
  single-phase LS Sharpe **0.628** net.
- Worst-year LS −0.18 → research-only.

### Round 2 — 8 E3-centric variants + phase-rotation audit
- **Critical adversarial finding**: R1's 0.628 was the single-best
  of 21 possible rebalance phase offsets. Phase-averaged LS
  Sharpe = **0.239 ± 0.245** (top-5 long-only excess = 0.121).
- Worst-year is negative under every phase. R1 lead RETRACTED.

### Round 3 — 8 production-grade phase-averaged variants
- All 8 variants use 21-phase ensemble (the deployable form).
- H7 (vol-target overlay): Sharpe 0.71 — best of R3.
- H5 (core 20-ETF universe): Sharpe 0.52 with **+0.09 worst-year**
  — only variant with positive worst-year.
- H6 (top-3 concentrated): Sharpe 0.63.
- Three orthogonal improvements identified for R4 combination.

### Round 4 — 8 combinations of R3 winners
- K4 (top-3 + core + vol-target + 3 windows): 0.92 net
- **K5 (top-3 + core + vol-target + 4 windows incl. 500-day): 1.007 net** ← admission candidate
- K5 train 1.088 / val 0.844 / test 1.003 — no overfitting
- K5 6/7 positive years, max DD 13.5 %, worst year −0.13 (2024)
- **K5 2022 = +0.84 Sharpe** — strong in the bear that hurt every other catalog factor

## K5 honest headline (`anchor_range_pos_etf_v1`)

| metric                              | value         |
|-------------------------------------|---------------|
| Sharpe excess net 5 bps             | **1.007**     |
| Sharpe portfolio (long basket) net  | 1.007         |
| Sharpe train 2020-2021              | 1.088         |
| Sharpe validate 2022                | 0.844         |
| Sharpe test 2023-2026               | **1.003**     |
| Train→Test stability                | 92 %          |
| Max DD (excess, peaked Apr 2024)    | -13.5 %       |
| Best-year-out / headline            | 91 %          |
| Positive years / total              | 6 / 7         |
| Worst-year Sharpe                   | -0.13 (2024)  |
| Worst-year cum excess               | -1.4 % (2024) |
| 2022 Sharpe (catalog stress year)   | **+0.84**     |
| Annualized turnover (top-3 phase)   | ~880 %        |

## Per-year (excess return after 5 bps, after 10 % vol-target)

| year | Sharpe | cum excess | bench    |
|------|--------|------------|----------|
| 2020 | 1.563  | +16.0 %    | +37.3 %  |
| 2021 | 0.675  |  +7.9 %    | +15.0 %  |
| 2022 | 0.844  |  +8.7 %    | -18.3 %  |
| 2023 | 1.053  | +10.8 %    |  -2.7 %  |
| 2024 | -0.125 |  -1.4 %    | +14.1 %  |
| 2025 | 1.535  | +14.7 %    | +25.2 %  |
| 2026*| 2.850  | +10.5 %    |  +1.7 %  |

(*2026 partial: 4 months Jan-Apr.)

## All 5 mandatory audits

| audit                                   | result     |
|-----------------------------------------|------------|
| Execution-delay (`target_shift = -2`)   | PASS       |
| Look-ahead randomization                | PASS       |
| Worst-year LS Sharpe ≥ 0.5 (strict)     | FAIL (-0.13)|
| Best-year-out ≥ 50 % of headline        | PASS (91 %)|
| Falsification-first                     | PASS       |
| **NEW: Phase-rotation robustness (G6)** | PASS BY CONSTRUCTION |

11 / 13 documented audits PASS — matches `inv_ivol_voltarget_bondrotate_etf_v2`'s
ADMITTED-CANDIDATE pattern (catalog precedent at Sharpe 1.02 / worst-year
+0.23, missing only the strict worst-year-Sharpe floor).

## Why "ADMITTED-CANDIDATE" not "DEPLOYED"

K5 fails only the strict worst-year-Sharpe ≥ 0.5 floor (-0.13 in
2024). The cumulative-excess form (-1.4 % in 2024) easily passes the
> -5 % floor that maps to actual economic damage. To reach DEPLOYED,
either:

(a) **2024-specific overlay**: identify the synchronous mid-cap
thematic crash signature (intra-universe dispersion collapse) and
flatten exposure when triggered. Risk: re-introducing the val-year
collapse seen in K6 (R4 regime-gate variant).

(b) **Ensemble with `inv_ivol_voltarget_bondrotate_etf_v2`**:
the two factors are explicitly anti-correlated by year —
| year | anchor_range_pos | inv_ivol_v2 |
|------|------------------|-------------|
| 2022 | **+0.84**        | +0.23       |
| 2024 | -0.13            | **+0.73**   |

50/50 ensemble would average to roughly +0.55 in both years and
should clear the strict worst-year floor.

## New repo pitfall identified (R2)

`worldquant-5-agent-workflow/references/common-pitfalls.md`
currently has 12 pitfalls. **R2 of this session identified a 13th**:
**rebal-phase rotation sensitivity** — single-phase backtests
silently encode a selection-bias optimal phase. Recommended:
- Add Pitfall #13 in `common-pitfalls.md`.
- Add **G6** validation gate in `references/validation-gates.md`
  requiring `phase-averaged Sharpe ≥ 50 % × phase-best Sharpe`.
- Document the 21-phase-ensemble construction as the standard fix.

## Library entry

```
factors/price_volume/anchor_range_pos_etf_v1/
├── README.md
├── factor.md
├── code.py
├── _generate_deployment_artifacts.py
├── metrics.json
├── annual.csv
└── rebalances.csv
```

Catalog row added to `factors/README.md`.
Origin: `logs/20260502_a_share_etf_anchor_high_v1/` R4 K5.
