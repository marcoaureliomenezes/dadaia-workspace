"""The single CLI specs-dir resolution seam (v0.1.50 FR4).

Every resolver-driven ``dadaia`` command resolves its specs directory through
:func:`resolve_specs_dir_for_cli`, which ALWAYS threads the current process's
ancestry pid chain into the core resolver — so bind-marker attribution works from
any ephemeral harness shell. Five per-command wrappers used to hand-copy this
call and four of them omitted ``ancestry_pids`` (bug
``bugs-append-bound-session-falls-through-to-cwd-specs``): centralizing here
makes the omission structurally impossible.
"""

from __future__ import annotations

import os
from pathlib import Path

from dadaia_workspace.core.specs_resolver import resolve_specs_dir as _core_resolve_specs_dir


def current_ancestry_pids() -> frozenset[int] | None:
    """This ``dadaia`` process's nearest-first ancestry pid chain (bind attribution).

    W1-8 (v0.1.47): the persisted-bind fallback attributes a bind-epoch marker by
    ancestry-chain MEMBERSHIP. A marker written from an ephemeral harness shell
    records the bind process's chain (incl. the long-lived harness pid); this CLI
    runs under a DIFFERENT short-lived shell but shares that harness pid deeper in
    ITS chain. Any failure ⇒ ``None`` ⇒ the resolver degrades to single-getppid
    equality.
    """
    try:
        from dadaia_workspace import container

        return frozenset(container.build_ancestry_pid_chain(os.getppid()))
    except Exception:  # noqa: BLE001 — attribution is best-effort; never break resolution.
        return None


def resolve_specs_dir_for_cli(specs_dir: str | None) -> Path:
    """Resolve the target specs/ dir (explicit flag → bound context → cwd/specs)."""
    return _core_resolve_specs_dir(specs_dir, ancestry_pids=current_ancestry_pids())
