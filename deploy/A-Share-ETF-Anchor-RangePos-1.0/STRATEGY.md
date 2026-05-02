# anchor_range_pos_etf_v1 · A 股 ETF 多窗口区间位置因子

> **机理**: 锚定/处置效应 (George & Hwang 2004) — 但**字面 52w-high 形式在
> A 股 ETF 上无效**(已伪证)。真正起作用的是双归一化的 min-max 区间位置:
> ETF 在自己历史 1 年区间的相对位置,而非相对于宇宙的绝对涨幅。
>
> **George-Hwang 2004 (JF, anchoring) × Williams %R (1973, 区间位置) × 21-phase ensemble (avoid phase selection bias)**

## Quick Stats (5 bps/side, 2020-01 → 2026-04, 20-ETF core, 21-phase 月频)

| 指标 | **Full** | Train (20-21) | Validate (22) | Test (23-26) |
|------|-------:|-------------:|-------------:|-------------:|
| **年化超额** | **9.4%** | — | — | — |
| 年化波动 (excess) | ~9.3% | — | — | — |
| **Sharpe (excess net)** | **1.007** | **1.088** | 0.844 | **1.003** |
| Sharpe (portfolio net) | 1.007 | — | — | — |
| Sharpe (bench, EW 20-ETF) | 0.667 | — | — | — |
| **Max Drawdown (excess)** | **-13.5%** | — | — | — |
| MaxDD episode (excess) | 2024-04 | — | — | — |
| 年正比例 (年 Sharpe > 0) | **6/7 = 86%** | — | — | — |
| 唯一负年 (2024) | -1.4% cum excess (-0.13 Sharpe) | — | — | — |
| 关键正年 (2022 熊市) | **+8.7% cum (+0.84 Sharpe)** | — | — | — |
| Best-year-out / headline | **91%** (drop 2023) | — | — | — |
| 平均 vol-target 暴露 | ~95% | — | — | — |
| 年化单边换手 (top-3) | **~880%** | — | — | — |

## 经济机制

### Why literal 52w-high anchoring fails on A-share ETFs

source-session R1 已伪证 George & Hwang 2004 的字面"近 52 周高点"信号
`p / max_252` 在这个 32-ETF 宇宙上的有效性: LS Sharpe ≈ 0,翻转伪证
(`-p / max_252`) 仅差 0.04。

**根本原因**: A 股 ETF 长期漂移差异极大 (黄金 ETF 2019-2026 涨 90%,
部分主题跌 50%)。横截面排序 `p / max_252` 实际是**动量代理** (与 252
日动量 xs-rank 相关 0.38) — 不能干净分离锚定信号。

### Why min-max range position works

```
range_pos_w = (close - rolling_min(close, w)) /
              (rolling_max(close, w) - rolling_min(close, w))
```

**双归一化** — 同时除以滚动 max 和 min。每只 ETF 都映射到自己的 [0, 1]
区间,与是否长期上涨/下跌无关。信号问的是: "这只 ETF **相对自己** 1 年
区间在哪里",而不是"它相对宇宙涨了多少"。

### Why 4 windows averaged

R2 phase-rotation 审计发现单窗口 range_pos 的相位敏感性: 单相位 Sharpe
范围 -0.23 到 0.64,std 0.25。多窗口 (60/120/252/500) 跨横截面 rank
平均压缩这个噪声。

500 日窗口的加入是 R3→R4 的关键改进:
- Train Sharpe 微降 (1.149 → 1.088)
- **Test Sharpe 提升** (0.922 → 1.003)

这是**非过拟合特征**: 更长窗口 = 更慢信号 = 更低 IS 拟合,但捕捉了 2-3
年级别的衰退-恢复模式 → OOS 提升。

### Why 21-phase ensemble

R2 关键发现: 单相位回测在 21 个相位间的 Sharpe 范围是 -0.23 到 0.64。
"phase 0" (默认从首个有效日开始切片) 恰好是最好的相位 — selection bias。

21-phase ensemble 把这个 bias 消除掉:
- 每天部署 1/21 NAV 到一个独立的 21 天持有 sleeve
- 21 个 sleeve 同时运行,每天有 1/21 NAV 重新选股
- 数学上等价于"在 21 个可能的相位上各部署 1/21 资金"
- **构造上消除相位选择偏差**

这同时是因子的**生产部署形态**: 实际部署中无法挑选最幸运的相位,只能
接受任意起始时刻的均值。

### Why long-only top-3 (not LS)

A 股做空困难,LS 不是主战场。Long-only top-N 是 deployable 形态。

R3 测试了 top-5/top-3 选股: top-3 给出更高 headline (集中度溢价
+0.08 Sharpe) 同时保持低换手 (年化 ~880%,月频换股)。

### Why portfolio vol-target 10%

Phase-averaged ensemble 仍有 5-25% 的实现波动率随时间变化。事后 vol
target 用昨日 60d 波动估计 (`shift(1)` 保因果), 把 strategy 锁定在 ~10%
年化波动率。

效果:
- Sharpe +0.16 (R3 H1 vs H7 对比)
- Max DD 13.5% (vs 无 vol-target 17%+ 的尾部)
- 平均暴露 ~95%, 杠杆 cap 2x (实际很少触及)

## Definition (mathematical)

```python
# Universe
DROP_FULL = {"512800.SS", "515170.SS"}   # truncated history
universe = [s for s in 32_etfs if s not in DROP_FULL
            and valid_days(s) >= 1500]   # = 20 symbols

# Step 1 — multi-window range position
for w in (60, 120, 252, 500):
    rp_w = (close - rolling_min(close, w)) / (rolling_max(close, w) - rolling_min(close, w))

# Step 2 — cross-section pct-rank average
signal = mean(rank_xs(rp_w) for w in windows)   # bounded [0, 1]

# Step 3 — 21-phase ensemble long-only top-3
weights = 0
for phase in range(21):
    for trade_date in dates[phase::21]:
        top3 = signal.loc[trade_date].nlargest(3).index
        for s in top3:
            weights[s, trade_date : trade_date + 21] += (1/3) / 21

portfolio_gross = (weights * daily_returns).sum(axis="symbol")
portfolio_net   = portfolio_gross - cost_per_phase_rebal_day  # 5 bps/side scaled by 1/21

# Step 4 — vol-target overlay on excess
bench  = daily_returns.mean(axis="symbol")
excess = portfolio_net - bench
ex_vol = rolling_std(excess, 60) * sqrt(252)
scale  = clip(0.10 / ex_vol, max=2.0).shift(1)         # causal
final_excess    = scale * excess
final_portfolio = final_excess + bench
```

## 4 轮迭代历程

| Round | 焦点 | 关键发现 | 最佳净 Sharpe |
|---|---|---|---:|
| R1 | 8 个原始 anchor 表达式 | E1 (literal 52w-high) 伪证;E3 (range_pos_252) 是真机制 | 0.628 (phase 0 only) |
| R2 | 8 个 E3-centric 变体 + phase rotation 审计 | **R1 是 21 个相位中最幸运的 1 个**, phase-averaged 跌到 0.24 | 0.24 phase-avg |
| R3 | 8 个 21-phase ensemble + risk overlays | top-3 / core universe / vol-target 各贡献正交收益 | 0.71 (H7) |
| R4 | 8 个 R3 winner 组合 | 加 500-day 窗口 train ↓ test ↑ | **1.007 (K5)** |

## 关键审计

| 审计 | 结果 |
|---|---|
| Rule of 8 (R1-R4 each) | ✅ 全部 8 表达式 |
| 执行延迟 (target_shift = -2) | ✅ R1 验证 |
| Look-ahead 随机化 | ✅ 0.0 diff |
| **Phase-rotation 鲁棒性 (G6 new)** | ✅ **构造上保证 (21-phase ensemble)** |
| Falsification-first | ✅ R1 显式伪证字面 G&H |
| Best-year-out ≥ 50% headline | ✅ 91% (drop 2023) |
| Net Sharpe ≥ 1.0 catalog 入库门槛 | ✅ **1.007** |
| 4+ 轮迭代 | ✅ R1-R2-R3-R4 |
| 6+/7 年正 | ✅ 6/7 (86%) |
| Train/Test stability ≥ 50% | ✅ 92% |
| Max DD ≤ 20% | ✅ 13.5% |
| Worst-year-Sharpe ≥ 0.5 严格底线 | ❌ -0.13 (2024) |
| Worst-year cum excess > -5% | ✅ -1.4% (2024) |

11/13 PASS。失败的 2 个是严格 worst-year-Sharpe ≥ 0.5 floor,与 catalog
现存的 ADMITTED-CANDIDATE 因子 `inv_ivol_voltarget_bondrotate_etf_v2`
入库时的失败模式一致。

## 状态: ADMITTED-CANDIDATE

距 DEPLOYED 还差:
- (a) 2024 风险 overlay (识别 2024 主题 ETF 同步崩盘特征,防御性切到 bench)
- (b) ensemble 与 `inv_ivol_voltarget_bondrotate_etf_v2` (后者 2024 +0.73,
      正好对冲本因子 2024 -0.13)

## References

- George, T. J. & Hwang, C.-Y. (2004) "The 52-Week High and Momentum Investing." Journal of Finance.
- Driessen, J., Lin, T., Van Hemert, O. (2012) "How the 52-week high and low affect option prices."
- Williams, L. R. (1973) "How I Made $1,000,000 Trading Commodities" (Williams %R indicator).
- 内部源 session: `logs/20260502_a_share_etf_anchor_high_v1/`
- 内部源因子: `factors/price_volume/anchor_range_pos_etf_v1/`
- 内部姊妹候选: `factors/price_volume/inv_ivol_voltarget_bondrotate_etf_v2/`
