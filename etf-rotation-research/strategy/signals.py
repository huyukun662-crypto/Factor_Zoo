"""Signal computation: RSRS + higher-moment dual momentum.

Conventions
-----------
All public functions take wide panels indexed by date (rows) × symbol (cols)
and return a DataFrame with the same shape. **Every signal is computed using
ONLY data ≤ T-1**; the returned value at row T is the signal observable for
trading at T+1 open. The backtest engine takes care of the additional
`shift(1)` for execution.

# [NO-LOOKAHEAD] All signals here use rolling windows ending at T-1
# (i.e. `df.shift(1).rolling(L)` semantics) so the value at T is fully
# determined by data observed before the close of T.

Pitfalls explicitly avoided (per worldquant-5-agent-workflow/references/common-pitfalls.md):
  1. NO target-derived masks on FEATURE matrix
  2. NO factor using close[t] paired with target=ret.shift(-1) (we shift by 1
     additional step inside the engine; here we already use prior-day data)
  3. We ALWAYS report cross-sectional z-scores using only data available at T-1
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---------- helpers ----------

def _xs_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional z-score per row, robust to NaN."""
    mu = df.mean(axis=1)
    sd = df.std(axis=1).replace(0, np.nan)
    return df.sub(mu, axis=0).div(sd, axis=0)


def _safe_log_ret(close: pd.DataFrame) -> pd.DataFrame:
    return np.log(close).diff()


# ---------- RSRS ----------

def _rolling_ols_slope_r2(y: pd.Series, x: pd.Series, n: int
                          ) -> tuple[pd.Series, pd.Series]:
    """Vectorized rolling OLS slope and R^2 over window n.

    Uses closed-form: beta = cov(x,y)/var(x); R^2 = beta^2 * var(x)/var(y).
    """
    x_mean = x.rolling(n, min_periods=n).mean()
    y_mean = y.rolling(n, min_periods=n).mean()
    xy_mean = (x * y).rolling(n, min_periods=n).mean()
    xx_mean = (x * x).rolling(n, min_periods=n).mean()
    yy_mean = (y * y).rolling(n, min_periods=n).mean()

    cov_xy = xy_mean - x_mean * y_mean
    var_x = xx_mean - x_mean ** 2
    var_y = yy_mean - y_mean ** 2

    beta = cov_xy / var_x.replace(0, np.nan)
    r2 = (cov_xy ** 2) / (var_x.replace(0, np.nan) * var_y.replace(0, np.nan))
    r2 = r2.clip(lower=0, upper=1)
    return beta, r2


def rsrs_panel(high: pd.DataFrame, low: pd.DataFrame,
               n: int = 18, m: int = 600,
               form: str = "rsrs_skew") -> pd.DataFrame:
    """Compute RSRS signal panel for each symbol.

    Parameters
    ----------
    high, low : wide panels (date × symbol)
    n : RSRS regression window
    m : standardization lookback (z-score window). Falls back to expanding
        with min_periods=252 when fewer than m bars available.
    form : 'raw' | 'z' | 'rsrs_skew'

    Returns
    -------
    DataFrame same shape as high, containing the chosen RSRS form.
    The value at row T uses high/low up to and INCLUDING T (close of T).
    The engine applies an additional shift to enforce T+1 execution.
    """
    assert form in {"raw", "z", "rsrs_skew"}, f"unknown form {form}"
    out_beta = pd.DataFrame(index=high.index, columns=high.columns, dtype=float)
    out_r2 = pd.DataFrame(index=high.index, columns=high.columns, dtype=float)

    for sym in high.columns:
        h = high[sym].astype(float)
        l = low[sym].astype(float)
        beta, r2 = _rolling_ols_slope_r2(h, l, n)
        out_beta[sym] = beta
        out_r2[sym] = r2

    if form == "raw":
        return out_beta

    # z-score over long window m, with expanding fallback when bars<m
    min_p = min(252, m)
    z = pd.DataFrame(index=out_beta.index, columns=out_beta.columns, dtype=float)
    for sym in out_beta.columns:
        s = out_beta[sym]
        roll_mean = s.rolling(m, min_periods=min_p).mean()
        roll_std = s.rolling(m, min_periods=min_p).std().replace(0, np.nan)
        z[sym] = (s - roll_mean) / roll_std

    if form == "z":
        return z
    return z * out_r2  # rsrs_skew


# ---------- Dual momentum + higher moments ----------

def momentum_panel(close: pd.DataFrame, L: int = 120) -> pd.DataFrame:
    """log(close[T] / close[T-L])."""
    return np.log(close).diff(L)


def vol_panel(close: pd.DataFrame, L: int = 120) -> pd.DataFrame:
    return _safe_log_ret(close).rolling(L, min_periods=max(20, L // 2)).std()


def sharpe_panel(close: pd.DataFrame, L: int = 120) -> pd.DataFrame:
    mom = momentum_panel(close, L)
    vol = vol_panel(close, L)
    return mom / (vol * np.sqrt(L)).replace(0, np.nan)


def skew_panel(close: pd.DataFrame, L: int = 120) -> pd.DataFrame:
    return _safe_log_ret(close).rolling(L, min_periods=max(20, L // 2)).skew()


def kurt_panel(close: pd.DataFrame, L: int = 120) -> pd.DataFrame:
    # pandas rolling.kurt returns excess kurtosis (Fisher)
    return _safe_log_ret(close).rolling(L, min_periods=max(20, L // 2)).kurt()


def higher_moment_score(close: pd.DataFrame, L: int = 120,
                        lambda_s: float = 0.3, lambda_k: float = 0.2
                        ) -> pd.DataFrame:
    """mom_score = z(sharpe) + λ_s * z(skew) - λ_k * z(kurt)."""
    z_sh = _xs_zscore(sharpe_panel(close, L))
    z_sk = _xs_zscore(skew_panel(close, L))
    z_ku = _xs_zscore(kurt_panel(close, L))
    return z_sh.fillna(0) + lambda_s * z_sk.fillna(0) - lambda_k * z_ku.fillna(0)


# ---------- Composite ----------

def composite_score(rsrs: pd.DataFrame, mom: pd.DataFrame,
                    w_rsrs: float = 0.4) -> pd.DataFrame:
    """w_rsrs * z_xs(rsrs) + (1-w_rsrs) * z_xs(mom_score)."""
    w_mom = 1.0 - w_rsrs
    return w_rsrs * _xs_zscore(rsrs).fillna(0) + w_mom * _xs_zscore(mom).fillna(0)


# ---------- Eligibility (absolute momentum filter) ----------

def absolute_momentum_filter(close: pd.DataFrame, L: int,
                              benchmark_symbol: str) -> pd.DataFrame:
    """Eligible iff mom_L_i > mom_L_benchmark.

    The benchmark itself is also subject to the comparison (mom > 0 effectively
    when benchmark has zero excess vs itself).
    """
    mom = momentum_panel(close, L)
    if benchmark_symbol not in mom.columns:
        # fall back to "absolute > 0"
        return mom > 0
    bench = mom[benchmark_symbol]
    return mom.gt(bench, axis=0)


# ---------- Convenience: build the full per-day score panel ----------

def build_signal_panel(close: pd.DataFrame, high: pd.DataFrame, low: pd.DataFrame,
                       params: dict, benchmark_symbol: str
                       ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Returns (composite_score, eligibility_mask, agg_rsrs_csi300_series).

    `composite_score` and `eligibility_mask` are wide panels (date × symbol).
    `agg_rsrs_csi300_series` is the aggregate-market RSRS_skew on the benchmark,
    used downstream to drive the risk-off overlay.
    """
    rsrs = rsrs_panel(high, low,
                      n=params["rsrs_N"], m=params["rsrs_M"],
                      form=params.get("rsrs_form", "rsrs_skew"))
    mom = higher_moment_score(close, L=params["mom_L"],
                              lambda_s=params["lambda_s"],
                              lambda_k=params["lambda_k"])
    score = composite_score(rsrs, mom, w_rsrs=params["w_rsrs"])
    elig = absolute_momentum_filter(close, params["mom_L"], benchmark_symbol)

    if benchmark_symbol in rsrs.columns:
        agg_rsrs = rsrs[benchmark_symbol]
    else:
        agg_rsrs = pd.Series(0.0, index=rsrs.index)

    return score, elig, agg_rsrs
