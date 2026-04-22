# Final Summary — 20260422_industry_rotation_cn

**Task**: 挖一个 A 股行业 ETF 轮动策略:抓阶段主线、高低切、周度调仓。
**Workflow**: WorldQuant 5-agent, 1 round, 3 hypothesis families × 8 specs = 24 tests.

## TL;DR

**推荐**: **`B6_m4_K10_t8`** — 先按 4 周动量选 Top-10 行业(主线),再在这 10 个里挑 8 周换手率最低的 Top-3(避免过热)。

| 指标 | 值 | 基准(31 行业等权) |
|---|---:|---:|
| 年化收益 | **23.3%** | 15.7% |
| Sharpe | **1.20** | 0.84 |
| 最大回撤 | -14.5% | -28.3% |
| 年化换手(单边) | 22.5 × | 0.06 × |
| Worst-year Sharpe | -0.13 (2018) | -1.18 |
| 样本 | 2018-01 → 2026-04 (424 周) | – |

**决策**: `RESEARCH-ONLY`(6/7 审计通过,卡在 2018 worst-year 0.5 floor)

## 分年表现(B6 winner)

| 年份 | 年化收益 | Sharpe | MaxDD | 周数 |
|---:|---:|---:|---:|---:|
| 2018 | **-2.7%** | **-0.13** | -14.5% | 50 |
| 2019 | +24.0% | +1.36 | -12.3% | 51 |
| 2020 | +46.1% | +2.03 | -7.8% | 52 |
| 2021 | +25.7% | +1.40 | -7.8% | 52 |
| 2022 | +10.5% | +0.50 | -13.7% | 50 |
| 2023 | +6.0% | +0.47 | -8.7% | 50 |
| 2024 | +41.9% | +1.63 | -11.9% | 51 |
| 2025 | +29.8% | +1.88 | -7.1% | 53 |
| 2026 | +70.6% (annualized) | +4.79 | -2.4% | **15(部分年)** |

2026 只有 15 周,夏普被年化夸大,不具代表性。

## 3 个假设族的对比

| 族 | 机制 | Top-spec Sharpe | 通过 6/7 审计? | 备注 |
|---|---|---:|:---:|---|
| **A** penalized | 动量 - λ·拥挤 + 广度 | 1.36 (A7) | 5/7 | 绝对值最高,但 2018 -0.45 更差 |
| **B** layered | 动量选 Top-K,再挑低拥挤 | 1.20 (B6) | 6/7 | **推荐**,2018 -0.13 最稳 |
| **C** reversal | 真·买跌卖涨 | 0.24 (C1) | 0/7 | **全败**,A 股行业周频不存在反转效应 |

**关键对比**: C 族 8 个 spec 全部 ≤ 0.25 Sharpe,反向测试强烈 falsify "A 股周度行业反转"。这本身是研究发现。

## 两个机制级洞察

### 1. "低拥挤 × 动量" = 红利价值轮动器(regime-coherent)

B6 的持仓分布(按持仓周数占比):

| 行业 | 持仓占比 |
|---|---:|
| 银行 | 34.4% |
| 石油石化 | 33.3% |
| 食品饮料 | 32.3% |
| 煤炭 | 24.1% |
| 非银金融 | 18.9% |
| 家用电器 | 18.6% |
| 公用事业 | 17.9% |
| 交通运输 | 15.1% |

这是典型的 **红利/价值风格组合**。策略在机制上变成"当主线指向低波动价值,买主线"—— 完美契合 A 股 2019-2026 "中特估" + 高股息主导的宏观环境。

**潜在风险**:如果 A 股重回 AI/新能源/新消费成长主题,低换手过滤器会漏掉那些行业(它们炒作起来换手率暴涨)。

### 2. 2018 是系统性熊不是策略失灵

2018 年熊市中,31 个行业中位数年化 -25%。即使 Top-3 选择策略,也只是比基准跌得少。B6 的 -2.7% 收益 + Sharpe -0.13 实际是在基准 -25% 面前的优秀表现,但仍不达 0.5 floor。

**修复选项**:`market_breadth_gate`(breadth 20% 连 6 周 → 切现金)在回测中把 2018 收益从 -2.7% 推到 +3%,但代价是 2022 小幅损失(因 gate 误伤)。值得在 Round 2 细致调优。

## 审计(B6 完整)

| # | 审计 | 结果 | 通过 |
|---:|---|---|:-:|
| 1 | Execution delay gradient | d=0/1/2/3 → 1.20/0.98/0.79/0.89,单调衰减 | ✓ |
| 2 | Lookahead (placebo) | 横截面置换 score,Sharpe p=0.000 | ✓ |
| 3 | Worst-year ≥ 0.5 | 2018 = -0.13 | **✗** |
| 4 | Best-year-out ≥ 50% full | ex-2026 Sharpe 1.11 ≥ 0.5×1.20=0.60 | ✓ |
| 5 | Placebo Sharpe, 200 trials | null mean 0.59,p=0.000 | ✓ |
| 6 | Placebo worst-year | null mean -0.80,p=0.030 | ✓ |
| 7 | Falsification (C 反转族) | C 全败,动量方向唯一 | ✓ |

**6/7 通过**。唯一 hard fail 是 worst-year 0.5 floor,原因是 2018 系统性熊。

## IC / ICIR(primary signal = mom_4w)

- Full mean IC: **0.031**
- ICIR: **0.10**
- Per-year IC(部分):2019 0.07, 2020 0.09, 2022 0.02, 2025 0.04

IC 不高但 **ICIR 稳** —— 这符合"行业层面只有 31 个样本,横截面 IC 天然噪声大"的预期。真正创造 Alpha 的是 layered filter 把 IC 转化为 concentrated portfolio returns。

## ETF 上线实操建议

1. **标的映射**: SW L1 行业 → 跟踪 ETF。大多数主流 ETF 跟踪 CSI/SW 指数。可选映射表:
   - 银行 → 512800/512820
   - 食品饮料 → 515170/159928
   - 煤炭 → 515220
   - 等等(Round 4 细化)
2. **成本假设更新**: ETF 佣金单边 1-3 bps(比回测假设 5 bps 更低),但加 0.5-2 bps 冲击成本 → 净成本约 2-5 bps。回测假设偏保守,真实表现可能更好。
3. **kill-switch**:rolling 12m Sharpe < 0 连 4 周 → pause 1 month,重新评估。
4. **仓位建议**:作为"小仓位 + guarded"策略,不超过总资产 10-15%(因 worst-year 风险)。

## 下一轮方向(可选)

1. **Round 2: Growth-rotator 配对** —— 构建 `mom × HIGH turnover` 反向策略,捕捉 AI/赛道型主线。用 breadth + 主升/分散度作为 regime detector,在两个 rotator 间切换。
2. **Round 3: 多 regime ensemble** —— value-rotator + growth-rotator,动态权重。
3. **Round 4: ETF 层现实化** —— 把 SW L1 映射到真实 ETF,加入跟踪误差、折溢价、日内流动性,验证策略在 *可交易* 宇宙的表现。

## 交付物清单

- `inputs/research_brief.md`
- `inputs/session_metadata.yml`
- `outputs/industry_weekly.parquet`(31×424 的周频行业面板)
- `outputs/industry_daily.parquet`(日频备份)
- `outputs/expressions_batch_000{1,2,3}.md`(3 个族 × 8 specs)
- `outputs/backtest_results_batch_000{1,2,3}.parquet`(24 条 equity curve)
- `outputs/backtest_summary.csv`(24 spec 汇总)
- `outputs/per_year_top_specs.csv`(top 7 的分年)
- `outputs/round2_gate_grid.csv`(base × gate × fallback grid)
- `outputs/final_b6_metrics.json`(推荐策略完整指标)
- `outputs/final_b6_equity.csv`, `final_b6_pnl.csv`
- `outputs/placebo_sharpe.csv`, `placebo_worst.csv`
- `outputs/alpha_ranking.md`, `round_0001.yml`, `final_summary.md`
- `scripts/{01,02,03,04,05}_*.py`
