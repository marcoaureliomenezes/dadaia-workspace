"""``core/release_state.py`` never writes (v0.5.x, successor to
``test_release_events_read_only.py``).

Intent: CONTRACT — the new module is a pure parse/serialize pair over a single mutable
``RELEASE.json`` document; the ONE tri-state disk read + the CAS write both stay a
``features``/``infrastructure``-layer concern (out of ``core/``, per the file-I/O
purity ratchet, architect A9), same precedent its predecessor set. Size: SMALL — an AST
walk over one packaged module, no I/O beyond reading that module's own source.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MODULE = _REPO_ROOT / "dadaia_workspace" / "core" / "release_state.py"

_WRITE_PATH_ATTRS = frozenset({"write_text", "write_bytes", "mkdir", "unlink", "rmdir"})
_WRITE_OPEN_MODES = frozenset({"w", "a", "x", "wb", "ab", "xb", "w+", "a+", "r+"})


def _write_offenses(source: str) -> list[tuple[int, str]]:
    tree = ast.parse(source)
    offenses: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in {"open", "atomic_write"}:
            if func.id == "atomic_write":
                offenses.append((node.lineno, "atomic_write(...)"))
                continue
            mode_arg = node.args[1] if len(node.args) > 1 else None
            mode_kw = next((kw.value for kw in node.keywords if kw.arg == "mode"), None)
            for candidate in (mode_arg, mode_kw):
                if isinstance(candidate, ast.Constant) and candidate.value in _WRITE_OPEN_MODES:
                    offenses.append((node.lineno, f"open(..., {candidate.value!r})"))
        elif isinstance(func, ast.Attribute):
            if func.attr in _WRITE_PATH_ATTRS or func.attr == "atomic_write":
                offenses.append((node.lineno, f".{func.attr}(...)"))
    return offenses


def test_release_state_module_contains_no_write_call() -> None:
    """No ``open(..., "w"/"a"/...)``, ``Path.write_text``/``write_bytes``/``mkdir``, or
    ``atomic_write`` call site anywhere in ``core/release_state.py`` — it parses and
    serializes an already-supplied document; it never touches disk."""
    source = _MODULE.read_text(encoding="utf-8")
    offenses = _write_offenses(source)
    assert not offenses, (
        "core/release_state.py must never write (release-state-v1 read-only contract) "
        f"— found: {offenses}"
    )
    assert "read_text(" not in source
    assert not any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "open"
        for n in ast.walk(ast.parse(source))
    )
