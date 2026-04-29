"""Round 2: fetch northbound, build alpha_09..alpha_16, backtest, audit, report."""
import os, json, time, sys
from pathlib import Path
import numpy as np, pandas as pd
import tushare as ts

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "inputs" / "cache"
OUT = ROOT / "outputs"
OUT.mkdir(parents=True, exist_ok=True)
DELAY = 1
HORIZONS = [1, 5, 10, 20]
ALPHAS_R2 = [f"alpha_{k:02d}" for k in range(9, 17)]


# ----------------- 1. fetch northbound (year-by-year, free-tier 300-row cap) -----------------
def fetch_north():
    cache_path = CACHE / "north.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)
    pro = ts.pro_api(os.environ["TUSHARE_TOKEN"])
    parts = []
    for y in [2022, 2023, 2024, 2025]:  # 2022 for 20d lookback at start of 2023
        for k in range(5):
            try:
                df = pro.moneyflow_hsgt(start_date=f"{y}0101", end_date=f"{y}1231")
                parts.append(df); break
            except Exception as e:
                time.sleep(2 ** k)
                if k == 4: raise
    nb = pd.concat(parts, ignore_index=True).drop_duplicates("trade_date").sort_values("trade_date")
    # Tushare moneyflow_hsgt north_money = cumulative net buy; daily flow = first-difference
    nb["north_flow"] = nb["north_money"].astype(float).diff()
    nb.to_parquet(cache_path)
    print(f"[north] {len(nb)} days {nb['trade_date'].min()}..{nb['trade_date'].max()}")
    return nb


# ----------------- 2. utility -----------------
def winsor_mad(s, k=3.5):
    s = s.astype(float); med = s.median(); mad = (s - med).abs().median()
    if not np.isfinite(mad) or mad == 0: return s
    lo, hi = med - k * 1.4826 * mad, med + k * 1.4826 * mad
    return s.clip(lo, hi)


def cs_pipeline(panel, raw_col):
    s = panel.groupby("trade_date")[raw_col].transform(winsor_mad)
    ind_mean = panel.assign(_x=s).groupby(["trade_date", "industry"])["_x"].transform("mean")
    s = s - ind_mean
    g = s.groupby(panel["trade_date"])
    s = (s - g.transform("mean")) / g.transform("std").replace(0, np.nan)
    return s.groupby(panel["trade_date"]).rank(pct=True) - 0.5


def fwd_ret(p, h, delay=DELAY):
    return p.groupby("ts_code")["adj_close"].transform(
        lambda s: s.shift(-(1 + h)) / s.shift(-delay) - 1)


# ----------------- 3. compute alphas -----------------
def compute(p, nb):
    p = p.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)
    g = p.groupby("ts_code")
    # additional lags
    for c in ["inst_net", "is_upper_limit", "dtl_event", "adj_close", "amount", "amt20"]:
        for lag in [1, 2, 3, 7, 12]:
            col = f"{c}_l{lag}"
            if col not in p.columns: p[col] = g[c].shift(lag)

    # alpha_09: sum(inst_net[t-7..t-3], 5) / amt20_l1  -- skip 2 days
    p["raw_09"] = (g["inst_net"].shift(3).rolling(5, min_periods=2).sum().reset_index(0, drop=True)
                   / p["amt20_l1"])
    # alpha_10: sum(inst_net[t-12..t-8], 5) / amt20_l1 -- skip 7 days
    p["raw_10"] = (g["inst_net"].shift(8).rolling(5, min_periods=2).sum().reset_index(0, drop=True)
                   / p["amt20_l1"])
    # alpha_11: alpha_09 with ex-upper-limit mask on the contributing days
    p["inst_net_safe"] = p["inst_net"] * (~p["is_upper_limit"]).astype(int)
    p["raw_11"] = (g["inst_net_safe"].shift(3).rolling(5, min_periods=2).sum().reset_index(0, drop=True)
                   / p["amt20_l1"])
    # alpha_12: post-DTL drift reversal -- if any DTL in [t-12..t-7], take -1*(adj_close[t-2]/adj_close[t-7]-1)
    had_dtl = g["dtl_event"].shift(7).rolling(6, min_periods=1).sum().reset_index(0, drop=True) > 0
    drift = p["adj_close_l2"] / p["adj_close_l7"] - 1
    p["raw_12"] = -1 * had_dtl.astype(int) * drift

    # raw alpha_02 from R1 (recompute for the overlay rather than rely on stored rank)
    raw_02 = g["inst_net"].shift(1).rolling(5, min_periods=2).sum().reset_index(0, drop=True) / p["amt20_l1"]

    # northbound: per-date map north_flow + 20d sum + zscore, lagged 1 day for trade-time
    nb = nb.copy()
    nb["nb20"] = nb["north_flow"].rolling(20, min_periods=10).sum()
    nb["nb20_z60"] = ((nb["nb20"] - nb["nb20"].rolling(60, min_periods=20).mean())
                     / nb["nb20"].rolling(60, min_periods=20).std()).clip(-2, 2)
    # lag(1): regime decision uses yesterday's published value
    nb["nb20_l1"] = nb["nb20"].shift(1)
    nb["nb20_z60_l1"] = nb["nb20_z60"].shift(1)
    p = p.merge(nb[["trade_date", "nb20_l1", "nb20_z60_l1"]], on="trade_date", how="left")
    p["nb_sign_l1"] = np.sign(p["nb20_l1"]).fillna(0)
    p["nb_gate_l1"] = (p["nb20_l1"] > 0).astype(int)

    p["raw_13"] = raw_02 * p["nb_sign_l1"]
    p["raw_14"] = raw_02 * p["nb20_z60_l1"].fillna(0)
    p["raw_15"] = raw_02 * p["nb_gate_l1"]

    cols = []
    for k in range(9, 16):
        col = f"alpha_{k:02d}"
        p[col] = cs_pipeline(p, f"raw_{k:02d}")
        cols.append(col)
    # alpha_16: ensemble alpha_09 + alpha_13 (rank-mean)
    ens = (p["alpha_09"].fillna(0) + p["alpha_13"].fillna(0))
    p["alpha_16"] = ens.groupby(p["trade_date"]).rank(pct=True) - 0.5
    cols.append("alpha_16")
    return p, cols


# ----------------- 4. backtest helpers -----------------
def sharpe(r, ann):
    r = r.dropna()
    if len(r) < 5 or r.std() == 0: return np.nan
    return float(r.mean() / r.std() * np.sqrt(ann))


def quintile(p, alpha, h, monthly=False):
    df = p[["trade_date", "ts_code", alpha]].copy()
    df["fwd"] = fwd_ret(p, h)
    df = df.dropna(subset=[alpha, "fwd"])
    if monthly:
        df["ym"] = pd.to_datetime(df["trade_date"]).dt.to_period("M")
        first = df.groupby(["ts_code", "ym"])["trade_date"].transform("min")
        df = df[df["trade_date"] == first]

    def qcut5(s):
        try: return pd.qcut(s.rank(method="first"), 5, labels=False, duplicates="drop")
        except ValueError: return pd.Series(np.nan, index=s.index)
    df["q"] = df.groupby("trade_date")[alpha].transform(qcut5)
    df = df.dropna(subset=["q"])
    avg = df.groupby("trade_date")["fwd"].mean().rename("xs")
    pq = df.groupby(["trade_date", "q"])["fwd"].mean().unstack("q")
    pq = pq.rename(columns={i: f"q{i+1}" for i in range(5)})
    pq["ls"] = pq["q5"] - pq["q1"]
    pq["q5e"] = pq["q5"] - avg
    sz = df.groupby(["trade_date", "q"]).size().unstack("q").rename(columns={i: f"sz{i+1}" for i in range(5)})
    return pq.join(sz)


def ic(p, alpha, h):
    fr = fwd_ret(p, h)
    df = pd.DataFrame({"d": p["trade_date"], "f": p[alpha], "r": fr}).dropna()
    if df.empty: return (np.nan,) * 3
    daily_ic = df.groupby("d").apply(lambda x: x["f"].corr(x["r"], method="spearman")).dropna()
    if len(daily_ic) < 20: return (np.nan,) * 3
    m, s = daily_ic.mean(), daily_ic.std()
    t = m / (s / np.sqrt(len(daily_ic))) if s > 0 else np.nan
    ir = m / s if s > 0 else np.nan
    return float(m), float(t), float(ir)


def yearly_ls_q5e(p, alpha, h=10):
    pq = quintile(p, alpha, h, monthly=False)
    pq.index = pd.to_datetime(pq.index.astype(str))
    out = []
    for y, g in pq.groupby(pq.index.year):
        out.append(dict(alpha=alpha, year=int(y),
            ls_sr=sharpe(g["ls"], 252), q5e_sr=sharpe(g["q5e"], 252)))
    return out


# ----------------- 5. residualization -----------------
def residualize(p, alphas):
    p = p.sort_values(["ts_code", "trade_date"]).copy()
    g = p.groupby("ts_code")
    p["ret1"] = g["adj_close"].transform(lambda s: s.pct_change())
    p["mom20"] = g["adj_close"].transform(lambda s: s.pct_change(20))
    p["rev5"] = -g["adj_close"].transform(lambda s: s.pct_change(5))
    p["max10"] = g["ret1"].rolling(10, min_periods=3).max().reset_index(0, drop=True)
    p["sz"] = np.log(g["amount"].rolling(60, min_periods=20).mean().reset_index(0, drop=True) + 1)
    fr = g["adj_close"].transform(lambda s: s.shift(-11) / s.shift(-1) - 1)
    out = {}
    for a in alphas:
        df = p[["trade_date", a, "mom20", "rev5", "max10", "sz"]].assign(r=fr).dropna()
        if df.empty: out[a] = None; continue

        def resid(sub):
            X = sub[["mom20", "rev5", "max10", "sz"]].values
            y = sub[a].values
            X = np.c_[np.ones(len(X)), X]
            try:
                beta, *_ = np.linalg.lstsq(X, y, rcond=None)
                return pd.Series(y - X @ beta, index=sub.index)
            except Exception:
                return pd.Series(y, index=sub.index)
        df["resid"] = df.groupby("trade_date").apply(resid).reset_index(level=0, drop=True)

        def qc(s):
            try: return pd.qcut(s.rank(method="first"), 5, labels=False, duplicates="drop")
            except ValueError: return pd.Series(np.nan, index=s.index)
        df["raw_q"] = df.groupby("trade_date")[a].transform(qc)
        df["res_q"] = df.groupby("trade_date")["resid"].transform(qc)

        def ls_sr(qcol):
            ls = df.groupby("trade_date").apply(
                lambda x: x.loc[x[qcol] == 4, "r"].mean() - x.loc[x[qcol] == 0, "r"].mean()).dropna()
            return float(ls.mean() / ls.std() * np.sqrt(252)) if ls.std() > 0 else np.nan

        raw_sr, res_sr = ls_sr("raw_q"), ls_sr("res_q")
        out[a] = {"raw_ls_sr": raw_sr, "resid_ls_sr": res_sr,
                  "ratio_resid_to_raw": (res_sr / raw_sr) if raw_sr and raw_sr != 0 else None}
    return out


# ----------------- 6. main -----------------
def main():
    nb = fetch_north()
    p = pd.read_parquet(OUT / "panel.parquet").sort_values(
        ["ts_code", "trade_date"]).reset_index(drop=True)
    p["trade_date"] = p["trade_date"].astype(str)

    p, cols = compute(p, nb)

    # backtest
    rows = []; yearly_rows = []
    for a in cols:
        for h in HORIZONS:
            ic_m, ic_t, ir = ic(p, a, h)
            pq_d = quintile(p, a, h, monthly=False)
            pq_m = quintile(p, a, h, monthly=True)
            row = dict(alpha=a, h=h, ic_mean=ic_m, ic_t=ic_t, ic_ir=ir,
                ls_sr_daily=sharpe(pq_d["ls"], 252 / h),
                q5e_sr_daily=sharpe(pq_d["q5e"], 252 / h),
                ls_sr_monthly=sharpe(pq_m["ls"], 12),
                q5e_sr_monthly=sharpe(pq_m["q5e"], 12),
                q5_size_mean=float(pq_d["sz5"].mean()) if "sz5" in pq_d else np.nan)
            rows.append(row)
        yearly_rows.extend(yearly_ls_q5e(p, a, 10))
    summ = pd.DataFrame(rows)
    summ.to_csv(OUT / "ic_ls_summary_batch_0002.csv", index=False)
    yearly = pd.DataFrame(yearly_rows)
    yearly.to_csv(OUT / "yearly_sharpe_h10_r2.csv", index=False)

    # audits
    floors = {a: dict() for a in cols}
    for a in cols:
        sub = yearly[yearly["alpha"] == a].dropna(subset=["ls_sr", "q5e_sr"])
        if not sub.empty:
            floors[a] = dict(worst_year_ls=float(sub["ls_sr"].min()),
                             worst_year_q5e=float(sub["q5e_sr"].min()),
                             n_years_pos_ls=int((sub["ls_sr"] > 0).sum()),
                             n_years=int(len(sub)))

    # best-year-out
    byo = {}
    for a in cols:
        pq = quintile(p, a, 10, monthly=False)
        if pq.empty or pq["ls"].std() == 0: byo[a] = None; continue
        ls = pq["ls"]; ls.index = pd.to_datetime(ls.index.astype(str))
        head = ls.mean() / ls.std() * np.sqrt(252)
        years = sorted(set(ls.index.year))
        worst = (None, None)
        for y in years:
            sub = ls[ls.index.year != y]
            if sub.std() == 0: continue
            sr = sub.mean() / sub.std() * np.sqrt(252)
            if worst[1] is None or sr < worst[1]: worst = (y, float(sr))
        byo[a] = dict(headline_sr=float(head), worst_year_dropped=worst[0],
                      best_year_out_sr=worst[1],
                      ratio=worst[1] / head if head and head != 0 else None)

    res = residualize(p, cols)
    audits = dict(worst_year_floor=floors, best_year_out=byo, residualization=res)
    (OUT / "audits_r2.json").write_text(json.dumps(audits, indent=2, default=str))

    # ranking + decisions
    head_h10 = summ[summ["h"] == 10].copy()
    head_h10["score"] = head_h10["q5e_sr_monthly"].fillna(-9) + 0.3 * head_h10["ic_ir"].fillna(-9)
    head_h10 = head_h10.sort_values("score", ascending=False)

    lines = ["# Alpha ranking — batch 0002 (round 2)\n",
             "Universe: A-share ex-IPO<250d, 2023-01 → 2025-12, delay=1.\n",
             "Tests: A=post-DTL window (alpha_09..12), B=northbound regime overlay (alpha_13..15), ensemble (alpha_16).\n\n",
             "## Headline (h=10)\n\n",
             head_h10[["alpha", "ic_mean", "ic_t", "ic_ir",
                       "ls_sr_daily", "q5e_sr_daily",
                       "ls_sr_monthly", "q5e_sr_monthly", "q5_size_mean"]].round(3).to_markdown(index=False),
             "\n\n## Per-year LS Sharpe (h=10)\n\n",
             yearly.pivot(index="alpha", columns="year", values="ls_sr").round(2).to_markdown(),
             "\n\n## Audit floors\n\n",
             "| alpha | worst_year_LS | worst_year_Q5e | best_year_out_LS | resid_LS_pct_of_raw |\n",
             "|---|---|---|---|---|\n"]
    for a in cols:
        wy = floors.get(a) or {}; b = byo.get(a) or {}; r = res.get(a) or {}
        lines.append(f"| {a} | {wy.get('worst_year_ls')} | {wy.get('worst_year_q5e')} | "
                     f"{b.get('best_year_out_sr')} | {r.get('ratio_resid_to_raw')} |\n")

    lines.append("\n\n## Decision per alpha\n\n")
    for a in cols:
        wy = floors.get(a) or {}; b = byo.get(a) or {}; r = res.get(a) or {}
        c1 = (wy.get("worst_year_ls") is not None and wy.get("worst_year_ls") >= 0.5)
        c2 = (wy.get("worst_year_q5e") is not None and wy.get("worst_year_q5e") >= 0.4)
        c3 = (b.get("ratio") is not None and b.get("ratio") >= 0.5)
        c4 = (r.get("ratio_resid_to_raw") is not None and r.get("ratio_resid_to_raw") >= 0.5)
        decision = "PROMOTE_CANDIDATE" if all([c1, c2, c3, c4]) else "RESEARCH_ONLY"
        lines.append(f"### {a} → **{decision}**\n\n")
        for k, v in [("worst_year_LS>=0.5", c1), ("worst_year_Q5e>=0.4", c2),
                     ("best_year_out>=50%", c3), ("residualized>=50%", c4)]:
            lines.append(f"- {'✓' if v else '✗'} {k}\n")
        lines.append("\n")

    (OUT / "alpha_ranking_r2.md").write_text("".join(lines))
    print(head_h10[["alpha", "ic_mean", "ic_t", "ic_ir",
                    "ls_sr_monthly", "q5e_sr_monthly", "q5_size_mean"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
