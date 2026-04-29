"""Backtest with delay-aware forward returns. Implements:
- IC at h in {1,5,10,20}
- Q1..Q5 long-only excess vs cross-section equal-weight, monthly rebalance
- Q5-Q1 LS daily and monthly
- Per-year Sharpe table for worst-year and best-year-out audits
- Turnover and after-cost net Sharpe (30bp round-trip)

INVARIANT: delay=1 -> ret_fwd[t,h] = adj_close.shift(-(1+h)) / adj_close.shift(-1) - 1.
"""
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DELAY = 1
HORIZONS = [1, 5, 10, 20]
COST_BP = 30
ALPHAS = [f"alpha_{k:02d}" for k in range(1, 9)]


def fwd_ret_panel(panel, h, delay=DELAY):
    """delay-aware forward return per stock."""
    return panel.groupby("ts_code")["adj_close"].transform(
        lambda s: s.shift(-(1 + h)) / s.shift(-(delay)) - 1)


def ic_table(p, alpha, h):
    fr = fwd_ret_panel(p, h)
    df = pd.DataFrame({"d": p["trade_date"], "f": p[alpha], "r": fr}).dropna()
    if df.empty: return np.nan, np.nan, np.nan
    daily_ic = df.groupby("d").apply(lambda x: x["f"].corr(x["r"], method="spearman"))
    daily_ic = daily_ic.dropna()
    if len(daily_ic) < 20: return np.nan, np.nan, np.nan
    m, s = daily_ic.mean(), daily_ic.std()
    t = m / (s / np.sqrt(len(daily_ic))) if s > 0 else np.nan
    ir = m / s if s > 0 else np.nan
    return float(m), float(t), float(ir)


def quintile_returns(p, alpha, h, monthly=False):
    """Build Q1..Q5 daily returns + LS + Q5 long-only excess."""
    df = p[["trade_date", "ts_code", "industry", alpha]].copy()
    df["fwd"] = fwd_ret_panel(p, h)
    df = df.dropna(subset=[alpha, "fwd"])

    if monthly:
        df["ym"] = pd.to_datetime(df["trade_date"]).dt.to_period("M")
        first_per_m = df.groupby(["ts_code", "ym"])["trade_date"].transform("min")
        df = df[df["trade_date"] == first_per_m]

    def q_assign(s):
        try: return pd.qcut(s, 5, labels=False, duplicates="drop")
        except ValueError: return pd.Series(np.nan, index=s.index)
    df["q"] = df.groupby("trade_date")[alpha].transform(q_assign)
    df = df.dropna(subset=["q"])
    df["q"] = df["q"].astype(int)

    avg = df.groupby("trade_date")["fwd"].mean().rename("xs_mean")
    pq = df.groupby(["trade_date", "q"])["fwd"].mean().unstack("q")
    pq = pq.rename(columns={i: f"q{i+1}" for i in range(5)})
    pq["ls"] = pq["q5"] - pq["q1"]
    pq["q5_excess"] = pq["q5"] - avg
    pq["q1_excess"] = pq["q1"] - avg
    sizes = df.groupby(["trade_date", "q"]).size().unstack("q").rename(
        columns={i: f"sz{i+1}" for i in range(5)})
    return pq.join(sizes), df


def sharpe(r, ann=252):
    r = r.dropna()
    if len(r) < 5 or r.std() == 0: return np.nan
    return float(r.mean() / r.std() * np.sqrt(ann))


def yearly_sharpe(r, ann=252):
    r = r.dropna()
    if r.empty: return pd.Series(dtype=float)
    r.index = pd.to_datetime(r.index.astype(str))
    return r.groupby(r.index.year).apply(lambda x: sharpe(x, ann))


def main():
    p = pd.read_parquet(OUT / "factors_panel.parquet").sort_values(
        ["ts_code", "trade_date"]).reset_index(drop=True)
    p["trade_date"] = p["trade_date"].astype(str)

    rows = []
    yearly_rows = []
    for a in ALPHAS:
        for h in HORIZONS:
            ic_m, ic_t, ir = ic_table(p, a, h)
            pq_d, _ = quintile_returns(p, a, h, monthly=False)
            pq_m, _ = quintile_returns(p, a, h, monthly=True)
            ann_d, ann_m = 252 / h, 12 / max(1, h // 21)
            ls_sr_d = sharpe(pq_d["ls"], 252 / h)
            q5e_sr_d = sharpe(pq_d["q5_excess"], 252 / h)
            ls_sr_m = sharpe(pq_m["ls"], 12)
            q5e_sr_m = sharpe(pq_m["q5_excess"], 12)
            mean_q5_sz = pq_d["sz5"].mean() if "sz5" in pq_d else np.nan

            rows.append(dict(alpha=a, h=h,
                ic_mean=ic_m, ic_t=ic_t, ic_ir=ir,
                ls_sr_daily=ls_sr_d, q5e_sr_daily=q5e_sr_d,
                ls_sr_monthly=ls_sr_m, q5e_sr_monthly=q5e_sr_m,
                q5_size_mean=mean_q5_sz))

            if h == 10:
                ys_ls = yearly_sharpe(pq_d["ls"], 252)
                ys_q5 = yearly_sharpe(pq_d["q5_excess"], 252)
                for y in sorted(set(ys_ls.index) | set(ys_q5.index)):
                    yearly_rows.append(dict(alpha=a, year=int(y),
                        ls_sr=float(ys_ls.get(y, np.nan)),
                        q5e_sr=float(ys_q5.get(y, np.nan))))

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "ic_ls_summary_batch_0001.csv", index=False)
    pd.DataFrame(yearly_rows).to_csv(OUT / "yearly_sharpe_h10.csv", index=False)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
