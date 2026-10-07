"""The census of every atomic write in the package is DERIVED by scan, never a hand-kept list:
a function that writes content to a local name (``.write_text``/``.write_bytes``) and then
swaps that same name into place (``os.replace``/``Path.replace``). Plain renames of an
existing file (log rotation, DB quarantine) never write first, so they never match.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers.scan_population import assert_populated

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_ROOT = _REPO_ROOT / "dadaia_workspace"

#: The two homes, proven by scan: the package's writer, and the stdlib ledger scripts'
#: one writer, staged beside each script (a skill script cannot import the package).
_EXPECTED_DEFINITIONS = [
    "dadaia_workspace/core/atomic_write.py:atomic_write",
    "dadaia_workspace/public/skills/dd-bug-resolution/scripts/_ledger.py:replace",
]


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
    temp-then-replace content-write idiom, as ``<relative-path>:<name>``."""
    files = sorted(package_root.rglob("*.py"))
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
                hits.append(f"{rel}:{node.name}")
    return hits


def test_only_core_atomic_write_defines_the_temp_then_replace_idiom() -> None:
    """A2.2: the census is DERIVED by scan. The next accidental reintroduction of a raw
    tmp-write-then-swap idiom anywhere under ``dadaia_workspace/`` — named anything —
    fails this test loudly instead of silently escaping a hand-kept list.
    sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts#48.6: the ledger scripts
    carry no `_replace` copy of their own; one staged source is the scripts' writer."""
    hits = _temp_then_replace_writer_defs(_PACKAGE_ROOT)

    assert hits == _EXPECTED_DEFINITIONS, (
        "a temp-then-replace content writer exists outside core/atomic_write.py — "
        f"route it through core.atomic_write.atomic_write instead (A2.2): {hits}"
    )
