"""T-070-05 (v0.7.0 FR5): tiered timeouts, quarantine discipline, marker-set pin.

Intent: CONTRACT — v0.7.0 FR5 (test-stewardship mechanical enforcement).

The stewardship law (DADAIA.md §6 / dadaia-test-stewardship) requires every test to
carry a size tier with an enforced timeout, a ``quarantine`` lane that is impossible
to use without a registered bug, and a marker set that cannot drift between its
surfaces. These contracts are executed-path where possible: the tier-timeout checks
assert the marker THIS very suite's conftest applied to them.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Tier -> timeout mapping, proven on the executed path (this test's own item)
# ---------------------------------------------------------------------------


def test_contract_tier_carries_30s_timeout(request: pytest.FixtureRequest) -> None:
    marker = request.node.get_closest_marker("timeout")
    assert marker is not None, "conftest applied no timeout marker to a contract-tier test"
    assert marker.args and marker.args[0] == 30


@pytest.mark.timeout(45)
def test_explicit_timeout_marker_is_never_overridden(request: pytest.FixtureRequest) -> None:
    marker = request.node.get_closest_marker("timeout")
    assert marker is not None
    assert marker.args and marker.args[0] == 45, (
        "the tier default clobbered an explicit @pytest.mark.timeout — the default may "
        "only fill absence"
    )


def test_tier_timeout_table_covers_all_four_layers() -> None:
    from tests.conftest import _TIER_TIMEOUTS

    assert _TIER_TIMEOUTS == {"unit": 10, "contract": 30, "integration": 60, "e2e": 120}


# ---------------------------------------------------------------------------
# Quarantine discipline: no bug id -> collection refuses, actionably
# ---------------------------------------------------------------------------


class _FakeItem:
    """Minimal stand-in carrying only what the validator reads."""

    def __init__(self, marker_kwargs: dict[str, object] | None, name: str = "test_x") -> None:
        self._kwargs = marker_kwargs
        self.name = name
        self.nodeid = f"tests/unit/test_fake.py::{name}"

    def get_closest_marker(self, name: str) -> object | None:
        if self._kwargs is None:
            return None

        class _M:
            kwargs = self._kwargs
            args: tuple[object, ...] = ()

        return _M() if name == "quarantine" else None


def test_quarantine_without_bug_id_refuses_collection() -> None:
    from tests.conftest import _validate_quarantine_markers

    with pytest.raises(pytest.UsageError) as excinfo:
        _validate_quarantine_markers([_FakeItem({})])  # type: ignore[list-item]
    message = str(excinfo.value)
    assert "bug" in message
    assert "quarantine" in message


def test_quarantine_with_bug_id_is_accepted() -> None:
    from tests.conftest import _validate_quarantine_markers

    _validate_quarantine_markers([_FakeItem({"bug": "some-bug-slug"})])  # type: ignore[list-item]


# ---------------------------------------------------------------------------
# Marker-set pin: pyproject <-> conftest cannot drift; flaky/quarantine exist
# ---------------------------------------------------------------------------


def test_marker_set_is_pinned_across_pyproject_and_conftest() -> None:
    from tests.conftest import _KNOWN_MARKERS

    pyproject = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = re.search(r"markers\s*=\s*\[(.*?)\]", pyproject, re.S)
    assert block is not None, "pyproject.toml declares no pytest markers block"
    declared = set(re.findall(r'"([a-z0-9]+):', block.group(1)))
    assert declared == set(_KNOWN_MARKERS), (
        f"marker drift: pyproject={sorted(declared)} conftest={sorted(_KNOWN_MARKERS)}"
    )
    assert {"flaky", "quarantine"} <= declared


# ---------------------------------------------------------------------------
# Gating invocation: quarantine excluded; the dead performance ignore is gone
# ---------------------------------------------------------------------------


def test_preflight_pytest_excludes_quarantine_and_drops_dead_ignore() -> None:
    from dadaia_workspace.features.ci_preflight.service import _pytest_check

    check = _pytest_check(quick=True, python_executable=None, dadaia_bin=None)
    command = tuple(check.argv)
    assert "--ignore=tests/performance" not in command, (
        "dead ignore: tests/performance no longer exists"
    )
    joined = " ".join(command)
    assert "not quarantine" in joined, "the gating invocation must exclude quarantined tests"


@pytest.mark.timeout(120)
def test_naked_quarantine_refusal_is_actionable_serial_and_xdist() -> None:
    """T-070-09 finding 2: the refusal must reach the operator readably in BOTH modes.

    Real collection, real subprocesses: a probe file under tests/tmp/ carrying a naked
    quarantine marker must refuse collection with the actionable message on stderr —
    serial AND under -n 2 (where the UsageError alone would surface as an opaque
    xdist INTERNALERROR; the conftest prints the actionable line first).

    Explicit timeout (S-09/S-10): two full pytest subprocess boots, ~8 s each solo.
    """
    import os
    import subprocess
    import sys as _sys

    probe = _REPO_ROOT / "tests" / "tmp" / f"_quarantine_probe_{os.getpid()}.py"
    probe.write_text(
        "import pytest\n\n\n"
        "@pytest.mark.quarantine\n"
        "def test_naked_quarantine() -> None:\n"
        "    pass\n",
        encoding="utf-8",
    )
    try:
        for extra in ((), ("-n", "2")):
            result = subprocess.run(
                [
                    _sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    str(probe),
                    *extra,
                ],
                capture_output=True,
                text=True,
                cwd=_REPO_ROOT,
                timeout=90,
            )
            combined = result.stdout + result.stderr
            assert result.returncode != 0, (
                f"naked quarantine collected clean ({extra}):\n{combined}"
            )
            assert "requires a registered bug id" in combined, (
                f"actionable message missing in mode {extra}:\n{combined[-2000:]}"
            )
    finally:
        probe.unlink(missing_ok=True)
