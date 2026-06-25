"""Anti-slop self-governance: directory-aware slop metric (WS-6).

The workspace's pre-existing hygiene metric (``LifecycleHygieneService``) is
directory-BLIND — it only matches ``path.is_file()``, so multi-GB directory trees
(stray venvs, caches) hide from every count. This package adds a read-only,
directory-aware *metric* (the measurement, not the sweep): a directory tree counts
as ONE entry with its recursive byte size. The canonical root manifest derives from
``hooks/root_whitelist._WHITELIST`` so the metric reads the same source the gate
enforces (D4).
"""

from __future__ import annotations

from dadaia_workspace.features.lifecycle.antislop.slop_scan import (
    SlopEntry,
    SlopEntryKind,
    SlopReport,
    canonical_root_manifest,
    slop_scan,
)

__all__ = [
    "SlopEntry",
    "SlopEntryKind",
    "SlopReport",
    "canonical_root_manifest",
    "slop_scan",
]
