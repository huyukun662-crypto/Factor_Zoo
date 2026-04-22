# idio_12_3_momentum_disp_gated_v1

> A 股 量价因子 / 异质动量(Blitz-Huij-Martens 2011)+ 横截面分散度 regime gate(Stivers-Sun 2010 RFS)

## Quick Stats (万5 单边手续费, 2018-01 → 2025-04, 89 次月度再平衡)

| 指标 | 全样本 | Train (18-22) | Validate (23) | Test (24-25YTD) |
|------|------:|-------------:|-------------:|----------------:|
| LS 净 Sharpe | **1.22** | 1.17 | 0.63 | **1.74** |
| LS 净 年化 | 6.41% | 6.06% | 1.69% | 11.27% |
| Q5 多头 净 IR | **0.56** | 0.69 | −1.41 | **1.03** |
| Q5 多头 净 年化超额 | 2.05% | 1.72% | −2.81% | 6.92% |
| LS Max DD | −5.53% | −5.53% | −1.66% | −2.25% |
| ICIR (5d / 20d / 60d) | 0.26 / 0.37 / 0.49 | 0.29 / 0.37 / 0.40 | 0.25 / 0.40 / 0.73 | 0.21 / 0.36 / 0.66 |
| Gate on-fraction | 42.7% | 37.7% | 41.7% | 62.5% |
| 平均 LS 成本 | 3.61 bps/期 | 3.40 bps/期 | 3.41 bps/期 | 4.55 bps/期 |
| n 再平衡期 | 89 | 61 | 12 | 16 |

## Definition

```
# 步骤 1 — 12-3 idio momentum (cs-residualized)
raw_29(s,t)        = cum_252(log_ret_s, t) - cum_63(log_ret_s, t)
alpha_idio_12_3(s,t) = residual of OLS(raw_29(*,t) on [const, log_mv(*,t), σ_120(*,t), ret_20(*,t)])
                       (per trade_date, walk-forward-safe)

# 步骤 2 — 行业中性化 (CITIC L1)
alpha_n(s,t)       = alpha_idio_12_3(s,t) - mean(alpha_idio_12_3 within industry(s) at t)

# 步骤 3 — Dispersion gate (Stivers-Sun 2010 RFS)
mkt_disp(t)        = cross-sectional std of ret_20 across stocks at t
gate(t)            = 1 if mkt_disp(t) > rolling_252d_median(mkt_disp) else 0

# 步骤 4 — Final factor
alpha_final(s,t)   = alpha_n(s,t) × gate(t)

# Sign convention: alpha_final 越高 → 未来收益越高
# Gate = 0 时持现金,边界期支付清算换手成本
```

## Universe & Frequency

- A 股,要求历史 ≥ 252 交易日(确保 cum_252 / σ_120 well-defined)
- ~5,300 只股票 / ~110 个行业(CITIC L1)
- **月度再平衡**(每 20 交易日)
- T+1 执行(delay = 1)
- 5 bps 单边 turnover-aware 成本

## Files

| 文件 | 内容 |
|------|------|
| `factor.md` | 完整规格 / 机制 / 文献 / 审计(7/7 通过) |
| `code.py` | 可复用的因子构建代码(`build_factor()` 主接口) |
| `metrics.json` | 全部头部指标 (含 TVT split + IC + 审计) |
| `annual.csv` | 分年表现(LS + Q5 + gate-on 月数) |
| `rebalances.csv` | 89 次再平衡逐期回报 + 换手 + 成本 + gate 状态 |

## 部署建议

- **首选形态**:LS(long Q5, short Q1,等权)— gate 在 2023 救了 worst-year
- **备选形态**:Q5 多头 — index-enhancement 形态,但 2023 IR -1.41,**长期只做多承担更高 regime 风险**
- **目标**:LS Sharpe 1.0-1.3, Q5 IR 0.5-0.7(test 2024 数字 1.74 / 1.03 偏乐观,prefer train 1.17 数字)
- **kill-switch**:rolling-12m Sharpe < 0,Max DD < −8%,连续 3 季度负收益
- **Gate 监控**:每周检查 mkt_disp vs 252d median,预期 on 比例 40-50%。**整年关 gate 报警**。
- **复盘频率**:月度 P&L 跟踪;季度因子健康审计;年度 spec sensitivity 复测(确保 252d-median 仍是稳健 spec)

## 来源

Session: `logs/20260422_trend_technical_alpha/`
- 6 轮迭代 / 32 raw alpha + 8 regime overlays / 100 placebo trials
- Round 1: 8/8 raw trend signals 反向(证伪经典 momentum)
- Round 2: cs-residualize → 符号翻转
- Round 3-4: 12-2 / 12-3 skip-window 提升 IC IR 至 14.5
- Round 5: dispersion gate 救 worst-year (0.04 → 0.63)
- Round 6: spec sensitivity 5/7 通过 + 100 random gates 全输

## 文献

- Stivers & Sun (2010). "Cross-sectional return dispersions and time variation in value and momentum premiums." *JFQA* 45(4): 987-1014. **← Gate mechanism**
- Liu, Stambaugh & Yuan (2019). "Size and value in China." *JFE* 134(1): 48-69. **← A 股反转主导**
- Jegadeesh & Titman (1993). "Returns to buying winners and selling losers." *JF* 48(1): 65-91. **← 12-1 momentum baseline**
- Blitz, Huij & Martens (2011). "Residual momentum." *JEF* 18(3): 506-521. **← Idio 残差化**
