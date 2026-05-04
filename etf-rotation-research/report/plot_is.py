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

    # Prefer v5 winner, else v4, else R6
    v5_eq = OUT_DIR / "v5_winner_equity.csv"
    v5_py = OUT_DIR / "v5_winner_per_year.csv"
    v4_eq = OUT_DIR / "v4_winner_equity.csv"
    v4_py = OUT_DIR / "v4_winner_per_year.csv"
    if v5_eq.exists() and v5_py.exists():
        eq = pd.read_csv(v5_eq, index_col=0, parse_dates=True)["equity"]
        py = pd.read_csv(v5_py)
        title_suffix = "Round 30 (regime × CPI defensive routing)"
        out_name = "is_equity_and_yearly_v5.png"
    elif v4_eq.exists() and v4_py.exists():
        eq = pd.read_csv(v4_eq, index_col=0, parse_dates=True)["equity"]
        py = pd.read_csv(v4_py)
        title_suffix = "Round 23 (regime-gated)"
        out_name = "is_equity_and_yearly_v4.png"
    else:
        eq = pd.read_csv(OUT_DIR / "round6_equity.csv", index_col=0, parse_dates=True)["equity"]
        py = pd.read_csv(OUT_DIR / "round6_per_year.csv")
        title_suffix = "Round 6 (RSRS + 加阶矩双动量)"
        out_name = "is_equity_and_yearly.png"

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), gridspec_kw={"height_ratios": [2, 1]})

    ax = axes[0]
    ax.plot(eq.index, eq.values, lw=1.5, label="strategy (net)")
    ax.set_title(f"IS 2013-2023 净值曲线 — {title_suffix}")
    ax.set_ylabel("equity (start=1)")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left")

    ax = axes[1]
    colors = ["#d62728" if s < 0 else "#2ca02c" for s in py["sharpe"]]
    ax.bar(py["year"].astype(int).astype(str), py["sharpe"], color=colors)
    ax.axhline(0, color="black", lw=0.8)
    ax.axhline(0.5, color="gray", ls="--", lw=0.6, label="audit floor 0.5")
    ax.set_title("逐年 Sharpe")
    ax.set_ylabel("Sharpe")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.3, axis="y")

    fig.tight_layout()
    out_fp = OUT_DIR / out_name
    fig.savefig(out_fp, dpi=140)
    print(f"saved {out_fp}")


if __name__ == "__main__":
    main()
