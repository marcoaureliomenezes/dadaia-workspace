"""``core/release_events.py`` never writes (v0.5.0 FR4 fold-3, T-050-11).

Intent: CONTRACT — SPEC v0.5.0 FR4 ("A contract test asserts core/release_events.py
contains no write call"). Size: SMALL — an AST walk over one packaged module, no I/O
beyond reading that module's own source.

The fold reads and folds; it never writes (milestone/phase records are appended
elsewhere, by agents with file tools, because RELEASE.jsonl is append-only). This
mirrors the AST technique of ``tests/contract/test_core_file_io_purity.py`` but is
narrower: it flags exactly the write-shaped calls a fold module must never contain,
regardless of the general core file-I/O ratchet (this module additionally does ZERO
file I/O at all — read or write — precisely so it never needs to join that ratchet's
authorized set, which would in turn require reopening specs/memory/architecture.md,
MEMORY and out of this task's write set).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MODULE = _REPO_ROOT / "dadaia_workspace" / "core" / "release_events.py"

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
            # open(...) with a write-shaped mode, or any call to an `atomic_write` name.
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


def test_release_events_module_contains_no_write_call() -> None:
    """No ``open(..., "w"/"a"/...)``, ``Path.write_text``/``write_bytes``/``mkdir``, or
    ``atomic_write`` call site anywhere in ``core/release_events.py`` — the fold reads
    and folds an already-supplied event stream; it never touches disk at all."""
    source = _MODULE.read_text(encoding="utf-8")
    offenses = _write_offenses(source)
    assert not offenses, (
        "core/release_events.py must never write (SPEC v0.5.0 FR4, fold-3 read-only "
        f"contract) — found: {offenses}"
    )
    # Read-only means no file I/O at all in this module (see module docstring): a
    # `read_text`/`open` call for reading would also be out of place here, since every
    # caller supplies its own tri-state disk read (this is what keeps the module out of
    # the core file-I/O purity ratchet's authorized set).
    assert "read_text(" not in source
    assert not any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "open"
        for n in ast.walk(ast.parse(source))
    )
