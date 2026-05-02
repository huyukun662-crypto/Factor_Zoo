#!/usr/bin/env python3
"""Round 3 — production-grade phase-averaged variants.

All 8 variants use 21-phase ensemble (1/21 capital per trading day,
21-day holding). Selection: top-5 long-only excess vs equal-weight
universe (or vs bench for H2).

H1 baseline: multi-window rank average phase-averaged top-5
H2: H1 + bench MA200 risk-on gate
H3: H1 + ETF-level inverse-vol weighting
H4: H2 + H3
H5: H1 on 20-ETF core universe
H6: H1 with n=3 (more concentrated)
H7: H1 with portfolio vol-target 10% ann
H8: H4 + H7 (full risk-managed)
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("/home/user/Factor_Zoo/logs/20260502_a_share_etf_anchor_high_v1")
SHARED = Path("/home/user/Factor_Zoo/logs/_shared_cache")
OUT = ROOT / "outputs"

DROP_FULL = {"512800.SS", "515170.SS"}
BENCH = "510300.SS"
DELAY = 1
COST_BPS = 5.0
PRIMARY_K = 20
REBAL = 21
TARGET_VOL = 0.10
N_TOP = 5

TRAIN_END = pd.Timestamp("2021-12-31")
VAL_END = pd.Timestamp("2022-12-30")


def load_panel():
    df = pd.read_parquet(SHARED / "etf_daily.parquet")
    df = df[~df.symbol.isin(DROP_FULL)].copy()
    df = df.sort_values(["date", "symbol"]).reset_index(drop=True)
    df["ret"] = df.groupby("symbol")["close"].pct_change()
    return df


def to_wide(df, col):
    return df.pivot(index="date", columns="symbol", values=col).sort_index()


def range_pos(close, w):
    pmax = close.rolling(w, min_periods=200 if w >= 252 else int(w * 0.8)).max()
    pmin = close.rolling(w, min_periods=200 if w >= 252 else int(w * 0.8)).min()
    return (close - pmin) / (pmax - pmin).replace(0, np.nan)


def annualize_sharpe(daily, k=1, min_obs=20):
    x = daily.dropna()
    if len(x) < min_obs or x.std() == 0:
        return float("nan")
    return float(x.mean() / x.std() * np.sqrt(252 / k))


def per_year_sharpe(daily, k=1):
    return daily.groupby(daily.index.year).apply(
        lambda x: annualize_sharpe(x, k))


def per_year_excess_pct(daily):
    """Annualized cumulative excess return per year (sum of daily excess)."""
    return daily.groupby(daily.index.year).sum()


def core_universe(close):
    """Return the 20 ETFs with at least 1500 valid days."""
    counts = close.notna().sum()
    keep = counts[counts >= 1500].index.tolist()
    return keep


def _select_topn(sig_at_t, n):
    """Return list of top-n symbols by signal at time t (NaN-safe)."""
    s = sig_at_t.dropna()
    if len(s) < n:
        return []
    return s.nlargest(n).index.tolist()


def phase_ensemble_long_only(
    sig: pd.DataFrame, ret_d: pd.DataFrame,
    n: int = 5, rebal: int = REBAL,
    universe_filter: list | None = None,
    inv_vol_w: int = 0, regime: pd.Series | None = None,
    cost_bps: float = COST_BPS,
):
    """
    21-phase ensemble of an n-name long-only top-N rebalanced every `rebal`
    days. Returns:
      portfolio_daily   — daily portfolio return (gross of cost)
      portfolio_daily_net — same with turnover cost
      bench_daily       — equal-weight portfolio over same universe
    Modifications:
      - inv_vol_w > 0: weights = (1/vol)/sum(1/vol), vol = trailing inv_vol_w
      - regime is a daily 0/1 series; on 0-days we ignore signal and instead
        hold equal-weight bench.
    """
    cols = sig.columns.tolist()
    if universe_filter is not None:
        cols = [c for c in cols if c in universe_filter]
    sig = sig[cols]
    ret_d = ret_d[cols]
    dates = sig.index

    # vol panel for inv-vol weighting
    if inv_vol_w > 0:
        vol = ret_d.rolling(inv_vol_w, min_periods=int(inv_vol_w * 0.8)).std() * np.sqrt(252)
    else:
        vol = None

    bench_daily = ret_d.mean(axis=1)

    # build per-phase position panel: weights[t, symbol]
    weights_total = pd.DataFrame(0.0, index=dates, columns=cols)
    cost_daily = pd.Series(0.0, index=dates)
    n_phases_active = pd.Series(0.0, index=dates)
    bench_holding_total = pd.Series(0.0, index=dates)  # for regime-off allocation

    for phase in range(rebal):
        rebal_dates = dates[phase::rebal]
        prev_w = pd.Series(0.0, index=cols)
        prev_was_bench = False
        # for each rebal day, set weights for the next `rebal` days
        for i, rd in enumerate(rebal_dates):
            # decide whether regime is on
            on = True
            if regime is not None:
                on = bool(regime.loc[rd]) if rd in regime.index else False
            if on:
                top = _select_topn(sig.loc[rd], n)
                if len(top) < n:
                    new_w = prev_w.copy()
                    holds_bench = prev_was_bench
                else:
                    if inv_vol_w > 0:
                        v = vol.loc[rd, top].fillna(vol.loc[rd, top].median())
                        inv = 1.0 / v.replace(0, np.nan)
                        w = inv / inv.sum()
                        new_w = pd.Series(0.0, index=cols)
                        for s, ww in w.items():
                            new_w[s] = ww
                    else:
                        new_w = pd.Series(0.0, index=cols)
                        for s in top:
                            new_w[s] = 1.0 / n
                    holds_bench = False
            else:
                # regime off: hold equal-weight bench
                new_w = pd.Series(1.0 / len(cols), index=cols)
                holds_bench = True

            # turnover cost
            turnover = (new_w - prev_w).abs().sum() / 2.0
            cost_daily.loc[rd] += turnover * (cost_bps / 1e4) / rebal  # spread over rebal days? no, hit on rebal day

            # actually attribute cost on rebal day for that phase only
            # The /rebal would smooth — instead:
            # remove the /rebal so cost lands on the rebal day for this phase,
            # representing 1/rebal of total NAV being traded
            # The factor 1/rebal is already implicit because each phase deploys 1/rebal NAV.
            cost_daily.loc[rd] -= turnover * (cost_bps / 1e4) / rebal  # undo prior add
            cost_daily.loc[rd] += turnover * (cost_bps / 1e4) * (1.0 / rebal)

            # determine the holding period for this rebal cycle
            if i + 1 < len(rebal_dates):
                end_idx = rebal_dates[i + 1]
            else:
                end_idx = dates[-1] + pd.Timedelta(days=1)
            mask = (dates >= rd) & (dates < end_idx)
            # weight contributes 1/rebal to total portfolio (since 1/rebal NAV per phase)
            for s in cols:
                if new_w[s] != 0:
                    weights_total.loc[mask, s] += new_w[s] / rebal
            n_phases_active.loc[mask] += 1.0 / rebal
            prev_w = new_w
            prev_was_bench = holds_bench

    # daily portfolio return
    portfolio_daily = (weights_total * ret_d).sum(axis=1)
    portfolio_daily_net = portfolio_daily - cost_daily
    return portfolio_daily, portfolio_daily_net, bench_daily, weights_total, cost_daily


def vol_target_overlay(daily, target=TARGET_VOL, w=60):
    rv = daily.rolling(w, min_periods=int(w * 0.8)).std() * np.sqrt(252)
    scale = (target / rv).clip(upper=2.0)  # cap leverage at 2x
    scale = scale.shift(1)  # use yesterday's vol estimate (no peeking)
    return daily * scale


def main():
    df = load_panel()
    close = to_wide(df, "close")
    rets = to_wide(df, "ret")

    # bench regime gate
    bench = close[BENCH]
    ma200 = bench.rolling(200, min_periods=180).mean()
    regime_on = (bench > ma200).astype(int)

    rp_60 = range_pos(close, 60)
    rp_120 = range_pos(close, 120)
    rp_252 = range_pos(close, 252)
    multi_rank = (rp_60.rank(axis=1, pct=True)
                  + rp_120.rank(axis=1, pct=True)
                  + rp_252.rank(axis=1, pct=True)) / 3.0

    core = core_universe(close)
    print(f"Core universe size: {len(core)} (full: {close.shape[1]})")

    variants = {}

    # H1 baseline
    pd1, pn1, bench_d, w1, c1 = phase_ensemble_long_only(multi_rank, rets)
    variants["H1"] = {"port": pd1, "port_net": pn1, "bench": bench_d, "weights": w1, "cost": c1}

    # H2: H1 + MA200 gate
    pd2, pn2, _, _, _ = phase_ensemble_long_only(multi_rank, rets, regime=regime_on)
    variants["H2"] = {"port": pd2, "port_net": pn2, "bench": bench_d}

    # H3: H1 + inv-vol
    pd3, pn3, _, _, _ = phase_ensemble_long_only(multi_rank, rets, inv_vol_w=60)
    variants["H3"] = {"port": pd3, "port_net": pn3, "bench": bench_d}

    # H4: H2 + H3
    pd4, pn4, _, _, _ = phase_ensemble_long_only(multi_rank, rets, inv_vol_w=60, regime=regime_on)
    variants["H4"] = {"port": pd4, "port_net": pn4, "bench": bench_d}

    # H5: H1 on core universe
    bench_core = rets[core].mean(axis=1)
    pd5, pn5, _, _, _ = phase_ensemble_long_only(multi_rank, rets, universe_filter=core)
    variants["H5"] = {"port": pd5, "port_net": pn5, "bench": bench_core}

    # H6: top-3
    pd6, pn6, _, _, _ = phase_ensemble_long_only(multi_rank, rets, n=3)
    variants["H6"] = {"port": pd6, "port_net": pn6, "bench": bench_d}

    # H7: H1 + vol target
    pd7_pre, pn7_pre, _, _, _ = phase_ensemble_long_only(multi_rank, rets)
    excess7 = pn7_pre - bench_d
    pd7 = vol_target_overlay(excess7) + bench_d  # apply vol target to excess only
    pn7 = pd7  # net already includes cost
    variants["H7"] = {"port": pd7, "port_net": pn7, "bench": bench_d, "excess_voltarget": True}

    # H8: H4 + vol target on excess
    excess8 = pn4 - bench_d
    pd8 = vol_target_overlay(excess8) + bench_d
    variants["H8"] = {"port": pd8, "port_net": pd8, "bench": bench_d}

    # ---------- Evaluate ----------
    rows = []
    py_rows = []
    py_excess_rows = []
    for vid, v in variants.items():
        port = v["port_net"]
        bench_local = v["bench"]
        excess = port - bench_local
        excess = excess.dropna()
        valid = excess.index[excess.index.year >= 2020]  # skip warmup year 2019
        excess = excess.loc[valid]
        port_v = port.reindex(valid)

        sharpe_excess = annualize_sharpe(excess, 1)
        sharpe_port = annualize_sharpe(port_v, 1)

        py_excess = per_year_sharpe(excess, 1)
        py_port = per_year_sharpe(port_v, 1)
        py_excess_pct = per_year_excess_pct(excess)
        py_bench_pct = per_year_excess_pct(bench_local.reindex(valid))
        py_port_pct = per_year_excess_pct(port_v)

        train_mask = excess.index <= TRAIN_END
        val_mask = (excess.index > TRAIN_END) & (excess.index <= VAL_END)
        test_mask = excess.index > VAL_END
        sharpe_train = annualize_sharpe(excess[train_mask], 1)
        sharpe_val = annualize_sharpe(excess[val_mask], 1)
        sharpe_test = annualize_sharpe(excess[test_mask], 1)

        worst_year_sharpe = float(py_excess.min())
        n_pos_years = int((py_excess > 0).sum())
        n_total_years = int(py_excess.notna().sum())

        rows.append({
            "id": vid,
            "sharpe_excess_net": sharpe_excess,
            "sharpe_port_net": sharpe_port,
            "sharpe_train_excess": sharpe_train,
            "sharpe_val_excess": sharpe_val,
            "sharpe_test_excess": sharpe_test,
            "worst_year_sharpe_excess": worst_year_sharpe,
            "n_pos_years": n_pos_years,
            "n_total_years": n_total_years,
            "frac_pos_years": n_pos_years / max(n_total_years, 1),
        })
        for yr, sh in py_excess.items():
            py_rows.append({"id": vid, "year": int(yr), "sharpe": sh})
        for yr, ex in py_excess_pct.items():
            py_excess_rows.append({
                "id": vid, "year": int(yr),
                "excess_return_ann": float(ex),
                "port_return_ann": float(py_port_pct.get(yr, np.nan)),
                "bench_return_ann": float(py_bench_pct.get(yr, np.nan)),
            })

    pd.DataFrame(rows).to_csv(OUT / "r3_summary_batch_0003.csv", index=False)
    pd.DataFrame(py_rows).to_csv(OUT / "r3_per_year_sharpe_batch_0003.csv", index=False)
    pd.DataFrame(py_excess_rows).to_csv(OUT / "r3_per_year_excess_batch_0003.csv", index=False)

    # PROMOTE floor evaluation
    floors = {}
    for r in rows:
        vid = r["id"]
        floors[vid] = {
            "sharpe_excess_net": r["sharpe_excess_net"],
            "promote_sharpe_geq_1.0": r["sharpe_excess_net"] >= 1.0,
            "candidate_sharpe_geq_0.5": r["sharpe_excess_net"] >= 0.5,
            "worst_year_geq_0": r["worst_year_sharpe_excess"] >= 0,
            "worst_year_geq_0.5": r["worst_year_sharpe_excess"] >= 0.5,
            "test_geq_50pct_full": (
                r["sharpe_test_excess"] >= 0.5 * r["sharpe_excess_net"]
                if r["sharpe_excess_net"] > 0 else False
            ),
            "frac_pos_years_geq_70pct": r["frac_pos_years"] >= 0.70,
            "verdict": (
                "PROMOTE" if (r["sharpe_excess_net"] >= 1.0 and r["worst_year_sharpe_excess"] >= 0)
                else "ADMITTED_CANDIDATE" if (r["sharpe_excess_net"] >= 1.0)
                else "RESEARCH_ONLY" if (r["sharpe_excess_net"] >= 0.5)
                else "REJECT"
            ),
        }
    with open(OUT / "r3_floors_batch_0003.json", "w") as f:
        json.dump(floors, f, indent=2)

    df_summary = pd.DataFrame(rows).round(3)
    print("\n=== R3 Summary ===")
    print(df_summary.to_string(index=False))
    print("\n=== Floors ===")
    print(pd.DataFrame(floors).T.round(3).to_string())

    # Markdown report
    md = ["# Backtest Results — batch_0003 (R3 production-grade phase-averaged)\n"]
    md.append(f"\nUniverse: 32 ETFs (H5: 20-ETF core) | period: 2020-2026 (skip 2019 warmup)\n")
    md.append(f"\nAll variants use 21-phase ensemble. Cost = {COST_BPS} bps/side.\n")
    md.append("\n## Summary table — top-5 long-only excess vs equal-weight benchmark\n")
    md.append(df_summary.to_markdown(index=False))
    md.append("\n\n## Per-year excess Sharpe\n")
    py_df = pd.DataFrame(py_rows)
    py_pivot = py_df.pivot(index="id", columns="year", values="sharpe").round(2)
    md.append(py_pivot.to_markdown())
    md.append("\n\n## Per-year excess return (cumulative, %)\n")
    py_ret_df = pd.DataFrame(py_excess_rows)
    py_ret_pivot = py_ret_df.pivot(index="id", columns="year", values="excess_return_ann").round(3)
    md.append(py_ret_pivot.to_markdown())
    md.append("\n\n## PROMOTE floor decisions\n")
    md.append(pd.DataFrame(floors).T.round(3).to_markdown())

    with open(OUT / "r3_backtest_results_batch_0003.md", "w") as f:
        f.write("\n".join(str(x) for x in md))

    return floors


if __name__ == "__main__":
    main()
