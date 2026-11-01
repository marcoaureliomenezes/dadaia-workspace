"""``-p scripts.covdata``: the ONE decider of where coverage data lands — a temp dir
outside the checkout, removed when pytest exits. An xdist worker inherits the controller's,
which combines the workers' data before removing it."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Generator

import pytest


@pytest.hookimpl(wrapper=True)  # runs before pytest-cov's tryfirst hook, which starts coverage
def pytest_load_initial_conftests(early_config: pytest.Config) -> Generator[None]:
    if "COVERAGE_FILE" not in os.environ:
        tmp = tempfile.mkdtemp(prefix="dadaia-cov-")
        early_config.add_cleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        os.environ["COVERAGE_FILE"] = os.path.join(tmp, ".coverage")
    return (yield)
