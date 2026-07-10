"""Contract: the PI Ring-1 extension pins the entry-harness signal (v0.1.64 T-64-21).

FR4/AC-5, grep-level (assertable without a TS runtime): the canonical source of
``dadaia-sdd-gate.ts`` contains the GUARDED ``DADAIA_ENTRY_HARNESS = "pi"`` export:
set-only-when-unset, so an operator pin always wins.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL = _REPO_ROOT / "dadaia_workspace" / "public" / "pi" / "extensions" / "dadaia-sdd-gate.ts"

#: The guarded export: the truthiness guard on the SAME var it then sets to "pi".
_GUARDED_EXPORT = re.compile(
    r"if\s*\(\s*!process\.env\.DADAIA_ENTRY_HARNESS\s*\)\s*\{\s*"
    r'process\.env\.DADAIA_ENTRY_HARNESS\s*=\s*"pi"\s*;',
)


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
