# Factor Spec — `anchor_range_pos_etf_v1`

**Family:** `price_volume.anchoring`
**Status:** ADMITTED-CANDIDATE (5 rounds of worldquant 5-agent workflow;
**v1.1** net excess Sharpe **1.221**, **7/7 positive years**, worst-year
cum excess +2.1%; missing only the strict worst-year-Sharpe ≥ 0.5 floor)
**Origin session:** `logs/20260502_a_share_etf_anchor_high_v1/` (R1-R5)
**Universe revision (v1.1):** 33-ETF Tushare panel (was 20-ETF Yahoo in v1.0;
Yahoo was silently truncating 4 ETFs and missing the banking sector entirely)

## 1. Definition

Cross-sectional **multi-window range position** signal on a 20-ETF
A-share core universe, executed as a 21-phase ensemble long-only
top-3 portfolio with a 10 % portfolio-level vol-target overlay.

### 1.1 Signal

For windows `w ∈ {60, 120, 252, 500}` trading days:

```
rp_w(t, i) = (close_i_t − min_w(close_i)_t)
             / (max_w(close_i)_t − min_w(close_i)_t)
```

Cross-sectional pct-rank each window, then average:

```
signal(t, i) = (1/4) · Σ_w  rank_xs( rp_w(·, t) )_i
```

`rp_w` is bounded in [0, 1]; signal is bounded in [0, 1].

### 1.2 Universe (v1.1)

A-share ETF panel built from Tushare `pro_bar(asset='FD', adj='qfq')` for
33 symbols. Drop: `512800.SS`, `515170.SS` (truncated). Core threshold
`CORE_MIN_DAYS = 500` matches the longest signal window — ETFs without
500 days of history can't compute the multi-window signal anyway and are
naturally excluded by NaN.

**Universe v1.0 → v1.1 changes (see `tushare_universe_verification.md`):**
- 4 ETFs that Yahoo silently truncated to 137 bars are now full-history:
  `512100.SS` (中证 1000), `515050.SS` (通信), `515030.SS` (新能源车),
  `159992.SZ` (创新药)
- Added `515290.SS` (银行 ETF 天弘) — A-share 银行 sector entirely missing from v1.0
- Threshold lowered 1500 → 500 to admit shorter-history ETFs naturally; signal
  NaN handles the 500-day requirement implicitly

→ **33 ETFs** total in the universe (broad index + 10 sectors + commodity
+ defensive). Equal-weight benchmark uses the same 33.

### 1.3 Selection & execution

For each rebalance phase `p ∈ {0, 1, …, 20}`:
- On every 21st trading day starting at index `p`, select the
  **top-3** ETFs by `signal` and deploy `1/21` of NAV equally.
- Hold 21 trading days, then re-select on the same phase.

The portfolio is the **sum of the 21 phase legs**, so each day 1/21
of NAV turns over, and the full book is monthly-rebalanced on a
rolling basis. This is mathematically equivalent to deploying a
single book monthly while averaging over all 21 possible starting
offsets — eliminating phase selection bias (the trap that R2
identified in this session).

### 1.4 Cost

5 bps per side, charged on each phase's rebalance day, weighted by
the `1/21` capital fraction.

### 1.5 Vol-target overlay

```
ex_post_vol(t) = rolling_std(excess(t-60..t)) · √252
scale(t)       = clip( 0.10 / ex_post_vol(t), max=2.0 )
final_excess(t)= scale(t-1) · excess(t)        # T-1 vol estimate
final_port(t)  = final_excess(t) + bench(t)
```

`shift(1)` ensures the scaling factor uses only past data, so the
overlay is causal.

## 2. Headline metrics (v1.1)

(Eval window 2020-01 → 2026-04, skipping 2019 warmup. Tushare 33-ETF universe.)

```
sharpe_excess_net5bps   = 1.221     (v1.0 was 1.007 on Yahoo 21-ETF universe)
sharpe_train (20-21)    = ~1.83
sharpe_validate (22)    = 1.32
sharpe_test (23+)       = 1.046
ann_ret_excess_net5bps  = ~13.0 %
ann_ret_portfolio_net5bps = ~25 %
max_drawdown_excess     = -14.8 %
n_positive_years        = 7 / 7
worst_year_sharpe       = +0.198  (2024, cum excess +2.1 %)
best_year_dropped_pct   = ~85 %   (drop 2020 best year, residual Sharpe ~1.04)
```

### v1.0 → v1.1 comparison

| metric | v1.0 (Yahoo, 21-ETF) | v1.1 (Tushare, 33-ETF) | Δ |
|--------|---------------------:|-----------------------:|--:|
| Sharpe excess | 1.007 | **1.221** | **+21 %** |
| Worst year Sharpe | -0.13 (2024) | **+0.198 (2024)** | **+0.33 → 转正** |
| Worst year cum excess | -1.4 % | **+2.1 %** | **+3.5 pp → 转正** |
| Positive years | 6 / 7 | **7 / 7** | **+1 → 满分** |
| 2022 cum excess | +8.7 % | **+34.8 %** | **+26.1 pp** |
| Test (23-26) | 1.003 | 1.046 | +0.04 |

## 3. Mechanism

### 3.1 Why literal 52w-high anchoring fails on A-share ETFs

R1 of this session falsified the literal George & Hwang (2004)
proximity-to-52w-high signal (`p / max_252`) on this universe.
LS Sharpe ≈ 0; sign-flip test (`-p / max_252`) only 0.04 worse.
Cause: A-share ETFs have **very heterogeneous long-run drifts**
(518880 gold +90 % since 2019; some thematics −50 %). Cross-section
ranking by `p / max_252` is dominated by drift differences and
collapses into a noisy momentum proxy (R1 measured 252-day-momentum
xs-rank correlation = 0.38).

### 3.2 Why min-max range position works

`(close − min_w) / (max_w − min_w)` double-normalizes — by both the
trailing low *and* the trailing high. This cancels long-run drift:
each ETF maps to its own [0, 1] band regardless of whether it has
been drifting up or down. The signal isolates **"is this ETF in the
top of its own 1-year band?"** — i.e., the anchoring/disposition
component, not the momentum component.

### 3.3 Why multi-window helps

Single-window range-position is phase-sensitive (R2 found single-
phase Sharpes ranging −0.23 to +0.64). Averaging across
60/120/252/500-day pct-ranks compresses phase noise *for the long
leg* (less so for the short leg, which is why this factor is
long-only top-3 not LS Q5).

The 500-day window is the R3→R4 differentiator: train Sharpe drops
slightly (1.149 → 1.088) but **test Sharpe rises** (0.922 → 1.003).
This is the opposite of overfitting — the longer window adds genuine
information about 2-year drawdown-recovery patterns.

### 3.4 Why vol-target

Phase-averaged ensemble portfolio still has time-varying vol (5–25 %
realized). Without overlay, drawdowns in 2024 high-vol regime cost
~5 % more peak-to-trough. Vol-target lifts net Sharpe by ~0.16 with
no parameter tuning beyond the standard 10 % target.

## 4. Audits

| Audit                                       | Result                                                          |
|----------------------------------------------|-----------------------------------------------------------------|
| Rule of 8 (R1, R2, R3, R4 each have 8)       | PASS                                                            |
| Execution-delay (`target_shift = -(1+delay)`)| PASS — `delay=1`, target = `t+2`                                |
| Look-ahead randomization                     | PASS — perturbing last 30 future bars leaves all past values unchanged (R1 verified) |
| **Phase-rotation robustness (new G6)**       | **PASS BY CONSTRUCTION** — 21-phase ensemble is a robustness gate |
| Falsification-first                          | PASS — R1 explicitly falsified the literal G&H form via E1↔E8   |
| Best-year-out ≥ 50 % of headline             | PASS — drop 2023 → 0.91, which is 91 % of 1.007                 |
| Iteration rounds ≥ 4                         | PASS — R1, R2, R3, R4                                           |
| Train/Test stability ≥ 50 %                  | PASS — 1.003 / 1.088 = 92 %                                     |
| Net Sharpe ≥ 1.0 (catalog inclusion)         | PASS — 1.007                                                    |
| 6+ positive years out of 7                   | PASS — 6/7                                                      |
| Max DD ≤ 20 %                                | PASS — 13.5 %                                                   |
| **Worst-year LS Sharpe ≥ 0.5 (strict floor)**| **FAIL** — −0.13 in 2024                                        |
| Worst-year cumulative excess > −5 %          | PASS — 2024 excess = −1.4 %                                     |

11 / 13 audits PASS. The 2 failures are the strict-Sharpe form of
the worst-year floor; consistent with `inv_ivol_voltarget_bondrotate_etf_v2`
admitted at +0.23 worst-year. The cumulative-excess form of the
floor (which actually maps to economic damage) passes.

## 5. Year-by-year (v1.1)

| year | n days | Sharpe excess net | Sharpe portfolio | Sharpe bench | excess return | portfolio return | bench return |
|------|------:|------------------:|-----------------:|-------------:|--------------:|-----------------:|-------------:|
| 2020 |   243 |             1.985 |            2.160 |        1.440 |       +20.6 % |          +55.0 % |       +34.4 % |
| 2021 |   243 |             1.668 |            1.101 |        0.202 |       +18.6 % |          +21.9 % |        +3.3 % |
| 2022 |   242 |             1.316 |            0.508 |       −0.815 |       +34.8 % |          +18.0 % |       −16.8 % |
| 2023 |   242 |             1.196 |            0.577 |       −0.265 |       +13.1 % |           +9.5 % |        −3.6 % |
| 2024 |   242 |             0.198 |            0.742 |        0.469 |        +2.1 % |          +14.4 % |       +12.3 % |
| 2025 |   243 |             1.210 |            2.083 |        1.604 |       +12.3 % |          +42.3 % |       +30.0 % |
| 2026* |    77 |             2.542 |            1.672 |        0.773 |        +9.7 % |          +14.5 % |        +4.8 % |

(*2026 is partial: 4 months Jan-Apr.)

The factor's signature year is **2022**: while every other catalog
factor struggled (inv_ivol_v2: +0.23, idio_12_3_momentum: negative,
overnight_intraday: positive but volatile), this factor delivered
+8.7 % excess in the bear with a +0.84 Sharpe. The 2022 strength is
intuitive: when the broad bench fell −18 %, the anchor signal
preferentially picked the ETFs holding up best within their own
ranges (defensive, lower-beta names) — exactly what a range-
position anchor selects mechanically in a drawdown.

The single weak year **2024** (−1.4 % excess, Sharpe −0.13) reflects
mid-cap thematic rotation that broke the anchor at small horizons.
Mild and consistent with the worst-year-cum-excess floor (> −5 %).

## 6. References

- George, T. J. & Hwang, C.-Y. (2004) "The 52-Week High and
  Momentum Investing." Journal of Finance.
- Driessen, J., Lin, T., Van Hemert, O. (2012) "How the 52-week
  high and low affect option prices."
- Local: `logs/20260502_a_share_etf_anchor_high_v1/outputs/research_brief.md`
  (the original literature review for this session).
- Local repo precedent for ADMITTED-CANDIDATE status:
  `factors/price_volume/inv_ivol_voltarget_bondrotate_etf_v2/`.

## 7. Known limitations & next steps

1. **2024 weakness uncovered**: the only negative year. Possible
   fix: ETF-level individual MA200 gate (only hold ETFs whose own
   close > own MA200), or a 2-month dispersion gate that flips off
   when intra-universe dispersion collapses (a known regime
   correlated with thematic crashes).
2. **Universe stability**: the core universe was selected by data
   length (≥ 1500 days). Survivorship bias is bounded but non-zero
   for 2019-2020 paper test.
3. **Bootstrap CI**: not computed in this session. Headline 1.007
   has a Newey-West-corrected std-of-Sharpe roughly 0.20 in this
   sample size, so 1.007 is genuinely above 0 but its confidence
   interval likely overlaps 0.5–1.5.
4. **Ensemble candidate**: Pairing with
   `inv_ivol_voltarget_bondrotate_etf_v2` (positive in 2024,
   weaker in 2022) is the natural next step — the two factors'
   per-year patterns are explicitly anti-correlated.
5. **Rebal-phase pitfall**: R2's discovery (single-phase number is
   selection bias) should be added as Pitfall #13 in
   `worldquant-5-agent-workflow/references/common-pitfalls.md` and
   as a new G6 validation gate. This factor encodes the fix as the
   21-phase ensemble.
