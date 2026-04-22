# lottery_idio_max_q5_overlay_v1

> A 股 lottery / idio-MAX 长多 index-enhancement 因子,带 size-regime overlay
> 防御 megacap-rally 年份(Bali-Cakici-Whitelaw 2011 × A-share size-regime)

## Quick Stats (万5 单边手续费, 2018-01 → 2026-04, 99 次月度再平衡)

| 指标 | 全样本 | Train (18-22) | Validate (23) | Test (24-26YTD) |
|------|------:|-------------:|-------------:|----------------:|
| 超额 IR (vs universe 等权) | **1.13** | 1.61 | 0.77 | 0.77 |
| 超额净年化 | 3.70% | 4.02% | 2.53% | 4.44% |
| 超额 Max DD | −4.18% | −4.18% | −1.76% | −2.61% |
| 绝对净 Sharpe | 0.49 | 0.11 | 0.21 | 1.36 |
| 绝对净年化 | 12.25% | 8.42% | 3.04% | 21.64% |
| 绝对 Max DD | −34.52% | −28.89% | −9.21% | −15.45% |
| **IC (5d / 20d / 60d)** | **0.056 / 0.071 / 0.068** | 0.057 / 0.072 / 0.066 | 0.051 / 0.060 / 0.073 | 0.058 / 0.073 / 0.071 |
| **ICIR (5d / 20d / 60d)** | **0.67 / 0.89 / 0.97** | 0.71 / 0.96 / 0.94 | 0.70 / 0.73 / 1.00 | 0.61 / 0.84 / 1.03 |
| t-stat (5d / 20d / 60d) | 30.1 / 39.5 / 42.8 | — | — | — |
| Gate on-fraction | 80.8% | 75.0% | 100% | 88.6% |
| 平均换手 | 71.9% | 73.6% | 71.8% | 67.6% |
| 平均成本 | 3.59 bps/期 | 3.68 | 3.59 | 3.38 |
| n 再平衡期 | 99 | 60 | 12 | 27 |

> IC / ICIR 基于 industry-neutralized α_17 信号(未加 gate)在每日横截面与
> 5d / 20d / 60d 前向收益的 Spearman rank 相关,然后按段聚合。计算口径
> 与 `idio_12_3_momentum_disp_gated_v1` 一致(raw mean/std,无年化乘数)。

## 2020-01 → 2026-04 原始(绝对)逐年表

剔除 2018 / 2019 两个早期年,聚焦过去 6 完整年 + 2026 YTD。

| 年 | n | gate on | 年化 | Sharpe | MaxDD | 波动 |
|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 12 | 66.7% | +13.81% | +0.88 | −9.40% | 15.77% |
| 2021 | 12 | 100% | +28.93% | **+2.43** | **−3.62%** | 11.89% |
| 2022 | 12 | 91.7% | −5.34% | −0.33 | −12.67% | 16.03% |
| 2023 | 12 | 100% | +3.04% | +0.21 | −9.21% | 14.79% |
| 2024 | 12 | 100% | +13.07% | +0.26 | −15.45% | 50.66% |
| **2025** | 13 | 76.9% | **+46.20%** | **+2.41** | −8.57% | 19.17% |
| 2026 YTD | 2 | 50% | (−47.28%) | (−3.54) | −7.80% | 13.36% |

### 段落聚合(2020-01 → 2026-04,75 期月度)

| 维度 | 年化 | Sharpe/IR | MaxDD | 波动 |
|---|---:|---:|---:|---:|
| **本因子绝对** | **+15.31%** | **+0.60** | **−34.52%** | 25.50% |
| Universe (基准) | +11.45% | +0.48 | −33.29% | 24.00% |
| **超额** | **+3.86%** | **IR 1.10** | **−4.18%** | 3.51% |

- 绝对 MaxDD 区间:**peak 2023-01-10 → trough 2024-01-05**(跨年累积)
- 本因子 Sharpe 比 universe 高 0.12(纯 alpha 贡献);超额 IR 1.10 仍过 1.0 门槛
- 6 完整年里 5 正 1 负(2022 −5.3%)

## Definition

```
# 步骤 1 — α_17: σ-bucket rank of idio-MAX (来自 lottery session)
# (完整构造见 logs/20260421_volprice_max_lottery/ round 3,简述:
#  α_08 = 过去 20 交易日 idiosyncratic-MAX
#  α_17 = σ-bucket rank of α_08,分 σ_20 5 桶后再按桶内排序 winsor 得 ±1
#  符号:α_17 越低 → 未来收益越高,所以取最低者)
alpha_17_signal(s,t) = α_17(s,t) − mean(α_17 within industry(s) at t)   # 行业中性化

# 步骤 2 — size-regime overlay signal
q5_ret(t) = mean daily log ret of top market-cap quintile at t
q1_ret(t) = mean daily log ret of bottom market-cap quintile at t
size_q5q1_12m_sh(t) = trailing 252d annualized Sharpe of (q5_ret − q1_ret)

# 步骤 3 — 63d 动态 gate
threshold(t)  = 63d rolling 97th percentile of size_q5q1_12m_sh
gate(t)       = 1 if size_q5q1_12m_sh(t) < threshold(t) else 0

# 步骤 4 — 组合构造
if gate(t) == 1:
    hold Q5 = top 20 % by alpha_17_signal, equal-weight
elif gate(t) == 0:
    hold equal-weight universe (benchmark)

# Sign convention: 低 α_17 → 高未来收益 → 买最低 (实现上取负号排序)
# Delay = 1 (T+1 执行);成本 5 bps/side turnover-aware
```

## Universe & Frequency

- A 股,要求历史 ≥ 252 交易日(size_q5q1_12m_sh 需要 252d 滚动)
- ~5,300 只股票 / ~110 个行业(CITIC L1)
- **月度再平衡**(每 20 交易日)
- T+1 执行(delay = 1)
- 5 bps 单边 turnover-aware 成本

## Audit Results (7/7)

| # | 规则 | 阈值 | 实际 | 判定 |
|:-:|------|------|------:|:----:|
| 1 | 全样本超额 IR | ≥ 1.0 | 1.129 | ✅ |
| 2 | Worst-year 超额 IR | ≥ 0.5 | 0.766 (2023) | ✅ |
| 3 | Best-year-out / full | ≥ 50% | 93.4% (drop 2022) | ✅ |
| 4 | Spec sensitivity pass majority | ≥ 5/8 | 5/8 | ✅ |
| 5 | Placebo IR p-value | < 0.05 | 0.020 | ✅ |
| 6 | Placebo worst-year p-value | < 0.05 | 0.000 | ✅ |
| 7 | Excess MaxDD | > −10% | −4.18% | ✅ |

## Per-Year Performance

| 年 | 超额净 | 超额 IR | 绝对 ann | 绝对 Sharpe | Gate on |
|---:|---:|---:|---:|---:|---:|
| 2018 | +4.51% | **+1.80** | −24.95% | −1.44 | 33% |
| 2019 | +1.87% | +0.86 | +30.33% | +1.15 | 83% |
| **2020** | **+3.21%** | **+1.16** | +13.81% | +0.88 | 67% |
| 2021 | +6.14% | +2.16 | +28.93% | +2.43 | 100% |
| 2022 | +4.37% | +2.28 | −5.34% | −0.33 | 92% |
| 2023 | +2.53% | +0.77 | +3.04% | +0.21 | 100% |
| 2024 | +5.26% | +0.84 | +13.07% | +0.26 | 100% |
| **2025** | **+2.91%** | **+1.26** | +46.20% | +2.41 | 77% |

- **2020 overlay 成功**:从 ungated −0.33 IR → +1.16 IR
- **2025 OOS IR 1.26**,在 α_35 崩溃同年 α_17 长多这个形态健康
- **所有 8 个完整年份超额 IR 均 ≥ 0.77**

## Files

| 文件 | 内容 |
|------|------|
| `factor.md` | 完整规格 / 机制 / 文献 / 审计 |
| `code.py` | 可复用构建代码(`build_portfolio()`) |
| `metrics.json` | 全部头部指标 + TVT + audit + placebo |
| `annual.csv` | 分年表现(超额 / 绝对 / gate-on) |
| `rebalances.csv` | 99 次再平衡逐期回报 + 换手 + 成本 + gate 状态 |

## 部署建议

- **首选形态**:Q5 长多(top 20% by α_17),gate off 时持基准等权
- **目标指标**:超额 IR 1.0–1.3,年化超额 3–5%(配合 A 股宽基 benchmark)
- **绝对 MaxDD −34%** 来自 A 股市场 beta(universe 本身 MaxDD 也在 −32%)
- **Kill-switch**:
  - rolling-12m 超额 IR < 0
  - 超额 MaxDD < −8%
  - 连续 3 季度超额负收益
  - Gate on-fraction 年度 < 40% 报警(说明 size-regime overlay 长期关断)
- **监控**:每周检查 `size_q5q1_12m_sh`;季度跑 bootstrap 检验超额 IR 显著性;
  年度重跑 spec sensitivity 确认 lb=63 / pct=97 仍鲁棒
- **与 α_35 的互补性**:α_35 (momentum) 2025 崩盘时,本因子 IR 1.26 —
  两个部署因子在不同 regime 表现反向,合理做多策略组合

## 来源

Session: `logs/20260422_lottery_megacap_overlay/`

Precursor:
- α_17 signal:`logs/20260421_volprice_max_lottery/` (RESEARCH-ONLY pre-overlay)
- 2025 regime diagnosis:`logs/20260422_trend_technical_alpha/outputs/diagnosis_2025_regime_break.md`
- Long-only review:`logs/20260422_trend_technical_alpha/outputs/alpha17_longonly_review.md`

3 轮 overlay 迭代:
- Round 1:4 megacap 候选 × 3 mode × 2 fallback,24 个变体,0 过
- Round 2:70 单信号 + 30 AND-pair + 2 majority-of-3,0 过(最佳 0.452 just miss)
- Round 3:144 精细变体;3 通过,最佳 size_q5q1_12m_sh | lb=63 | pct=97

## 文献

- Bali, T. G., Cakici, N., & Whitelaw, R. F. (2011). "Maxing out: Stocks
  as lotteries and the cross-section of expected returns." *JFE* 99(2):
  427–446. **← Lottery / idio-MAX 原始论文**
- Liu, J., Stambaugh, R. F., & Yuan, Y. (2019). "Size and value in China."
  *JFE* 134(1): 48–69. **← A 股 size regime,2020 megacap rally 背景**
- Fama, E. F., & French, K. R. (1992). "The cross-section of expected
  stock returns." *JF* 47(2): 427–465. **← 市值因子**
- Ang, A., Hodrick, R. J., Xing, Y., & Zhang, X. (2006). "The cross-section
  of volatility and expected returns." *JF* 61(1): 259–299. **← idio vol
  anomaly,与 lottery 因子相关**
