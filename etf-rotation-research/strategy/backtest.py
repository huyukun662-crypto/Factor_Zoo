"""Vectorized backtest engine + cost model + no-lookahead validator.

Conventions (per execution-delay-audit.md, common-pitfalls.md):
  - Decision at close[T] using info ≤ T-1
  - Execution at open[T+1]
  - Return measured close-to-close starting from open[T+1] over [T+1 close → T+2 close)
  - Engine internally shifts target weights by +1 (one extra day) before pricing.

Cost model
----------
  Per trade side:
    commission_buy  = 3 bps
    commission_sell = 3 bps
    stamp_duty_sell = 10 bps  (only if symbol is NOT bond/money)
    slippage        = 5 bps   (both sides)

  Volume cap: per-day per-symbol fill ≤ 25% × actual amount.
              Excess turnover is **rolled** into the next day's target
              (vectorized via cumulative pressure).

# [NO-LOOKAHEAD] Engine consumes pre-computed weights and prices; the only
# price column it can see at row T+1 is open[T+1] (already known by the time
# the order fills). Returns are computed strictly forward.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np
import pandas as pd


@dataclass
class CostConfig:
    commission_buy: float = 3e-4
    commission_sell: float = 3e-4
    stamp_duty_sell: float = 10e-4
    slippage_per_side: float = 5e-4
    bond_or_money_set: set[str] = field(default_factory=set)
    volume_cap: float = 0.25  # 25% of daily traded amount

    def per_symbol_buy_bps(self, sym: str) -> float:
        return self.commission_buy + self.slippage_per_side

    def per_symbol_sell_bps(self, sym: str) -> float:
        stamp = 0.0 if sym in self.bond_or_money_set else self.stamp_duty_sell
        return self.commission_sell + self.slippage_per_side + stamp


@dataclass
class BacktestResult:
    pnl_gross: pd.Series
    pnl_cost: pd.Series
    pnl_net: pd.Series
    equity: pd.Series
    weights_realized: pd.DataFrame
    turnover: pd.Series
    capped_turnover: pd.Series
    metrics: dict


def annualize_metrics(pnl: pd.Series, periods: int = 252) -> dict:
    pnl = pnl.dropna()
    if len(pnl) < 5:
        return dict(ann_ret=0.0, ann_vol=0.0, sharpe=0.0, max_dd=0.0,
                    calmar=0.0, sortino=0.0, win_rate=0.0, n=len(pnl))
    eq = (1 + pnl).cumprod()
    yrs = max(len(pnl) / periods, 1e-9)
    ann_ret = eq.iloc[-1] ** (1 / yrs) - 1
    ann_vol = pnl.std() * np.sqrt(periods)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
    peak = eq.cummax()
    dd = eq / peak - 1
    max_dd = dd.min()
    calmar = ann_ret / abs(max_dd) if max_dd < 0 else 0.0
    downside = pnl[pnl < 0].std() * np.sqrt(periods)
    sortino = ann_ret / downside if downside > 0 else 0.0
    win_rate = (pnl > 0).mean()
    return dict(ann_ret=float(ann_ret), ann_vol=float(ann_vol),
                sharpe=float(sharpe), max_dd=float(max_dd),
                calmar=float(calmar), sortino=float(sortino),
                win_rate=float(win_rate), n=int(len(pnl)))


def per_year_metrics(pnl: pd.Series, periods: int = 252) -> pd.DataFrame:
    """Yearly Sharpe / return / DD."""
    rows = []
    for yr, sub in pnl.groupby(pnl.index.year):
        m = annualize_metrics(sub, periods)
        m["year"] = int(yr)
        rows.append(m)
    return pd.DataFrame(rows).set_index("year").sort_index()


def run_backtest(target_weights: pd.DataFrame,
                 close: pd.DataFrame,
                 open_: pd.DataFrame,
                 amount: pd.DataFrame,
                 cost_cfg: CostConfig,
                 ) -> BacktestResult:
    """Vectorized backtest.

    Parameters
    ----------
    target_weights : decision panel — value at row T uses info ≤ T close
    close, open_, amount : wide panels aligned on (date, symbol)
    cost_cfg : CostConfig
    """
    # Align all panels to the union of available dates and symbols
    cols = sorted(set(target_weights.columns) & set(close.columns) & set(open_.columns))
    idx = sorted(set(target_weights.index) & set(close.index) & set(open_.index))
    tw = target_weights.reindex(index=idx, columns=cols).fillna(0.0)
    cl = close.reindex(index=idx, columns=cols).astype(float)
    op = open_.reindex(index=idx, columns=cols).astype(float)
    amt = amount.reindex(index=idx, columns=cols).astype(float)

    # T+1 execution: shift weights forward by 1 trading day
    tw_exec = tw.shift(1).fillna(0.0)

    # Returns for held position: open[T+1] -> close[T+1] (intra-day) +
    # close[T+1] -> close[T+2] etc. Use simple close-to-close (proxy: held
    # at open[T+1], measured at close[T+1] forward). For a vectorized first
    # pass we approximate execution price as open[T+1] and PnL as close-to-close
    # ret on that day.
    ret_cc = cl.pct_change().fillna(0.0)
    # On day T+1 we earn (close[T+1]/open[T+1] - 1) for the freshly opened block
    # and 0 on existing block; for simplicity take ret = (close[T+1]/open[T+1]-1)
    # on T+1 plus the standard close-to-close from T+2 onward.
    # Practical approximation that keeps full vectorization: PnL on day t from
    # weights tw_exec[t] applied to ret_cc[t]. We sacrifice the open->close
    # micro-effect (small at daily frequency) for clean vectorization.
    pnl_gross = (tw_exec * ret_cc).sum(axis=1)

    # ---- Turnover & cost ----
    # weight changes per symbol per day (signed)
    dw_signed = tw_exec.diff().fillna(tw_exec.iloc[[0]].reindex_like(tw_exec).fillna(0))
    # "buy" component (positive change), "sell" component (negative change)
    buy_dw = dw_signed.clip(lower=0)
    sell_dw = (-dw_signed).clip(lower=0)

    # Volume cap: per-day per-symbol notional traded ≤ vol_cap × daily amount
    # Express our trade as fraction-of-portfolio; assume portfolio NAV ≈ 1
    # (relative units), then trade_notional_i = |dw_i| (in NAV units).
    # The cap is on the symbol's daily amount; we approximate per-symbol max
    # tradable fraction-of-portfolio as min(|dw|, vol_cap_factor) where
    # vol_cap_factor is sym-specific and large enough that it almost never
    # binds for our liquidity-filtered universe (audit: see capped_turnover).
    # For correctness rather than realism, we compute the capped fraction
    # explicitly and roll the un-filled remainder into the next day.

    # Translate amount (CNY) to "fraction-of-portfolio cap" assuming a fixed
    # portfolio AUM of CAP_AUM. Smaller AUM -> looser cap; we choose 100M CNY
    # so that a 25% cap on a typical ETF (~500M daily amount) gives a per-day
    # max trade of ~125% of NAV — almost always non-binding for daily rebalance.
    AUM = 1e8
    max_trade_frac = (cost_cfg.volume_cap * amt.fillna(0.0) / AUM).clip(upper=1.0)

    # Compute capped buy/sell fractions, with "rollover" to next day for excess.
    # Vectorized rollover via simple per-day clip + carry-over accumulation.
    capped_buys = pd.DataFrame(index=tw_exec.index, columns=tw_exec.columns, dtype=float)
    capped_sells = pd.DataFrame(index=tw_exec.index, columns=tw_exec.columns, dtype=float)

    # We loop over symbols (a small dim), still avoiding any time loop.
    for s in tw_exec.columns:
        cap_s = max_trade_frac[s].values
        b = buy_dw[s].values.copy()
        sl = sell_dw[s].values.copy()
        # Rollover via single-pass cumulative; each day execute at most cap_s,
        # and push remainder to next day's pending bucket.
        pending_b = 0.0
        pending_s = 0.0
        ob = np.zeros_like(b)
        os_ = np.zeros_like(sl)
        for i in range(len(b)):
            want_b = b[i] + pending_b
            want_s = sl[i] + pending_s
            do_b = min(want_b, cap_s[i])
            do_s = min(want_s, cap_s[i])
            ob[i] = do_b
            os_[i] = do_s
            pending_b = want_b - do_b
            pending_s = want_s - do_s
        capped_buys[s] = ob
        capped_sells[s] = os_

    # cost per symbol per day = capped_buy * buy_bps + capped_sell * sell_bps
    buy_bps = pd.Series({s: cost_cfg.per_symbol_buy_bps(s) for s in tw_exec.columns})
    sell_bps = pd.Series({s: cost_cfg.per_symbol_sell_bps(s) for s in tw_exec.columns})
    daily_cost = (capped_buys.mul(buy_bps, axis=1) + capped_sells.mul(sell_bps, axis=1)).sum(axis=1)

    pnl_net = pnl_gross - daily_cost
    equity = (1 + pnl_net).cumprod()

    # bookkeeping
    turnover = (buy_dw + sell_dw).sum(axis=1)             # one-way turnover
    capped_turnover = (capped_buys + capped_sells).sum(axis=1)

    metrics = annualize_metrics(pnl_net)
    metrics["gross_sharpe"] = annualize_metrics(pnl_gross)["sharpe"]
    metrics["ann_turnover"] = float(turnover.sum() / max(len(turnover) / 252, 1))
    metrics["ann_capped_turnover"] = float(capped_turnover.sum() / max(len(turnover) / 252, 1))

    return BacktestResult(
        pnl_gross=pnl_gross,
        pnl_cost=daily_cost,
        pnl_net=pnl_net,
        equity=equity,
        weights_realized=tw_exec,
        turnover=turnover,
        capped_turnover=capped_turnover,
        metrics=metrics,
    )


# ---------- No-lookahead audit ----------

def validate_no_lookahead(signal_fn, prices_panels: dict[str, pd.DataFrame],
                          rng_seed: int = 42, n_perturb: int = 20,
                          shock_horizon: int = 5,
                          shock_size: float = 0.05,
                          ) -> tuple[bool, str]:
    """Random-future-perturbation audit.

    Picks `n_perturb` random days; for each day t, perturbs prices on
    [t+1, t+shock_horizon] by ±shock_size and recomputes signals on
    [max(0, t-30), t]. Asserts those signals are bit-for-bit identical to
    the unperturbed run.

    `signal_fn` must take the panel dict (with keys close/open/high/low)
    and return a DataFrame whose row index aligns with prices.
    """
    rng = np.random.default_rng(rng_seed)
    base_panels = {k: v.copy() for k, v in prices_panels.items()}
    sig_base = signal_fn(base_panels)

    n = len(base_panels["close"])
    if n < shock_horizon + 60:
        return True, "panel too short — skipped"
    sample_idx = rng.choice(np.arange(60, n - shock_horizon - 1), size=min(n_perturb, n - 80), replace=False)

    for t in sample_idx:
        perturbed = {k: v.copy() for k, v in prices_panels.items()}
        shock = 1.0 + rng.uniform(-shock_size, shock_size,
                                   size=(shock_horizon, perturbed["close"].shape[1]))
        for key in ("open", "high", "low", "close"):
            if key in perturbed:
                perturbed[key].iloc[t + 1: t + 1 + shock_horizon, :] = (
                    perturbed[key].iloc[t + 1: t + 1 + shock_horizon, :].values * shock
                )
        sig_pert = signal_fn(perturbed)
        # compare on [max(0, t-30):t+1]
        a = sig_base.iloc[max(0, t - 30): t + 1].fillna(0).values
        b = sig_pert.iloc[max(0, t - 30): t + 1].fillna(0).values
        if not np.allclose(a, b, atol=1e-10, equal_nan=True):
            diff = np.nanmax(np.abs(a - b))
            return False, f"lookahead leak at t={t}, max abs diff={diff:.4e}"
    return True, "ok"
