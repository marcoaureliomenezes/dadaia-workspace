"""Contract: the PI Ring-1 extension pins the entry-harness signal (v0.1.64 T-64-21).

FR4/AC-5, grep-level (assertable without a TS runtime): the canonical source of
``dadaia-sdd-gate.ts`` — and, when present, its staged copy under
``<workspace>/.dadaia/agentic/pi/extensions/`` (fail-soft: absent in a bare checkout,
propagated at W4 via ``public stage/install``) — contains the GUARDED
``DADAIA_ENTRY_HARNESS = "pi"`` export: set-only-when-unset, so an operator pin always
wins, plus the ARCH64-2 security-posture documentation in the header.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL = _REPO_ROOT / "dadaia_workspace" / "public" / "pi" / "extensions" / "dadaia-sdd-gate.ts"

#: The guarded export: the truthiness guard on the SAME var it then sets to "pi".
_GUARDED_EXPORT = re.compile(
    r"if\s*\(\s*!process\.env\.DADAIA_ENTRY_HARNESS\s*\)\s*\{\s*"
    r'process\.env\.DADAIA_ENTRY_HARNESS\s*=\s*"pi"\s*;',
)


def _staged_copy() -> Path | None:
    """The staged copy under the enclosing workspace's ``.dadaia/agentic``, if any."""
    for ancestor in _REPO_ROOT.parents:
        candidate = ancestor / ".dadaia" / "agentic" / "pi" / "extensions" / "dadaia-sdd-gate.ts"
        if candidate.is_file():
            return candidate
        if (ancestor / ".dadaia").is_dir():
            return None  # workspace root found but no staged copy — fail-soft
    return None


def test_canonical_source_contains_guarded_entry_pin() -> None:
    source = _CANONICAL.read_text(encoding="utf-8")
    assert _GUARDED_EXPORT.search(source), (
        "dadaia-sdd-gate.ts must pin DADAIA_ENTRY_HARNESS='pi' guarded set-only-when-unset "
        "(v0.1.64 FR4)."
    )
    # An UNGUARDED assignment (outside the guard) would let the extension clobber an
    # operator pin — count assignments and require exactly the one inside the guard.
    assignments = re.findall(r'process\.env\.DADAIA_ENTRY_HARNESS\s*=\s*"', source)
    assert len(assignments) == 1, "exactly one (guarded) DADAIA_ENTRY_HARNESS assignment"


def test_canonical_header_documents_arch64_2_posture() -> None:
    source = _CANONICAL.read_text(encoding="utf-8")
    for needle in (
        "SESSION-WIDE",
        "CREDIT-AFFECTING",
        "set-only-when-unset",
        "loud echo",
        "NEVER derived from",  # telemetry
    ):
        assert needle in source, f"ARCH64-2 posture text missing from header: {needle!r}"


def test_staged_copy_when_present_contains_guarded_entry_pin() -> None:
    staged = _staged_copy()
    if staged is None:
        pytest.skip("no staged copy (bare checkout) — fail-soft per T-64-21")
    source = staged.read_text(encoding="utf-8")
    if "DADAIA_ENTRY_HARNESS" not in source:
        # Pre-W4 window: the workspace's staged copy predates this edit; propagation
        # (`dadaia public stage/install`) is T-64-40's job. Fail-soft, never mask an
        # UNGUARDED assignment (checked below when the var IS present).
        pytest.skip("staged copy predates the FR4 pin — propagated at W4 (T-64-40)")
    assert _GUARDED_EXPORT.search(source), (
        f"staged copy {staged} carries DADAIA_ENTRY_HARNESS without the set-only-when-"
        "unset guard — re-stage from canonical (`dadaia public stage`)."
    )
