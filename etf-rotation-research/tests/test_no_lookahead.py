"""Random-future-perturbation audit for every signal we use."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from data.fetch_data import build_close_open_panels, load_panel  # noqa: E402
from strategy.backtest import validate_no_lookahead  # noqa: E402
from strategy.signals import (
    higher_moment_score,
    momentum_panel,
    rsrs_panel,
    sharpe_panel,
    skew_panel,
    kurt_panel,
)  # noqa: E402
from strategy.universe import SYMBOLS  # noqa: E402


@pytest.fixture(scope="module")
def panels():
    pd_dict = load_panel(SYMBOLS, start="2013-01-01", end="2019-12-31")
    if not pd_dict:
        pytest.skip("no cached data — run scripts_fetch_all.py first")
    close, open_, high, low, volume, amount = build_close_open_panels(pd_dict)
    return {"close": close, "open": open_, "high": high, "low": low,
            "volume": volume, "amount": amount}


def _wrap(fn):
    """Wrap a single-panel signal fn to accept the dict the validator expects."""
    return fn


def test_rsrs_skew_no_lookahead(panels):
    def sig(p):
        return rsrs_panel(p["high"], p["low"], n=18, m=250, form="rsrs_skew")
    ok, msg = validate_no_lookahead(sig, panels)
    assert ok, msg


def test_momentum_no_lookahead(panels):
    def sig(p):
        return momentum_panel(p["close"], L=120)
    ok, msg = validate_no_lookahead(sig, panels)
    assert ok, msg


def test_sharpe_no_lookahead(panels):
    def sig(p):
        return sharpe_panel(p["close"], L=120)
    ok, msg = validate_no_lookahead(sig, panels)
    assert ok, msg


def test_skew_no_lookahead(panels):
    def sig(p):
        return skew_panel(p["close"], L=120)
    ok, msg = validate_no_lookahead(sig, panels)
    assert ok, msg


def test_kurt_no_lookahead(panels):
    def sig(p):
        return kurt_panel(p["close"], L=120)
    ok, msg = validate_no_lookahead(sig, panels)
    assert ok, msg


def test_higher_moment_score_no_lookahead(panels):
    def sig(p):
        return higher_moment_score(p["close"], L=120, lambda_s=0.3, lambda_k=0.2)
    ok, msg = validate_no_lookahead(sig, panels)
    assert ok, msg
