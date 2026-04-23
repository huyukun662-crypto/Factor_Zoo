# Research Brief — 中国行业 ETF 轮动策略 (Industry Rotation CN)

**Agent 1 · Research Librarian · 2026-04-22**

## Task

设计一个中国 A 股行业 ETF 轮动策略,目标:
1. **抓阶段主线** —— 识别当前主导市场的行业/板块
2. **高低切** —— 过热行业减仓,欠热行业加仓
3. **周度调仓** —— 周频再平衡(周五收盘计算,下周一开盘执行,delay=1)

## Literature (relevant to Chinese industry rotation)

### 1. 行业动量 (cross-industry momentum)
- **Moskowitz & Grinblatt (1999, JF)** — "Do Industries Explain Momentum?"
  行业层面的动量比个股动量更稳健,短期动量在行业上表现显著。
- **Jegadeesh & Titman (1993, JF)** — 经典动量 3-12M 长度,对应到周频为 4-24w。
- **Novy-Marx (2012, JFE)** — "Is Momentum Really Momentum?" 动量主要由 7-12 月的中段贡献,而非最近 1 月。反映"避免近期高点反转"的必要。

### 2. 注意力/拥挤度(crowding proxy)
- **Da, Engelberg, Gao (2011, JF)** — SVI 搜索量作为注意力指标。A 股可用 **成交额/市值**、**换手率 z-score** 作为替代。
- **Lou (2014, RFS)** — "Attracting Investor Attention Through Advertising": 过高关注度预示短期反转。
- **Cooper, Gutierrez, Hameed (2004, JF)** — 市场状态依赖(up-market 动量强,down-market 动量反转),对应 market-state gate。

### 3. 短期反转(变体 C 的基础)
- **Jegadeesh (1990, JF)** — 月度股票短期反转。
- **Lehmann (1990, QJE)** — 周度反转效应。
- **Da, Liu, Schaumburg (2014, RFS)** — 行业反转与行业内反转可分解。
- **Bali, Cakici, Whitelaw (2011, JFE)** — Lottery/MAX 效应的反转本质;行业层面亦存在"炒作反噬"。

### 4. 中国 A 股特定
- **Carpenter, Lu, Whitelaw (2021, JFE)** — A 股独有的波动结构;散户主导带来更强的动量-反转共存。
- **Liu, Stambaugh, Yuan (2019, JFE)** — CH-3:规模因子特殊、估值以 EP 为佳。
- **Cheema & Nartea (2017)** — Chinese industry momentum 在 1-4 周有效,超过 4 周动量衰减明显。
- **实务观察**:2021 白酒、2023 CPO、2024H1 AI 均经历"主升 → 过热 → 崩跌"三段,提示 **拥挤惩罚不可或缺**。

## Data

- **Universe**: CITIC / SW L1 行业(~28-30 个)——用 tushare `index_classify(level='L1')` 拿映射,用股票合成行业组合(流通市值加权),比直接用 ETF 价格干净(无跟踪误差、无折溢价噪声)。
- **Sample**: 2018-01 → 2026-04(~8 年,覆盖 2018 熊、2019 反转、2020 疫情 V、2021 赛道、2022 熊、2023 AI、2024 震荡、2025 政策反复)
- **Frequency**: 日频数据 → 周度聚合(周五收盘快照)
- **Cache**: `/home/user/Factor_Zoo/.cache/daily.parquet`, `daily_basic.parquet`, `adj_factor.parquet` 已有至 2026-04-22。

## Three hypothesis families

| Variant | 核心表达式(概念) | 入选逻辑 |
|---|---|---|
| **A (penalized)** | `score = z(mom_4w) − λ·z(crowd_20d) + μ·z(breadth_above_MA20)` | 动量减拥挤罚分,一个数排序 Top-3 |
| **B (layered)** | Step 1: mom 排序取 Top-10;Step 2: 在 Top-10 内按 `−crowd` 排序取 Top-3 | 先抓主线,再在主线内挑"温和上涨"行业 |
| **C (reversal)** | `score = −mom_2w`(外加 crowd 放大器)—— 短期反转 | 真·买跌卖涨,1-4w 窗口 |

## Key design decisions (locked)

- **Delay**: 1 (T+1 执行,周五信号 → 周一开盘)
- **Rebalance**: 每 5 交易日(近似周度)
- **Cost**: 5 bps/side(换手 × 成本)
- **Holdings**: Top-3 等权(和 Bottom-3 做对照,但主打 long-only)
- **Gate 备选**: 全市场 %above-MA20 < 30% 时切现金(2018/2022 防御)

## Risk / known failure modes

1. **2014-2015 风格极端**(不在样本内)
2. **2018/2022 系统性下跌**(需市场 gate)
3. **2021 赛道过热**(拥挤惩罚必要)
4. **2025 政策反复**(已知 α_35 kill-switch 触发,对行业轮动同样敏感)

## Agent 2 请继续

见 `working/handoff_1_to_2.json`。
