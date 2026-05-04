"""WFA diagnostics plot: equity curve + per-window train/test Sharpe + per-year WF Sharpe."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd

OUT_DIR = Path(__file__).resolve().parents[1] / "report" / "outputs"


def _setup_chinese_font() -> str:
    cands = ["WenQuanYi Zen Hei", "Noto Sans CJK SC", "SimHei",
              "Microsoft YaHei", "Arial Unicode MS", "DejaVu Sans"]
    avail = {f.name for f in font_manager.fontManager.ttflist}
    chosen = next((c for c in cands if c in avail), "DejaVu Sans")
    plt.rcParams["font.sans-serif"] = [chosen]
    plt.rcParams["axes.unicode_minus"] = False
    return chosen


def main():
    font = _setup_chinese_font()

    pnl = pd.read_csv(OUT_DIR / "wfa_concat_pnl.csv", index_col=0, parse_dates=True)["pnl"]
    eq = (1 + pnl).cumprod()
    windows = pd.read_csv(OUT_DIR / "wfa_windows.csv")
    py = pd.read_csv(OUT_DIR / "wfa_per_year.csv")

    fig, axes = plt.subplots(3, 1, figsize=(12, 10),
                              gridspec_kw={"height_ratios": [2, 1.2, 1]})

    # 1. Equity curve
    ax = axes[0]
    ax.plot(eq.index, eq.values, lw=1.5, color="#1f77b4", label="WFA strategy (net)")
    ax.set_title(f"Walk-Forward Analysis 净值曲线 (R37 strategy, 2016-Q1 to 2023-Q1)")
    ax.set_ylabel("equity (start=1)")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left")

    # 2. Per-window train vs test Sharpe
    ax = axes[1]
    x = windows["window"]
    ax.plot(x, windows["train_sharpe"], "o-", lw=1, label="train (756d)", color="#2ca02c")
    ax.plot(x, windows["test_sharpe"], "s-", lw=1, label="test (252d)", color="#d62728")
    ax.axhline(0.5, color="gray", ls="--", lw=0.6, label="0.5 floor")
    ax.axhline(0, color="black", lw=0.6)
    ax.set_title("逐窗口 Train vs Test Sharpe (decay 越小越好)")
    ax.set_xlabel("WFA window index")
    ax.set_ylabel("Sharpe")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.3)

    # 3. Per-year WF Sharpe
    ax = axes[2]
    colors = ["#d62728" if s < 0 else "#2ca02c" for s in py["sharpe"]]
    ax.bar(py["year"].astype(int).astype(str), py["sharpe"], color=colors)
    ax.axhline(0.5, color="gray", ls="--", lw=0.6, label="0.5 floor")
    ax.axhline(0, color="black", lw=0.6)
    ax.set_title("WFA 拼接收益逐年 Sharpe")
    ax.set_ylabel("Sharpe")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.3, axis="y")

    fig.tight_layout()
    out_fp = OUT_DIR / "wfa_diagnostics.png"
    fig.savefig(out_fp, dpi=140)
    print(f"saved {out_fp}")


if __name__ == "__main__":
    main()
