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

(动量因子 2018-2025YTD 数字保留作历史参照;扩展至 2026-04 的数字见各因子
factor.md。均使用 A 股 5 bps 单边手续费 turnover-aware 成本。lottery
因子为长多 index-enhancement,指标是 Q5 相对 universe 等权 benchmark 的
超额 IR,非 Q5 绝对 Sharpe。)

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
