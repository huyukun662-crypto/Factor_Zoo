"""Importing this module discovers and registers all expressions."""
from __future__ import annotations

import importlib
import pkgutil

from . import expressions as _expressions_pkg
from .base import FACTORS  # noqa: F401  (re-exported)


def _discover():
    for mod in pkgutil.iter_modules(_expressions_pkg.__path__):
        importlib.import_module(f"{_expressions_pkg.__name__}.{mod.name}")


_discover()
