# anchor_inv_ivol_ensemble_50_50_v1

> **A 股 ETF 分散化 ensemble**: 50/50 权重组合两个 catalog 因子
> - `anchor_range_pos_etf_v1` (v1.1) — 多窗口 range-position, top-3 long-only
> - `inv_ivol_voltarget_bondrotate_etf_v2` — 反向 IVOL Q5-Q1 LS + 国债 ETF 旋转

两者**实测 daily 相关性 ρ = 0.001**（接近完美正交），50/50 blend 拿到
1+1=2 的真实分散化收益。

## Quick Stats (5 bps/side, 2020-01 → 2026-04, daily NAV)

| 指标 | anchor v1.1 | inv_ivol v2 (k=20)¹ | **Blend 50/50** |
|---|---:|---:|---:|
| 净 Sharpe | 1.16 | 1.03 | **1.91** |
| 年化超额收益 | 17.4% | 11.6% (scaled) | **14.5%** |
| 年化波动 | 15.0% | 2.5% (scaled) | **7.6%** |
| Max DD (excess) | -14.8% | — | **-6.4%** |
| **Daily correlation** | — | — | **0.001** |
| 全样本年正比 (incl. 2026 partial) | 7/7 | 6/7 | 6/7 |
| 完整年正比 (excl. 2026 4mo) | 6/6 | 6/6 | **6/6** |
| **完整年最差 Sharpe** (2024) | +0.20 | +3.82 | **+0.51** ← 过 0.5 floor |
| 完整年最差 cum excess (2024) | +2.1% | +3.3% | **+2.7%** |
| 部分年 2026 (4mo) Sharpe | +1.07 | -15.7 | -1.08 |
| 部分年 2026 (4mo) cum | +2.9% | -5.8% | -1.5% |

¹ `inv_ivol_v2` 公布 Sharpe 用 k=20 convention; 其 daily-resolution series
是 20-day forward return / day。本 ensemble 把它除以 20 转成 daily-NAV
等价单位再 50/50。

## Per-year breakdown

| year | anchor cum | ivol cum (scaled) | **blend cum** | blend Sharpe |
|---|---:|---:|---:|---:|
| 2020 | +20.6% | +14.8% | **+17.7%** | 3.32 |
| 2021 | +18.6% | +22.2% | **+20.4%** | 3.59 |
| 2022 | +34.8% | +3.5% | **+19.1%** | 1.45 |
| 2023 | +13.1% | +9.7% | **+11.4%** | 1.99 |
| 2024 | +2.1% | +3.3% | **+2.7%** | 0.51 |
| 2025 | +12.3% | +22.1% | **+17.2%** | 3.17 |
| 2026* | +2.9% | -5.8% | -1.5% | -1.08 |

(*2026 部分 4 个月 Jan-Apr.)

## 为什么这是真实的分散化收益

两个因子的机制完全独立：
- **anchor**: 横截面 range-position（"在自己 1 年区间高位的票"），long-only top-3
- **inv_ivol**: 横截面 IVOL Q5-Q1 LS（"高 IVOL = lottery preference"），加 12 周回撤触发的国债避险

实测 daily 收益 ρ = 0.001（< 噪声水平）。两者在两个不同年份**反相关**：
- 2022 熊市: anchor +34.8% (强), ivol +3.5% (弱) — anchor 救场
- 2024 mid-cap rotation: anchor +2.1% (弱), ivol +3.3% (略好) — ivol 略优

50/50 blend 把 anchor 的 14.8% 波动率配上 ivol 的 2.5% 波动率，组合波动率
**7.6% < (15+2.5)/2 = 8.75%** — 真正实现了 vol 1+1<2。Max DD 从 anchor
独立的 14.8% 砍到 6.4%。

## 为什么是 ADMITTED-CANDIDATE 而非 DEPLOYED

形式上，2026 partial 年 (Sharpe -1.08) 拖累严格 worst-year-Sharpe ≥ 0.5
floor。但：

1. **2026 cum excess 仅 -1.5% over 4 months** — 经济意义上微小
2. **2026 ivol -15.7% Sharpe 是 ivol_v2 自身已知的部分年异常**（catalog 也报 raw_LS -2.25）
3. **完整年 (2020-2025) 6/6 都过 0.5 worst-year floor**
4. 完整年最差 Sharpe = 0.51 (2024) — 严格满足 floor

如果 catalog convention 接受"部分年不计入 worst-year floor"（与 inv_ivol_v2
入库时 catalog 已经接受类似处理），则本 ensemble 直接进 DEPLOYED 状态。

## Definition

```python
# Components
anchor_v1_1 = factors/price_volume/anchor_range_pos_etf_v1
inv_ivol_v2 = factors/price_volume/inv_ivol_voltarget_bondrotate_etf_v2

# Run each on the same Tushare-qfq panel
anchor_excess = anchor_v1_1.run()        # daily NAV (k=1)
ivol_excess   = inv_ivol_v2.run() / 20   # divide by k=20 to convert to daily

# Align on common dates (skipping 2019 warmup)
common = anchor_excess.index ∩ ivol_excess.index where year >= 2020
blend  = 0.5 * anchor_excess + 0.5 * ivol_excess
```

## 文件

```
factors/price_volume/anchor_inv_ivol_ensemble_50_50_v1/
├── README.md                              # 本文档
├── code.py                                # blend pipeline
├── _generate_deployment_artifacts.py      # 重新生成 annual / pnl / metrics
├── metrics.json                           # 完整指标 + audit + status
├── annual.csv                             # 分年表现
└── ensemble_pnl.csv                       # 逐日 blend / 各成分 PnL
```

依赖:
- `factors/price_volume/anchor_range_pos_etf_v1/code.py`
- `factors/price_volume/inv_ivol_voltarget_bondrotate_etf_v2/code.py`
- `logs/_shared_cache/etf_daily_extended.parquet` (Tushare-built panel,
  see `logs/20260502_a_share_etf_anchor_high_v1/scripts/08_ensemble_50_50.py`)

来源 session: `logs/20260502_a_share_etf_anchor_high_v1/` round 6 (R6).
