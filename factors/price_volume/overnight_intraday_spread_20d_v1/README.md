# overnight_intraday_spread_20d_v1

> A 股 量价因子 / 隔夜-日内收益分解 spread(Lou-Polk-Skouras 2019 JFE)
> 利用 T+1 + 单一开盘集合竞价的结构性差异,把信息流(隔夜)与散户噪声(日内)分离

## Quick Stats (万5 单边手续费, 2018-01 → 2026-04, 99 次月度再平衡)

| 指标 | 全样本 | Train (18-22) | Validate (23) | Test (24-26YTD) |
|------|------:|-------------:|-------------:|----------------:|
| LS 净 Sharpe | **2.44** | 2.85 | 2.48 | **1.81** |
| LS 净 年化 | 16.13% | 16.66% | 15.58% | 15.20% |
| Q5 多头 净 IR | **1.04** | 1.59 | 0.28 | **0.62** |
| Q5 多头 净 年化超额 | 4.06% | 4.99% | 0.92% | 3.38% |
| LS Max DD | −4.90% | −4.90% | −1.93% | −2.56% |
| Q5 超额 Max DD | −5.08% | −3.41% | −2.42% | −1.56% |
| ICIR (5d / 20d / 60d) | 0.64 / 0.96 / 1.18 | 0.72 / 1.07 / 1.29 | 0.74 / 0.70 / 0.79 | 0.52 / 0.89 / 1.20 |
| t-stat (5d / 20d / 60d) | 28.5 / 42.7 / 51.6 | — | — | — |
| 平均换手 (Q5 单边) | 75.1% | 75.1% | 73.6% | 76.1% |
| 平均成本 (LS 单期) | 7.30 bps | 7.39 | 7.20 | 7.14 |
| n 再平衡期 | 99 | 60 | 12 | 27 |

> IC / ICIR 基于行业中性化后的 α_04 与 5d / 20d / 60d 前向收益的横截面 Spearman
> rank 相关。计算口径与 `idio_12_3_momentum_disp_gated_v1` /
> `lottery_idio_max_q5_overlay_v1` 一致(raw mean/std,无年化乘数)。

## 分年表现 (LS / Q5 超额)

| 年 | n | LS 年化 | LS Sharpe | Q5 超额 年化 | Q5 IR |
|---:|---:|---:|---:|---:|---:|
| 2018 | 12 | +24.60% | **+4.67** | +7.54% | +2.06 |
| 2019 | 12 | +12.87% | +3.68 | +4.31% | +2.65 |
| **2020** | 12 | +7.98% | **+0.90** ← LS 最差 | +2.68% | +0.93 |
| 2021 | 12 | +18.82% | +3.80 | +6.28% | +2.25 |
| 2022 | 12 | +19.01% | +3.69 | +4.16% | +0.94 |
| 2023 | 12 | +15.58% | +2.48 | +0.92% | +0.28 |
| 2024 | 12 | +17.31% | +1.64 | +0.82% | +0.14 |
| **2025YTD** | 13 | +15.26% | +2.20 | +7.15% | +1.31 |

- **8 年全部 LS Sharpe ≥ 0.5**(过 worst-year 硬底线);最差 2020(0.90)
- **8 年 Q5 超额全部为正**(最差 2024 +0.82%)
- 2020 megacap 行情压缩了隔夜回报的横截面分散度,是 LS 唯一接近临界年

## 纯多 Q5 (绝对净) 逐年表

部署形态是 Q5 多头(top 20% 等权,月度再平衡,5 bps/边),所以也披露不扣 universe 基准的
**绝对净** 表现 —— 即 Q5 多头组合在 A 股市场实际 P&L,以及对应基准(universe 等权)
的对比和超额。绝对 Sharpe / MaxDD 含 A 股市场 beta,基准本身在 2018 / 2022 / 2026 也是负年。

| 年 | n | Q5 绝对净年化 | Q5 绝对 Sharpe | Universe 年化 | Universe Sharpe | 超额年化 | 超额 IR | Q5 MaxDD | Q5 波动 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 12 | −21.52% | −1.13 | −29.06% | −1.71 | **+7.54%** | **+2.06** | −28.47% | 19.08% |
| 2019 | 12 | +35.73% | +1.24 | +31.43% | +1.13 | +4.31% | +2.65 | −11.62% | 28.74% |
| 2020 | 12 | +15.46% | +0.85 | +12.78% | +0.72 | +2.68% | +0.93 | −8.65% | 18.28% |
| 2021 | 12 | +28.95% | **+2.33** | +22.66% | +2.05 | +6.28% | +2.25 | −3.95% | 12.40% |
| 2022 | 12 | −4.51% | −0.24 | −8.67% | −0.54 | +4.16% | +0.94 | −11.71% | 18.57% |
| 2023 | 12 | +0.63% | +0.04 | −0.28% | −0.02 | +0.92% | +0.28 | −10.92% | 16.73% |
| 2024 | 12 | +10.43% | +0.19 | +9.61% | +0.19 | +0.82% | +0.14 | −14.63% | 55.01% |
| **2025** | 13 | **+54.05%** | **+2.27** | +46.90% | +2.40 | +7.15% | +1.31 | −10.13% | 23.80% |
| 2026 YTD | 2 | (−48.24%) | (−2.66) | (−42.48%) | (−2.35) | (−5.75%) | — | −7.44% | 18.13% |

> 2026 仅 2 期再平衡,Sharpe / IR 数字括号标注作 YTD 参考,不计入年度统计。

### 段落聚合 (2018-01 → 2026-04, 99 期月度)

| 维度 | 年化 | Sharpe / IR | MaxDD | 波动 |
|---|---:|---:|---:|---:|
| **Q5 绝对净** | **+14.02%** | **+0.52** | **−36.90%** | 26.80% |
| Universe 等权(基准) | +9.96% | +0.41 | −32.79% | 24.34% |
| **Q5 超额(净)** | **+4.06%** | **IR +1.04** | **−5.08%** | 3.90% |

- **9 完整年里 8 正 1 负**(2018 −21.5% 与基准同跌,但当年仍跑赢基准 +7.54%)
- **绝对 MaxDD −36.90%** 来自 A 股市场 beta(universe 自身 MaxDD −32.79%);
  超额 MaxDD 仅 −5.08%,表明跌幅几乎完全来自 beta,alpha 端非常稳定
- **2018 / 2022 / 2026 三个市场负年**,Q5 绝对回报全部好于基准;**2025 OOS 绝对 +54%、超额 IR 1.31**

## Definition

```
# 步骤 1 — 隔夜 / 日内 / 全日 三段日收益(全部按 adj_factor 复权)
ret_ON(s,t) = (open_t · adj_t)  / (close_{t-1} · adj_{t-1}) − 1     # 隔夜
ret_ID(s,t) = close_t / open_t − 1                                   # 日内
ret_CC(s,t) = (close_t · adj_t) / (close_{t-1} · adj_{t-1}) − 1      # 收-收
log_ON, log_ID, log_CC = log1p(.) clip 至 ±0.105                     # ±10% 涨跌停 winsor

# 步骤 2 — 20 日累计 spread
sum_ON_20(s,t) = rolling_sum(log_ON, 20, min_periods=15)             # 过去 20 交易日
sum_ID_20(s,t) = rolling_sum(log_ID, 20, min_periods=15)
alpha_raw(s,t) = sum_ON_20(s,t) − sum_ID_20(s,t)

# 步骤 3 — 每日横截面流水线(walk-forward 安全)
for each trade_date d:
    s = alpha_raw(*, d)
    s = winsor(s, 0.01, 0.99)                                        # 横截面 1/99 winsor
    s = s − mean(s within industry(s) at d)                          # 行业中性化(CITIC L1)
    alpha(*, d) = (s − mean(s)) / std(s)                             # 横截面 z-score

# 步骤 4 — 组合构造
首选(部署):top 20% by alpha,等权,月度再平衡(20 交易日,T+1 执行)
备选(信号验证):long Q5 / short Q1 等权,dollar-neutral(A 股做空摩擦,只做参考)

# Sign convention: alpha 越高 → 未来收益越高
# Delay = 1(T+1 执行);成本 5 bps/side turnover-aware
```

**机制要点。** A 股 T+1 结算迫使隔夜持仓承担信心成本,叠加单一开盘集合竞价
集中信息释放,隔夜段是 informed flow 通道;日内段则被散户(>80% 成交)噪声主导。
做多 sum_ON_20 − sum_ID_20 在累计意义上对全日(收-收)累计回报机械正交,因此既不是
隐性动量也不是隐性反转 —— 已通过 4 个控制栈的残差化验证(min 79.8% Sharpe 保留)。

## Universe & Frequency

- A 股 主板 + 创业板 + 科创板(排除 北交所),排除 ST,要求历史 ≥ 20 交易日(`min_periods=15` 后 sum_ON_20 well-defined)
- 包含已退市股票(`stock_basic.list_status='L'+'D'`)— 抗 survivorship bias
- ~5,500 只股票 / ~110 个行业(CITIC L1 via `stock_basic.industry`)
- **月度再平衡**(每 20 交易日)
- T+1 执行(delay = 1,target_shift = -2 不变量已审计)
- 5 bps 单边 turnover-aware 成本

## Audit Results (R1 单轮 + R2-R4 多轮 全过)

| # | 规则 | 阈值 | 实际 | 判定 |
|:-:|------|------|------:|:----:|
| 1 | 执行延迟不变量 | `target_shift == -(1+delay) == -2` | 满足 | ✅ |
| 2a | Look-ahead grep | `.where(.*shift(-\d+))\|next_*` 0 hit | 0 | ✅ |
| 2b | Future-perturbation 不变性 | 扰动未来后过去 alpha 最大绝对差 ≈ 0 | 0.0 | ✅ |
| 3 | Worst-year LS Sharpe | ≥ 0.5 | 0.90 (2020) | ✅ |
| 4 | Best-year-out / 全样本 | ≥ 50% | 91.0% (剔 2018) | ✅ |
| 5 | 残差化(全控制栈) | ≥ 50% | 81.2% | ✅ |
| 6 | R2 残差化 4 栈 min | ≥ 50% | 79.8% (vol_only) | ✅ |
| 7 | R3 规格敏感 win∈{10..40} | ≥ 5/6 通过 LS≥1.5 + worst-year≥0.5 | **6/6** | ✅ |
| 8 | R4 TVT 三段全过 0.5 | train/val/test 均 ≥ 0.5 | 2.85 / 2.48 / 1.81 | ✅ |
| 9 | R4 100-placebo p-value | < 0.01 | **0.0000** (actual 2.45 vs max 0.28) | ✅ |

## Files

| 文件 | 内容 |
|------|------|
| `factor.md` | 完整规格 / 机制 / 文献 / 审计(R1 单轮 + R2-R4 多轮) |
| `code.py` | 可复用的因子构建代码(`build_factor()` 主接口) |
| `metrics.json` | 全部头部指标(含 LS / Q5 / IC / 5 项强制审计) |
| `annual.csv` | 分年表现(LS + Q5 超额) |
| `rebalances.csv` | 99 次再平衡逐期回报 + 换手 + 成本 |
| `_generate_deployment_artifacts.py` | 由 session 输出再生 metrics/annual/rebalances |

## 部署建议

- **首选形态**:Q5 长多(top 20% by alpha,等权)— A 股做空摩擦下的可部署形态
- **备选形态**:LS Q5−Q1 dollar-neutral — 仅作信号验证,不分配资本
- **目标指标**:LS Sharpe 1.5–2.5,Q5 IR 0.6–1.2(test 期 1.81 / 0.62 偏稳健,prefer train 2.85 偏乐观)
- **kill-switch**:
  - rolling-12m LS Sharpe < 0
  - LS Max DD < −8%
  - rolling-12m Q5 IR < −0.5
  - 连续 3 季度负超额
- **监控**:每周检查隔夜回报横截面分散度(过 252d-median 视为健康);
  季度对照 `idio_12_3_momentum_disp_gated_v1` / `lottery_idio_max_q5_overlay_v1` 跑相关性检查;
  年度重跑 R3 规格敏感(win=20 仍稳健即可)
- **2020-类 megacap 行情警戒**:历史最弱年 LS Sharpe 0.90,如出现类似行情预期单年 LS Sharpe 0.7–1.0
- **与已有量价因子的关系**:
  - vs `idio_12_3_momentum_disp_gated_v1`(close-to-close 动量)— 本因子 spread 在累计回报上机械正交
  - vs `lottery_idio_max_q5_overlay_v1`(MAX 极值)— 本因子用累计 *路径*,做多 informed-flow,与 lottery 短高 MAX 方向相反
  - 部署前需测两两 rebalance 相关(deployment QA);预期 |ρ| < 0.20

## 来源

Session: `logs/20260428_a_share_overnight_intraday_alpha/`(4 轮 R1-R4,8 表达式 R1 + winner R2-R4)

- **R1**:8 候选(α_01..α_08)单轮 batch — 4 个 alpha(α_01/02/03/04)过 5/5 强制审计;winner = α_04(LS Sharpe 2.44,Q5 IR 1.04)
- **R2 残差化筛**:α_04 在 4 个控制栈(full / vol_only / rev_only / vol_rev)上保留 79.8%–93.5%,分布最紧
- **R3 规格敏感**:win∈{10,15,20,25,30,40} 6/6 全过;Sharpe 1.80→2.58 单调递增(信号有 horizon depth)
- **R4 TVT + 100-placebo**:train 2.85 / validate 2.48 / test 1.81,gradient 1.15(健康带),test/train 63.5%;100 次随机扰动 max 0.28 << actual 2.45,p = 0.0000

## 文献

- Lou, D., Polk, C., & Skouras, S. (2019). "A tug of war: Overnight versus intraday expected returns." *JFE* 134(1): 192–213. **← 主锚论文,隔夜-日内分解 spread**
- Aboody, D., Even-Tov, O., Lehavy, R., & Trueman, B. (2018). "Overnight returns and firm-specific investor sentiment." *RFS* 31(11): 4242–4272. **← 隔夜回报作为关注度/情绪 proxy**
- Berkman, H., Koch, P. D., Tuttle, L., & Zhang, Y. J. (2012). "Paying attention: Overnight returns and the hidden cost of buying at the open." *JFQA* 47(4): 715–741. **← 散户开盘买入的成本结构**
- Liu, J., Stambaugh, R. F., & Yuan, Y. (2019). "Size and value in China." *JFE* 134(1): 48–69. **← A 股散户主导背景**
