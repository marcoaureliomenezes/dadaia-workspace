"""Quarantine of known-legacy ``.dadaia/`` top-level subdirs (never delete).

Bug ``reconcile-legacy-dadaia-dirs-unmigrated`` (consumer validation, 2026-07-15): a
long-lived consumer workspace upgraded across versions can carry ``.dadaia/bugs`` and
``.dadaia/src`` — created by pre-0.2.x flows (portability pipeline era). The ROOT-4
doctor invariant correctly rejects them as non-canonical, but nothing migrated them, so
``dadaia reconcile --expect-version`` could never converge such a workspace.

This module is the migration half of that contract: known legacy subdirs are MOVED
(never deleted — never-delete law) into a timestamp-free quarantine under
``.dadaia/tmp/legacy-quarantine/<run-id>/``, with a manifest recording what moved and
why, so the operator can inspect or restore the content.
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

#: ``.dadaia/`` top-level subdirs known to be legacy leftovers of earlier versions.
#: Only names on this list are ever quarantined — unknown dirs keep failing ROOT-4
#: loudly (that is the invariant working, and operator-created dirs are never touched
#: implicitly).
LEGACY_DADAIA_SUBDIRS: frozenset[str] = frozenset({"bugs", "src"})


def quarantine_legacy_dadaia_dirs(workspace_root: Path) -> list[str]:
    """Move known-legacy ``.dadaia/`` subdirs into ``.dadaia/tmp/legacy-quarantine/``.

    Returns the sorted list of subdir names that were quarantined (empty when the
    workspace is already clean — the call is idempotent). Content is preserved
    byte-for-byte under ``.dadaia/tmp/legacy-quarantine/<run-id>/<name>/`` together
    with a ``manifest.json`` describing the move.
    """
    dadaia_dir = workspace_root / ".dadaia"
    present = sorted(
        name
        for name in LEGACY_DADAIA_SUBDIRS
        if (dadaia_dir / name).is_dir() and not (dadaia_dir / name).is_symlink()
    )
    if not present:
        return []

    quarantine_root = dadaia_dir / "tmp" / "legacy-quarantine" / f"run-{uuid.uuid4().hex}"
    quarantine_root.mkdir(parents=True, exist_ok=False)
    moved: list[str] = []
    for name in present:
        shutil.move(str(dadaia_dir / name), str(quarantine_root / name))
        moved.append(name)

    manifest = {
        "schema": "legacy-dadaia-dirs-quarantine-v1",
        "moved": moved,
        "reason": (
            "Known-legacy .dadaia top-level subdirs are non-canonical (ROOT-4) and are "
            "quarantined by reconcile/migrate instead of blocking convergence. Content "
            "is preserved verbatim; inspect and restore/delete deliberately."
        ),
        "bug": "reconcile-legacy-dadaia-dirs-unmigrated",
    }
    (quarantine_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return moved
