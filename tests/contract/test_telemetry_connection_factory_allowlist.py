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

from tests.helpers.scan_population import assert_populated

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
    py_files = sorted(_PKG_ROOT.rglob("*.py"))
    # v0.4.5 FR5 (scan-test-vacuity-guard): a mis-rooted _PKG_ROOT would degrade this
    # walk to zero files, under which `assert not violations` below passes vacuously.
    assert_populated(py_files, sentinel=_PKG_ROOT / _FACTORY_INTERNAL.split("/", 1)[1])
    sites: dict[str, list[int]] = {}
    for py_file in py_files:
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError) as exc:  # pragma: no cover - defensive
            raise AssertionError(f"could not parse {py_file}: {exc}") from exc
        rel = py_file.relative_to(_REPO_ROOT).as_posix()
        for node in ast.walk(tree):
            if _is_sqlite3_connect(node):
                sites.setdefault(rel, []).append(node.lineno)
    return {path: sorted(lines) for path, lines in sites.items()}


def test_sqlite3_connect_routing_allowlist_and_readonly_exemption() -> None:
    """No production ``sqlite3.connect`` outside the factory internals or exempt list;
    the factory's own internal open exists (guards against silent removal); and the
    exempt foreign readers open read-only URI connections (never the WAL factory)."""
    sites = _connect_sites()
    violations = {path: lines for path, lines in sites.items() if path not in _ALLOWLIST}
    assert not violations, (
        "sqlite3.connect found outside the factory/exempt allowlist — route these "
        "telemetry-store connections through schema.open_connection "
        f"(read_only=True for reads):\n{violations!r}"
    )
    assert _FACTORY_INTERNAL in sites, (
        "the pragma'd factory schema.open_connection must own its internal sqlite3.connect."
    )
    for rel in _EXEMPT_FOREIGN_READERS:
        text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "mode=ro" in text, (
            f"exempt foreign reader {rel} must open ~/.codex read-only (mode=ro); "
            "it must never receive the WAL-writing factory."
        )
