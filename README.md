# Factor_Zoo

**因子挖掘结果展示仓库** —— 系统化存放量化因子的挖掘、回测与评估产出。

本仓库不仅作为 `worldquant-5-agent-workflow` 工作流的云端运行目录,更是
团队 / 个人因子挖掘沉淀的结果中心。所有入选因子都会在此持续更新评测指标与
增量样本外表现。

---

## 一、因子类别

本仓库覆盖的因子体系涵盖 A 股与加密市场,分为以下几大类:

### 1. 量价因子 (Price–Volume Factors)
基于价格序列、成交量、换手率等交易数据构造的高频 / 中低频信号。
- **动量类**:N 日收益率、跨周期动量 (Moskowitz/Ooi/Pedersen 2012)
- **反转类**:短期反转、日内反转
- **波动率类**:已实现波动率、振幅、下行波动
- **流动性类**:换手率、Amihud illiquidity、成交量加权
- **量价配合**:OBV、MFI、VPT、成交量 Z-score
- **WorldQuant Alpha 101 / 191**:经典表达式因子库

### 2. 基本面因子 (Fundamental Factors)
基于财务报表、估值指标与一致预期构造的中低频信号。
- **估值**:PE / PB / PS / PCF、股息率、EV/EBITDA
- **盈利能力**:ROE / ROA / 毛利率 / 净利率、经营现金流质量
- **成长**:营收 / 净利润同比环比、SUE
- **质量**:应计项、Piotroski F-score、资产负债率
- **分析师一致预期**:盈利预测调整、目标价偏离度

### 3. 趋势 / 技术因子 (Trend & Technical Factors)
捕捉价格结构、趋势强弱与均值回归的技术类信号。
- **趋势跟随**:MA 穿越、MACD、DMI/ADX
- **偏离度**:LogBias、布林带位置、KDJ
- **相对强弱**:Wilder RSI(14)、相对基准 (沪深 300 / BTC) 强弱
- **形态识别**:突破、缺口、K 线结构

### 4. 另类与跨市场因子 (Alternative & Cross-Market)
- **资金流向**:北向资金、ETF 申赎、主力资金流
- **情绪**:融资融券、期权 PCR、舆情
- **宏观**:无风险利率、通胀、汇率、信用利差
- **加密链上数据**:Exchange Netflow、Whale Activity、Funding Rate

---

## 二、目录结构

| 目录 | 说明 |
| --- | --- |
| `worldquant-5-agent-workflow/` | WorldQuant 风格的 5-Agent 因子生成 / 评估工作流 (Knowledge → Planner → Generator → Backtest → Evaluator) |
| [`factors/`](factors/) | **入库因子定义、构建代码、评估指标(每个因子一个子目录)** |
| [`logs/`](logs/) | 因子挖掘 session 完整 artifacts(research_brief / expressions / backtest_results / 审计) |
| `figures/` *(TBA)* | 分层净值曲线、IC 衰减图、热力图 |
| `reports/` *(TBA)* | 每批次因子挖掘的研究报告 |

## 已入库因子

| 因子 | 类别 | LS Sharpe (净万5) | Q5 IR (净万5) | Max DD | 状态 |
|------|------|------------------:|--------------:|-------:|:----:|
| [`accruals_median_ttm_ind_neutral_v2`](factors/fundamental/accruals_median_ttm_ind_neutral_v2/) | `fundamental.quality` | **1.34** | **1.13** | −1.85% | DEPLOYED |
| [`ag_orth_nsi_2y_v1`](factors/fundamental/ag_orth_nsi_2y_v1/) | `fundamental.investment` | — (long-only) | **Abs Sharpe 0.70 / CAGR 17.5%** | — | PROMOTE |

(accruals 基于 A 股 2018-2025,5,285 只股票,82 次月度再平衡,5 bps 单边手续费,turnover-aware 成本模型)
(ag_orth_nsi_2y_v1 基于 A 股 2020-2025,~4,500 只股票,月度再平衡,5 bps/side,定位 long-only 绝对回报产品;
 5/6 年正收益, 最差年 2022 -0.4%, 2025 YTD 68 天 +9.3% 实际回报; 严格 excess 口径下 2025 YTD Sharpe -0.61, 68天样本t不显著)

## 研究记录 (RESEARCH-ONLY)

未通过完整审计、暂不部署但具有研究价值的 session:

| Session | 类别 / 机制 | 最佳原始 LS Sharpe | 关键发现 |
|---|---|---:|---|
| [`20260421_volprice_max_lottery`](logs/20260421_volprice_max_lottery/) | `volume_price.lottery_demand` (MAX + 偏度) | 2.62 (α_05) / 2.92 测试 (α_15) | A 股 "lottery demand" 信号 (MAX / 偏度 / 跳跃计数) 基本被波动率 + 短期反转吸收;去除 σ 和 ret 20 后残差 IC < 0.02,不具有独立 alpha,见 [`final_summary.md`](logs/20260421_volprice_max_lottery/outputs/final_summary.md) |
| [`20260423_btc_minute_reversal_v1`](logs/20260423_btc_minute_reversal_v1/) | `crypto.minute_reversal` (vol-scaled, 15m hold) | R1: 8.42 gross / R2: 2.54 gross | BTC-USD 1m × 60d,Coinbase。**2 rounds**:R1 (k=5m) 撞到死区,2/8 过闸;R2 (k=15m + 15-bar hold) 机制确认 (IC t=3.86,G5 batch-horizon 100% 过),但 0/8 过新 G3 net-Sharpe 闸 — 成本结构性阻塞 (breakeven 0.4 bps/side vs 现实 5-10 bps,信号比成本小 30×)。首次 dogfood `validation-gates.md` 的 G1-G5 + 新 net-Sharpe 闸 + G5 batch horizon,见 [`final_summary.md`](logs/20260423_btc_minute_reversal_v1/outputs/final_summary.md) |
| [`20260423_a_share_etf_reversal_v1`](logs/20260423_a_share_etf_reversal_v1/) | `trend_technical.long_term_reversal_etf` (60d, monthly) | R2: **+0.58 gross / +0.56 net@5bps** | 18 只 A 股 ETF 日频 2020-2026。**2 rounds**:R1 (k=10 周频) 假设被数据反证 — 7/8 IC 负,G5 正确识别"机制错了而不是代码错了",返回 Agent 2 重定位;R2 (k=60 月频) 机制确认,`r2_lt_rev_60d` IC t=+2.35,Q5-Q1 单调,净 Sharpe 过 0.5 闸,但 2020 worst-year Sharpe -0.68 卡住 PROMOTE。关键新发现:**反转在 A 股 ETF 上是一个窄 ~60 日窗口**,≤20 日是动量,~1 年也是动量。RSI<30 选择性抄底 IC t=+7.75 @ k=20 (研究中最强),但 top4/bot4 strategy spec 不匹配。首次引入 "audit probe" (`+logret_20d` 作为管道 sanity 检查,IC≈0 确认无 pipeline bug),见 [`final_summary.md`](logs/20260423_a_share_etf_reversal_v1/outputs/final_summary.md) |
| [`20260423_a_share_etf_weekly_tqpb_v1`](logs/20260423_a_share_etf_weekly_tqpb_v1/) | `trend_technical.breakout_volume_confirmed_weekly_etf` (combine target: V7_gold) | **Round 1 (RETRACTED):** 1.79 combined / **Round 2 (CORRECTED):** 1.71-1.75 combined (V7 基线 1.76, 全部 Δ 在噪音内) | 34 只 V7_gold universe 主题 ETF 2019-2026, 377 周。**2 rounds**:R1 报告 `r1_breakout_vol_conf` 与 V7 相关性 -0.009,15% LS overlay 得 Sh 1.79 / MaxDD -7.7%;**R2 审计发现 R1 信号恒为 0** —— `max_high_20 = rolling(20).max()` 包含 today 本身,breakout 日 `close - max = 0`,全 42,788 obs signal 均为 0;R1 的 Sh 1.79 是 pandas stable-sort 对 tie 的字母排序 ghost alpha。R2 用正确语义 (`shift(1).rolling(20).max()`, 严格 `>`) 重跑 4 个方向:(1) long-only top-3 叠 V7 5%→Sh 1.71 (Δ -0.05);(2) Leg A 信号级融合 (0.15 breadth + 0.15 z(brk))→Sh 1.73 (Δ -0.03);(3) regime-conditional @ breadth_z<-0.25 →Sh 1.75 (Δ +0.02, t≈0.4 噪音);(4) 扩 48 ETF universe→Sh 1.71 (Δ -0.05);always-on 15% LS 用正确信号→Sh **1.693 (低于 V7 基线)**。**R1 部署推荐正式 RETRACT**,V7_gold 独立运行 (Sh 1.76 / MaxDD -9.1%)。Dogfood 新发现:(a) G1 应加 signal-non-degeneracy 检查 (count(!=0), unique_count);(b) "breaks prior N-day high" 必须 `shift(1).rolling(N).max()` + 严格 `>`;(c) overlay session 每个 rebalance date 必须显式写零权重(避免 ffill 无限持仓);(d) combine 基线必须从源头重算 (不信已存 PnL);(e) "zero-signal probe" 作为 combine session 强制审计。见 [`round2/final_summary.md`](logs/20260423_a_share_etf_weekly_tqpb_v1/outputs/round2/final_summary.md) |
| [`20260424_a_share_etf_reversal_v2`](logs/20260424_a_share_etf_reversal_v2/) | `trend_technical.medium_horizon_reversal_etf` (k=40-80, long-only) | **+0.81 gross / +0.774 net@5bps** (long-only top-3 monthly) | 34 只 V7_gold universe 主题 ETF 2019-2026。跟进 v1 的 "~60d 反转带" 发现,把宇宙从 18 扩到 34 并重扫 horizon (k=1/5/20/40/60/80 + 2 drawdown event)。**机制跨宇宙复现且变锐**:IC t-stat 阶梯 k=20:0.79 → **k=40:3.02** → k=60:2.43 → k=80:2.29;k=40 取代 k=60 成为新 sweet spot,反转带从一个点扩成一段 (40-80d)。**长-only top-3 monthly 完全压倒 LS**:LS 全部 net Sh<0 (短腿是结构性 ~0.8-1.0 Sharpe 拖累,动量在 A 股主题板块持续胜出);long-only 让 r1_rev_40d 从 -0.010 跳到 +0.774。**4 个管道审计 PASS**:执行延迟 (双路径 diff 1.5e-15)、look-ahead 随机化 (within-date 标签打乱使 IC 从 0.026 崩到 0.004)、best-year-out ratio 0.73、falsification probe (+logret_20d IC ≈ 0)。**Worst-year floor FAIL**:2023 是反转灾年 (r1_rev_40d monthly Sh -0.585, r1_rev_80d monthly -0.705),所有候选 < 0 的研究门槛。V7 融合:任意 blend (10%-50%) Δ ≤ 0,反转因子无法改进 V7 chassis。**跨 session pattern**:v1 (18 ETFs) 坏年 = 2020 空头腿伤 (COVID 动量),v2 (34 ETFs) 坏年 = 2023 多头腿伤 (TMT 分化);反转家族在 A 股 ETF 上似乎 ~1/4 年翻符号,regime-conditional gating 是自然下一步。Dogfood:long-only vs LS 在集中-regime 宇宙必须同测;within-date 而非 within-symbol 才是正确随机化;baseline 必须在 exact 对齐窗口上重算。见 [`final_summary.md`](logs/20260424_a_share_etf_reversal_v2/outputs/final_summary.md) |

---

## 三、评估指标

每个入库因子至少包含以下评估维度:

- **IC 系列**:IC 均值、IC_IR、Rank IC、ICIR、IC 衰减
- **分层回测**:Top-Bottom 多空、分层单调性、年化收益 / 夏普 / 最大回撤
- **稳定性**:样本内 vs 样本外、滚动窗口表现、行业 / 市值中性化后表现
- **相关性**:与现有因子的相关矩阵,新因子增量信息 (orthogonal IC)
- **换手 / 容量**:双边换手率、冲击成本估计

---

## 四、工作流

因子挖掘以 `worldquant-5-agent-workflow` 为核心流水线:

```
Knowledge  →  Planner  →  Generator  →  Backtest  →  Evaluator
  文献/经验    设计方案     公式生成      样本内外       指标 + 归档
                                         回测         (入库 / 淘汰)
```

入库标准(建议):Rank IC 均值 > 0.03、ICIR > 0.3、多空年化夏普 > 1.0、
与现有库相关性 < 0.6。

---

## 五、使用

```bash
git clone https://github.com/huyukun662-crypto/Factor_Zoo.git
cd Factor_Zoo
# 查看工作流说明
cat worldquant-5-agent-workflow/SKILL.md
```
