"""Thin tushare wrapper: token from env, retry with exponential backoff."""
from __future__ import annotations

import os
import time
from typing import Callable

import tushare as ts
from dotenv import load_dotenv

load_dotenv()

_PRO = None


def get_pro():
    global _PRO
    if _PRO is None:
        token = os.environ.get("TUSHARE_TOKEN")
        if not token:
            raise RuntimeError(
                "TUSHARE_TOKEN env var not set. "
                "Copy .env.example to .env, fill in the (reset) token, then re-run."
            )
        ts.set_token(token)
        _PRO = ts.pro_api()
    return _PRO


def call_with_retry(fn: Callable, *args, retries: int = 5, base_delay: float = 1.0, **kwargs):
    last_err = None
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_err = exc
            sleep = base_delay * (2 ** attempt)
            print(f"  [retry] attempt {attempt + 1}/{retries} failed: {exc!r}; sleeping {sleep:.1f}s")
            time.sleep(sleep)
    raise RuntimeError(f"call_with_retry exhausted: {last_err!r}")
