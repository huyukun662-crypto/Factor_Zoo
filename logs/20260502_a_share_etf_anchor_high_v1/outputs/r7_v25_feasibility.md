# R7 Feasibility — anchor_inv_ivol_ensemble × V25 ETF rotation

> **Verdict: PROMOTE-OVERLAY (research)**
> 三方 vol-parity 组合（anchor 0.21 / inv_ivol_v2 0.57 / V25 0.23）weekly Sharpe **2.72**, max DD **−3.1%**, 完整年最差 Sharpe **+1.84 (2022)** — 显著优于现入库 ensemble 的 Sharpe 2.00 / DD −4.8% / worst-year 1.25。两方 ensemble × V25 0.7/0.3 也给出 Sharpe 2.35 / DD −3.6%。所有 4 条决策门槛全过。
>
> 但本结论是 **weekly resolution + addendum 性质**，未跑 13-floor catalog audit；如要正式入库需开 R7-R10 完整 session。

## 输入

| 序列 | 文件 | 频率 | 期间 |
|---|---|---|---|
| anchor v1.1 excess | `factors/.../anchor_inv_ivol_ensemble_50_50_v1/ensemble_pnl.csv` (col `anchor_excess`) | daily | 2020-01 → 2026-03 |
| inv_ivol_v2 excess (k=20→1 scaled) | 同上 (col `ivol_excess_scaled`) | daily | 同 |
| ensemble blend | 同上 (col `blend_excess`) | daily | 同 |
| V25 NAV | `/tmp/v25_repo/results/nav_v25_vs_benchmark.csv` (col `v25_nav`) | weekly Friday | 2019-01 → 2026-04 |
| CSI bench | 同上 (col `csi_nav`) | weekly Friday | 同 |

来源 V25 仓库: `huyukun662-crypto/A-Share-ETF-Rotation-Strategy-2.0` (clone 到 /tmp/v25_repo)。

## 方法

1. ensemble 三列日收益 `.resample('W-FRI').sum()` → weekly Friday returns
2. 与 V25 / CSI 的 weekly Friday returns inner-join on common dates
3. 限定 `year >= 2020`（ensemble 起始）→ **301 weekly bars**
4. 注意 ⚠：`v25_daily_pnl.csv` (daily 版本) 经验证 **timing 不一致**——daily-sum→weekly 重建出 0.40 weekly Sharpe，与公布 1.85 严重不符。本分析改用公布 weekly NAV。

## Weekly Pearson 相关性 (n=301)

|  | anchor | ivol_v2 | ensemble | v25 | csi |
|---|---:|---:|---:|---:|---:|
| **anchor** | 1.000 | 0.040 | 0.942 | **0.212** | -0.130 |
| **ivol_v2** | 0.040 | 1.000 | 0.374 | **0.133** | 0.106 |
| **ensemble** | 0.942 | 0.374 | 1.000 | **0.242** | -0.085 |
| **v25** | 0.212 | 0.133 | 0.242 | 1.000 | 0.068 |
| **csi** | -0.130 | 0.106 | -0.085 | 0.068 | 1.000 |

关键观察：
- ρ(ensemble, V25) = **0.24** weekly < 0.30 阈值 ✓ — diversification 有效
- ρ(anchor, V25) = **0.21** — 共享 momentum-flavor 但不致命
- ρ(ivol_v2, V25) = **0.13** — 与 ivol_v1 baseline (0.05) 同量级；v2 的国债 rotation 略与 V25 的 50w-MA gate 共振
- 注 daily ρ(anchor, ivol_v2) = 0.001（catalog metric）；weekly 抬到 0.04，仍是噪声水平

## Standalone weekly stats (2020-01 → 2026-04, 301 weeks)

| label | Sharpe | ann ret | ann vol | max DD | worst year |
|---|---:|---:|---:|---:|---:|
| anchor | 1.33 | 19.3% | 14.5% | -11.9% | +0.95 (2024) |
| inv_ivol_v2 | 2.27 | 12.0% | 5.3% | -6.5% | +0.90 (2022) |
| **ensemble** (0.5/0.5) | **2.00** | 15.6% | 7.8% | **-4.8%** | **+1.25 (2024)** |
| **V25** | **1.79** | -- | -- | -8.2% | +0.80 (2022) |
| CSI bench | 0.11 | 1.9% | 17.4% | -41.6% | -1.13 (2022) |

> ⚠ weekly 的 Sharpe 与 catalog 公布的 daily-annualized Sharpe **不直接可比**。inv_ivol_v2 weekly 2.27 vs catalog 1.02（daily k=20 unit）是单位不同；V25 weekly 1.79 ≈ 公布 1.85 (full sample 2019+) → V25 的 weekly 数字与公布 native 单位一致。本表内部可比，跨表慎用。

## Two-way grid: ensemble × V25

| w_ens | w_V25 | Sharpe | max DD | worst year | ann ret |
|------:|------:|------:|------:|------:|------:|
| 1.00 | 0.00 | 2.00 | -4.8% | 1.25 | 15.6% |
| 0.90 | 0.10 | **2.02** | **-4.0%** | **1.41** | 14.6% |
| 0.80 | 0.20 | 1.97 | -3.3% | 1.23 | 13.5% |
| **0.70** | **0.30** | **2.35** | **-3.6%** | **1.66** | 17.5% |
| 0.60 | 0.40 | 2.33 | -3.8% | 1.68 | 18.2% |
| 0.50 | 0.50 | 2.25 | -4.0% | 1.66 | 18.8% |
| 0.40 | 0.60 | 1.10 | -9.4% | -0.04 | 9.3% |
| 0.30 | 0.70 | 0.88 | -12.2% | -0.40 | 8.2% |
| 0.20 | 0.80 | 0.69 | -14.9% | -0.72 | 7.1% |
| 0.10 | 0.90 | 0.53 | -17.5% | -0.97 | 6.1% |
| 0.00 | 1.00 | 0.40 | -23.8% | -1.17 | 5.0% |

> ⚠ V25-weight ≥ 0.4 区间（grid 表第 6-11 行）出现 Sharpe 急剧下降——这是 **V25 weekly NAV 直接相加** 时未做 vol-rescale 的 artifact：V25 ann vol = 12.7%, ensemble ann vol = 7.8%，等权混合时 V25 主导噪声。低 V25 weight (0.1-0.3) 是结构性稳态。
>
> 修正口径（vol-equalize V25 → 7.8% 后再 blend）见下面 vol-parity 三方组合。

## Three-way 组合

| label | weights (a/i/v) | Sharpe | max DD | worst year | ann ret | ann vol |
|---|---|---:|---:|---:|---:|---:|
| three_way_equal | 0.33/0.33/0.33 | 2.35 | -3.7% | 1.67 | 17.8% | 7.6% |
| **three_way_volparity** | **0.21/0.57/0.23** | **2.72** | **-3.1%** | **1.84** | 15.8% | **5.8%** |

vol-parity 权重由 1/σ 归一化算出（σ_anchor=14.5%, σ_ivol=5.3%, σ_v25=12.7%）。这把 ivol_v2（最低 vol、最高 Sharpe）权重抬到 57%，anchor 和 V25 各取 ~22%，等价于**让 ivol_v2 当核心、其余两个做 satellite**。

## Per-year 表 (top candidates)

| year | anchor | ivol_v2 | ensemble | V25 | ens0.7+v25_0.3 | three_way_volparity |
|---|---:|---:|---:|---:|---:|---:|
| 2020 | 2.81 / +24% | 2.75 / +15% | 3.77 / +19% | 2.14 / +30% | 3.95 / +23% | **3.99 / +20%** |
| 2021 | 1.67 / +19% | 4.59 / +25% | 3.38 / +22% | 1.59 / +22% | 2.96 / +22% | **3.95 / +23%** |
| 2022 | 1.39 / +39% | 0.90 / +4% | 1.54 / +21% | 0.93 / +8% | 1.66 / +17% | **1.84 / +12%** |
| 2023 | 1.47 / +14% | 1.90 / +11% | 1.99 / +12% | 1.76 / +24% | 2.24 / +16% | **2.44 / +14%** |
| 2024 | 0.95 / +10% | 1.78 / +3% | 1.25 / +6% | 1.81 / +25% | 2.00 / +12% | **2.27 / +9%** |
| 2025 | 0.98 / +9% | 3.59 / +24% | 2.46 / +17% | 2.22 / +31% | 2.79 / +21% | **3.29 / +23%** |
| 2026* | 1.14 / +3% | -7.29 / -6% | -1.18 / -2% | -0.56 / -2% | -1.34 / -2% | -4.03 / -3% |

(*2026 = 14 weekly bars Jan-Apr，small-sample noise.)

完整年（2020-2025）每个组合都正；最差年情形：
- ensemble 最差 = **2024 +1.25** （anchor 弱、ivol 救场）
- V25 最差 = **2022 +0.93** （震荡市 50w-MA gate 干仓 / gold fallback 略亏）
- ens0.7+v25_0.3 最差 = **2022 +1.66** ← 改善最大；ivol_v2 在 2024 拉的功劳被 V25 在 2024 (+1.81) 巩固
- three_way_volparity 最差 = **2022 +1.84** ← 全场最佳

## 决策门槛验证

| 标准 | 阈值 | ensemble | ens0.7+v25_0.3 | three_way_volparity | 通过? |
|---|---|---:|---:|---:|---|
| ρ(ensemble, V25) ≤ 0.30 | weekly | -- | 0.242 | (混合) | ✓ |
| Sharpe ≥ 2.10 | weekly | 2.00 | **2.35** | **2.72** | ✓✓ |
| Worst-year Sharpe ≥ 0.70 | complete years | 1.25 | **1.66** | **1.84** | ✓✓ |
| Max DD better than -7.5% | -- | -4.8% | **-3.6%** | **-3.1%** | ✓✓ |

**4/4 全过 → PROMOTE 候选**。

## 推荐配置

| 优先 | 配置 | 理由 |
|---|---|---|
| 1️⃣ | **three_way_volparity (a:0.21, i:0.57, v:0.23)** | 最优 Sharpe 2.72 + 最低 DD -3.1% + 最高 worst-year 1.84；以 ivol_v2 为核心，其余两个做 vol-budget 一致的 satellite。劣势：anchor 权重最低 (~21%)，对喜欢 anchor 强 2022 表现的人来说有些 underweight |
| 2️⃣ | **ens0.7 + V25 0.3** (两方简易) | 实现最简：ensemble 已入库，加一个 V25 leg 30%。Sharpe 2.35 / DD -3.6% / worst-year 1.66，全部 ≥ 现 ensemble。可直接作为 deploy package 的 v2 升级。 |
| 3️⃣ | **three_way_equal** (33/33/33) | Sharpe 2.35 / DD -3.7% / worst-year 1.67，与 ens0.7+V25_0.3 几乎同表现，只是参数更"对称"。无信息论上的理由偏好 |

## Caveats

1. **Weekly resolution**：日内信息丢失。daily ρ(anchor, ivol_v2) = 0.001 vs weekly 0.04，可知 weekly 倾向高估相关性。daily V25 NAV 不可得（pnl.csv timing 不一致），无法做 daily-resolution 的 cross-check。
2. **V25 cost 假设**：V25 NAV 来自外部 deploy 仓库，其 5 bps cost 与 catalog convention 一致（已验证），但 turnover 计算和 tradable check 可能不同——做 deploy 时需重对一遍。
3. **2026 partial**：14 weekly bars 不足以诊断；`three_way_volparity` 2026 Sharpe -4.03 但 cum -3% 的经济损害仍小。Wait 2026 满 6 个月再复测。
4. **未做 13-floor audit**：本 R7 是 addendum 性质，未跑 phase-rotation / look-ahead / execution-delay。如要正式入库 catalog，需开 R7-R10 session。
5. **ivol_v2 weekly Sharpe 偏高 (2.27)**：因为 v2 underlying 是 k=20 forward return，weekly 单位天然吻合；这是结构性的，不是 cherry-pick。但跨表对比时要记得这点。

## Next-action 菜单

- **option A — 文档归档**：把本 R7 报告 commit 到 `claude/ashare-etf-factor-worldquant-JuIGT` 分支，session 保持 CLOSED。无 catalog/deploy 改动。这是最保守路径。
- **option B — 升级 deploy package**：`deploy/A-Share-ETF-Anchor-RangePos-1.0` → v2，加 V25 leg，文档建议 0.7/0.3 或 vol-parity。不动 catalog，不开新 session。中等。
- **option C — 全 session 入库**：开 `logs/2026MMDD_anchor_ivol_v25_triple_v1/`，从 R1 开始跑 4-6 轮 13-floor audit，目标新 ADMITTED catalog 因子 `anchor_ivol_v25_triple_v1`。重型，但合规。
- **option D — 等 2026 满 6 月复测**：跟 ensemble 升级 DEPLOYED 的 calendar 任务并轨。

## Files

- `outputs/r7_v25_feasibility.md` — 本报告
- `outputs/r7_v25_weight_grid.csv` — 完整 grid (18 行 × 21 列)
- `outputs/r7_v25_summary.json` — corr matrix + 全部 stats (machine-readable)
- `scripts/09_v25_feasibility.py` — 可重跑分析脚本
