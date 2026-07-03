"""Core file-I/O purity AST ratchet (release v0.1.54, FR7 / T-54-12).

`architecture.md` names exactly four `core/` modules as *authorized* file-I/O exceptions —
``specs_backup``, ``specs_version``, ``specs_resolver``, ``workspace_resolver`` — pending
the (now-consumed) ``import-boundary-enforcement`` backlog. The two import-linter contracts
``core-no-upper-layers`` and ``core-no-os-primitives`` are KEPT and unchanged; neither
catches *file I/O* (they guard upward imports and OS-primitive modules, not calls to
``open`` / ``pathlib.Path`` write helpers). So the file-I/O purity of ``core/`` was, until
now, undecided and unenforced.

This contract is the disposition (architect A9: **GUARD, not relocation**). An AST-based
walker over ``dadaia_workspace/core/**/*.py`` flags any file-I/O call site — ``open(...)``,
``Path.read_text`` / ``write_text`` / ``mkdir`` / ``exists`` / ``glob`` / ``iterdir`` /
``rglob``, and ``shutil.copy*`` / ``copytree`` / ``move`` — in any core module OUTSIDE the
authorized set. It is a ratchet: new file I/O may only enter ``core/`` by being added to
the authorized set on purpose (with the architecture rationale), never by accident.

Honesty of the walker (why AST, not grep):

* It matches both the attribute form (``from pathlib import Path; p.read_text()`` — the
  attribute *name* is the signal) and the builtin ``open(...)`` (a bare ``Name`` call).
* It inspects only ``ast.Call`` nodes, so non-call references such as ``d.get("open")`` or
  ``d["open"]`` — where ``open`` is a *string*, not an invoked builtin — never false-fire.
* ``shutil`` copies are tied to a ``shutil`` receiver so a benign ``some_list.copy()`` or a
  ``queue.move()`` on an unrelated object does not trip the guard.

``core/platform.py`` is intentionally NOT in the authorized set and is NOT flagged: its
``sys.platform`` usage is attribute *access* (not a file-I/O call), covered by the separate
``sys``-platform exception note (the ``core-no-os-primitives`` contract permits the
``platform`` seam's ``sys`` read) — it does no file I/O, so this guard has nothing to say
about it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORE_DIR = _REPO_ROOT / "dadaia_workspace" / "core"

# Modules whose file I/O is architecture-authorized (specs_backup migrates consumer trees;
# specs_version rewrites the pattern-version file; specs_resolver + workspace_resolver walk
# the filesystem). architecture.md pins this exact set.
_AUTHORIZED_STEMS: frozenset[str] = frozenset(
    {"specs_backup", "specs_version", "specs_resolver", "workspace_resolver"}
)

# pathlib.Path (and os.PathLike) write/read/traversal helpers flagged by attribute name.
_PATH_IO_ATTRS: frozenset[str] = frozenset(
    {"read_text", "write_text", "mkdir", "exists", "glob", "iterdir", "rglob"}
)


def _core_modules() -> list[Path]:
    """Every ``*.py`` under ``core/`` (recursively), excluding cache artifacts."""
    return sorted(p for p in _CORE_DIR.rglob("*.py") if "__pycache__" not in p.parts)


def _is_shutil_copy_or_move(func: ast.Attribute) -> bool:
    """True for ``shutil.copy*`` / ``shutil.copytree`` / ``shutil.move`` attribute calls."""
    receiver = func.value
    if not (isinstance(receiver, ast.Name) and receiver.id == "shutil"):
        return False
    return func.attr.startswith("copy") or func.attr == "move"


def _file_io_offenses(source: str) -> list[tuple[int, str]]:
    """Return ``(lineno, description)`` for each file-I/O call site in *source*.

    Only ``ast.Call`` nodes are considered, so string literals like ``d.get("open")`` are
    never mistaken for a call to the ``open`` builtin.
    """
    tree = ast.parse(source)
    offenses: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Builtin open(...) — a bare Name call.
        if isinstance(func, ast.Name) and func.id == "open":
            offenses.append((node.lineno, "open(...)"))
            continue
        if isinstance(func, ast.Attribute):
            if func.attr in _PATH_IO_ATTRS:
                offenses.append((node.lineno, f".{func.attr}(...)"))
            elif _is_shutil_copy_or_move(func):
                offenses.append((node.lineno, f"shutil.{func.attr}(...)"))
    return offenses


def test_core_modules_outside_authorized_set_do_no_file_io() -> None:
    """No unauthorized ``core/`` module performs file I/O (the ratchet is GREEN)."""
    violations: list[str] = []
    for module in _core_modules():
        if module.stem in _AUTHORIZED_STEMS:
            continue
        for lineno, description in _file_io_offenses(module.read_text(encoding="utf-8")):
            rel = module.relative_to(_REPO_ROOT)
            violations.append(f"{rel}:{lineno} {description}")
    assert not violations, (
        "core/ file-I/O purity violated — the following core modules perform file I/O but "
        "are not in the authorized set "
        f"{sorted(_AUTHORIZED_STEMS)}:\n" + "\n".join(violations) + "\n\n"
        "core/ file I/O is a ratchet (architect A9). If a new core module genuinely needs "
        "file I/O, add its stem to _AUTHORIZED_STEMS here AND record the architecture "
        "rationale in specs/memory/architecture.md — never let it in by accident."
    )


def test_authorized_set_is_grounded_in_reality() -> None:
    """Every authorized stem must name a real ``core/`` module (no stale exception).

    A stem that no longer maps to a file would silently widen the exception surface, so pin
    the authorized set to the tree: if an authorized module is relocated out of ``core/``
    (R7 work), this fails and forces the set to shrink in the same change.
    """
    present = {m.stem for m in _core_modules()}
    stale = sorted(_AUTHORIZED_STEMS - present)
    assert not stale, (
        f"authorized core file-I/O stems no longer present under core/: {stale}. "
        "Remove them from _AUTHORIZED_STEMS (ratchet down)."
    )
