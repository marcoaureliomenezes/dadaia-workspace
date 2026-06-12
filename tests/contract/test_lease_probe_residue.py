"""Lease pid-probe residue contract (T-011-01, FR-W1-01).

The v0.1.10 pid-liveness probe must be threaded through EVERY production call site
of ``lease.acquire`` / ``lease.steal``. ``pid_probe`` is a REQUIRED keyword parameter
on those two functions (``mypy --strict`` enforces it at the type level); this contract
is the grep-level backstop: no production call site of ``lease.acquire`` or
``lease.steal`` may omit ``pid_probe=``.

A probe-less call site is exactly the lease-theft / no-GC side door this release
closes (residual R1, bug ``doctor-stale-lease-misdiagnosed-as-forgery``).

It uses ``ast`` (not a text grep) so docstrings, comments, and unrelated
``adapter.acquire`` / ``lock.try_acquire`` calls never produce false positives.
"""

from __future__ import annotations

import ast
from pathlib import Path

#: Production root scanned for lease call sites. Tests are intentionally excluded —
#: test helpers may call the lease with planted probes and are not the side-door risk.
_PRODUCTION_ROOT = "dadaia_workspace"

#: The lease module: its OWN module-level ``acquire(``/``steal(`` calls (e.g. inside
#: ``_main``) appear unqualified. Everywhere else the call must be qualified with the
#: ``lease``/``_lease`` import alias.
_LEASE_MODULE = "dadaia_workspace/features/spec_context/lease.py"

_LEASE_ALIASES = frozenset({"lease", "_lease"})
_TARGET_FUNCS = frozenset({"acquire", "steal"})


def _is_lease_call(node: ast.Call, *, in_lease_module: bool) -> str | None:
    """Return the lease func name if ``node`` is a lease.acquire/steal call, else None."""
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr in _TARGET_FUNCS:
        # Qualified call: ``lease.acquire(...)`` / ``_lease.steal(...)``.
        value = func.value
        if isinstance(value, ast.Name) and value.id in _LEASE_ALIASES:
            return func.attr
        return None
    if in_lease_module and isinstance(func, ast.Name) and func.id in _TARGET_FUNCS:
        # Bare module-level call inside lease.py itself (``acquire(...)`` in ``_main``).
        return func.id
    return None


def _probeless_sites(relpath: str, text: str) -> list[str]:
    failures: list[str] = []
    tree = ast.parse(text)
    in_lease_module = relpath == _LEASE_MODULE
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _is_lease_call(node, in_lease_module=in_lease_module) is None:
            continue
        has_probe = any(kw.arg == "pid_probe" for kw in node.keywords)
        if not has_probe:
            failures.append(f"{relpath}:{node.lineno}: probe-less lease call")
    return failures


def test_no_probeless_lease_acquire_or_steal_call_site() -> None:
    """Every production ``lease.acquire``/``lease.steal`` call threads ``pid_probe=``."""
    repo_root = Path(__file__).resolve().parents[2]
    prod_root = repo_root / _PRODUCTION_ROOT

    failures: list[str] = []
    for path in sorted(prod_root.rglob("*.py")):
        relpath = path.relative_to(repo_root).as_posix()
        text = path.read_text(encoding="utf-8")
        failures.extend(_probeless_sites(relpath, text))

    assert failures == [], "probe-less lease call site(s):\n" + "\n".join(failures)
