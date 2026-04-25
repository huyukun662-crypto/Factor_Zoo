"""Generate the three diagnostic figures for the session winner / lead."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..backtest.audits import G4_PEAK_HORIZONS, ic_at_horizon
from ..backtest.engine import per_year_breakdown, run_backtest
from ..backtest.tvt import slice_split
from ..data.panel import load_panel
from ..factors import registry  # noqa
from ..factors.base import FACTORS

SESSION_DIR = Path("logs/20260425_a_share_style_timing_csi300_csi1000")
FIG_DIR = SESSION_DIR / "outputs" / "figures"


def fig_cumulative_pnl(name: str, deadband: float = 0.5):
    panel = load_panel()
    f = FACTORS[name]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for split, color in [("train", "#1f77b4"), ("val", "#ff7f0e"), ("test", "#2ca02c")]:
        bt = run_backtest(f, slice_split(panel, split), deadband=deadband)
        eq = (1.0 + bt.daily_pnl.fillna(0.0)).cumprod()
        ax.plot(eq.index, eq.values, label=f"{split} (Sh={bt.metrics['sharpe']:+.2f})", color=color)
    ax.set_title(f"{name} — cumulative net equity (5 bps/side, deadband={deadband})")
    ax.set_ylabel("equity (start = 1.0)")
    ax.axhline(1.0, color="grey", lw=0.5, linestyle="--")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{name}_cumpnl.png", dpi=110)
    plt.close(fig)


def fig_per_year_sharpe(name: str, deadband: float = 0.5):
    panel = load_panel()
    f = FACTORS[name]
    rows = []
    for split in ["train", "val", "test"]:
        bt = run_backtest(f, slice_split(panel, split), deadband=deadband)
        py = per_year_breakdown(bt.daily_pnl, bt.traded_position)
        py["split"] = split
        rows.append(py)
    py = pd.concat(rows, ignore_index=True)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    colors = {"train": "#1f77b4", "val": "#ff7f0e", "test": "#2ca02c"}
    for split, grp in py.groupby("split"):
        ax.bar(grp["year"].astype(str) + f" ({split[:1]})", grp["sharpe"], color=colors[split], label=split)
    ax.axhline(0.5, color="red", linestyle="--", linewidth=0.8, label="PROMOTE worst-year floor")
    ax.axhline(0.0, color="grey", linewidth=0.5)
    ax.set_title(f"{name} — per-year Sharpe across TVT splits")
    ax.set_ylabel("Sharpe")
    ax.legend(fontsize=8)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{name}_per_year_sharpe.png", dpi=110)
    plt.close(fig)


def fig_ic_decay(name: str):
    panel = load_panel()
    panel_train = slice_split(panel, "train")
    f = FACTORS[name]
    score = f.generate(panel_train)
    horizons = list(range(1, 31))
    rows = [ic_at_horizon(score, panel_train, h) for h in horizons]
    df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(df["horizon"], df["ic"], marker="o", color="#1f77b4")
    ax.axhline(0.0, color="grey", linewidth=0.5)
    ax.set_xlabel("forward horizon (trading days)")
    ax.set_ylabel("IC (Pearson)")
    ax.set_title(f"{name} — IC decay on TRAIN")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{name}_ic_decay.png", dpi=110)
    plt.close(fig)


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    # E1 = only G4 survivor, E4 = best per-year stability
    for name in ["r1_e1_volspread_20d", "r1_e4_volspread_10d"]:
        print(f"[fig] {name} ...")
        fig_cumulative_pnl(name)
        fig_per_year_sharpe(name)
        fig_ic_decay(name)
    print(f"[fig] wrote figures to {FIG_DIR}")


if __name__ == "__main__":
    main()
