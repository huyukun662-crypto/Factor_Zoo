"""anchor_inv_ivol_ensemble_50_50_v1 — diversified A-share ETF ensemble.

50/50 blend of two catalog factors:
  - anchor_range_pos_etf_v1 (v1.1) — multi-window range position, top-3 long-only,
    21-phase ensemble + 10% vol target. Daily-NAV-stream output.
  - inv_ivol_voltarget_bondrotate_etf_v2 — inverted IVOL Q5-Q1 LS + 10% vol target
    + 12-week bond rotation overlay. Catalog convention: daily-resolution
    series in k=20 forward-return units.

Scaling convention: divide inv_ivol's daily series by k=20 to convert to
daily-NAV-equivalent. Then 50/50 weight = simple average of daily returns.

Headline (2020-01 → 2026-04, 5 bps/side, after vol target on each component):
    sharpe_full              = 1.91
    ann_return_excess        = 14.5 %
    ann_vol_excess           = 7.6 % (vs anchor 15%, ivol_scaled 2.5%)
    max_dd_excess            = -6.4 %  (vs anchor -14.8 %)
    daily_correlation_components = 0.001  (effectively uncorrelated)
    n_pos_years              = 6 / 7  (incl. 2026 partial; 6/6 if exclude 2026)
    worst_year_complete      = +0.51 Sharpe (2024)  → clears strict 0.5 floor
    worst_year_complete_cum  = +2.7 % (2024)
    worst_year_partial       = -1.08 Sharpe (2026, 4 months) — small sample
    worst_year_partial_cum   = -1.5 %
"""
from __future__ import annotations
import sys
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("/home/user/Factor_Zoo")
ANCHOR_CODE_PATH = ROOT / "factors/price_volume/anchor_range_pos_etf_v1/code.py"
IVOL_CODE_PATH = ROOT / "factors/price_volume/inv_ivol_voltarget_bondrotate_etf_v2/code.py"

# ivol catalog uses k=20 convention; daily series is k×daily-equivalent
IVOL_K_SCALE = 20

ANCHOR_SYMBOLS = [
    "510300.SS", "510500.SS", "510050.SS", "159915.SZ", "510180.SS",
    "159949.SZ", "588000.SS", "588080.SS", "512100.SS", "510880.SS",
    "512880.SS", "512660.SS", "512170.SS", "512760.SS", "515030.SS",
    "512290.SS", "515050.SS", "512690.SS", "512980.SS", "515290.SS",
    "518880.SS",
    "512480.SS", "159819.SZ", "515880.SS", "159890.SZ", "159869.SZ",
    "159857.SZ", "159755.SZ", "512010.SS",
    "159992.SZ", "159980.SZ", "515220.SS", "515210.SS",
]


def _load_module(name: str, path: Path):
    """Load python module from explicit file path; bypasses sys.modules cache.
    Required because two factors both have a file named code.py."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod              # required for @dataclass decorators
    spec.loader.exec_module(mod)
    return mod


def run_anchor_v1_1(panel: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Returns (excess_daily, bench_daily) — both in true daily NAV units."""
    a = _load_module("anchor_v1_1_module", ANCHOR_CODE_PATH)
    p = panel[panel.symbol.isin(ANCHOR_SYMBOLS)].copy()
    p = p.sort_values(["date", "symbol"]).reset_index(drop=True)
    p["ret"] = p.groupby("symbol")["close"].pct_change()
    close = p.pivot(index="date", columns="symbol", values="close").sort_index()
    rets = p.pivot(index="date", columns="symbol", values="ret").sort_index()

    sig = a.signal(close)
    universe = a.core_universe(close)
    _, net, bench, _ = a.phase_ensemble_long_only(
        sig, rets, n=a.N_TOP, rebal=a.REBAL,
        cost_bps=a.COST_BPS, universe_filter=universe,
    )
    excess = a.vol_target_overlay(net - bench)
    return excess.dropna(), bench


def run_inv_ivol_v2(panel: pd.DataFrame) -> pd.Series:
    """Returns daily series scaled by 1/k=20 to give daily-NAV-equivalent."""
    iv = _load_module("inv_ivol_v2_module", IVOL_CODE_PATH)
    p = panel.copy()
    p["ret"] = p.groupby("symbol")["close"].pct_change()
    res = iv.run(p)
    return (res.final_ret_net5bps / IVOL_K_SCALE).dropna()


def blend_50_50(panel: pd.DataFrame) -> pd.Series:
    """Compute the 50/50 blend daily excess return."""
    anchor_ex, _ = run_anchor_v1_1(panel)
    ivol_ex = run_inv_ivol_v2(panel)
    common = anchor_ex.index.intersection(ivol_ex.index)
    common = common[common.year >= 2020]   # skip warmup
    return 0.5 * anchor_ex.loc[common] + 0.5 * ivol_ex.loc[common]


def annualize_sharpe(s: pd.Series, k: int = 1, min_obs: int = 20) -> float:
    x = s.dropna()
    if len(x) < min_obs or x.std() == 0:
        return float("nan")
    return float(x.mean() / x.std() * np.sqrt(252 / k))
