"""Generate IS-period equity-curve PNG and per-year bar chart from the
saved Round 6 artifacts. Chinese fonts auto-detected.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "report" / "outputs"


def _setup_chinese_font() -> str:
    """Try common CJK fonts and set rcParams. Returns the chosen family."""
    candidates = ["WenQuanYi Zen Hei", "Noto Sans CJK SC", "SimHei",
                  "Microsoft YaHei", "Arial Unicode MS", "DejaVu Sans"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    chosen = next((c for c in candidates if c in available), "DejaVu Sans")
    plt.rcParams["font.sans-serif"] = [chosen]
    plt.rcParams["axes.unicode_minus"] = False
    return chosen


def main():
    font = _setup_chinese_font()
    print(f"Using font: {font}")

    eq = pd.read_csv(OUT_DIR / "round6_equity.csv", index_col=0, parse_dates=True)["equity"]
    py = pd.read_csv(OUT_DIR / "round6_per_year.csv")

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), gridspec_kw={"height_ratios": [2, 1]})

    ax = axes[0]
    ax.plot(eq.index, eq.values, lw=1.5, label="R6 strategy (net)")
    ax.set_title("IS 2013-2019 — Round 6 净值曲线 (RSRS + 加阶矩双动量)")
    ax.set_ylabel("equity (start=1)")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left")

    ax = axes[1]
    colors = ["#d62728" if s < 0 else "#2ca02c" for s in py["sharpe"]]
    ax.bar(py["year"].astype(int).astype(str), py["sharpe"], color=colors)
    ax.axhline(0, color="black", lw=0.8)
    ax.axhline(0.5, color="gray", ls="--", lw=0.6, label="audit floor 0.5")
    ax.set_title("逐年 Sharpe (注意 2014-2015 牛市贡献过高)")
    ax.set_ylabel("Sharpe")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.3, axis="y")

    fig.tight_layout()
    out_fp = OUT_DIR / "is_equity_and_yearly.png"
    fig.savefig(out_fp, dpi=140)
    print(f"saved {out_fp}")


if __name__ == "__main__":
    main()
