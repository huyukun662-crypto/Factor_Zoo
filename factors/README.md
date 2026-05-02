# Factor Library

入库标准:经过 4 轮以上 worldquant-5-agent-workflow 流程,通过全部强制审计
(Rule of 8、look-ahead、worst-year floor、best-year-out、pub-lag、residualization),
且 Q5 多头 IR (净) ≥ 1.0 或 LS Sharpe (净) ≥ 1.2(全样本)。

## Catalog

| 类别 | 因子 | LS Sharpe (净万5) | Q5 IR (净万5) | Max DD | 状态 |
|------|------|------------------:|--------------:|-------:|:----:|
| `fundamental.quality` | [`accruals_median_ttm_ind_neutral_v2`](fundamental/accruals_median_ttm_ind_neutral_v2/) | **1.34** | **1.13** | −1.85% | DEPLOYED |
| `fundamental.surprise` | accruals SUE/PEAD | TBA | TBA | TBA | planned |
| `fundamental.profitability` | gross_profitability | TBA | TBA | TBA | planned |
| `price_volume.momentum` | [`idio_12_3_momentum_disp_gated_v1`](price_volume/idio_12_3_momentum_disp_gated_v1/) | 1.22 (18-25YTD) / **1.13 (18-26)** | 0.56 | −5.53% / −6.21% (ext) | DEPLOYED ⚠️ (2025 kill-switch triggered, see extended_stress_test) |
| `price_volume.volatility` | [`lottery_idio_max_q5_overlay_v1`](price_volume/lottery_idio_max_q5_overlay_v1/) | n/a (long-only) | **1.13** (excess) | −4.18% (excess) | DEPLOYED |
| `price_volume.decomposition` | [`overnight_intraday_spread_20d_v1`](price_volume/overnight_intraday_spread_20d_v1/) | **2.44** | **1.04** (excess) | −4.90% / −5.08% (excess) | ADMITTED 2026-04-28 (4 轮 R1-R4) |
| `price_volume.volatility` (ETF) | [`inv_ivol_ls_voltarget_etf_v1`](price_volume/inv_ivol_ls_voltarget_etf_v1/) | 0.81 (standalone) / **2.30** (V25 50/50 ensemble) | n/a (LS) | −8.7% (standalone) | RESEARCH-ONLY standalone, **PROMOTE candidate** as 0.5/0.5 weekly overlay with V25 / V7_gold (superseded by v2) |
| `price_volume.volatility` (ETF) | [`inv_ivol_voltarget_bondrotate_etf_v2`](price_volume/inv_ivol_voltarget_bondrotate_etf_v2/) | **1.02** (standalone, 61 ETF + bond rotation) | n/a (LS) | −8.3% | **ADMITTED-CANDIDATE** — passes ≥1.0 net Sharpe + 7/7 years positive + Test 1.13 + look-ahead/exec-delay; only worst-year floor 0.5 missed (2022 net=+0.23) |
| `price_volume.anchoring` (ETF) | [`anchor_range_pos_etf_v1`](price_volume/anchor_range_pos_etf_v1/) | n/a (long-only) | **1.22** (excess, v1.1) | −14.8% (excess) | **ADMITTED-CANDIDATE** — 5 轮 R1-R5 完成；v1.1 升级到 Tushare qfq 33-ETF universe (修复 Yahoo 截断 4 ETF + 增 515290 银行)；多窗口 range-position + 21-phase ensemble + 10% vol-target；**7/7 年正**；2022 +1.32 / +34.8% (与 inv_ivol v2 互补)；worst-year **+0.198** (2024 cum +2.1%, 转正)；strict worst-year-Sharpe 0.5 floor 未达 |

(动量因子 2018-2025YTD 数字保留作历史参照;扩展至 2026-04 的数字见各因子
factor.md。均使用 A 股 5 bps 单边手续费 turnover-aware 成本。lottery
因子为长多 index-enhancement,指标是 Q5 相对 universe 等权 benchmark 的
超额 IR,非 Q5 绝对 Sharpe。inverted-IVOL v1 为 30 ETF 横截面 LS;v2 升级
扩到 61 ETF + 12 周回撤触发的国债 ETF rotation,Sharpe 净 1.02 通过
≥1.0 LS 门槛,worst-year 从 0.11 改善至 0.23,仅差 0.27 即可 ADMITTED。
**anchor_range_pos_etf_v1** 为长多 top-3 index-enhancement,**v1.1** Sharpe 净
**1.22** 通过 ≥1.0 门槛;**7/7 年正**,2022 +1.32 / +34.8% 是 catalog 内
2022 表现最强的因子;v1.0 的 6/7 (2024 −1.4%) 在 v1.1 转正为 +2.1% cum
excess。R2 阶段发现的关键审计是 **rebal-phase rotation sensitivity** ——
单相位回测会被 21 个相位中最幸运的那个 cherry-pick,该因子构造上用
21-phase ensemble 解决,建议作为 G6 验证 gate 加入 skill package。R5
(v1.1) 的关键发现是 **Yahoo Finance 静默截断 A 股 ETF 历史**——512100
中证1000 / 515050 通信 ETF 在 Yahoo 只有 137 个 K,Tushare 校验后恢复
完整历史使 Sharpe 从 1.01 → 1.22。)

## Directory layout

每个因子目录包含:
```
factors/<family>/<name>/
├── README.md         # quick reference
├── factor.md         # full spec (定义/机制/文献/审计)
├── code.py           # 可复用构建代码
├── metrics.json      # headline metrics + TVT split + audits
├── annual.csv        # 分年表现
└── rebalances.csv    # 逐期再平衡回报
```

## Workflow source

所有因子来自 [`worldquant-5-agent-workflow/`](../worldquant-5-agent-workflow/) 流水线。
研究 session 完整 artifacts 在 [`logs/`](../logs/) 目录。
