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
| `price_volume.momentum` | [`idio_12_3_momentum_disp_gated_v1`](price_volume/idio_12_3_momentum_disp_gated_v1/) | **1.22** | **0.56** | −5.53% | DEPLOYED |
| `price_volume.volatility` | — | — | — | — | none yet (lottery RESEARCH-ONLY, see logs/20260421) |

(数字基于 A 股 2018-2025 全样本,5 bps 单边手续费,turnover-aware 成本模型)

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
