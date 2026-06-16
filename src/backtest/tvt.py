"""TVT split helpers (half-open intervals matching the approved plan)."""
from __future__ import annotations

import pandas as pd

TRAIN = ("2018-01-01", "2022-01-01")
VAL = ("2022-01-01", "2024-01-01")
TEST = ("2024-01-01", "2026-04-26")  # exclusive upper bound; today is 2026-04-25


def slice_split(panel: pd.DataFrame, split: str) -> pd.DataFrame:
    if split == "train":
        s, e = TRAIN
    elif split == "val":
        s, e = VAL
    elif split == "test":
        s, e = TEST
    elif split == "trainval":
        s, _ = TRAIN
        _, e = VAL
    else:
        raise ValueError(f"unknown split {split}")
    return panel[(panel.index >= pd.Timestamp(s)) & (panel.index < pd.Timestamp(e))]


def selection_score(train_sharpe: float, val_sharpe: float) -> float:
    return val_sharpe - 0.3 * abs(train_sharpe - val_sharpe)


def is_eligible(train_sharpe: float, val_sharpe: float) -> bool:
    return train_sharpe > 0.5 and val_sharpe > 0
