# α_17 长多 index-enhancement 部署评审

**Session:** `20260422_trend_technical_alpha` (follow-on)
**Script:** `scripts/16_alpha17_longonly_review.py`
**Date:** 2026-04-22
**Sample:** 2018-01-02 → 2026-04-03 (101 monthly rebalances, 5 bps/side turnover-aware cost)

## 背景

2025 regime-break diagnosis 显示 α_17 (σ-bucket rank of idio-MAX,来自
lottery session) 的 Q5 长多超额 IR 1.29(全样本)/ 1.56(2025 OOS)。
相比之下,α_35 (DEPLOYED) LS 在 2025 崩溃,但 Q5 长多在 2025 照跑赢市场
+0.72%。结合 attribution 看:**2025 的 LS 崩是空头端(Q1 = past losers
reversal)导致,Q5 本身还是抓到赢家**。

本评审系统地检验:**α_17 Q5 长多能否入库作为 index-enhancement 因子?**

## 基线结果

配置:industry-demeaned α_17 取 top 20%(等权),每 20 交易日再平衡,
5 bps/side turnover-aware cost。

| 指标 | 绝对 | **超额 vs universe** |
|---|---:|---:|
| 年化净 | +12.53% | **+3.98%** |
| Sharpe / **IR** | 0.50 | **1.09** |
| Max DD | −34.52%(市场 beta) | **−4.18%** |

### TVT 分段(超额 IR)

| 段 | n | excess IR | excess ann |
|---|---:|---:|---:|
| Train 2018–22 | 61 | 1.375 | +5.44% |
| Validate 2023 | 12 | 0.766 | +2.96% |
| **Test 2024–26YTD** | 28 | **0.804** | **+3.09%** |
| Full | 101 | 1.087 | +3.98% |

### 分年超额 IR

| 年 | excess IR |
|---:|---:|
| 2018 | **+2.41** |
| 2019 | +1.41 |
| **2020** | **−0.33** ⚠️ |
| 2021 | +2.17 |
| 2022 | +2.78 |
| 2023 | +0.77 |
| 2024 | +0.84 |
| **2025** | **+1.43** |
| 2026 YTD | (3 rebal, 不足统计) |

单一失败年:**2020**(A 股 megacap rally,lottery premium 被消灭)。其余 7
个完整年份全部正超额。

### 其它

- 平均换手:74.7% / 再平衡(比动量因子略高,lottery 信号切换更频繁)
- 平均 LS 成本:3.74 bps/期
- 2025 OOS 表现:超额 +1.43 IR,完全没受 2025 市场暴涨影响

## 全面审计

按 CLAUDE.md / SKILL.md 强制审计清单执行。

| 规则 | 阈值 | 基线值 | 判定 |
|---|---|---:|:---:|
| 1. Full-sample excess IR ≥ 1.0 | 1.0 | 1.087 | ✅ PASS |
| **2. Worst-year excess IR ≥ 0.5** | **0.5** | **−0.33** | **❌ FAIL** |
| 3. Best-year-out ≥ 50% × full | 50% | 90.3% (drop 2022) | ✅ PASS |
| **4. Spec sensitivity majority pass** | ≥ 5/9 | **0/9 pass** | **❌ FAIL** |
| 5. Placebo excess IR p < 0.05 | 0.05 | 0.000 | ✅ PASS |
| 6. Placebo worst-year p < 0.05 | 0.05 | 0.000 | ✅ PASS |
| 7. Excess MaxDD > −10% | −10% | −4.18% | ✅ PASS |

**5/7 通过,2 条硬门槛卡死**。两个 FAIL 的根因都指向 2020。

## Spec sensitivity(0/9 通过)

| variant | abs ann | exc IR | worst_yr | test IR | MaxDD | PASS |
|---|---:|---:|---:|---:|---:|:---:|
| BASELINE (top 20%, 20d) | 12.53% | **1.09** | −0.33 | 0.80 | −4.18% | ❌ |
| top_10pct | 12.05% | 0.63 | −0.61 | 0.59 | −6.91% | ❌ |
| top_30pct | 13.39% | 1.37 | −0.32 | 0.78 | −3.77% | ❌ |
| top_50_stocks | 9.84% | 0.12 | −0.97 | −0.19 | −14.26% | ❌ |
| top_100_stocks | 9.09% | 0.02 | −1.46 | −0.09 | −12.06% | ❌ |
| rebal_10d | 30.03% | 1.68 | −3.53 | 1.53 | −6.91% | ❌ |
| rebal_40d | 10.79% | 1.06 | **+0.26** | 0.88 | −2.41% | ❌(close) |
| no_industry_demean | 13.16% | 1.11 | −0.33 | 0.82 | −4.18% | ❌ |
| winsorized+ind | 13.15% | 1.11 | −0.27 | 0.82 | −4.13% | ❌ |

所有变体在 **headline IR 上健康**(多数 ≥ 1.0),但 **worst_year 全军覆没**
(除了 rebal_40d 的 +0.26,但仍 < 0.5)。**2020 不是 spec 问题,是结构问题**。

## Placebo(强力证据)

100 次随机 top-20% 组合,匹配换手与样本量:

| 指标 | 基线 | 随机中位数 | 随机 p95 | 随机 max | p-value |
|---|---:|---:|---:|---:|---:|
| Excess IR | **1.087** | −0.445 | 0.145 | 0.340 | **0.000** |
| Worst-year excess | −0.325 | −2.052 | −1.001 | −0.395 | **0.000** |

结论:**α_17 信号对随机组合的统计优势极强**。100 个随机 Q5 portfolio 没
有一个达到基线的 IR 或 worst-year。信号的 alpha 含量不是偶然。

## 整体诊断

### 好的部分(入库门槛的理由)

1. **Full-sample IR 1.09,超过 catalog 1.0 门槛**
2. **TVT 三段都 > 0.7**(Train 1.37 / Validate 0.77 / Test 0.80)—— 稳定跨段
3. **Placebo 两项都 p=0.000** —— 真实信号,与随机严格区分
4. **2025 OOS IR 1.43** —— 超越全样本均值,在 α_35 崩溃的同一年大放异彩
5. **MaxDD 超额 −4.2%** —— 远优于 −10% 门槛
6. **Best-year-out 90%** —— 不依赖单一好年

### 坏的部分(阻碍入库)

1. **2020 单年 IR −0.325**,超 A 股 megacap rally 年份
   - Mechanism:lottery stocks = 小盘高波动股,2020 沪深 300 单边涨,小盘跑输
   - 这是 **结构问题**:lottery premium 与大盘股 rally regime 内生冲突
   - **所有 9 个 spec 变体都在 2020 失败**——不是参数问题

### 处置选项

三条路,各有代价:

#### A) RESEARCH-ONLY(严格守规则)

- 按 SKILL.md 规定:"任何强制审计失败 → RESEARCH-ONLY,never PROMOTE"
- Worst-year 0.5 是硬门槛,规则先于数据
- 优点:守纪律,不把 2020 风险暴露给产品
- 缺点:放弃了一个 full-sample IR 1.09 / OOS 1.43 的优质信号

#### B) 带明确 tail-risk 声明 的 CONDITIONAL DEPLOY

- 入库,但 factor.md 明确标注:"2020 worst-year IR −0.33,A 股 megacap
  rally regime 下已知失效;需搭配 megacap-rally regime monitor 使用,
  或接受这一单年度尾部"
- 类似 α_35 的 2023 worst-year 问题,只是 2020 更严重
- 优点:把 1.09 IR 的信号用起来
- 缺点:开审计先例——"硬规则可以绕过",会腐蚀整个入库机制

#### C) 做 2020-specific 的 regime overlay 再试一次 ✦ 推荐

- 关掉 lottery leg 的开关:当"市场集中度"(megacap 相对强度)极端时
  不部署 α_17
- 候选 proxies:
  - 沪深 300 vs 中证 1000 的 60 日累计收益差(megacap 相对优势)
  - 市场集中度(top-100 市值占比 vs 历史)
  - Size factor rolling-12m Sharpe(风格反转触发器)
- 先在本 session 做一个"2020-only check"看是否能把 worst-year 抬到 0.5+
- 若通过,再做全流程 5-agent session 正规入库

优点:目标明确(救 2020),工作量小(单一 regime overlay 设计 + 证伪)
缺点:1-2 个 session 的研究工作量

**推荐 C**。是唯一既不破坏入库机制、又能留住信号的方案。α_35 就是走这条
路(dispersion gate 救 2023)成功入库的。

## 文献参考

- Bali, Cakici & Whitelaw (2011). "Maxing out." *JFE* 99(2) — Lottery 定义
- Liu, Stambaugh & Yuan (2019). "Size and value in China." *JFE* 134(1) —
  A 股 2020 megacap rally 背景
- Stivers & Sun (2010). JFQA 45(4) — dispersion gate(对 lottery 已验证不适用)

## 工件

- `scripts/16_alpha17_longonly_review.py`
- `outputs/alpha17_longonly_review.json`
- `outputs/alpha17_longonly_baseline_tape.csv`
- `outputs/_a17_review_run.log`

## Disposition

**α_17 Q5 长多:RESEARCH-ONLY(pending 2020-regime overlay 研究)**

现在 `factors/` catalog 不更新。若用户选择路径 C,下一步开新 session
`logs/YYYYMMDD_lottery_megacap_overlay/` 做:

1. 候选 regime overlay 的 per-year 验证(重点打 2020 IR)
2. 100 次 placebo overlay 证伪
3. 若 7/7 过,产出 `factors/price_volume/lottery_idio_max_q5_overlay_v1/`
