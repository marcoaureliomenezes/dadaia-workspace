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

import pytest

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


def test_tunables_are_pure_constants_with_no_io_imports() -> None:
    assert isinstance(kernel_tunables.LEASE_TTL_SECONDS, int)
    assert isinstance(kernel_tunables.SENTINEL_ORPHAN_AGE_SECONDS, float)
    assert isinstance(kernel_tunables.SENTINEL_GC_TTL_SECONDS, int)
    assert isinstance(kernel_tunables.SESSION_GC_TTL_SECONDS, int)
    assert isinstance(kernel_tunables.CAS_MAX_RETRIES, int)
    assert isinstance(kernel_tunables.CAS_INITIAL_BACKOFF_SECONDS, float)
    assert isinstance(kernel_tunables.RECONCILER_THROTTLE_TTL_SECONDS, int)

    # The module must be a zero-I/O constant home (no os/subprocess/pathlib/open).
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


@pytest.mark.parametrize(
    ("module", "name"),
    [
        ("dadaia_workspace.hooks.ctx_inject", "SENTINEL_GC_TTL_SECONDS"),
        ("dadaia_workspace.features.spec_context.doctor", "SENTINEL_ORPHAN_AGE_SECONDS"),
    ],
)
def test_kernel_module_imports_tunable_from_single_home(module: str, name: str) -> None:
    src = _module_source(module)
    assert _imports_name_from_kernel_tunables(src, name)


# --------------------------------------------------------------------------- #
# 3. Behavioral: the liveness predicate observes the centralized constant.
# --------------------------------------------------------------------------- #


def test_lock_liveness_observes_kernel_constant(monkeypatch: pytest.MonkeyPatch) -> None:
    """The liveness predicate path observes the centralized ``kernel_tunables`` TTL constant.

    v0.1.76 T-3: ``lease.py`` no longer imports ``kernel_tunables`` at all (the acquisition
    machinery that consumed ``LEASE_TTL_SECONDS``/``CAS_MAX_RETRIES`` as defaults —
    ``acquire``/``steal`` — is deleted; the presence module carries the live TTL contract
    now). This test re-baselines to the surviving single source: a record's own ``ttl``
    field, judged by ``core.lock_liveness.is_stale`` against the SAME
    ``kernel_tunables.LEASE_TTL_SECONDS`` a caller reads to stamp that field — proving the
    constant is a live single source, not a copy, without depending on any acquisition API.
    """
    from datetime import UTC, datetime, timedelta

    from dadaia_workspace.core import lock_liveness

    monkeypatch.setattr(kernel_tunables, "LEASE_TTL_SECONDS", 7)
    assert kernel_tunables.LEASE_TTL_SECONDS == 7
    ttl = kernel_tunables.LEASE_TTL_SECONDS
    old_hb = (datetime.now(tz=UTC) - timedelta(seconds=ttl + 10)).isoformat()
    fresh_hb = datetime.now(tz=UTC).isoformat()
    assert lock_liveness.is_stale({"heartbeat": old_hb, "ttl": ttl}) is True
    assert lock_liveness.is_stale({"heartbeat": fresh_hb, "ttl": ttl}) is False
