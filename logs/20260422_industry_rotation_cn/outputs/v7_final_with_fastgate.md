# V7 最终版:双 Gate + Bond-Gold Fallback

**Session**: `20260422_industry_rotation_cn` · Round 10
**Date**: 2026-04-22
**最终推荐**: `V7_gb7030_FG4_tuned`

## 配置

```yaml
V7_final:
  # 双腿 Ensemble
  leg_A:
    formula: "z(mom_4w) - 1.5 * z(turn_4w) + 0.3 * breadth_z"
    select: top-4 by score
    weight: 50% of ensemble (each ETF 12.5% when only A)
  leg_G:
    step1: rank 9 groups by internal 4w momentum
    step2: pick top-3 groups
    step3: within each, pick highest-4w-mom ETF
    weight: 50% of ensemble (each ETF 16.67% when only G)

  # 双 Gate
  slow_gate:
    rule: mkt_cum > 50w MA      # risk-on for long bull
  fast_gate:
    rule: rolling-4w vol > 2.5 * rolling-26w vol → OFF for 6 weeks
    purpose: catch COVID-style V-crashes
  risk_on: slow_gate AND fast_gate  # both must agree

  # 防御 Fallback (gate-off)
  fallback: {159934.SZ: 70%, 511010.SH: 30%}  # 70% 黄金 + 30% 5y 国债

  # 仓位管理
  vol_target: 15% annual (scale-down only, no leverage)
  rolling_vol_lookback: 26 weeks

  # 执行
  rebalance: weekly
  delay: 1
  cost_bps_per_side: 5
```

## 全样本表现 (2019-01-04 → 2026-04-22, 377 weeks)

| 指标 | 数值 |
|---|---:|
| 年化收益 | **26.6%** |
| 年化波动 | 14.4% |
| **Sharpe** | **1.85** |
| Sortino | ~3.0(估) |
| **Calmar** | **3.28** |
| **最大回撤** | **-8.11%** |
| MaxDD 日期 | 2020-02 → 2020-06(COVID) |
| 年化单边换手 | ~9×(含 fallback 切换) |

## IS / OOS 表现

| 区间 | Sharpe | Calmar | MaxDD | AnnRet |
|---|---:|---:|---:|---:|
| IS 2019-2023 | 1.80 | 3.0~ | -8.11% | ~24% |
| OOS 2024-2026 | ~2.0 | ~4.0 | <-8% | ~34% |

## 分年表现对比(vs V7_gb7030 baseline)

| 年 | baseline DD | **FG4 tuned DD** | 收益差 |
|---:|---:|---:|---:|
| 2019 | -5.6% | -5.6% | 同 |
| 2020 | **-8.89%** | **-8.11%** ⭐ | +0.8pp DD |
| 2021 | -6.2% | -6.2% | 同 |
| 2022 | -5.69% | -5.69% | 同(bond 主导) |
| 2023 | -5.0% | -5.0% | 同 |
| 2024 | -4.9% | -4.9% | 同 |
| 2025 | -5.7% | -5.7% | 同 |
| 2026 YTD | -6.5% | -6.5% | 同 |

## 机制总结

| 层 | 组件 | 目的 |
|---|---|---|
| 1 | Ensemble(A+G)| 主线捕获 + 分散 |
| 2 | 慢 Gate (MA50)| 防长熊(2022 型)|
| 3 | **快 Gate (vol expansion)** | **防急跌(COVID 型)** |
| 4 | **Gold 70% + Bond 30%**(fallback)| **真正的 anti-cyclic** |
| 5 | 15% vol target | 波动自动压仓 |

## vs 历史所有版本

| 版本 | Sh | Cal | DD | AnnRet | 增量 |
|---|---:|---:|---:|---:|---|
| V1_BASE(原 A_tuned_v1)| 1.40 | 2.10 | -9.26% | 19.5% | 基线 |
| V7_gold(Round 7)| 1.91 | 3.22 | -8.89% | 28.6% | +gold fallback |
| V7_gb7030(Round 9)| 1.81 | 2.94 | -8.89% | 26.1% | +30% bond |
| **V7_gb7030_FG4 tuned** ⭐ | **1.85** | **3.28** | **-8.11%** | **26.6%** | **+fast gate** |

**全程演化累计收益**:
- V1_BASE → V7_final: Sharpe 1.40 → 1.85(+32%)、Calmar 2.10 → 3.28(+56%)、MaxDD -9.3% → -8.1%、AnnRet 19.5% → 26.6%

## 诚实披露

1. **MaxDD 的主瓶颈是 2020 COVID**。要 < -6% 需要日频 gate 或更严 vol target,两者都会牺牲 Sharpe。
2. **OOS 的高 Sharpe (2.0+) 有 2024-2025 黄金涨势加持**。长期 Sharpe 预期 1.5-1.7 更现实。
3. **快 Gate 的 FP 率极低**(fg_on 97.9%),但这是 2019-2026 特定历史,未来异常波动率事件可能触发更频繁。
4. **国债 30% 的 2022 贡献明确**;若中国利率进入上行周期,bond 可能从"防御"变成"拖累"。

## 下一步

- 入库到 `factors/price_volume/industry_rotation_etf_v7_final/`
- 或继续研究:日频 gate、或接受 -8% MaxDD 直接交易

## 完整研究回路(9 轮)

1. Round 1: SW L1 宇宙,3 族(A/B/C)× 8 specs = 24 测试 → B6 胜
2. Round 2: 回归 overlay → 救不了 2018
3. Round 4: 切到 ETF 可交易宇宙 → 策略降级(理解程度提高)
4. Round 5: IS/OOS 严调参 → A_tuned_v1(A7 + gate + vol target)
5. Round 6: 滚动 OOS + gate 敏感性 → 确认 stable plateau
6. Round 7: 红利/ensemble → 黄金 fallback 让 Sharpe 跳到 1.91
7. Round 8: 防御 basket → 反直觉,纯黄金最优
8. Round 9: **国债**真 anti-cyclic → gb7030 救 2022
9. Round 10: **快 Gate**抓 COVID → V7 final Pareto 改进

这是一个端到端因子挖掘工作流的完整示范。
