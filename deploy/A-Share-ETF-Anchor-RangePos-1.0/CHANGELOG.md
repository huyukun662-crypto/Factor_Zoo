# Changelog

## 1.0 — 2026-05-02

Initial deploy package for `anchor_range_pos_etf_v1`, ADMITTED-CANDIDATE
status from session `logs/20260502_a_share_etf_anchor_high_v1` (4 rounds).

- 32-ETF Yahoo daily fetcher (no Tushare dependency)
- Multi-window range-position signal (60/120/252/500)
- 21-phase ensemble long-only top-3 backtest on 20-ETF core universe
- 10% portfolio vol-target overlay (causal, t-1 vol)
- 5 bps/side cost
- Latest-picks generator with per-phase next-rebal schedule

Headline (full sample 2020-01 → 2026-04, after 5 bps + vol-target):
- net excess Sharpe **1.007**
- Train (20-21) 1.088 / Validate (22) 0.844 / Test (23-26) 1.003
- 6/7 positive years, max DD -13.5 %
- Catalog inclusion threshold (net Sharpe ≥ 1.0) cleared
