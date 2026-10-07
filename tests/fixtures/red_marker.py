"""Pytest plugin (ADR 0209, AC6.1): a strict xfail is this repo's RED marker and expects an
assertion failure only; a RED test that errors fails instead of passing as an expected failure.
"""

from __future__ import annotations

from collections.abc import Iterable

import pytest


def pytest_collection_modifyitems(items: Iterable[pytest.Item]) -> None:
    for item in items:
        for mark in list(item.iter_markers("xfail")):
            if mark.kwargs.get("strict") and "raises" not in mark.kwargs:
                item.add_marker(pytest.mark.xfail(strict=True, raises=AssertionError), append=False)
                break
