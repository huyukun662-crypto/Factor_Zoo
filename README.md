# Factor_Zoo

因子挖掘工作区 —— 存放因子计算代码、回测工作流与挖掘结果产出。

## 当前内容

本仓库当前同步了 [`A-Share-ETF-Rotation-Strategy`](https://github.com/huyukun662-crypto/A-Share-ETF-Rotation-Strategy) 工作流，
用于 A 股 ETF 板块轮动因子的信号计算、参数搜索与回测。云端运行时可直接调用
`src/` 下的 pipeline 入口。

## 目录结构

| 目录 | 说明 |
| --- | --- |
| `src/` | 核心代码：数据加载、因子/指标、信号面板、参数搜索、回测、pipeline 入口 |
| `factor/` | 因子定义与说明 |
| `strategy/` | 策略 Notebook 与说明 |
| `backtest/` | 回测相关脚本/说明 |
| `results/` | 参数搜索、评分结果与交易清单 (CSV) |
| `figures/` | 回测图表产出 |
| `report/` | 研究报告 |
| `summary/` | 汇总说明 |
| `requirements.txt` | Python 运行依赖 |

## 快速开始

```bash
pip install -r requirements.txt
python -m src.pipeline
```

## 上游来源

工作流原始仓库: https://github.com/huyukun662-crypto/A-Share-ETF-Rotation-Strategy
