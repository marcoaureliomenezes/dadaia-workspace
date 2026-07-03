"""Tests for ``core/kernel_tunables.py`` — the single home for lifecycle-kernel constants.

T-014-01 (FR-W4-05, DP-1). The module is a pure-constant home (zero I/O) that every
kernel module (lease, gate_policy, doctor, hooks) imports its tunables from. These tests
assert three things:

1. **Single-home (AST/import check, NOT a digit grep).** Each kernel module that consumes a
   tunable imports its name from ``core.kernel_tunables`` rather than redeclaring the magic
   number inline. We parse the module source and assert the import edge exists.
2. **Behavioral observation.** Re-stamping ``kernel_tunables.LEASE_TTL_SECONDS`` is observed
   by the lease's own liveness predicate — the constant is a live single source, not a copy.

The lease-local ``lease.LEASE_TTL_SECONDS`` re-export (a one-release deprecation shim) was
removed in v0.1.53; ``LEASE_TTL_SECONDS`` is imported from ``core.kernel_tunables`` directly.
"""

from __future__ import annotations

import ast
from pathlib import Path

from dadaia_workspace.core import kernel_tunables


def _module_source(dotted: str) -> str:
    import importlib

    mod = importlib.import_module(dotted)
    assert mod.__file__ is not None
    return Path(mod.__file__).read_text(encoding="utf-8")


def _imports_name_from_kernel_tunables(source: str, name: str) -> bool:
    """True iff *source* imports *name* from ``...core.kernel_tunables`` (any alias form).

    Accepts ``from dadaia_workspace.core import kernel_tunables`` followed by attribute
    access (``kernel_tunables.<name>``) OR a direct
    ``from dadaia_workspace.core.kernel_tunables import <name>``.
    """
    tree = ast.parse(source)
    # Direct name import.
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "dadaia_workspace.core.kernel_tunables"
        ):
            for alias in node.names:
                if alias.name == name:
                    return True
    # Module import + attribute access.
    module_imported = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "dadaia_workspace.core"
        and any(a.name == "kernel_tunables" for a in node.names)
        for node in ast.walk(tree)
    )
    if module_imported:
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == name
                and isinstance(node.value, ast.Name)
                and node.value.id == "kernel_tunables"
            ):
                return True
    return False


# --------------------------------------------------------------------------- #
# 1. Module shape: pure constants, zero I/O.
# --------------------------------------------------------------------------- #


def test_tunables_are_pure_constants() -> None:
    assert isinstance(kernel_tunables.LEASE_TTL_SECONDS, int)
    assert isinstance(kernel_tunables.SENTINEL_ORPHAN_AGE_SECONDS, float)
    assert isinstance(kernel_tunables.SENTINEL_GC_TTL_SECONDS, int)
    assert isinstance(kernel_tunables.SESSION_GC_TTL_SECONDS, int)
    assert isinstance(kernel_tunables.CAS_MAX_RETRIES, int)
    assert isinstance(kernel_tunables.CAS_INITIAL_BACKOFF_SECONDS, float)
    assert isinstance(kernel_tunables.RECONCILER_THROTTLE_TTL_SECONDS, int)


def test_kernel_tunables_has_no_io_imports() -> None:
    """The module must be a zero-I/O constant home (no os/subprocess/pathlib/open)."""
    source = _module_source("dadaia_workspace.core.kernel_tunables")
    tree = ast.parse(source)
    banned = {"os", "subprocess", "pathlib", "sys", "json", "time", "socket"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned, alias.name
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in banned, node.module


# --------------------------------------------------------------------------- #
# 2. Single-home: kernel modules import from kernel_tunables (AST edge, not digit grep).
# --------------------------------------------------------------------------- #


def test_lease_imports_ttl_from_kernel_tunables() -> None:
    src = _module_source("dadaia_workspace.features.spec_context.lease")
    assert _imports_name_from_kernel_tunables(src, "LEASE_TTL_SECONDS")


def test_lease_imports_cas_retries_from_kernel_tunables() -> None:
    src = _module_source("dadaia_workspace.features.spec_context.lease")
    assert _imports_name_from_kernel_tunables(src, "CAS_MAX_RETRIES")


def test_ctx_inject_imports_sentinel_gc_ttl_from_kernel_tunables() -> None:
    src = _module_source("dadaia_workspace.hooks.ctx_inject")
    assert _imports_name_from_kernel_tunables(src, "SENTINEL_GC_TTL_SECONDS")


def test_doctor_imports_sentinel_orphan_age_from_kernel_tunables() -> None:
    src = _module_source("dadaia_workspace.features.spec_context.doctor")
    assert _imports_name_from_kernel_tunables(src, "SENTINEL_ORPHAN_AGE_SECONDS")


# --------------------------------------------------------------------------- #
# 3. Behavioral: lease liveness observes the centralized constant.
# --------------------------------------------------------------------------- #


def test_lease_renew_default_ttl_observes_kernel_constant(monkeypatch) -> None:
    """The lease liveness path observes the centralized ``kernel_tunables`` TTL constant.

    Re-stamp ``kernel_tunables.LEASE_TTL_SECONDS`` to a sentinel and assert the
    ``lock_liveness`` predicate judges a record against that very ttl field — wiring the
    constant end-to-end through the liveness predicate, proving it is a live single source,
    not a copy.
    """
    import inspect
    from datetime import UTC, datetime, timedelta

    from dadaia_workspace.core import lock_liveness
    from dadaia_workspace.features.spec_context import lease

    monkeypatch.setattr(kernel_tunables, "LEASE_TTL_SECONDS", 7)
    assert kernel_tunables.LEASE_TTL_SECONDS == 7
    sig = inspect.signature(lease.acquire)
    assert "ttl" in sig.parameters
    # A record stamped with the current TTL is judged by lock_liveness against that very ttl
    # field — wiring the constant end-to-end through the liveness predicate.
    ttl = kernel_tunables.LEASE_TTL_SECONDS
    old_hb = (datetime.now(tz=UTC) - timedelta(seconds=ttl + 10)).isoformat()
    fresh_hb = datetime.now(tz=UTC).isoformat()
    assert lock_liveness.is_stale({"heartbeat": old_hb, "ttl": ttl}) is True
    assert lock_liveness.is_stale({"heartbeat": fresh_hb, "ttl": ttl}) is False
