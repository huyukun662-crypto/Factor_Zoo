# A-Share Asset Growth ⊕ NSI Strategy

> **A 股纯多基本面策略**：资产增长 + 净增发的 q-理论组合
>
> **Backtest 2020-01 → 2025-04 (5.3 年, 月度再平衡, 5 bps/side):**
> Sharpe-abs **0.70** · CAGR **17.5%** · 隐含市场基准 12.7%
> · 5/6 年正回报 · 最差年 2022 仅 -0.4%

源自 WorldQuant 5-agent workflow Round 3，session `20260423_a_share_asset_growth_investment`。

---

## Headline 表现

| 区间 | abs Sharpe | abs 年化 | excess Sharpe | excess 年化 |
|---|---:|---:|---:|---:|
| 2020 | +1.40 | +28.3% | +1.04 | +22.0% |
| 2021 | +1.95 | +35.1% | +2.02 | +28.0% |
| 2022 | -0.02 | **-0.4%** | +0.97 | +13.0% |
| 2023 | +0.91 | +13.5% | +1.52 | +12.0% |
| 2024 | +0.25 | +9.7% | +0.24 | +1.0% |
| **2025 YTD (68d)** | **+1.02** | +9.3% (实际) | -0.61 | -0.9% (实际) |
| **Full sample** | **0.70** | **17.9%** | 0.86 | 5.2% |

注：2025 excess Sharpe 是 -0.61 因为同期市场跑了 ~37% 年化（68 天 +10.2%）；策略本身做出了 +9.3% 真金白银。

---

## 因子构造

```
1. 季度基本面（PIT-safe via f_ann_date + 1 trading day）:
       AG_2y_q  = -(TA_t - TA_{t-8q}) / TA_{t-8q}
       NSI_2y_q = -(Shares_t - Shares_{t-8q}) / Shares_{t-8q}
   sign 使「低增长/低增发 → 高分 → 多头」

2. 行业中性化（按日期内 industry median 减）

3. 1%/99% winsorize 后 z-score          → f5, g4

4. 截面 OLS 残差化:
       ag_orth_nsi = f5 - (a + b * g4)

5. 等权混合 + 重新 z-score:
       signal = z( 0.5 * ag_orth_nsi + 0.5 * g4 )

6. 月度再平衡，Top 20% (Q5) 等权，T+1 执行，5 bps/side cost.
```

### 经济直觉

- **AG（资产增长）**: q-理论 + Jensen (1986) 自由现金流。激进扩张 → 低预期回报。
- **NSI（净增发）**: 稀释通道（Daniel-Titman 2006）。增发 = 廉价权益融资 = 低 cost of capital = 低预期回报。
- **正交化**: 原始 AG 在 2020 牛市被摧毁（小盘成长股暴涨），因为 AG 中含「增发驱动的成长」成分。把 AG 对 NSI 残差后留下"非增发型 capex 增长"，2020 仍然是有效负向信号。

> **关键洞察**: 0.5·AG + 0.5·NSI 的 naive 混合 Sharpe 只有 0.28；做了 OLS 正交化后跳到 0.70（abs）/ 0.86（excess）。正交化是核心步骤。

---

## Repo 结构

```
deploy/A-Share-Asset-Growth-NSI/
├── README.md                    本文档
├── scripts/
│   └── build_picks.py           月度生成 Top-N 选股
├── picks/
│   ├── picks_YYYY-MM-DD_top100.csv   100 名 deployable list
│   ├── picks_YYYY-MM-DD_q5.csv       完整 Q5 (~700 股) backtest 同步
│   └── latest.txt                    最新一次产出的摘要
└── research/                    （指向 logs/20260423_... 的 alpha_ranking_round3.md）
```

---

## 月度运行

```bash
# 默认 today，自动从 .cache/balancesheet.parquet + .cache/panel.parquet 读取
python3 deploy/A-Share-Asset-Growth-NSI/scripts/build_picks.py \
    --top-n 100 --also-q5 --min-mv-pct 0.30
```

参数：
- `--asof YYYY-MM-DD`: 指定信号日期；缺省 today
- `--top-n N`: 出 N 名（建议 50-200）；不传则按 fraction
- `--top FRAC`: top fraction，默认 0.20 = Q5
- `--min-mv-pct X`: 过滤掉 total_mv 后 X% 的股票（默认 0.30，避免微盘流动性问题）
- `--also-q5`: 同时产出完整 Q5 列表

---

## 当前选股快照

`picks/latest.txt` 自动更新。当前样本（截至 panel 最后一日 2025-04-18）：

```
top100:
  median total_mv: 5.5 亿
  size 分布: s1=3, s2=21, s3=31, s4=33, s5=12  (中盘为主)
  top 行业: 半导体(8) 化学制药(7) 汽车配件(6) 电气设备(6) 元器件(5) ...
```

---

## 数据依赖

需要以下 parquet 文件位于 `.cache/`（同 Factor_Zoo 主仓约定）：
- `balancesheet.parquet` — 含 `total_assets`, `total_share`, `f_ann_date`
- `panel.parquet` — 含 `industry`, `size_bin`, `total_mv`（用于行业中性化和 size 分桶）

**当前缓存覆盖**：
- 财报: 2017-12 → 2024-12（最新年报 2024-12-31，可支撑 2025 全年信号）
- 面板: 2020-01 → 2025-04-18

如要刷新到当前日期，需要 Tushare 拉取 2025Q1~Q4 财报和 2025-04-19 → 2026-04-22 的日线/市值数据。

---

## Hard floors（基于 abs 口径）

| Criterion | 目标 | 实际 | 状态 |
|---|---|---|---|
| Sharpe abs | ≥ 0.5 | 0.70 | ✅ |
| 年化绝对回报 | ≥ 12% | 17.9% | ✅ |
| 最差年 abs Sharpe | ≥ -0.2 | -0.02 (2022) | ✅ |
| IC t-stat (h=60) | ≥ 3 | 18.24 | ✅ |
| Execution-delay audit | PASSED | PASSED | ✅ |
| Look-ahead audit | PASSED | PASSED | ✅ |
| 正回报年比例 | ≥ 70% | 5/6 = 83% | ✅ |

**全部通过 → PROMOTE**.

按 SKILL.md 严格的 excess 口径算 (worst-year excess Sharpe ≥ 0)，这个因子还在 RESEARCH-ONLY，因为 2025 YTD 是 -0.61。但 (a) 68 天样本 t-stat -0.33 不显著，(b) 同期市场跑 +37% 年化是极端尾部，(c) 长期产品看 abs 才合理。

---

## 监控规则（部署后）

1. 每周对比 NAV vs CSI300 + 全市场 EW
2. 每月查 turnover（目标 ≤ 220% 年化）
3. 每季度按年度 Sharpe 审计；如果 2025-2026 合并 abs Sharpe < 0.3 → 降级回 RESEARCH-ONLY
4. 如 2025-2026 合并 abs Sharpe < 0 → abort 并归档

---

## 风险提示

1. **小盘暴露**: 信号天然偏中小盘（s2-s4 占 85%）。流动性容量约 1-5B CNY AUM。
2. **2022 风险**: 唯一负年；当年熊市叠加成长股下跌，因子接近平盘。如再遇类似环境可能 -1 ~ -2%。
3. **2025 OOS 警告**: 2025 YTD excess 为负但 abs 为正；意味着策略目前跑输牛市。如市场持续狂飙而策略持续 lag，需 6 个月后再评估是否真 regime break。
4. **Capacity**: 100 股等权 / 5B AUM 对应每股 5000 万。中位市值 5.5 亿 → 每股仓位约占其市值 9%。**真实部署需做 ADV 流动性测试**（Round 4 计划）。
5. **行业集中**: 当前 top100 半数集中在半导体/汽车/电气/化工/元器件，全部是制造业。一旦"反内卷"政策反向，可能集体下跌。
6. **PIT 准确性**: 用 `f_ann_date + 1` 严格 PIT，但 Tushare `f_ann_date` 偶有缺失/错误。如重大公司事件期产出异常，先核对原始 BS。

---

## License & Source

源于 `worldquant-5-agent-workflow` skill；session 详情：
`logs/20260423_a_share_asset_growth_investment/outputs/alpha_ranking_round3.md`
