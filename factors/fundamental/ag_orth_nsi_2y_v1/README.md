# ag_orth_nsi_2y_v1

> A-share 基本面因子 / 投资异象（CGS 2008 + Daniel-Titman 2006），
> Asset Growth 对 Net Share Issuance 做截面 OLS 正交化后的 2 年复合信号。

## Quick Stats（5 bps/side, 月度再平衡, 2020-01 → 2025-04, 约 5.3 年）

| 指标 | Full | 2024 | 2025 YTD (68d) |
|------|------:|-----:|---------------:|
| **Sharpe abs (long-only Q5)** | **0.70** | 0.25 | 1.02 |
| **年化绝对回报 (Q5)** | **17.9%** | 9.7% | +9.3% (实际) |
| Sharpe excess (vs EW universe) | 0.86 | 0.24 | -0.61 |
| 年化超额 (vs EW) | 5.2% | 1.0% | -0.9% (实际) |
| 5/6 年绝对回报为正 | ✅ | — | — |
| 最差年绝对 Sharpe | -0.02 (2022, -0.4% 几乎平) | — | — |
| IC t-stat (20d / 60d) | 10.17 / 18.24 | — | — |
| 平均年化换手 | 219% | — | — |

**CAGR ≈ 17.5% / 5.3 年,NAV 1.0 → 2.22,隐含市场(EW)基准 12.7%.**

## Definition

```
# 1. 季度基本面信号 (PIT via f_ann_date + 1 trading day)
ag_2y  = -(total_assets_t - total_assets_{t-8q}) / total_assets_{t-8q}
nsi_2y = -(total_share_t  - total_share_{t-8q})  / total_share_{t-8q}

# 2. 行业中性化 (median per [trade_date, industry])
ag_2y_ind  = ag_2y  - group_median(ag_2y,  by=[trade_date, industry])
nsi_2y_ind = nsi_2y - group_median(nsi_2y, by=[trade_date, industry])

# 3. Winsor 1%/99% + z-score per trade_date
f5 = cs_winsor_z(ag_2y_ind)
g4 = cs_winsor_z(nsi_2y_ind)

# 4. 截面 OLS 残差化 (per trade_date)
ag_orth_nsi = f5 - (a_t + b_t * g4)     # 去掉 AG 中被 NSI 解释的"融资通道"部分

# 5. 等权混合 + 重新 z-score
signal = cs_winsor_z(0.5 * ag_orth_nsi + 0.5 * g4)

# 6. Top 20% (Q5) 等权 → 月度再平衡 → T+1 执行 → 5 bps/side cost
```

**符号约定**: 高分 = 做多（低增长 + 低增发 = 高预期回报）.

## Economic thesis (1 段)

q-理论 (Cochrane 1991) + Jensen 1986 帝国建造效应预言: 激进扩张的公司当前资本成本
低、未来预期回报低。扩张来自两个通道:
(a) 自有现金流做实体投资 (capex),
(b) 权益融资稀释老股东 (SPO/可转债/员工激励).

2020 A 股小票牛市同时推高 "融资型成长" (b) 股票价格, 让原始 AG 空头腿被摧毁.
把 AG **对 NSI 做截面 OLS 残差** 剥离通道 (b), 保留通道 (a) "实体过度投资",
再等权混合纯 NSI —— 得到两个正交的 q-理论信号.

## Why this version wins (vs naive composite)

| 因子 | Sharpe abs | Sharpe excess | 2020 Sharpe excess |
|---|---:|---:|---:|
| `raw_ag_2y_ind` (Round 1) | 0.58 | 0.59 | **-0.64** |
| `0.5·f5 + 0.5·g4` naive (r3_cma_2y) | 0.67 | 0.28 | -0.12 |
| `0.5·(f5⊥g4) + 0.5·g4` (this factor) | **0.70** | **0.86** | **+1.04** |

**正交化这一步把 2020 从 -0.64 Sharpe 翻到 +1.04，其他年基本不变.**

## Universe & Frequency

- A-share, panel.parquet 继承的宇宙（ST 已排除、上市 > 1 年）
- ~4,472 只股票 / 110 个行业中位数
- 月度再平衡（每 21 交易日）
- T+1 执行 (delay = 1)
- long-only Q5 (Top 20%)，等权

## Files

| 文件 | 内容 |
|---|---|
| `factor.md` | 完整 spec —— 经济理论 / 构造步骤 / 审计结果 / 部署规则 |
| `metrics.json` | 机器可读指标（IC, Sharpe, 年度, 审计） |
| `annual.csv` | 年度 Sharpe / 回报拆分 |
| `code.py` | 构造 + 选股生产脚本 |
| `picks/picks_YYYY-MM-DD_top100.csv` | 当前 Top-100 选股 |
| `picks/picks_YYYY-MM-DD_q5.csv` | 完整 Q5 (~700 股) backtest 同步 |
| `picks/latest.txt` | 最新一期摘要 |

## 使用

```bash
python3 factors/fundamental/ag_orth_nsi_2y_v1/code.py \
    --top-n 100 --also-q5 --min-mv-pct 0.30
```

默认从 `/home/user/Factor_Zoo/.cache/` 读数据，从 `factors/fundamental/ag_orth_nsi_2y_v1/picks/` 输出.

## Source session

`logs/20260423_a_share_asset_growth_investment/` — 3 rounds, 24 expressions,
see `outputs/alpha_ranking_round3.md` and `round_0003.yml` for decision record.

## Status

**PROMOTE**（绝对口径）; **RESEARCH-ONLY**（严格 excess 口径，仅因 2025 YTD 68 天样本）.

定位: A-share long-only nominal-return product (target CAGR 15%+).
**不是** market-neutral / hedge fund alpha.
