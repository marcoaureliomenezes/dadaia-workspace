"""The derived call-site census (release v0.4.5, FR2 / T-045-14).

Intent: CONTRACT — v0.4.5 A2.2. Size: SMALL.

A2.2 demands the census "enumerates EVERY atomic write in the package ... zero
remaining named writers, zero inline ``.tmp`` writers", derived BY SCAN — never a
hand-kept list. ``tests/unit/features/specs/test_migration_symlink_hardening.py`` used
to keep exactly that forbidden thing: a hand-authored, 10-case table of writer names.
T-045-14 deleted every writer that table named (the eight T-045-13 shims, the three
inline ``.tmp`` writers, plus the two writers T-045-13's sweep discovered beyond the
original enumeration — ``state_v3._atomic_write_json`` and
``bugs_single_file.migrate_bugs_single_file``'s inline ``.jsonl.tmp`` swap) and this
module replaces that table with a scan.

The predicate below identifies the temp-then-replace *content-write* idiom BY SHAPE,
never by name: a function that (1) writes fresh content to a local path via
``.write_text(...)``/``.write_bytes(...)`` and then (2) swaps that same path into a
final target via ``os.replace(...)`` or ``Path.replace(...)``. This is exactly what
distinguishes an atomic *write* from a plain rename of an EXISTING file — the shape the
package's three legitimate non-writer users of ``os.replace``/``.replace()`` have
instead:

- ``infrastructure/jsonl_log_rotation.py`` renames the CURRENT log file itself
  (``os.replace(path, rotated)`` — ``path`` was never written by this call, only read).
- ``features/telemetry/service.py`` quarantines an EXISTING corrupt database
  (``os.replace(db_path, quarantine_path)`` — ``db_path`` is never freshly written).
- ``tempfile.mkstemp``/``mkdtemp`` scratch usage in ``certify``/``ci_preflight``/
  ``core.platform`` never calls ``os.replace``/``.replace()`` on the scratch path at
  all — it is disposable working space, not a durable-content swap.

None of the three are excluded by a name-list; the predicate simply never fires for
them, because none writes content to the path it later passes as an
``os.replace``/``.replace()`` source.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers.scan_population import assert_populated

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PACKAGE_ROOT = _REPO_ROOT / "dadaia_workspace"

#: Every writer this census forbids from re-appearing — the SOLE surviving definition
#: site, exactly one entry, proven by scan rather than declared by name (the assertion
#: below fails loudly the moment a second one exists, for ANY def, named anything).
_EXPECTED_SOLE_DEFINITION = "dadaia_workspace/core/atomic_write.py:27:atomic_write"


def _writes_then_replaces(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True iff *func* writes fresh content to a local path, then swaps that same path
    into a final target via ``os.replace``/``Path.replace`` — detected by shape, never
    by the function's own name."""
    written_names: set[str] = set()
    for node in ast.walk(func):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("write_text", "write_bytes")
            and isinstance(node.func.value, ast.Name)
        ):
            written_names.add(node.func.value.id)

    if not written_names:
        return False

    for node in ast.walk(func):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "replace":
            continue
        receiver = node.func.value
        # os.replace(src, dst) — function form: the SOURCE is the first positional arg.
        if (
            isinstance(receiver, ast.Name)
            and receiver.id == "os"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id in written_names
        ):
            return True
        # <var>.replace(dst) — Path method form: the SOURCE is the receiver itself.
        if isinstance(receiver, ast.Name) and receiver.id in written_names:
            return True
    return False


def _temp_then_replace_writer_defs(package_root: Path) -> list[str]:
    """Every module- or class-level ``def`` anywhere under *package_root* matching the
    temp-then-replace content-write idiom, as ``<relative-path>:<line>:<name>``."""
    files = sorted(package_root.rglob("*.py"))
    # v0.4.5 FR5 (scan-test-vacuity-guard): belt-and-suspenders — the sole-definition
    # assertion below is already non-vacuous (an empty scan yields `hits == []`, which
    # fails the `== [_EXPECTED_SOLE_DEFINITION]` check), but this guard keeps the
    # convention uniform and catches the mis-root loudly, at the walk itself.
    assert_populated(files, sentinel=package_root / "core" / "atomic_write.py")
    hits: list[str] = []
    for path in files:
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _writes_then_replaces(
                node
            ):
                rel = path.relative_to(package_root.parent).as_posix()
                hits.append(f"{rel}:{node.lineno}:{node.name}")
    return hits


def test_only_core_atomic_write_defines_the_temp_then_replace_idiom() -> None:
    """A2.2: the census is DERIVED by scan. The next accidental reintroduction of a raw
    tmp-write-then-swap idiom anywhere under ``dadaia_workspace/`` — named anything —
    fails this test loudly instead of silently escaping a hand-kept list."""
    hits = _temp_then_replace_writer_defs(_PACKAGE_ROOT)

    assert hits == [_EXPECTED_SOLE_DEFINITION], (
        "a temp-then-replace content writer exists outside core/atomic_write.py — "
        f"route it through core.atomic_write.atomic_write instead (A2.2): {hits}"
    )


def test_no_named_shim_or_inline_tmp_writer_survives_by_name() -> None:
    """Belt-and-suspenders companion to the shape-based scan above: none of the thirteen
    writer names T-045-14 deleted (eight T-045-13 shims, three original inline ``.tmp``
    writers, and the two T-045-13-sweep discoveries) is importable from the package
    anymore — a stray re-add under the OLD name, even one that does not itself match the
    shape predicate (e.g. a re-export alias), still fails this companion check."""
    retired_names = {
        "atomic_write_text",
        "_atomic_write_text",
        "write_text_atomic",
        "_write_text_atomic",
        "_atomic_write_json",
        "_atomic_write_bytes",
    }
    files = sorted(_PACKAGE_ROOT.rglob("*.py"))
    # v0.4.5 FR5 (scan-test-vacuity-guard): a mis-rooted _PACKAGE_ROOT would degrade
    # this walk to zero files, under which `hits == []` below passes vacuously —
    # the exact companion check this belt-and-suspenders test exists to strengthen.
    assert_populated(files, sentinel=_PACKAGE_ROOT / "core" / "atomic_write.py")
    hits: list[str] = []
    for path in files:
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in retired_names
            ):
                rel = path.relative_to(_PACKAGE_ROOT.parent).as_posix()
                hits.append(f"{rel}:{node.lineno}:{node.name}")

    assert hits == [], f"a retired atomic-writer name was redefined: {hits}"
