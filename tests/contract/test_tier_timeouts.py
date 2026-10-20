"""An explicit `timeout` marker only raises a test's ceiling: it bypasses the platform
calibration in `tests/conftest.py`, so one below the medium tier kills a slower Windows
worker as an unattributable crash."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.conftest import tier_timeout_seconds

_TESTS = Path(__file__).resolve().parents[1]


def _explicit_timeouts() -> list[tuple[str, int, object]]:
    found = []
    for path in sorted(_TESTS.rglob("test_*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and ast.unparse(node.func) == "pytest.mark.timeout":
                found.append(
                    (
                        path.relative_to(_TESTS).as_posix(),
                        node.lineno,
                        ast.literal_eval(node.args[0]),
                    )
                )
    return found


def test_no_explicit_timeout_undercuts_the_medium_tier() -> None:
    floor = tier_timeout_seconds("medium")

    assert [hit for hit in _explicit_timeouts() if hit[2] < floor] == []
