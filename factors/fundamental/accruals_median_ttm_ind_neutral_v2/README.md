# accruals_median_ttm_ind_neutral_v2

> A-share 基本面因子 / 盈余质量(Sloan 1996),中位数-TTM 行业中性版本。

## Quick Stats (万5 单边手续费, 2018-07 → 2025-04)

| 指标 | 全样本 | Test (2024-25YTD) |
|------|------:|------------------:|
| LS 净 Sharpe | **1.34** | 0.96 |
| LS 净 年化 | 10.37% | 4.58% |
| Q5 多头 净 IR | **1.13** | 0.88 |
| Q5 多头 净 年化超额 | 4.42% | 2.42% |
| Max DD | −1.85% | −1.85% |
| ICIR (20d / 60d) | 0.44 / 0.94 | — |
| 平均换手 (Q5 单边) | 9.7% | 5.7% |
| 平均成本 (LS 单期) | 0.95 bps | — |

## Definition

```
acc_med = (median(NI_quarterly, 4q) - median(CFO_quarterly, 4q)) * 4
        / ts_mean(total_assets, 4q)

alpha   = -group_rank( winsorize(acc_med, 0.01, 0.99), industry )

# Sign convention: higher alpha = higher expected forward return
# (lower accruals = higher earnings quality = positive future return)
```

## Universe & Frequency

- A-share, 排除金融(银行/保险/券商/多元金融/地产)与 ST,上市 > 252 交易日
- ~5,300 只股票 / 110 个行业
- 月度再平衡(每 20 交易日)
- T+1 执行(delay = 1)

## Files

| 文件 | 内容 |
|------|------|
| `factor.md` | 完整规格 / 机制 / 文献 / 审计 |
| `code.py` | 可复用的因子构建代码 |
| `metrics.json` | 全部头部指标(含 TVT split + 审计结果) |
| `annual.csv` | 分年表现 |
| `rebalances.csv` | 82 次再平衡逐期回报 |

## 部署建议

- **形态**:Q5 行业内做多(top 20%),CSI300 基准
- **目标**:LS Sharpe ~1.2, Q5 IR ~1.0(扣除选择偏差)
- **kill-switch**:rolling-12m Sharpe < 0.3 或 Max DD < −5%
- **复盘频率**:月度 P&L 跟踪;季度因子健康审计

## 来源

Session: `logs/20260420_fundamental_accruals_alpha/` (4 轮 / 32 表达式 / 全部审计通过)

## 文献

Sloan, R. G. (1996). "Do stock prices fully reflect information in accruals and cash flows about future earnings?" *The Accounting Review*, 71(3), 289-315.
