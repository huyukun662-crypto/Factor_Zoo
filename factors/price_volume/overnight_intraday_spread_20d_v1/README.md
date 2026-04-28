# overnight_intraday_spread_20d_v1

A-share volume-price factor: 20-day cumulative log-overnight return minus
20-day cumulative log-intraday return, industry-demeaned and cross-section
z-scored per date.

| metric | LS Q5−Q1 net | Q5 long-only excess net |
|---|---:|---:|
| Sharpe / IR | **2.44** | **1.04** |
| Annualized return | 16.13 % | 4.06 % |
| Max drawdown | -4.90 % | -5.08 % |
| Worst-year LS Sharpe | 0.90 (2020) | — |

Source session: `logs/20260428_a_share_overnight_intraday_alpha/`
(1 round, 8 expressions, all 5 mandatory pre-PROMOTE audits clean).

See `factor.md` for the full specification.

Files:
- `code.py` — `build_factor()` entry point
- `factor.md` — economic thesis + headline metrics + audits
- `metrics.json` — machine-readable headline metrics
- `annual.csv` — per-year LS and Q5 metrics
- `rebalances.csv` — per-rebalance state (99 rows)
- `_generate_deployment_artifacts.py` — regenerates the three csv/json above from session outputs
