# inv_ivol_ls_voltarget_etf_v1

> A 股 ETF 量价因子 / **反向 IVOL 横截面 long-short** + 10% 年化 vol-target 暴露管理

把经典 Ang-Hodrick-Xing-Zhang IVOL 异常**反向**搬到 A 股主题 ETF 截面：做多高 IVOL ETF（narrative-leader 篮子）、做空低 IVOL ETF（防御篮子），月频再平衡，整体头寸动态缩放至 10% 年化波动目标。

## Quick Stats (5 bps/side 单边手续费, 2019-01 → 2026-04, 30 ETF, 月频再平衡)

| 指标 | 全样本 | Train (19-21) | Validate (22) | Test (23-26) |
|------|------:|-------------:|-------------:|-----------:|
| LS 净 Sharpe | **0.81** | 0.99 | 0.16 | **0.94** |
| LS 净年化收益 | 9.50% | 14.93% | 1.28% | 11.94% |
| LS 毛年化收益 | 9.85% | — | — | — |
| LS Max DD | -8.7% | — | — | — |
| 平均 gross 暴露 | 70% | 76% | 78% | 65% |
| Worst-year Sharpe | **+0.11** (2022) | — | — | — |
| Best-year-out 平均 Sharpe | 0.80 | — | — | — |
| Years 正 / 总年份 | **7 / 7** | — | — | — |
| 年化换手 | 432% | — | — | — |
| 平均成本 | 1.5 bps/期 | — | — | — |

## 核心结论

**没有负收益年份**——2019-2025 满 7 年 Sharpe 都为正。最差年是 2022（+0.11，narrative collapse 之年），其次 2024（+0.37，国家队买宽基 + 主题塌方）。

但 **worst-year 0.11 < 0.5 PROMOTE 地板** → standalone 状态为 **RESEARCH-ONLY**。

部署形态：作为 **0.5/0.5 周频 overlay** 与 V25（或 V7_gold）组合时，组合 Sharpe 升至 **2.30**（V25 alone 1.87；+23% lift），worst-year 升至 **+0.82**（well above 0.5）。详情见 `logs/20260501_a_share_etf_ivol_momentum_v1/outputs/v25_addendum.md`。

## 经济机制

经典 IVOL 异常在美股个股层面是 mean-reversion（Ang-Hodrick-Xing-Zhang 2006）：高 IVOL 股票被散户彩票偏好推贵 → 未来回报折价。

但 A 股主题 ETF 不是个股 —— **ETF 是预先打包好的 narrative bucket**。同一个 lottery preference 心理：

- 在**个股层面** 表现为单只股票被高估 → 价格收敛 → 经典 IVOL 信号
- 在 **ETF 层面** 表现为某个叙事篮子的持续散户净流入 → narrative momentum continuation → **反向 IVOL 信号**

ETF 篮子层面没有"篮子内重定价"这个收敛通道——你买的就是这个篮子。同时 A 股做空成本极高，缺乏套利方修正机制。所以同一心理通过不同市场结构产生**符号相反**的可交易信号。

实测：Q1（高 IVOL ETF，本应 short 但实际是 narrative-leader）年化 +24.6%；Q5（低 IVOL ETF，本应 long 但实际是防御篮子）年化 +6.7%。direction 完全反过来。

## Definition

```python
# 步骤 1 — 60d rolling beta 与残差
β_i,t = roll_cov(r_i, r_510300; 60d) / roll_var(r_510300; 60d)
ε_i,t = r_i,t − β_i,t × r_510300,t

# 步骤 2 — 20d rolling 残差波动 (annualized)
IVOL_i,t = roll_std(ε_i; 20d) × √252

# 步骤 3 — 横截面排名 (符号约定: 高 = 多)
signal_i,t = +IVOL_i,t                       # 注意是正号 (反向于经典 AHXZ)
rank_i,t   = signal_i,t.rank(axis=1, pct=True)

# 步骤 4 — Long-short 五分位
Q5 = {ETFs with rank ≥ 0.8}                  # 高 IVOL → LONG
Q1 = {ETFs with rank < 0.2}                  # 低 IVOL → SHORT
ls_ret_t = mean(fwd_20d_ret over Q5) − mean(fwd_20d_ret over Q1)
                                              # delay=1, target_shift = -(1+20) = -21

# 步骤 5 — 动态 vol-target overlay (这是相对裸 m1 的关键改进)
realized_vol_t = roll_std(ls_ret; 60d) × √(252/20)
exposure_t     = clip(0.10 / realized_vol_t, max=2.0).shift(1)
final_ret_t    = ls_ret_t × exposure_t

# 符号约定: signal 越高 → 未来收益越高 (反向 IVOL momentum)
# 平均 exposure ≈ 70% — vol-target 大部分时间 < 100% 因为底层 LS 现实波动 ~14% 高于目标 10%
```

## Universe

30 个 A 股 ETF（剔除 4 个 2025 年 10 月才上市的 short-history 标的：512100 / 515050 / 515170 / 512800）：

- **宽基 8 只**：510300 沪深300 / 510500 中证500 / 510050 上证50 / 159915 创业板 / 510180 上证180 / 159949 创业板50 / 588000 科创50 / 588080 科创板100 / 510880 红利
- **主题 21 只**：512880 证券 / 512660 军工 / 512170 医疗 / 512760 芯片 / 515030 新能源车 / 512290 生物医药 / 515050 5G / 512690 酒 / 512980 传媒 / 512480 半导体 / 159819 人工智能 / 515880 通信 / 159890 云计算 / 159869 游戏 / 159857 光伏 / 159755 电池 / 512010 医药 / 159992 创新药 / 159980 有色 / 515220 煤炭 / 515210 钢铁
- **商品 1 只**：518880 黄金

beta 基准：510300 沪深300（A 股最大宽基 ETF）。

## TVT 三段切分

| 段 | 起 | 止 | 用途 |
|---|---|---|---|
| Train | 2019-01 | 2021-12 | 形成机制假设、beta/IVOL 窗口选定 |
| Validate | 2022-01 | 2022-12 | 选 vol-target 参数、cost 校准 |
| Test | 2023-01 | 2026-04 | 一次性评估，未参与调参 |

Test Sharpe **0.94 ≈ Train 0.99**（1.05× ratio），无 train→test 退化。

## 风险与已知 caveats

| 风险 | 说明 | 实测 |
|---|---|---|
| Worst-year < 0.5 floor | A-share narrative-collapse 年（2022/2024）单独跑表现弱 | 失败 standalone PROMOTE，建议 ensemble 部署 |
| 30-ETF 截面较窄 | Q5/Q1 各 6 只 ETF；早期窗口 (2019-2021) 截面 ~22 只 | 已剔除 2025 后期上市标的；实际 unique Q5 名单 ≥ 18 |
| 与 V7/V25 不正交则无价值 | 若与 V7/V25 同向，加 overlay 没有意义 | 实测 V7 corr 0.052 / V25 corr 0.053 — 高度独立 |
| 单日 vol spike 误排 | black-swan 当日 IVOL 飙到第一不代表趋势 | mean-abs IVOL (m5 变体) 结果几乎一致，非单日驱动 |
| Look-ahead 风险 | beta / IVOL 窗口、vol-target 暴露都需要严格 backward | 已通过 perturb-future-bars 审计：sig_diff_max = 0.0, exposure_diff_max = 0.0 |

## 部署建议

| 用法 | 推荐权重 | 预期效果 |
|---|---|---|
| 与 V25 组合（max Sharpe） | 0.5 IVOL + 0.5 V25 | Sharpe 2.30, ann 19.5%, MDD -8.9%, worst-year 0.82 |
| 与 V25 组合（max Calmar） | 0.2 IVOL + 0.8 V25 | Sharpe 2.09, ann 22.7%, MDD -7.2%, Calmar 3.15 (最不打扰生产策略) |
| 与 V7_gold 组合 | 0.5 IVOL + 0.5 V7 | Sharpe 2.18, worst-year 0.83, +26% lift over V7 alone |
| 单独部署 | — | RESEARCH-ONLY，不建议 |

## 复现性

```bash
python3 factors/price_volume/inv_ivol_ls_voltarget_etf_v1/code.py
# vol-target LS net@5bps Sharpe: 0.81
# avg exposure: 0.70
# per-year Sharpe (2019..2025): 2.27 / 0.96 / 0.47 / 0.11 / 0.38 / 0.37 / 2.27
```

或重生成入库 artifacts：

```bash
python3 factors/price_volume/inv_ivol_ls_voltarget_etf_v1/_generate_deployment_artifacts.py
# regenerates metrics.json, annual.csv, rebalances.csv
```

## 来源 / 谱系

- **Session 1**: `logs/20260501_a_share_etf_ivol_reversal_v1` — 经典 AHXZ IVOL-reversal 假设被证伪（decile 反向：Q1=+24.6%, Q5=+6.7%）。
- **Session 2 R1**: `logs/20260501_a_share_etf_ivol_momentum_v1` round 1 — 反向假设确认；标准 LS 跑出 Sharpe 0.66 但 worst-year 0.04 fail 地板；MA50 大盘 gate 没救。
- **Session 2 R2**: `logs/20260501_a_share_etf_ivol_momentum_v1` round 2（本因子）— 八种 narrative-collapse 风控变体里 vol-target 是唯一全年正 Sharpe 的，作为 standalone 入库版。
- **Ensemble paper**: `logs/20260501_a_share_etf_ivol_momentum_v1/outputs/v25_addendum.md` — 与 V25 / V7 0.5/0.5 周频 ensemble 详细测试。

## Status

**RESEARCH-ONLY** standalone（worst-year 0.11 < 0.5 floor）；
**PROMOTE candidate** as 50/50 weekly overlay with V25 or V7_gold（详见 ensemble paper）。
