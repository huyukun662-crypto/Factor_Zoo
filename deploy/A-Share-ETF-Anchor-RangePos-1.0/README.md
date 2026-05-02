# A-Share ETF Anchor / Range-Position Strategy (v1.1)

> **A 股 ETF 多窗口截面 range-position 因子** + 21-phase ensemble + 10% 年化 vol-target,
> 长多 top-3 of 33-ETF Tushare universe,5 bps/侧。
>
> **Full sample (2020-01 → 2026-04, daily, 21-phase monthly rebal):**
> Net excess Sharpe **1.221** · Test (23-26) **1.046** · Max DD **-14.8%** · **7/7 年正**
>
> v1.1 vs v1.0: +21% Sharpe; worst year (2024) 转正 -0.13 → +0.20。
> 详见 [CHANGELOG.md](CHANGELOG.md)。

---

## Headline performance v1.1 (excess vs equal-weight 33-ETF benchmark, after 5 bps/side + vol target)

| 区间 | Sharpe excess | Sharpe portfolio | Sharpe bench |
|---|---:|---:|---:|
| Train (2020-2021) | ~1.83 | — | — |
| Validate (2022) | 1.32 | — | — |
| **Test (2023-2026)** | **1.046** | — | — |
| **Full** | **1.221** | 1.221 | 0.640 |

**7/7 年净超额为正**（最弱年 2024 净超额 +2.1%, Sharpe +0.20）。
Max DD (excess) -14.8%，2024 主题轮动期。

## Per-year breakdown v1.1

| year | n days | Sharpe excess net | Excess return | Portfolio return | Bench return |
|------|------:|------------------:|--------------:|-----------------:|-------------:|
| 2020 |   243 |          1.985   |      +20.6 %  |          +55.0 % |       +34.4 % |
| 2021 |   243 |          1.668   |      +18.6 %  |          +21.9 % |        +3.3 % |
| 2022 |   242 |        **1.316** |    **+34.8 %**|          +18.0 % |       −16.8 % |
| 2023 |   242 |          1.196   |      +13.1 %  |           +9.5 % |        −3.6 % |
| 2024 |   242 |          0.198   |       +2.1 %  |          +14.4 % |       +12.3 % |
| 2025 |   243 |          1.210   |      +12.3 %  |          +42.3 % |       +30.0 % |
| 2026* |    77 |        **2.542** |       +9.7 %  |          +14.5 % |        +4.8 % |

(*2026 is partial: 4 months Jan-Apr.)

**2022 是签名年**：基准跌 16.8%（A 股熊市），策略超额 **+34.8%**（Sharpe **+1.32**）。
v1.1 比 v1.0 在 2022 多赚 26 个百分点，主要因为银行 ETF (515290) 是 2022 最强 sector
之一，且新加入的中证 1000 / 通信 ETF 补全了 v1.0 缺失的多样化。

---

## Strategy architecture

```
                  ┌────────────────────────────────┐
                  │ 32 A-share ETFs (Yahoo daily)   │
                  └────────────────┬───────────────┘
                                   │  drop short-history
                                   ▼
                  ┌────────────────────────────────┐
                  │  20-ETF core (≥1500 trading days)│
                  └────────────────┬───────────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              │  Multi-window range_pos signal:          │
              │  for w in {60, 120, 252, 500}:           │
              │     rp_w = (close - min_w)/(max_w - min_w)│
              │  signal = mean(rank_xs(rp_w))            │
              └────────────────────┬────────────────────┘
                                   ▼
            ┌──────────────────────────────────────────┐
            │  21-phase ensemble:                       │
            │  every trading day t deploy 1/21 NAV      │
            │  to top-3 ETFs by signal_t,               │
            │  hold 21 trading days, recycle.           │
            └──────────────────────┬───────────────────┘
                                   ▼
            ┌──────────────────────────────────────────┐
            │  Cost: 5 bps/side per phase rebal day     │
            │  scaled by 1/21 NAV fraction              │
            └──────────────────────┬───────────────────┘
                                   ▼
            ┌──────────────────────────────────────────┐
            │  Excess = portfolio - bench (20-ETF EW)   │
            │  Vol-target: scale = clip(0.10/vol60, 2x) │
            │              .shift(1)  ← causal          │
            │  Final excess = scale × raw excess        │
            └──────────────────────┬───────────────────┘
                                   ▼
                         live PnL stream
```

---

## Quick start

```bash
pip install -r requirements.txt

# 1. Fetch 32 ETFs from Yahoo (~20s, no Tushare token required)
python scripts/01_fetch_data.py

# 2. Build the multi-window range-position signal
python scripts/02_build_signal.py

# 3. Backtest end-to-end (writes results/metrics.json, peryear.csv, pnl.csv...)
python scripts/03_run_strategy.py

# 4. Print today's top-3 picks across all 21 phases
python scripts/04_latest_picks.py
```

End-to-end runtime ≈ 30s on a laptop.

---

## Known limitations

1. **2024 weakness**: −1.4 % cum excess, the only negative year. Mid-cap thematic
   rotation broke the anchor at short horizons. Cumulative excess of −1.4 %
   passes the > −5 % economic-damage floor; Sharpe of −0.13 misses the strict
   ≥ 0.5 worst-year-Sharpe floor. Status is therefore **ADMITTED-CANDIDATE**,
   not full DEPLOYED.
2. **Universe survivorship**: 20-ETF core selected by ≥1500 valid days. Bias is
   bounded (drop only 14 late-listed thematics) but non-zero for 2019-2020.
3. **Confidence interval**: Newey-West-corrected Sharpe std ≈ 0.20 in this
   sample, so 95% CI ≈ 0.6-1.4. Headline 1.007 is genuinely above 0 but
   spans values from "research-grade" to "deployable-grade".
4. **Rebal-phase bias warning**: prior single-phase backtests of this factor
   (R1 of source session) reported Sharpe 0.628 vs the honest 21-phase
   ensemble 0.24-1.0 spread. **Always use 21-phase ensemble for any deploy
   form** — single-phase numbers are silently selection-biased.

---

## Natural ensemble candidate

This factor is anti-correlated by year with the catalog's existing
`inv_ivol_voltarget_bondrotate_etf_v2`:

| year | this factor | inv_ivol_v2 |
|---|---|---|
| 2022 | **+0.84 Sharpe** | +0.23 |
| 2024 | -0.13            | **+0.73** |

A 50/50 ensemble averages to roughly +0.55 in both stress years and would clear
the strict ≥ 0.5 worst-year-Sharpe floor for full DEPLOYED admission.

---

## File layout

```
A-Share-ETF-Anchor-RangePos-1.0/
├── README.md                      # this file
├── STRATEGY.md                    # full strategy spec + audits + literature
├── CHANGELOG.md
├── LICENSE                        # MIT
├── requirements.txt
├── .gitignore
├── scripts/
│   ├── 01_fetch_data.py           # Yahoo daily for 32 ETFs
│   ├── 02_build_signal.py         # multi-window range_pos rank avg
│   ├── 03_run_strategy.py         # 21-phase ensemble backtest
│   └── 04_latest_picks.py         # current top-3 picks per phase
├── data_cache/                    # (regenerated; gitignored)
└── results/                       # (regenerated)
    ├── metrics.json
    ├── peryear.csv
    ├── monthly.csv
    ├── pnl.csv
    ├── holdings.csv
    ├── picks_<latest_date>.csv
    └── latest_aggregate.csv
```

Source factor: [`factors/price_volume/anchor_range_pos_etf_v1/`](../../factors/price_volume/anchor_range_pos_etf_v1/)
Source session: [`logs/20260502_a_share_etf_anchor_high_v1/`](../../logs/20260502_a_share_etf_anchor_high_v1/) (4 rounds, R1-R4)
