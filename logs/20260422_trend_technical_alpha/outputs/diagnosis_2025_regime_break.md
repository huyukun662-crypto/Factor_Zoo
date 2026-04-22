# 2025 regime-break diagnosis: universe vs selection

**Session:** `20260422_trend_technical_alpha`
**Scripts:** `14_round6_extended_falsification.py`, `15_attribution_2025.py`
**Date:** 2026-04-22
**Sample:** 2018-01-02 → 2026-04-03 (101 monthly rebalances)

## User's question

> **"2025 年是标的池内没有区间内强势标的(没有 alpha),还是没有选到(选择质量差)?"**

Is 2025's failure (α_35 Sharpe −1.44, rotation Sharpe −0.18) because the
A-share universe had no cross-sectional winners, or because the
momentum/lottery signals picked losers?

## Direct answer

**是"没选到"——同时叠加"gate 反了"。标的池里 alpha 充裕,是 α_35 的
截面排序机制在 2025 失效。**

Detailed:

| 验证项 | 2018-24 基线 | 2025 | 比值 / 结论 |
|---|---:|---:|---|
| Universe top-bottom 20% spread (ex-post 理想上限) | 0.287 | **0.302** | **1.05 — 信号池 alpha 更多,不是更少** |
| Universe std(fwd_ret_20) | 0.114 | 0.123 | +0.42 z (分散度高于平均) |
| Universe mean(fwd_ret_20) | +0.009 | **+0.037** | 市场本身强势(+45% ann) |
| Momentum Q5−Q1 spread | 0.0073 | **0.0008** | **0.11 — 几乎无选股能力** |
| Momentum efficiency (实现/理论) | 0.024 | **0.0017** | **0.07 — 仅捕获 7% 的可得 alpha** |
| Momentum IC (Spearman) | 0.030 | 0.005 | z=-0.35,正相关性消失 |
| Momentum capture rate(Q5∩top20%)| 0.222 | 0.219 | 基本持平 |
| Lottery Q5−Q1 spread | 0.0120 | 0.0087 | −28% 下降但仍正 |
| Lottery IC | 0.068 | 0.066 | 稳定 |
| **Gate wrongness** (inactive − active) | **−0.008** | **+0.010** | **z=+0.54,从小利变小害** |

### 关键观察

1. **标的池 alpha 反而增加了**(spread_top_bot_20 ratio 1.05,z=+0.30)。
   2025 年 A 股截面分散度高于历史均值,winners/losers 并不缺席。
   → **Option A(无 alpha)明确否决**。

2. **α_35 (12-3 idio momentum) 的选股效率崩塌 93%**。IC 从 0.030 → 0.005;
   Q5-Q1 收益率价差从 0.73% → 0.08%(每月)。
   → **Option B(选错了)成立**。

3. **Capture rate 几乎不变**(Q5 覆盖 top-20% 赢家的比例从 22.2% → 21.9%)。
   但 Q5-Q1 spread 大幅下降。说明 **Q5 里赢家数量持平但 Q1 里也是赢家**
   —— 空头腿"踩雷"比多头腿"错过"更严重。
   → 2025 的 regime 对 **Q1(短期动量输家)的未来收益** 产生了系统性
   反转,典型 reversion-on-losers 场景。A 股 2025 小盘/主题股修复行情。

4. **Dispersion gate 从"小利"翻转为"小害"**。2018-24 平均 gate_wrongness
   = −0.008(gate 平均每月帮助 0.8%),2025 = +0.010(平均每月拖累 1.0%)。
   → **Option C(gate 反了)成立,但量级小,属于"signal 先失效,
   gate 才跟着反"的次级问题**。

5. **Lottery 腿保持原有效率**(IC 稳定 0.068 → 0.066,efficiency 下降但
   不显著)。α_17 本身在 2025 是工作的(+0.53 Sharpe),是 rotation 框架
   把它和失效的 α_35 绑在一起才被拖累。

## 机制假设:2025 A 股是什么 regime

综合上述信号,2025 年 A 股的截面回报似乎满足:
- 市场本身上涨(universe_mean 正,且大于历史)
- 截面分散度偏大(universe_std 偏高)
- **但过往 12-3 个月的走势与未来 20 日回报的相关性消失**

这是典型的 **"风格轮动 + 输家反转"** 情景:
- 2024 大盘科技/AI 主线结束,2025 资金转向 2023-24 的弱势板块反弹
- α_29 排序(过去 12 个月 − 过去 3 个月累计收益)本质上是 "old winners"
  排序,正好在 2025 被反转
- σ-residualize + industry-demean 处理了常见 confound,但无法对冲
  *未来 20 日* 回报方向翻转

## Round-6 扩展证伪结论(script 14)

### Spec sensitivity(7 个 dispersion-gate 变体)

| variant | LS full | Q5 full | worst-yr | 旧结果 | **扩展结果** |
|---|---:|---:|---:|---|---|
| BASELINE (252d / p50 / w20) | 1.806 | 0.973 | **−0.184** | ✅ PASS | ❌ FAIL |
| lookback_60 | 1.904 | 1.052 | 0.775 | ✅ | ✅ **PASS** |
| lookback_126 | 1.892 | 1.034 | −0.172 | ✅ | ❌ FAIL |
| lookback_504 | 1.460 | 0.724 | −0.727 | ❌ | ❌ FAIL |
| threshold_p40 | 1.529 | 0.673 | −0.309 | ✅ | ❌ FAIL |
| threshold_p60 | 1.785 | 1.075 | −0.184 | ✅ | ❌ FAIL |
| disp_window_60 | 1.413 | 0.487 | 0.820 | ❌ | ❌ FAIL |

**扩展样本下 1/7 通过 (vs 旧样本 5/7)**。唯一存活的 `lookback_60`(60日
中位数阈值)—— 短记忆 gate 适应 regime 变化更快,避开了 2025 的陷阱。
结果呼应了 Option C:**252d 中位数这个 lookback 具体不对,更短的 gate
能跟上 regime 变化**。

### Placebo (100 次随机互补 gate)

| 指标 | 基线 | 原 p-value | **扩展 p-value** |
|---|---:|---:|---:|
| LS full Sharpe | 1.806 | 0.000 | **0.010** |
| worst-year LS | −0.184 | 0.000 | **0.570** |

- LS full 仍然显著(p=0.01,扩展样本下 1/100 placebo 击败基线)
- **worst-year 完全不显著**(p=0.57):43% 的随机 gate 比真实 gate
  worst-year 更好。这验证了 Option C——**gate 的"regime 信号"在 2025
  失效**,真随机 gate 跟真实 gate 表现差不多(甚至更好)。

## 综合判定

三个选项叠加(B 为主,C 配合):

- **Option A (标的池无 alpha): REJECTED** ⟶ 2025 universe spread ratio 1.05
- **Option B (α_35 选股失效): CONFIRMED** ⟶ efficiency 0.024 → 0.0017,降 93%
- **Option C (dispersion gate 失效): PARTIALLY CONFIRMED** ⟶
  gate_wrongness 从 −0.008 翻到 +0.010;placebo worst-year p=0.57 说明
  gate 的 regime 择时能力在扩展样本下无法与随机区分

**α_17 lottery 腿未参与失效**,是 rotation 把它拖下水。

## 对建议的更新

| 之前的建议 | 诊断后的调整 |
|---|---|
| α_35 DEPLOYED → PAUSED(基于 kill-switch 规则 1) | **不变。Option B 的根因是 α_35 选股本身在 2025 失效,必须暂停** |
| Rotation 延后部署 | **不变。扩展审计 1/7 通过** |
| 深入研究 gate 失效 | **细化:研究重心从"gate 设计"挪到 "α_29 selection decay"**。gate 只是次级问题 |

**新的研究方向(高优先)**:

1. **α_29 signal decay investigation**:为什么 2025 年 12-3 idio momentum
   的 IC 从 0.030 降到 0.005?分板块 / 分市值 IC decomposition 可以帮助
   判断是不是特定板块(如科技股)主导 2018-24 样本,在 2025 被反转。
2. **更短的 gate lookback(60d median)** 作为稳定版:扩展证伪里是唯一
   通过的 spec。可能成为 α_35 v2 的改进点。

3. **构建"selection quality monitor"**:用 IC 和 efficiency 作为
   live 因子健康指标,配合原来的 rolling-12m Sharpe,可以更早触发
   kill-switch(实际上 2025 Q1 IC 就已经降了,无需等到 Sharpe 变负)。

## 附录:per-year 汇总表

| year | spread_top_bot_20 | ic_mom | ic_lot | eff_mom | eff_lot | gate_wrongness |
|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 0.215 | −0.007 | +0.109 | −0.046 | +0.098 | −0.031 |
| 2019 | 0.259 | +0.004 | +0.065 | +0.001 | +0.029 | −0.010 |
| 2020 | 0.313 | +0.060 | +0.035 | +0.052 | +0.004 | −0.002 |
| 2021 | 0.329 | +0.027 | +0.072 | +0.013 | +0.036 | −0.008 |
| 2022 | 0.283 | +0.035 | +0.088 | +0.038 | +0.071 | −0.013 |
| 2023 | 0.249 | +0.026 | +0.066 | +0.012 | +0.050 | −0.003 |
| 2024 | 0.302 | +0.035 | +0.075 | +0.041 | +0.061 | −0.007 |
| **2025** | **0.302** | **+0.005** | +0.066 | **+0.002** | +0.026 | **+0.010** |
| 2026 YTD | 0.296 | +0.090 | +0.020 | +0.089 | −0.026 | −0.033 |

2026 Q1 `ic_mom` 反弹到 0.090(高于历史均值 2×),momentum efficiency
恢复到 0.089 —— 这也和 α_35 2026 Q1 Sharpe +3.11 一致,可能是 regime
轮动的终点。但样本只有 3 个再平衡点,不足以下结论。

## 参考

- Stivers & Sun (2010). JFQA 45(4) — dispersion gate mechanism
- Bali-Cakici-Whitelaw (2011). JFE 99(2) — lottery / MAX effect
- Liu, Stambaugh, Yuan (2019). JFE 134(1) — A-share size/value regime
- Blitz, Huij, Martens (2011). JEF 18(3) — residual momentum

## 工件清单

- `scripts/14_round6_extended_falsification.py`
- `scripts/15_attribution_2025.py`
- `outputs/rotation_round6_extended.json`
- `outputs/attribution_2025.json`
- `outputs/attribution_2025_tape.csv`
- `outputs/_r6ext_run.log`, `_attr_run.log`
