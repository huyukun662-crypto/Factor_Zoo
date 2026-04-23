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
| [`20260421_volprice_max_lottery`](logs/20260421_volprice_max_lottery/) | `volume_price.lottery_demand` (MAX + 偏度) | 2.62 (α_05) / 2.92 测试 (α_15) | A 股 "lottery demand" 信号 (MAX / 偏度 / 跳跃计数) 基本被波动率 + 短期反转吸收;去除 σ 和 ret_20 后残差 IC < 0.02,不具有独立 alpha,见 [`final_summary.md`](logs/20260421_volprice_max_lottery/outputs/final_summary.md) |

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
