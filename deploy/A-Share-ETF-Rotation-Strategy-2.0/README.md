# A-Share ETF Rotation Strategy 2.0 — V7_gold

> **A-share 行业 ETF 轮动策略**:动量 × 拥挤惩罚 × 组轮动 Ensemble
> + 50 周 MA gate + 黄金 ETF 避险 fallback + 15% vol target
>
> **Full-sample (2019-01 → 2026-04, 377 weeks, weekly rebalance):**
> Sharpe **1.91** · Sortino **3.31** · Calmar **3.21** · MaxDD **-8.89%** · AnnRet **28.57%**

---

## Headline performance

| 区间 | 年化 | Sharpe | Sortino | Calmar | MaxDD | 周胜率 |
|---|---:|---:|---:|---:|---:|---:|
| IS 2019-2023 | 26.70% | 1.93 | 2.85 | 2.73 | -8.89% | 60.9% |
| **OOS 2024-2026** | **34.91%** | **2.04** | **4.26** | **4.51** | -7.73% | 55.5% |
| **Full** | **28.57%** | **1.91** | **3.31** | **3.21** | **-8.89%** | 60.5% |

9 年里 **8 年 Sharpe ≥ 0.8**,唯一弱年是 2022(熊市全年基本持黄金 +7.8%)。

---

## Strategy architecture

```
                   ┌─────────────────┐
                   │ 34 A-share ETFs │
                   │ (9 groups)      │
                   └────────┬────────┘
                            │
           ┌────────────────┴────────────────┐
           │                                 │
     ┌─────▼─────┐                     ┌─────▼─────┐
     │  LEG A    │                     │  LEG G    │
     │  penalized│                     │  9-group  │
     │  momentum │                     │  rotator  │
     │  top-4    │                     │  top-3    │
     └─────┬─────┘                     └─────┬─────┘
           │                                 │
           │    50/50 blend                  │
           └──────────┬──────────────────────┘
                      │
                ┌─────▼─────┐
                │ w_ensemble│  (≤ 7 ETFs per week)
                └─────┬─────┘
                      │
         ┌────────────▼────────────┐
         │ mkt_cum > 50w MA ?      │
         └────────┬────────────────┘
             yes  │              no
                  │              │
                  │       ┌──────▼──────┐
                  │       │ 100% 黄金ETF │
                  │       │  (159934.SZ)│
                  │       └──────┬──────┘
                  └──────────────┤
                                 │
                      ┌──────────▼──────────┐
                      │ Vol target: 15% ann │
                      │ scale = min(1, 0.15/rvol26w) │
                      └──────────┬──────────┘
                                 │
                      ┌──────────▼──────────┐
                      │ Execute Monday open │
                      │ delay=1, 5bps/side  │
                      └─────────────────────┘
```

---

## Universe

**34 可交易 A-share 主题 ETF**,按 9 组分类:

- **科技成长**(7): 半导体, 消费电子, 软件, 通信, 云计算, AI, 游戏
- **新能源**(4): 光伏, 电池, 新能源车, 电网设备
- **高端制造**(3): 机器人, 航空航天, 军工
- **大金融**(3): 银行, 证券, 非银
- **大消费**(6): 酒, 家电, 食品, 医药, 创新药, 医疗器械
- **周期资源**(7): 有色, 煤炭, 钢铁, 石油, 化工, 稀土, 黄金
- **地产链**(2): 房地产, 建材
- **农业**(1): 畜牧
- **红利**(1): 红利

Staggered join:每 ETF 上市满 12 周才进入横截面。

---

## Signal construction

### Leg A — 惩罚式单 ETF 打分

```
mom_4w[i,t]  = 过去 4 周累计收益
turn_4w[i,t] = 过去 4 周平均换手率 (成交额/市值)
breadth[t]   = z_{52w}(%全市场 above-MA20)

score_A[i,t] = z_cs(mom_4w) - 1.5 × z_cs(turn_4w) + 0.3 × breadth

w_A = 等权 top-4 by score_A  (每只 25%)
```

**直觉**:买 4 周涨得好的 ETF,但扣掉换手爆量的(防 2021 白酒 / 2023 CPO 熄火)。

### Leg G — 9-组主线轮动

```
group_mom_4w[g,t] = 组内等权平均 4 周收益
top-3 组         = argmax(group_mom_4w)[:3]
for g in top-3: 选组内 4w mom 最高 1 只 ETF

w_G = 等权 top-3 leaders (每只 33.3%)
```

**直觉**:先识别当前主线板块,再在主线内挑领头羊。

### Ensemble

```
w_raw[i,t] = 0.5 × w_A[i,t] + 0.5 × w_G[i,t]  # 最多 7 只 ETF
```

### Market gate(避熊市)

```
mkt_cum[t]  = 34 ETF 等权累计曲线
gate_on[t]  = mkt_cum[t] > mean(mkt_cum[t-50w..t])

if gate_on: w_pre_vt = w_raw
else:       w_pre_vt = {159934.SZ: 1.0}  # 100% 黄金 fallback
```

### Vol target

```
rolling_vol_26w[t] = 组合过去 26 周已实现年化波动
scale[t]           = min(1.0, 0.15 / rolling_vol_26w[t])
w_final[t]         = w_pre_vt[t] × scale[t]
```

---

## Quick start

### 1. Environment

```bash
pip install pandas numpy tushare pyarrow
```

Set your tushare token:

```bash
export TUSHARE_TOKEN="your_token_here"
```

### 2. Fetch data

```bash
python scripts/01_fetch_data.py
```

拉取 34 主题 ETF + 黄金 ETF(自动缓存到 `data_cache/`)。

### 3. Build weekly panel

```bash
python scripts/02_build_panel.py
```

### 4. Run full backtest

```bash
python scripts/03_run_strategy.py
```

输出 `results/` 下所有指标 + 权益曲线。

### 5. Generate this week's picks (live)

```bash
python scripts/04_latest_picks.py
```

根据最新一周的数据输出下周一应调至的目标持仓。

---

## Why it works

1. **"动量 + 拥挤惩罚"双轴**(Leg A)— 过热赛道罚分,避开 2021 白酒 / 2023 CPO 式熄火
2. **9-组主线识别**(Leg G)— 单 ETF 层噪声大,板块层稳;group rotator 提供结构性分散
3. **黄金 fallback 是真 anti-cyclic** — 2022 A 股 -22% 时黄金 +9.2%;2024 美联储转向时 +23%
   (红利 / 铜 / 港股 / 纳指 在全球同步熊市里都是 long-beta,只有黄金真避险)

---

## Risks & limitations

1. **2020 COVID DD 无法完全消除**(-8.89%)— MA50 慢 gate 对 4 周急跌反应过慢
2. **黄金 beta 依赖** — OOS 高 Sharpe 有相当部分来自金价 2024-2025 +23% 上涨;长期预期 Sharpe **1.4-1.7**(而非 1.91)
3. **策略是 long-beta 增强,不是 market-neutral** — 牛市表现好,熊市靠三重防御,但不会 short
4. **样本不含 2018 深熊** — 2018 A 股 -25% 下表现未知
5. **快 gate 缺席** — 见 `research/06_fast_gate.md` 的 V7_gb7030_FG4 变体
6. **黄金 ETF 跟踪误差** — 已含在回测里(用 159934.SZ 实际净值)
7. **34 主题 ETF 样本短** — 部分 2021+ 上市

---

## Research journey (10 rounds)

| 轮 | 主题 | 关键发现 |
|---:|---|---|
| 1 | SW L1 宇宙 × 3 族 × 8 specs | B6 (layered mom×低拥挤) 赢,Sh 1.20 |
| 2-3 | 回归 overlay 救 2018 | 无效,结构性熊 |
| 4 | 切到 34 主题 ETF 宇宙 | 策略降级 Sh 0.82 |
| 5 | IS/OOS 严调参 | A_tuned_v1 胜 (Sh 1.40, DD -9.3%) |
| 6 | 滚动 OOS + gate 敏感性 | MA40/50/60 是稳定 plateau |
| 7 | 红利 / ensemble 探索 | 黄金 fallback 跳到 Sh 1.91 |
| 8 | 防御 basket(铜银港美油)| **反直觉**:纯黄金最优 |
| 9 | 国债 fallback | 真 anti-cyclic,gb7030 救 2022 |
| 10 | 快 gate (vol expansion) | V7_gb7030_FG4 小 Pareto 改进 |

详见 `research/` 各章。

---

## Files

```
.
├── README.md                  (本文档)
├── STRATEGY.md                (V7_gold 详细定义)
├── CHANGELOG.md               (10 轮研究历程)
├── LICENSE                    (MIT)
├── scripts/
│   ├── 01_fetch_data.py       (拉取 ETF + 黄金数据)
│   ├── 02_build_panel.py      (构造周频面板)
│   ├── 03_run_strategy.py     (回测 V7_gold)
│   ├── 04_latest_picks.py     (生成实时选股)
│   └── 05_full_stats.py       (详细指标计算)
├── results/
│   ├── metrics.json           (全指标结构化数据)
│   ├── peryear.csv            (分年)
│   ├── drawdowns.csv          (top-5 drawdown 明细)
│   ├── holdings.csv           (时间加权持仓)
│   ├── pnl.csv                (周频 PnL)
│   └── equity_curve.csv
├── research/
│   ├── 01_sw_l1_baseline.md
│   ├── 02_etf_universe_pivot.md
│   ├── 03_isoos_tuning.md
│   ├── 04_rolling_robustness.md
│   ├── 05_fallback_exploration.md
│   └── 06_fast_gate.md
└── data_cache/                (tushare 数据缓存,自动生成)
```

---

## License

MIT © 2026 Derick_Huyukun

## Citation

If you use this in research/trading, please cite:

```
@software{v7_gold_2026,
  title  = {A-Share ETF Rotation Strategy 2.0 — V7_gold},
  author = {Derick Huyukun},
  year   = {2026},
  url    = {https://github.com/huyukun662-crypto/A-Share-ETF-Rotation-Strategy-2.0}
}
```
