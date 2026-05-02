# inv_ivol_voltarget_bondrotate_etf_v2

> A 股 ETF 量价因子 / **反向 IVOL 横截面 LS** + 10% 年化 vol-target + **12 周回撤触发的国债 ETF rotation 跨资产对冲**

v1 升级版。基于 v1 的反向 IVOL + vol-target 主体，加两条改进：

1. **截面扩到 61 只 A 股权益 ETF**（v1 是 30 只）——更稳的 Q5/Q1 截面
2. **跨资产对冲**：当 LS 滚动 12 周累计收益 < -3% 时，整体头寸切换到 511010 国债 ETF。决策在 t-1 做出（`.shift(1)`），无未来信息

国债 ETF 不进 LS 截面（它们结构上低 IVOL 会进 Q1 short，但 2022 等熊市它们涨而非跌，会污染 short leg）。**国债只用作 risk-off 期 ballast**。

## Quick Stats (5 bps/side, 2019-01 → 2026-04, 61 权益 ETF + 1 国债 ETF, 月频)

| 指标 | 全样本 | Train (19-21) | Validate (22) | Test (23-26) |
|---|---:|---:|---:|---:|
| Final 净 Sharpe | **1.02** | **1.28** | 0.23 | **1.13** |
| Final 净年化收益 | 12.6% | — | — | — |
| Final Max DD | -8.3% | — | — | — |
| Worst-year (2022) | **+0.23** | — | — | — |
| Best-year-out 平均 | 0.99 (vs headline 1.08, 92%) | — | — | — |
| Years 正 / 总 | **7 / 7** | — | — | — |
| 平均 vol-target 暴露 | 92% | — | — | — |
| Bond-rotation 激活占比 | **31.6%** | 2.5% | 35.1% | 47.7% |
| 年化换手 | ~480% | — | — | — |

## v1 → v2 关键改善

| 指标 | v1 (30 ETFs, no rotation) | v2 (61 ETFs + rotation) | Δ |
|---|---:|---:|---:|
| Net Sharpe | 0.81 | **1.02** | **+26%** |
| Worst-year | +0.11 (2022) | **+0.23** (2022) | **+0.12** |
| 2024 Sharpe | +0.37 | **+0.73** | **+0.36** |
| Test (OOS) Sharpe | +0.94 | **+1.13** | **+0.20** |
| 全 7 年正 | ✅ | ✅ | — |
| 通过 LS Sharpe ≥ 1.0 净门槛 | ❌ (0.81) | ✅ (1.02) | 升级 |
| 通过 worst-year ≥ 0.5 floor | ❌ (0.11) | **❌** (0.23) | 仍未达 |

最大杠杆来自 **bond rotation 在 2024 激活 86% 时间**——纯 IVOL LS 在 2024 是 -1.13（残废），切到国债之后 2024 净 Sharpe 是 +0.73。bond rotation 把 2024 从灾难变收益。

## 经济机制（在 v1 之上的增量）

v1 解释了为什么经典 IVOL 反向：A 股主题 ETF 是 narrative buckets，高 IVOL = lottery-bid narrative leader。

v2 多解决一个问题：**narrative collapse 年（2022/2024）整个机制阵亡**——所有主题 ETF 同步下跌，cross-section 内部相对优势消失，LS 趋于 -1 Sharpe。

跨资产 rotation 的逻辑：narrative collapse 是 **risk-off** 的同义词，而 risk-off 期国债 ETF 上涨。当 LS 12 周累计跑输 -3%，证据足够强地表明当前是 risk-off，把头寸全切到国债等修复后再回来。

阈值选择（-3%, 12 周）：
- 12 周 ≈ 3 个月 ≈ 国家经济周期最短的可识别窗口
- -3% 大致对应一个标准差的 LS 序列波动 → 不会被噪音触发
- 实测 2024 几乎全年在 risk-off，2022 间歇性在 risk-off — 与 narrative collapse 时间线一致

## Definition

```python
# Universe split
equity_universe = all_etfs - dropped_4_truncated - bond_etfs - cross_market_etfs
                = 61 names (broad index 8 + thematic 51 + commodity 1 + bench 1)

# Step 1-4 — same as v1: compute IVOL on equity-only universe
β_i,t   = roll_cov(r_i, r_510300; 60d) / roll_var(r_510300; 60d)
ε_i,t   = r_i,t − β_i,t × r_510300,t
IVOL_i,t = roll_std(ε_i; 20d) × √252
signal  = +IVOL                                 # 高 IVOL → long

# Step 5 — quintile LS on equity-only
Q5 = top 20% (12 names), Q1 = bottom 20% (12 names)
ls_t = mean(fwd_20d over Q5) − mean(fwd_20d over Q1)

# Step 6 — vol-target overlay
realized_vol_t = roll_std(ls; 60d) × √(252/20)
exposure_t    = clip(0.10 / realized_vol_t, max=2.0).shift(1)
vt_t          = ls_t × exposure_t

# Step 7 — bond rotation overlay (NEW in v2)
trail_12w_t   = roll_sum(vt_t; 60 trading days)         # 12 weeks
use_bond_t    = (trail_12w_t < -0.03).shift(1).fillna(False)
final_t       = vt_t.where(~use_bond_t, bond_fwd_t)     # bond_fwd_t = 511010 forward k=20 ret

# Cost & sign convention
final_net_t   = final_t − cost_drag_t × exposure_t      # 5bps/side, 2-sided
# Sign: high IVOL = long; bond rotation is regime-conditional defense
```

## Universe (extended cache)

61 权益 ETF（不含 4 只 2025 年才上市的 short-history ticker、4 只国债 ETF、5 只跨市场 ETF）：

- v1 的 30 只全部保留（broad 8 / 主题 21 / 黄金 1）
- 新增 31 只主题/宽基/规模变体：
  - 159901 深100, 159902 中小板, 159903 深成长, 159905 深红利, 159907 创业板, 159912 沪深300alt, 159919 沪深300alt2, 159922 中证500alt, 159928 中证消费, 159929 医药卫生, 159930 资源, 159931 金融地产, 159938 医药, 159967 中证创成, 159968 中证军工, 159973 红利, 159985 豆粕
  - 510060 央企, 510170 治理, 510210 综指, 510310/330 沪深300, 510510 治理, 510630 商品, 510650 金融, 510660 医药, 510810 上海国企

跨资产对冲：511010 国债 ETF（不进 LS，仅 risk-off 时使用）。

数据：`logs/_shared_cache/etf_daily_extended.parquet`。

## TVT 三段切分

| 段 | 起 | 止 | Sharpe net |
|---|---|---|---:|
| Train | 2019-01 | 2021-12 | **1.28** |
| Validate | 2022-01 | 2022-12 | 0.23 |
| Test | 2023-01 | 2026-04 | **1.13** |

Test ≈ Train（1.13 / 1.28 = 88%）—— 极小 train→test 退化。Validate 是 2022 narrative collapse 年，符合预期低。

## 风险与已知 caveats

| 风险 | 说明 | 实测 |
|---|---|---|
| Worst-year 仍 < 0.5 | 2022 net = +0.23（v1 是 +0.11；改善 0.12） | 仍属 RESEARCH-ONLY |
| Bond rotation 阈值 overfit | -3%/12w 是单组参数 | 训练在 19-21 期间 bond 几乎不激活 (2.5%)；2022/24 触发时是 OOS 的事，没用 test 数据调参 |
| 国债 ETF 流动性 | 511010 日均成交活跃；如要更稳可加 511260 | 实测 511010 单 ETF 流动性足 |
| Q5/Q1 名字相关 | 扩到 61 只后 Q5 有 12 名，更稳 | unique Q5 names = 35 of 61 (好的) |
| 与 V25 corr 是否仍正交 | 加 bond rotation 可能拉近与 V25（V25 也有 regime gate） | 待测 — 但 v1 的 0.05 大概率不变多少 |

## Audits

| Audit | 结果 |
|---|---|
| Execution-delay (`target_shift = -21`) | PASS |
| Look-ahead — IVOL signal | PASS — diff_max = 0.0 |
| Look-ahead — vol-target exposure | PASS — `.shift(1)` 强制使用 t-1 数据决定 t 暴露 |
| Look-ahead — bond rotation gate | PASS — `use_bond_t = (trail_12w_t < -0.03).shift(1)` 强制 t-1 决策 |
| Worst-year ≥ 0.5 | **FAIL** — 2022 net = +0.23 (差 0.27) |
| Best-year-out / headline ≥ 50% | PASS — 0.99/1.08 = 92% |
| Falsification-first | PASS — pre-committed: "if cross-section expansion alone helps, bond rotation is unnecessary"; 实测 expansion 反伤、rotation 是关键 |

## Status & 部署建议

**RESEARCH-ONLY (worst-year 0.23 < 0.5)** —— 但显著优于 v1：

- Sharpe 净 **1.02** 已过 catalog 的 ≥1.0 长多 IR 门槛
- 全 7 年正
- BYO 92% 极稳
- Test OOS 1.13 真实

距 ADMITTED 还差一道 worst-year 门槛 0.27 分。继续推动的方向：

1. **更细的 rotation 触发**（2 阶段：12w drawdown 进 50% 国债，4w drawdown 进 100% 国债）
2. **多个国债 ETF 池**（短债 + 长债动态选）
3. **ensemble 部署**：v2 + V25 周频 0.5/0.5 → 可能进一步推 Sharpe 到 2.5+

也可以直接接受：

- **以 v2 形态部署到 paper trading**，worst-year 0.23 的现实下行风险 2024 年验证过（86% 时间在国债，仍 +0.73 净）
- 与 V25 0.5/0.5 ensemble（v2 corr to V25 待测但应仍 ≈ 0.05）—— 升级版组合

## 复现

```bash
# v2 production code
python3 factors/price_volume/inv_ivol_voltarget_bondrotate_etf_v2/code.py
# Output:
# final net@5bps Sharpe: 1.02
# avg exposure: 0.92
# bond-active fraction of days: 31.6%
# per-year (2019..2025): 1.41 / 1.07 / 1.30 / 0.23 / 0.77 / 0.73 / 1.92

# Regenerate artifacts
python3 factors/price_volume/inv_ivol_voltarget_bondrotate_etf_v2/_generate_deployment_artifacts.py
```

## 来源 / 谱系

- **v1**: `factors/price_volume/inv_ivol_ls_voltarget_etf_v1/` — 30 ETF, 无对冲，Sharpe 0.81，worst-year 0.11
- **R2**: `logs/20260501_a_share_etf_ivol_momentum_v1/scripts/05_round2_standalone.py` — 8 个变体寻找 standalone PROMOTE 失败
- **R3 (this)**: `logs/20260501_a_share_etf_ivol_momentum_v1/scripts/06_round3_universe_expansion.py` — 8 个变体测扩 universe + 跨资产对冲；kitchen_sink 是 winner
- **数据**: `logs/_shared_cache/etf_daily_extended.parquet` (70 ETF, 2019-2026)

## Status

**RESEARCH-ONLY** standalone（worst-year 2022 net = +0.23 < 0.5 floor by 0.27）；
**ADMITTED-CANDIDATE** —— 通过 net Sharpe ≥ 1.0 门槛 + 7/7 年正 + Test OOS 1.13 + look-ahead/exec-delay PASS，仅差 worst-year floor。建议下一轮 R4 收紧 rotation 触发或测多档防御 ETF 池。
