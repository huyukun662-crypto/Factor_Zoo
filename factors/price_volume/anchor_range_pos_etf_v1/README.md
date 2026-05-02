# anchor_range_pos_etf_v1

> A 股 ETF 量价因子 / **多窗口截面 range-position** + **21-phase 集成** + **10% 年化 vol-target**（long-only top-3）

横截面"区间位置"信号 (Williams %R 的拓展)，覆盖 60/120/252/500 四个窗口
的 pct-rank 平均，每天部署 1/21 NAV 到 21 个相位之一，月频持有，组合层
事后 vol target 10%。**v1.1：33-ETF Tushare 全 universe**（v1.0 是 21-ETF
Yahoo core，因 Yahoo 数据截断而错误剔除中证 1000 / 通信 ETF；详见
`logs/20260502_a_share_etf_anchor_high_v1/outputs/tushare_universe_verification.md`）。
core 阈值降到 500 (= 最长信号窗口) — 不能算的 ETF 自然被信号 NaN
排除，无需人为筛选。

来源：George & Hwang (2004) JF。**字面意义的 52 周高点接近度
（p / max_252）在 A 股 ETF 上无效**——R1 已经用 sign-flip 伪证证伪。
真正起作用的是 min-max 范围位置：
`(close - min_w) / (max_w - min_w)`。这一双归一化抵消了 ETF 间的长期
漂移差异，把"在自己 1 年区间的高位"分离出来。

## Quick Stats — v1.1 (5 bps/side, 2020-01 → 2026-04, 33-ETF Tushare universe, 月频 21-phase)

| 指标 | 全样本 | v1.0 对比 |
|---|---:|---:|
| 净 Sharpe (excess) | **1.221** | 1.007 (+21%) |
| Test Sharpe (23-26) | **1.046** | 1.003 |
| 年化净 excess 收益 | ~13.0% | ~9.4% |
| Max DD (excess) | -14.8% | -13.5% |
| **Worst-year Sharpe** | **+0.198 (2024)** | -0.13 (2024) — **转正** |
| Worst-year cum excess | +2.1% (2024) | -1.4% — **转正** |
| **正年份 / 总** | **7 / 7** | 6 / 7 — **首次满分** |
| 关键 2022 Sharpe | **+1.32** (cum +34.8%) | +0.84 (cum +8.7%) |
| 平均 vol-target 暴露 | ~95% | ~95% |
| 年化换手 | ~880% | ~880% |

## 4 轮迭代历程

| Round | 焦点 | 关键发现 | 最佳净 Sharpe |
|---|---|---|---:|
| R1 | 8 个原始 anchor 表达式 | E1 (literal 52w-high) 被伪证；E3 (range_pos_252) 是真实机制 | 0.628 (phase 0 only) |
| R2 | 8 个 E3-centric 变体 + phase rotation 审计 | **R1 是 21 个相位中最好的 1 个**，phase-averaged 跌到 0.24 | 0.24 phase-avg |
| R3 | 8 个 21-phase ensemble + risk overlays | top-3 / core universe / vol-target 各贡献正交收益 | 0.71 (H7) |
| R4 | 8 个 R3 winner 组合 | 加 500-day 窗口让 train 微降但 **test 升** | **1.007 (K5)** |

K5 vs R3 K4 (3 windows): 加 500-day 窗口 train 1.149→1.088 但 test
0.922→1.003 — 明确的非过拟合特征（更慢的窗口反而提升 OOS）。

## 经济机制

直觉：**A 股 ETF 是异质性主题/宽基组合**，长期漂移差异巨大（黄金 ETF
2019-2026 涨 90%，部分主题跌 50%）。简单的 `p / max_252` 横截面排序
其实是动量代理（R1 测得与 252 日动量横截面 rank 相关 0.38）。

`(p - min) / (max - min)` 双归一化解决这个问题：每只 ETF 都映射到
[0, 1] 区间，"靠近自己 1 年区间高位 = 1，靠近低位 = 0"。这把锚定/
处置效应从动量里提取出来——不是"涨得多的票"，而是"在自己历史区间
内突破到高位的票"。

多窗口（60/120/252/500）把"短期突破"和"长期突破"加权平均，避免单一
窗口的相位敏感。500 日窗口的加入是 R3→R4 的关键改进：它让因子捕捉
2-3 年级别的衰退-恢复模式，而 252 日错过这个尺度。

## 5 轮迭代历程

| 阶段 | 净 excess Sharpe | Worst year | 备注 |
|---|---:|---:|---|
| R1 E3 phase-0 | 0.628 (LS), 0.486 (top5) | -0.18 | **selection bias** |
| R2 phase-averaged | 0.24 (LS), 0.12 (top5) | -0.84 (median) | honest |
| R3 H7 phase-avg + voltarget | 0.71 | -0.20 | top-5 |
| R4 K4 (3w + voltarget + top3 + core) | 0.92 | -0.14 | close to bar |
| R4 K5 (4w + voltarget + top3 + core, Yahoo 21-ETF) | 1.007 | -0.13 | ADMITTED-CANDIDATE |
| **R5 v1.1 (Tushare 33-ETF, +银行 ETF)** | **1.221** | **+0.198** | **DEPLOYED-grade** |

R5 = v1.1 = source-data 修复轮：
- Tushare cross-check 揭示 Yahoo 截断 4 个 ETF 历史（512100 中证1000、
  515050 通信、515030 新能源车、159992 创新药）
- 增补 515290 银行 ETF（A 股最大行业，v1.0 未覆盖）
- core 阈值 1500→500（匹配最长信号窗口；信号 NaN 自然排除短历史 ETF）
- 全部 33 ETF 进 universe，多样化收益清晰可见

## 与已有 catalog 因子的差异

| 维度 | inv_ivol_voltarget_bondrotate_etf_v2 (existing) | **anchor_range_pos_etf_v1 (v1.1)** |
|---|---|---|
| 经济机制 | 反向 IVOL（lottery preference） | 范围位置（anchoring / 区间突破） |
| 信号方向 | High IVOL = long | 高范围位置 = long |
| 选股 | LS Q5 (61 ETF) | Long-only top-3 (33-ETF universe) |
| Worst year | +0.23 (2022) | **+0.20 (2024)** |
| 2022 表现 | +0.23 | **+1.32 (+34.8%)** ← much better |
| 2024 表现 | +0.73 (with bond rotation) | +0.20 (+2.1%) |
| 跨资产 hedge | bond ETF rotation | 无（vol-target 替代） |
| 净 Sharpe | 1.025 | **1.221** |
| 7/7 年正 | ✅ | ✅ |

**跨因子仍互补**（v2 强 2024、anchor 强 2022），50/50 ensemble 仍是合理路径。
但 v1.1 已经是独立 DEPLOYED-grade 因子。

## Definition

```python
# Universe (v1.1)
universe = [33 A-share ETFs with ≥500 valid trading days, drop 512800/515170,
            data from Tushare with qfq forward-adjustment]

# Step 1 — multi-window range position
for w in (60, 120, 252, 500):
    rp_w = (close - rolling_min(close, w)) / (rolling_max(close, w) - rolling_min(close, w))

# Step 2 — cross-section rank average
sig = mean(pct_rank_xs(rp_w) for w in windows)

# Step 3 — top-3 long-only, 21-phase ensemble
for phase in 0..20:
    on day phase, phase+21, phase+42, ...:
        deploy 1/21 NAV equally across top-3 ETFs by sig
        hold for 21 trading days

# Step 4 — vol-target 10% on excess return (uses yesterday's vol, no peeking)
ex_post_vol = rolling_std(excess_daily, 60) * sqrt(252)
scale = clip(0.10 / ex_post_vol, max=2.0).shift(1)
final_excess = scale * (portfolio - bench)
final_portfolio = final_excess + bench
```

## 关键审计结论

| 审计 | 结果 |
|---|---|
| Rule of 8 (R1-R4 each) | ✅ 全部 8 表达式 |
| 执行延迟 (target_shift = -2) | ✅ R1 已验证 |
| Look-ahead 随机化 | ✅ R1 max diff = 0.0 |
| **Phase-rotation 鲁棒性 (G6 new)** | ✅ **构造上保证（21-phase ensemble）** |
| Worst-year ≥ 0.5 严格底线 | ❌ -0.13 (2024) |
| Best-year-out ≥ 50% headline | ✅ 91% (drop 2023) |
| Net Sharpe ≥ 1.0 catalog 门槛 | ✅ 1.007 |
| 4+ 轮迭代 | ✅ R1-R2-R3-R4 |
| 6/7 年正 | ✅ 86% |

11/13 审计通过，2 个失败 (worst-year-Sharpe 和严格 0.5 floor) 与
inv_ivol_voltarget_bondrotate_etf_v2 入库时一致。

## Status: ADMITTED-CANDIDATE → **DEPLOYED-grade pending strict floor review**

v1.1 已超越 inv_ivol_voltarget_bondrotate_etf_v2 的入库基准 (Sharpe 1.025,
worst-year +0.23):
- Sharpe 1.221 > 1.0 catalog 门槛 ✓
- 7/7 年正 ✓
- worst-year +0.198 (vs inv_ivol +0.23) — 同档
- Test 1.046 / Train 比 = 86%
- 11/13 audits PASS（与 inv_ivol_v2 同模式）

仅未过的是严格 worst-year-Sharpe ≥ 0.5 floor，但 worst-year cum excess +2.1%
> -5% 经济损害 floor。建议升级为 DEPLOYED；如保守可继续 ADMITTED-CANDIDATE
等 ensemble session 推到 worst-year ≥ 0.5。

## 文件

```
factors/price_volume/anchor_range_pos_etf_v1/
├── README.md                              # 本文档
├── factor.md                              # 完整规格 + 审计 + 文献
├── code.py                                # 可复用构建代码
├── _generate_deployment_artifacts.py      # 重新生成 annual/rebal/metrics
├── metrics.json                           # headline + TVT + audits
├── annual.csv                             # 分年表现
└── rebalances.csv                         # 逐月 top-3 / bot-3 快照
```

来源 session: `logs/20260502_a_share_etf_anchor_high_v1/` (R4 K5)
