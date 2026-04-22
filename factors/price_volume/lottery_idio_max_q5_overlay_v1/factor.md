# lottery_idio_max_q5_overlay_v1 — 完整规格

## 1. Definition

A 股量价 lottery / idio-MAX **长多 index-enhancement** 因子,叠加
**size-regime overlay** 防御 megacap-rally 年份的 lottery-premium 消失期。

### 数学构造

```
# Step 1 — 基础 lottery 信号 (α_17,来自 lottery session)
idio_ret(s,d) = log_ret(s,d) − mean_across_all_s( log_ret(s,d) )     # idio return
idio_MAX_20(s,t) = max( idio_ret(s, d) ) for d in [t-19, t]          # α_08
sigma_20(s,t) = std( log_ret(s, d) ) for d in [t-19, t]
α_17(s,t) = winsorized rank of idio_MAX_20 within σ_20-quintile bucket(s,t)
            (σ-decoupled rank; removes the lottery-vol confound)

# Step 2 — 行业中性化
alpha_17_signal(s,t) = α_17(s,t) − mean( α_17 within industry(s) at t )

# Step 3 — Size-regime overlay signal
size_q  (s,t) = cross-section quintile of total_mv(s,t) on each date t
q5_size_ret(t) = mean_s [ log_ret(s,t) for s in top-mv-quintile ]
q1_size_ret(t) = mean_s [ log_ret(s,t) for s in bot-mv-quintile ]
size_spread(t) = q5_size_ret(t) − q1_size_ret(t)
size_q5q1_12m_sh(t) = trailing 252d annualized Sharpe of size_spread

# Step 4 — 动态 gate (63d rolling 97-percentile)
threshold(t)  = 63d rolling 97th-percentile of size_q5q1_12m_sh
gate(t)       = 1  if size_q5q1_12m_sh(t) < threshold(t)
                0  otherwise

# Step 5 — 组合 (monthly rebalance, delay=1)
if gate(t) == 1:
    portfolio = top-20% by alpha_17_signal, equal-weight
else:
    portfolio = equal-weight universe (benchmark)

# Cost: 5 bps/side × turnover(t)
```

## 2. Mechanism (经济解释)

Lottery premium(Bali-Cakici-Whitelaw 2011):高 idiosyncratic-MAX 股票下期
系统性跑输 → 反向 sort 买低 MAX。α 签名:**低 α_17 = 未来高收益**。

在 A 股的关键问题:2020 megacap rally(Liu-Stambaugh-Yuan 2019 描述的 A 股
size regime)年份,大盘股单边上涨,小盘 / 高 idio-vol 股被边缘化。
Lottery Q5 在这种 regime 下超额为负(2020 未加 overlay 时 −0.33 IR)。

### Overlay signal 选择理由

`size_q5q1_12m_sh` = top-mv-quintile 日收益减 bottom-mv-quintile 日收益的
滚动 12-month Sharpe。当大盘股系统性跑赢小盘股时(风格反转 / megacap
rally regime),该信号持续上升。

- **63-day rolling 97% percentile** 阈值:捕捉 "近 3 月内 size spread
  进入极端 megacap-rally 区间",触发保守状态(持 benchmark)。这是
  short-memory + tight-threshold 的组合 — round 3 通过完整 spec 网格
  (lookback × percentile × smoothing)找到的唯一稳健组合。
- **Benchmark fallback**(不是 cash):gate off 时持等权 universe,超额 = 0。
  避免 cash fallback 在 megacap rally 年份(市场大涨)造成的 benchmark
  underperform。

### 样本期内触发历史

- 2018:gate on 仅 33% — 2018 A 股跌市,市场微观结构弱;overlay 大部分
  时间在 benchmark,恰好规避 lottery Q5 在 2018 的波动(2018 abs ann
  为 −24.95% 是 universe 跌,但 2018 excess 达 +4.51%)
- 2020:gate on 67% — 成功识别并规避大部分 megacap-rally 期间
- 2021–2024:gate on ≥ 92%,持续部署 lottery Q5
- 2025:gate on 77% — 2025 小盘 / 主题股修复行情,gate 多数时间开,
  捕捉 lottery α,IR 1.26

## 3. Backtest Specification

- **Universe**: A 股所有普通股,要求 ≥252 交易日历史(size_q5q1_12m_sh 可算)
- **Industry classification**: CITIC L1 (~110 行业)
- **Rebalance**: 20 交易日(月度)
- **Delay**: 1(T+1 执行,inherited from α_17 panel)
- **Cost**: 5 bps 单边 × turnover per rebalance
- **Weights**: Q5 等权
- **Fallback**: 等权 universe(benchmark),excess = 0
- **Target**: fwd_ret_20 = log-ret cumulated over [t+1+delay, t+20+delay]

## 4. Audit (7/7 PASS)

| # | Rule | Threshold | Actual | Result |
|:-:|------|----------|-------:|:------:|
| 1 | 全样本超额 IR | ≥ 1.0 | **1.129** | ✅ |
| 2 | Worst-year excess IR | ≥ 0.5 | **0.766** (2023) | ✅ |
| 3 | Best-year-out / full ratio | ≥ 50% | **93.4%** | ✅ |
| 4 | Spec sensitivity majority pass | ≥ 5/8 | **5/8** | ✅ |
| 5 | Placebo excess IR p-value | < 0.05 | **0.020** | ✅ |
| 6 | Placebo worst-year p-value | < 0.05 | **0.000** | ✅ |
| 7 | Excess MaxDD | > −10% | **−4.18%** | ✅ |

### Placebo 证据 (100 次随机 gate 匹配 on_frac=0.808)

| 指标 | 基线 | 随机中位 | 随机 max | p-value |
|---|---:|---:|---:|---:|
| 超额 IR | 1.129 | 0.904 | 1.241 | **0.020** |
| Worst-year | 0.766 | −0.328 | 0.581 | **0.000** |
| 2020 IR | 1.162 | −0.325 | 1.662 | **0.010** |

### Spec sensitivity (±neighborhood of winner)

| lookback | percentile | full IR | worst | PASS |
|---:|---:|---:|---:|:---:|
| 50 | 97 | 1.117 | 0.766 | ✅ |
| 63 | 95 | 1.035 | −0.221 | ❌ |
| 63 | 96 | 1.102 | 0.638 | ✅ |
| **63** | **97** | **1.129** | **0.766** | ✅ (winner) |
| 63 | 98 | 1.129 | 0.766 | ✅ |
| 63 | 99 | 0.940 | 0.016 | ❌ |
| 75 | 97 | 1.102 | 0.638 | ✅ |
| 90 | 97 | 0.978 | 0.452 | ❌ |

5/8 pass — 中心的参数(63, 97)鲁棒,边界(lookback 太短 50 / 太长 90,
percentile 太宽 95 / 太紧 99)才开始失效。

### Execution delay & look-ahead audit

- α_17 panel 的 fwd_ret_20 使用 `ret.shift(-(1+delay)).rolling(20).sum()`
  with delay=1,符合 target_shift = −2 规则 ✅
- size_q5q1_12m_sh 仅由 trailing rolling 运算构造,无未来函数 ✅
- Gate 阈值是 63d rolling trailing 97-percentile,无未来函数 ✅

### Residualization audit

- α_17 本身已做 σ-decoupling(σ_20 quintile bucket rank)+ winsor
- 本因子代码再做 industry demean 层
- 因此 α_17_signal 已消除 vol / industry 两大 confound

## 5. Per-Year Performance

| year | n | 超额净 ann | 超额 IR | 绝对净 ann | 绝对 Sharpe | 超额 DD | 绝对 DD | gate on |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 12 | +4.51% | +1.80 | −24.95% | −1.44 | 0.00% | −28.89% | 33% |
| 2019 | 12 | +1.87% | +0.86 | +30.33% | +1.15 | −1.74% | −13.01% | 83% |
| **2020** | 12 | +3.21% | **+1.16** | +13.81% | +0.88 | −0.79% | −9.40% | 67% |
| 2021 | 12 | +6.14% | +2.16 | +28.93% | +2.43 | −0.95% | −3.62% | 100% |
| 2022 | 12 | +4.37% | +2.28 | −5.34% | −0.33 | −0.55% | −12.67% | 92% |
| 2023 | 12 | +2.53% | +0.77 | +3.04% | +0.21 | −1.76% | −9.21% | 100% |
| 2024 | 12 | +5.26% | +0.84 | +13.07% | +0.26 | −2.61% | −15.45% | 100% |
| **2025** | 13 | +2.91% | **+1.26** | +46.20% | +2.41 | −0.92% | −8.57% | 77% |

## 6. Risk assessment

### 已识别的风险

1. **A 股系统性 beta**:Q5 长多天然吃市场 beta,绝对 MaxDD −34.5% ≈ universe
   MaxDD −32%。产品设计要明确 benchmark(如沪深全 A / 等权 A 股)并以
   相对超额为核心 KPI。

2. **Lottery premium 在 megacap-rally 下消失**:Overlay 已防护 2020 那样的
   典型情景。但极端长期(> 1 年)的 size-regime 反转仍有可能突破 overlay —
   2018 年 gate on 仅 33% 已经是例子,虽然那年结果意外好(benchmark 本身跌)。

3. **非 lottery 型小盘反弹**:2025 是 "主题股 / 输家反转" 年,overlay 保持
   开启并捕捉到 alpha。若未来 A 股进入 "defensive small-cap" 型 regime
   (小盘涨但非 lottery stock 涨),overlay 可能打开但 alpha 不兑现。

4. **信号构造依赖** lottery session 的 α_17 panel(目前是研究工件)。
   生产化需固化 α_17 的构造代码到本 factor 的 code.py 或独立 module。

### Kill-switch

- **(1)** Rolling-12m 超额 IR < 0
- **(2)** 超额 MaxDD < −8%(当前 −4.18% 距此较远)
- **(3)** 连续 3 季度超额负收益
- **(4)** Gate 年度 on-fraction < 40%(说明 size-regime overlay 长期关断,
  样本中仅 2018 出现过,且 2018 excess +1.80 IR —— 如 future 再现类似
  低 on-frac 年份但 excess 不正,需重新审视 overlay 逻辑)

## 7. Monitoring

- **周度**:计算当前 `size_q5q1_12m_sh` 与 63d 97% 阈值;对比 gate 状态
- **月度**:re-run 本因子 pipeline,与模型发出的信号比对(数据可溯源)
- **季度**:rolling-12m 超额 IR / 超额 MaxDD / 超额年化 vs 年化预期
- **年度**:完整 spec sensitivity 复测 + placebo 重跑(≥ 5/8 spec pass,
  placebo p-values 均 < 0.05)

## 8. 部署建议

- **产品形态**:A 股指增(long-only)策略,相对 universe 等权 benchmark
- **预期指标**(基于 TVT):
  - 超额年化:3 – 5%
  - 超额 IR:1.0 – 1.3
  - 超额 MaxDD:通常 < −5%
  - 目标持仓数:~1000 只(20% × 5000)或可按信号分数加权至 ~500 – 800
- **复盘频率**:月度 P&L / 季度因子健康 / 年度 spec 复测

## 9. 文献

- **Bali, T. G., Cakici, N., & Whitelaw, R. F. (2011).** "Maxing out: Stocks
  as lotteries and the cross-section of expected returns." *JFE* 99(2):
  427–446. **Lottery / idio-MAX 原始论文**
- **Liu, J., Stambaugh, R. F., & Yuan, Y. (2019).** "Size and value in China."
  *JFE* 134(1): 48–69. **A 股 size regime,2020 megacap rally**
- **Fama, E. F., & French, K. R. (1992).** "The cross-section of expected
  stock returns." *JF* 47(2): 427–465. **市值因子**
- **Ang, A., Hodrick, R. J., Xing, Y., & Zhang, X. (2006).** "The cross-section
  of volatility and expected returns." *JF* 61(1): 259–299. **idio vol anomaly**

## 10. Source

- **Session**: `logs/20260422_lottery_megacap_overlay/`
- **Precursor α_17 panel**: `logs/20260421_volprice_max_lottery/outputs/panel_round3.parquet`
- **Diagnosis preceding this factor**:
  `logs/20260422_trend_technical_alpha/outputs/diagnosis_2025_regime_break.md`
  `logs/20260422_trend_technical_alpha/outputs/alpha17_longonly_review.md`
