# Research Objective — A-share broad-base ETF style-timing factor (R1)

## Goal

Mine a daily timing factor that predicts the direction of the
**CSI 300 vs CSI 1000 style spread** in A-share, deployable as a long/flat/short
position on the spread (long 510300 ETF / short 512100 ETF when score > 0,
flat at 0, opposite when score < 0).

## Universe

- ETF (execution): `510300.SH`, `510500.SH`, `512100.SH` (CSI 300 / 500 / 1000)
- Index (signal construction): `000300.SH`, `000905.SH`, `000852.SH`
  (CSI 300 / 500 / 1000)

CSI 500 included for diagnostic / future "mid-cap leg" use; the R1 leg is
purely 300 vs 1000.

## TVT discipline

| Window | Range (half-open) | Trading days |
|---|---|---:|
| Train | [2018-01-01, 2022-01-01) | 973 |
| Val   | [2022-01-01, 2024-01-01) | 484 |
| Test (frozen) | [2024-01-01, 2026-04-25] | 558 |

Test window is **2.3y**, below the TVT template's 3y+ floor; PROMOTE
floors are still applied unchanged. RESEARCH-ONLY is the most likely
outcome by construction.

## Constraints (binding)

- Single round (R1) unless a clearly productive R2 direction emerges
- Rule of 8: exactly 8 expressions in the batch
- delay = 1 (signal at close of t → trade close-to-close from t+1)
- 5 bps per side per leg cost
- No constituent-stock pulls, no BRAIN, no QQBot
- A-share-specific lessons in `worldquant-5-agent-workflow/SKILL.md:297` apply
  except industry neutralization (N/A for index level)

## Evaluation primary metric

- TVT selection: `val_sharpe − 0.3·|train_sharpe − val_sharpe|`,
  eligible iff `train_sharpe > 0.5 AND val_sharpe > 0`.
- All 5 mandatory pre-PROMOTE audits enforced.

## Out of scope for this round

- Northbound flow / margin-trading / sentiment data (free-tier reliability uncertain)
- Multi-asset basket (300 vs 500 vs 1000 simultaneously)
- Intraday signals
