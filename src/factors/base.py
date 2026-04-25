"""Factor base class and registry."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass
class Factor:
    """A timing factor that maps a panel to a daily score series.

    score_t > 0  → favor CSI300 (long 300 / short 1000)
    score_t < 0  → favor CSI1000 (long 1000 / short 300)
    score_t = 0  → flat

    `thesis_sign` is the SIGN OF IC vs forward (idx300 - idx1000) returns
    that the economic thesis predicts. By construction every factor here
    should produce thesis_sign = +1 (signal already oriented "long this side").
    G4 enforces this — a factor that prints positive scores when 1000 is
    about to outperform has the wrong sign.
    """

    name: str
    thesis_sign: int  # +1 or -1
    horizon: int      # primary horizon in trading days
    fn: Callable[[pd.DataFrame], pd.Series]
    rationale: str = ""

    def generate(self, panel: pd.DataFrame) -> pd.Series:
        s = self.fn(panel)
        s.name = self.name
        return s


FACTORS: dict[str, Factor] = {}


def register(factor: Factor) -> Factor:
    if factor.name in FACTORS:
        raise ValueError(f"duplicate factor name: {factor.name}")
    FACTORS[factor.name] = factor
    return factor
