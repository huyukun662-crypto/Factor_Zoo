# Session Objective — A-share Overnight–Intraday Return Decomposition Alpha

**Session:** `20260428_a_share_overnight_intraday_alpha`
**Date:** 2026-04-28
**Trigger:** user request `/worldquant-5-agent-workflow 挖一个A股量价因子`
**Branch:** `claude/build-price-volume-factor-w8QPW`

## Goal
Mine a new A-share volume-price factor that is **economically distinct** from the
two factors already in `factors/price_volume/`:

- `idio_12_3_momentum_disp_gated_v1` — idiosyncratic 12-3 momentum + dispersion gate
- `lottery_idio_max_q5_overlay_v1`   — MAX / lottery demand + size-regime overlay

The new factor must:

1. Use only OHLCV data already cached (`open`, `close`, `vol`, `amount`, `adj_factor`,
   `circ_mv`/`total_mv`).
2. Survive industry neutralization (mandatory for A-share volume-price per CLAUDE.md).
3. Pass the 5 mandatory pre-PROMOTE audits or — if real data is unavailable in
   the runtime environment — be packaged as RESEARCH-ONLY with a fully runnable
   pipeline.

## Constraint
The dev container has no Tushare token and no `.cache/*.parquet` files. The
pipeline must therefore be:

- runnable on the standard `.cache/` layout when real data is present, AND
- demonstrably G1/G2 clean (importable + runs end-to-end without exception)
  on a synthetic A-share-like panel inside the container.

Real-data G3/G4/G5 gates and the 5-audit decision are explicitly DEFERRED
until the user runs the pipeline against the real cache.
