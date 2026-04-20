"""
Numeric audits on the Round 2 winner alpha_v5 (median-TTM industry-neutral Sloan):
- Shuffle-forward-returns look-ahead test.
- Publication-lag leakage (end_date vs ann_date for median-TTM).
"""
import os, time, json
import numpy as np
import pandas as pd

CACHE = "/home/user/Factor_Zoo/.cache"
OUT = "/home/user/Factor_Zoo/logs/20260420_fundamental_accruals_alpha/outputs"


def log(s):
    print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)


def ic(df, col, ret):
    s = df.dropna(subset=[col, ret]).groupby("trade_date").apply(
        lambda x: x[col].corr(x[ret], method="spearman"), include_groups=False
    ).dropna()
    if len(s) < 10:
        return dict(ic_mean=np.nan, icir=np.nan, tstat=np.nan, n=len(s))
    return dict(
        ic_mean=float(s.mean()),
        icir=float(s.mean() / s.std()),
        tstat=float(s.mean() / s.std() * np.sqrt(len(s))),
        n=int(len(s)),
    )


log("loading Round 2 panel")
panel = pd.read_parquet(f"{CACHE}/panel_round2.parquet")
log(f"rows {len(panel):,}")

# ---- 1. shuffle test ----
log("shuffle-forward-returns test on alpha_v5")
rng = np.random.default_rng(0)
panel["fwd_shuf"] = panel.groupby("trade_date")["fwd_ret_20"].transform(
    lambda s: pd.Series(rng.permutation(s.values), index=s.index)
)
clean = ic(panel, "alpha_v5", "fwd_ret_20")
shuf = ic(panel, "alpha_v5", "fwd_shuf")
log(f"alpha_v5 clean:    IC={clean['ic_mean']:.4f}  ICIR={clean['icir']:.3f}  t={clean['tstat']:.1f}")
log(f"alpha_v5 shuffled: IC={shuf['ic_mean']:.6f}")
log(f"signal/noise ratio: {abs(clean['ic_mean'] / (shuf['ic_mean'] or 1e-9)):.0f}x")

# ---- 2. publication-lag leakage test (rebuild leaky median-TTM) ----
log("publication-lag leakage test on alpha_v5 (end_date vs ann_date)")
income = pd.read_parquet(f"{CACHE}/income.parquet")
bs = pd.read_parquet(f"{CACHE}/balancesheet.parquet")
cf = pd.read_parquet(f"{CACHE}/cashflow.parquet")
for d in (income, bs, cf):
    d["ann_date"] = pd.to_datetime(d["ann_date"], format="%Y%m%d", errors="coerce")
    d["end_date"] = pd.to_datetime(d["end_date"], format="%Y%m%d", errors="coerce")

f = (
    income[["ts_code", "ann_date", "end_date", "n_income"]]
    .merge(bs[["ts_code", "end_date", "total_assets"]], on=["ts_code", "end_date"])
    .merge(cf[["ts_code", "end_date", "n_cashflow_act"]], on=["ts_code", "end_date"])
    .sort_values(["ts_code", "end_date"])
)
g = f.groupby("ts_code", group_keys=False)
f["ni_med"] = g["n_income"].transform(lambda s: s.rolling(4, min_periods=3).median() * 4)
f["cfo_med"] = g["n_cashflow_act"].transform(lambda s: s.rolling(4, min_periods=3).median() * 4)
f["ta_avg"] = g["total_assets"].transform(lambda s: s.rolling(4, min_periods=3).mean())
f["acc_med_end"] = (f["ni_med"] - f["cfo_med"]) / f["ta_avg"]

lk = panel[["ts_code", "trade_date", "fwd_ret_20", "industry"]].sort_values(
    ["trade_date", "ts_code"]
).reset_index(drop=True)
f_sorted = f.dropna(subset=["end_date", "acc_med_end"]).sort_values(
    ["end_date", "ts_code"]
).reset_index(drop=True)
lk = pd.merge_asof(
    lk, f_sorted[["ts_code", "end_date", "acc_med_end"]],
    left_on="trade_date", right_on="end_date", by="ts_code",
    direction="backward", allow_exact_matches=False,
)
lk["acc_med_w"] = lk.groupby("trade_date")["acc_med_end"].transform(
    lambda s: s.clip(lower=s.quantile(0.01), upper=s.quantile(0.99))
)
lk["alpha_v5_leaky"] = -lk.groupby(["trade_date", "industry"])["acc_med_w"].rank(
    pct=True
) + 0.5
leaky = ic(lk, "alpha_v5_leaky", "fwd_ret_20")
log(f"alpha_v5 LEAKY (end_date): IC={leaky['ic_mean']:.4f} ICIR={leaky['icir']:.3f} t={leaky['tstat']:.1f}")
log(f"leaky vs clean ratio: {leaky['ic_mean']/clean['ic_mean']:.2f}")

# ---- save ----
res = dict(
    winner="alpha_v5 (median-TTM industry-neutral Sloan CFS)",
    shuffle_test=dict(clean_ic=clean["ic_mean"], shuffled_ic=shuf["ic_mean"]),
    publication_lag=dict(clean_ic=clean["ic_mean"], leaky_ic=leaky["ic_mean"], ratio=leaky["ic_mean"]/clean["ic_mean"]),
    shuffle_pass=bool(abs(shuf["ic_mean"]) < 0.005),
    pub_lag_pass=bool(leaky["ic_mean"] / clean["ic_mean"] < 1.5),
)
with open(f"{OUT}/audit_v5_winner.json", "w") as fh:
    json.dump(res, fh, indent=2, default=str)
log(f"wrote {OUT}/audit_v5_winner.json")
log(f"ALL AUDITS PASS: {res['shuffle_pass'] and res['pub_lag_pass']}")
