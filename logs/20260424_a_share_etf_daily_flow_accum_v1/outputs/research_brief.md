# Research Brief — ETF Daily Flow-Accumulation Factor

**Agent 1 (Research Librarian) output.** Written 2026-04-24. Compresses operator/dataset/literature evidence for the downstream agents.

---

## 1. Mechanism candidates considered and the one chosen

Three daily-horizon mechanism families are economically distinct on ETFs:

| Family | Primary signal | Prior-art in this repo | Orthogonal? | Selected? |
|---|---|---|---|---|
| **Reversal (price-history)** | `-logret_k` for k ∈ 5..250 | ✅ 20260423 reversal session exhaustively | Done | ❌ |
| **Volume-as-confirmation** | breakout × volume-surge | ✅ 20260423 weekly TQPB overlay | Partially done | ❌ |
| **Volume-as-primary (PVO family)** | `zscore(log_amount)` + PVO variants | ❌ untouched on ETFs in this repo | Fully orthogonal | ✅ **chosen** |

Selected mechanism: **amount-based stealth-accumulation / price-volume-orthogonal (PVO) flow signal**.

Economic thesis: institutional ETF-buying has a volume footprint before it has a price footprint. A series of high-amount / low-price-impact days cross-sectionally identifies ETFs under patient institutional accumulation, which resolves into positive 5-20 day forward returns. Conversely, high-amount-with-large-price-move is momentum chasing (already priced in).

## 2. Supporting evidence / literature

- **Amihud, Y. (2002).** *JFMkts* 5: 31-56. ILLIQ = |ret|/amount. Negative price of ILLIQ → low-impact names earn a premium *over long windows*. Daily-horizon rotation uses `-|ret|/amount` ≈ `amount/|ret|` scaled, see e5 expression.
- **Llorente, Michaely, Saar, Wang (2002).** *RFS* 15: 1005-1047. Decomposes daily volume into informed-trading vs liquidity-trading components. The **quiet-day high-amount** signature (e4 expression) is their "informed-trading regime" — amount without price noise.
- **Kaniel, Saar, Titman (2008).** *JFE* 63: 273-310. Individual-investor buying predicts next-day returns. At ETF level the buyer pool is different, but the asymmetry (persistent one-sided flow predicts returns) carries.
- **Barardehi & Bernhardt (2018).** *JFE* 131(2): 460-482. PVO family — orthogonalizing volume against price movement isolates the "non-public information" component of trading activity.
- **Empirical prior in this repo:** weekly TQPB session's `r1_breakout_vol_conf` achieved **LS Sharpe +0.45** with volume as a *filter*; this session tests whether volume *as the primary signal* works at daily horizon.

## 3. Datasets & operators available

### Dataset

- **`inputs/etf_daily.parquet`** — 34 symbols × ~1,770 trading days, OHLC (split/div adjusted via adj-close ratio), volume (shares), amount = close × volume (CNY). Fetched 2026-04-24 from Yahoo Finance v8/chart.
- **Coverage caveat:** 4 of 34 symbols (512100.SS, 515050.SS, 512800.SS, 515170.SS) returned only 131 bars from Yahoo despite being long-history ETFs onshore. They will be auto-excluded from cross-sections that require a 60-day lookback until 60 bars of data accumulate. Effective cross-section is ~29-30 ETFs most days.
- **No fundamental data** (no daily_basic, no industry tags). This is fine for this mechanism — ETFs are already sector-bundled so industry neutralization does not apply.

### Operators (all implementable in pandas)

- `zscore_ts(x, win)` — backward-looking (shift-1-safe) z-score per symbol over `win` days
- `rolling_mean_ts(x, win)` — backward-looking rolling mean per symbol
- `xs_demean(x)` — cross-sectional demean per date (for factor-portfolio neutrality)
- `xs_rank(x)` — cross-sectional rank per date (primary signal combination method)
- `sign(x)` — elementwise
- `log`, `abs`, `+`, `-`, `*`, `/` — pointwise

### NOT used (dataset-only-constrained or semantically wrong)

- `market_cap`, `turnover_rate_f`, `pb`, `industry` — not available / not applicable to ETFs
- `shift(-k)` with k > 0 — would create look-ahead
- `winsorize` — too small a cross-section (~30) to matter, and amount distributions are already log-taken

## 4. Risks / caveats

1. **Daily-horizon flow signals are notoriously cost-sensitive.** Pitfall 10 (from `references/common-pitfalls.md`) killed a prior factor with +1.4 Sharpe gross → -6.6 Sharpe net. *Mitigation:* weekly (5-day) rebalance not daily, explicit cost sensitivity at 2/5/8 bps, ensemble expressions that smooth flow over 5-day windows.
2. **Volume-price correlation can be mechanical.** Trivially `amount = close × volume`, so `log(amount)` is *linearly related* to `log(close)` — risk of picking up a price-level factor. *Mitigation:* use *z-scored relative* `log(amount)` (per-symbol 60d z), which removes the price-level effect within symbol.
3. **Thin-history ETFs in the middle of a bull year could bias cross-section.** *Mitigation:* signals require 60d history before contributing; G3 gate requires ≥ 6 valid names on ≥ 95% of days.
4. **2020 regime risk.** The reversal session died in 2020. Our factor structurally avoids the short-leg failure, but we must still verify: 2020 is *inside* our TRAIN window (2019-2020), so the worst-year floor will be applied to an honest OOS (2022-2026).
5. **Pitfall 9: orthogonalized-LS-dead risk.** If our signal correlates > 0.5 with 20d momentum or 60d amount level, it's a vehicle for a known factor. *Mitigation:* explicit corr check in the harness; if it fails, label honestly and do not PROMOTE.
6. **Pitfall 1: look-ahead via target-derived masks.** *Mitigation:* all lookbacks are strictly past-only; explicit `future_perturbation_test` in the backtest script randomizes future bars and asserts past signals are bit-identical.

## 5. Recommended focus for Agent 2 (Hypothesis Architect)

- Mechanism: **amount-based stealth accumulation (PVO)**
- Horizon: **k = 10 days primary**, evaluated on k ∈ {5, 10, 20}
- Rebalance: **weekly (5-day period)** — the cost-turnover sweet spot given daily signal and PVO's typical decay
- Primary deployable metric: **long-only top-6 excess Sharpe vs universe-EW** (A-share ETFs can't be shorted efficiently)
- Reporting also LS for sanity
- Explicit gate on the 60d z-score look-ahead invariant and on corr vs momentum/amount-level
- Rule of 8: 8 distinct expressions covering the PVO motif space (pure abnormal volume, smoothed, ratio, quiet-day-filtered, inverse-Amihud, signed, relative share-of-universe, rank-ensemble)

## 6. Files this brief was derived from

- `worldquant-5-agent-workflow/SKILL.md` (lines 297-320: A-share adaptation lessons)
- `worldquant-5-agent-workflow/references/common-pitfalls.md` (the 12 named pitfalls)
- `worldquant-5-agent-workflow/references/validation-gates.md` (G1-G5 thresholds)
- `worldquant-5-agent-workflow/references/execution-delay-audit.md`
- `worldquant-5-agent-workflow/references/tvt-split-template.md`
- `logs/20260423_a_share_etf_reversal_v1/outputs/final_summary.md` (reversal session close-out)
- `logs/20260423_a_share_etf_weekly_tqpb_v1/outputs/final_summary.md` (weekly session close-out)
