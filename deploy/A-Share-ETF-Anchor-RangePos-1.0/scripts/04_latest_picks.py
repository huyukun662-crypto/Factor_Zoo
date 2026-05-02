"""
04_latest_picks.py — Generate the latest top-3 picks of the
anchor / range-position ETF strategy for the most recent trade date.

For each of the 21 phases, prints the next phase rebal date and its
top-3 holdings, plus the **aggregate active position** (positions
weighted across all phases for the latest available trading day).

Outputs (in ./results/):
  - picks_<latest_date>.csv       per-phase rebal-date and top-3 list
  - latest_aggregate.csv          symbol -> aggregate weight on latest day
  - latest_aggregate.json         summary
"""
from __future__ import annotations
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "data_cache"
OUT = HERE / "results"; OUT.mkdir(parents=True, exist_ok=True)

REBAL = 21
N_TOP = 3


def say(s: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)


def main() -> None:
    sig_path = CACHE / "signal.parquet"
    uni_path = CACHE / "core_universe.json"
    panel_path = CACHE / "etf_daily.parquet"
    for p in (sig_path, uni_path, panel_path):
        if not p.exists():
            raise FileNotFoundError(f"missing {p}; run 01 and 02 first.")

    sig = pd.read_parquet(sig_path).sort_index()
    with open(uni_path) as f:
        meta = json.load(f)
    universe = meta["symbols"]
    sig = sig[universe]

    df = pd.read_parquet(panel_path)
    df = df[df.symbol.isin(universe)].copy()
    df = df.sort_values(["date", "symbol"]).reset_index(drop=True)
    last_date = sig.dropna(how="all").index[-1]
    say(f"Latest signal date: {last_date:%Y-%m-%d}")

    # 21-phase next-rebal schedule
    dates = sig.dropna(how="all").index
    rebal_rows = []
    weights_today = pd.Series(0.0, index=universe)
    for phase in range(REBAL):
        phase_rebals = dates[phase::REBAL]
        last_rebal = phase_rebals[-1]
        next_rebal = (last_rebal + pd.Timedelta(days=21)).strftime("%Y-%m-%d")
        snap = sig.loc[last_rebal].dropna()
        if len(snap) < N_TOP:
            continue
        top = snap.nlargest(N_TOP).index.tolist()
        avg_score = float(snap.loc[top].mean())
        rebal_rows.append({
            "phase": phase,
            "last_rebal_date": last_rebal.strftime("%Y-%m-%d"),
            "next_rebal_date": next_rebal,
            "top_n_etfs": ";".join(top),
            "top_n_signal_avg": avg_score,
        })
        # contribute to today's aggregate weight
        for s in top:
            weights_today[s] += 1.0 / N_TOP / REBAL

    picks_df = pd.DataFrame(rebal_rows)
    out_picks = OUT / f"picks_{last_date:%Y-%m-%d}.csv"
    picks_df.to_csv(out_picks, index=False)
    say(f"Wrote {out_picks}")

    # aggregate
    agg = weights_today[weights_today > 0].sort_values(ascending=False)
    agg_df = pd.DataFrame({"symbol": agg.index, "weight": agg.values})
    agg_df.to_csv(OUT / "latest_aggregate.csv", index=False)

    summary = {
        "latest_signal_date": last_date.strftime("%Y-%m-%d"),
        "n_phases": REBAL,
        "n_active_symbols_today": int((weights_today > 0).sum()),
        "total_active_weight": float(agg.sum()),
        "top_5_aggregate_weights": agg.head(5).round(4).to_dict(),
    }
    with open(OUT / "latest_aggregate.json", "w") as f:
        json.dump(summary, f, indent=2)

    print()
    say("=== Latest aggregate top-N positions (sum across phases) ===")
    for sym, w in agg.head(10).items():
        last_close = df[(df.symbol == sym) & (df.date <= last_date)].iloc[-1]["close"]
        sig_today = sig.loc[last_date, sym]
        print(f"  {sym:<12} weight={w*100:5.2f}%  signal={sig_today:.3f}  close={last_close:.2f}")

    print()
    say("=== Phase-by-phase next-rebal schedule (top-3 each) ===")
    for r in rebal_rows[:6]:
        print(f"  phase {r['phase']:>2}  next={r['next_rebal_date']}  top-3={r['top_n_etfs']}  avg_score={r['top_n_signal_avg']:.3f}")
    print(f"  ... ({len(rebal_rows)} phases total)")


if __name__ == "__main__":
    main()
