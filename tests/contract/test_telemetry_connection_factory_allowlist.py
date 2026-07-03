"""Contract: every ``sqlite3.connect`` in production is factory-routed or exempt.

v0.1.52 FR3 routes every *writable* telemetry-store connection through the
pragma'd factory ``telemetry/store/schema.open_connection`` (WAL + busy_timeout),
and every store read through its read-only URI mode.  After the fix, the ONLY
``sqlite3.connect`` call sites permitted anywhere under ``dadaia_workspace/`` are:

* the factory's own internal open (``telemetry/store/schema.py``); and
* the two enumerated foreign read-only readers of the operator's ``~/.codex``
  database — ``telemetry/aggregator/runtimes.py`` and ``telemetry/reader/codex.py``
  — which open ``file:...?mode=ro`` and MUST NEVER receive the WAL-writing
  factory (WAL is a write; it would mutate the operator's Codex DB).

Any ``sqlite3.connect`` outside that allowlist (notably a bare panel or service
open) is a routing violation and fails this contract.  This is the deterministic
guard behind AC-3 (``check_same_thread=False`` gone) and AC-7(b) (a bypassing
store path is caught here).
"""

from __future__ import annotations

import ast
from pathlib import Path

# Repo root = three parents up from tests/contract/<this file>.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PKG_ROOT = _REPO_ROOT / "dadaia_workspace"

# Allowlisted call sites, relative to the repo root (POSIX form).
_FACTORY_INTERNAL = "dadaia_workspace/features/telemetry/store/schema.py"
_EXEMPT_FOREIGN_READERS = frozenset(
    {
        "dadaia_workspace/features/telemetry/aggregator/runtimes.py",
        "dadaia_workspace/features/telemetry/reader/codex.py",
    }
)
_ALLOWLIST = frozenset({_FACTORY_INTERNAL}) | _EXEMPT_FOREIGN_READERS


def _is_sqlite3_connect(node: ast.AST) -> bool:
    """True for ``sqlite3.connect(...)`` call expressions."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "connect"
        and isinstance(func.value, ast.Name)
        and func.value.id == "sqlite3"
    )


def _connect_sites() -> dict[str, list[int]]:
    """Map repo-relative POSIX path → sorted line numbers of sqlite3.connect calls."""
    sites: dict[str, list[int]] = {}
    for py_file in sorted(_PKG_ROOT.rglob("*.py")):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError) as exc:  # pragma: no cover - defensive
            raise AssertionError(f"could not parse {py_file}: {exc}") from exc
        rel = py_file.relative_to(_REPO_ROOT).as_posix()
        for node in ast.walk(tree):
            if _is_sqlite3_connect(node):
                sites.setdefault(rel, []).append(node.lineno)
    return {path: sorted(lines) for path, lines in sites.items()}


def test_no_sqlite3_connect_outside_factory_or_exempt_allowlist() -> None:
    """No production ``sqlite3.connect`` outside the factory internals or exempt list."""
    sites = _connect_sites()
    violations = {path: lines for path, lines in sites.items() if path not in _ALLOWLIST}
    assert not violations, (
        "sqlite3.connect found outside the factory/exempt allowlist — route these "
        "telemetry-store connections through schema.open_connection "
        f"(read_only=True for reads):\n{violations!r}"
    )


def test_factory_internal_site_is_present() -> None:
    """The factory's own internal open must exist (guards against silent removal)."""
    sites = _connect_sites()
    assert _FACTORY_INTERNAL in sites, (
        "the pragma'd factory schema.open_connection must own its internal sqlite3.connect."
    )


def test_exempt_foreign_readers_are_read_only_uris() -> None:
    """The exempt foreign readers open read-only URI connections (never the WAL factory)."""
    for rel in _EXEMPT_FOREIGN_READERS:
        text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "mode=ro" in text, (
            f"exempt foreign reader {rel} must open ~/.codex read-only (mode=ro); "
            "it must never receive the WAL-writing factory."
        )
