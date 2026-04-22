"""
Round 2 build: idiosyncratic momentum.
Adds log_mv, sigma_120, ret_20 controls, then residualizes α_01,02,03,04,05,07,08 per date.
"""
from __future__ import annotations
import time
import numpy as np
import pandas as pd

ROOT = "/home/user/Factor_Zoo/logs/20260422_trend_technical_alpha"
PANEL = f"{ROOT}/outputs/panel_trend.parquet"
OUT = f"{ROOT}/outputs/panel_trend_round2.parquet"


def cs_residualize(df: pd.DataFrame, target: str, controls: list[str]) -> pd.Series:
    """Per-date OLS residualization. Returns a Series aligned to df.index."""
    cols = [target] + controls
    sub = df[["trade_date"] + cols].copy()
    out = pd.Series(np.nan, index=df.index, dtype=np.float64)
    for d, idx in sub.groupby("trade_date").indices.items():
        rows = sub.loc[idx]
        m = rows[cols].dropna()
        if len(m) < 50:
            continue
        y = m[target].values
        X = np.column_stack([np.ones(len(m))] + [m[c].values for c in controls])
        try:
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            yhat = X @ beta
            out.loc[m.index] = y - yhat
        except np.linalg.LinAlgError:
            continue
    return out


def main():
    t0 = time.time()
    print("[r2] loading round-1 panel...")
    df = pd.read_parquet(PANEL)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)

    # Build needed controls from raw daily ret. We need log_p again to get ret.
    print("[r2] rebuilding controls (log_mv, sigma_120, ret_20)...")
    daily = pd.read_parquet("/home/user/Factor_Zoo/.cache/daily.parquet").merge(
        pd.read_parquet("/home/user/Factor_Zoo/.cache/adj_factor.parquet"),
        on=["ts_code", "trade_date"], how="left"
    )
    daily["adj_factor"] = daily["adj_factor"].fillna(1.0)
    daily["P"] = daily["close"] * daily["adj_factor"]
    daily = daily.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)
    daily["ret"] = daily.groupby("ts_code")["P"].transform(lambda s: np.log(s).diff())
    daily["sigma_120"] = daily.groupby("ts_code")["ret"].transform(lambda s: s.rolling(120, min_periods=80).std(ddof=0))
    daily["ret_20"] = daily.groupby("ts_code")["ret"].transform(lambda s: s.rolling(20, min_periods=15).sum())

    df = df.merge(daily[["ts_code", "trade_date", "sigma_120", "ret_20"]], on=["ts_code", "trade_date"], how="left")
    df["log_mv"] = np.log(df["total_mv"].replace(0, np.nan))

    # Residualize each raw alpha
    print("[r2] residualizing raw alphas (cs per date)...")
    raw_to_idio = {
        "alpha_01": "alpha_09",
        "alpha_02": "alpha_10",
        "alpha_03": "alpha_11",
        "alpha_04": "alpha_12",
        "alpha_05": "alpha_13",
        "alpha_07": "alpha_14",
        "alpha_08": "alpha_15",
    }
    controls = ["log_mv", "sigma_120", "ret_20"]
    for raw, idio in raw_to_idio.items():
        ts = time.time()
        df[idio] = cs_residualize(df, raw, controls)
        print(f"  {raw} -> {idio}  ({time.time()-ts:.1f}s)")

    # alpha_16: combo z-score average of alpha_09 and alpha_15
    z09 = df.groupby("trade_date")["alpha_09"].transform(lambda s: (s - s.mean()) / s.std(ddof=0))
    z15 = df.groupby("trade_date")["alpha_15"].transform(lambda s: (s - s.mean()) / s.std(ddof=0))
    df["alpha_16"] = (z09 + z15) / 2.0

    keep = (
        ["ts_code", "trade_date", "industry", "total_mv", "log_mv", "sigma_120", "ret_20"]
        + [f"alpha_{i:02d}" for i in [1,2,3,4,5,7,8]]  # raw for diag
        + [f"alpha_{i:02d}" for i in range(9, 17)]
        + [f"fwd_ret_{K}" for K in [1, 5, 20, 60]]
    )
    out = df[keep].copy()
    print("[r2] NaN frac (idio + combo):")
    for c in [f"alpha_{i:02d}" for i in range(9, 17)]:
        print(f"  {c}: {out[c].isna().mean():.3f}")
    out.to_parquet(OUT, index=False)
    print(f"[r2] wrote {OUT}, elapsed={time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
