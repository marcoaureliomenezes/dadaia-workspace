"""State-file migration: spec_contexts.json v2 -> v3 (FR15, v0.4.4).

Purely additive: v3 adds an ordered ``associated_repos`` collection (slug + url each)
next to the unique main repo. Unlike the v1 -> v2 hop (a breaking state-string rename,
``state_v2.py``), this hop changes no existing semantics — a v2 file with zero
associated repos already behaves identically to a v3 file with zero associated repos
(``JsonContextStore`` tolerates both on read; see its module docstring). This module is
the formal, backup-first, idempotent upgrade that stamps a v2 file explicitly to v3.

Migration is idempotent once ``schema_version == "3"`` (no-op, no write, no new backup).
On unknown schema versions it raises ValueError.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

_BACKUP_NAME = "spec_contexts.v2.bak.json"


@dataclass
class MigrationPlan:
    """Describes what the v2 -> v3 migration will do — produced in dry-run mode."""

    schema_version_before: str
    contexts_to_migrate: list[dict] = field(default_factory=list)  # type: ignore[type-arg]
    already_v3: bool = False
    backup_path: str | None = None


def _detect_schema_version(data: dict) -> str:  # type: ignore[type-arg]
    """Return the schema version string from the data dict, defaulting to "2".

    A v2 file may carry an explicit ``schema_version: "2"`` or (for the oldest v2
    writers) no key at all — both mean "not yet migrated to v3" for this hop.
    """
    ver = data.get("schema_version") or data.get("version")
    return "2" if ver is None else str(ver)


def plan_migration(states_dir: Path) -> MigrationPlan:
    """Read spec_contexts.json and compute the v2 -> v3 migration plan without writing."""
    ctx_file = states_dir / "spec_contexts.json"

    if not ctx_file.exists():
        return MigrationPlan(schema_version_before="3", already_v3=True)

    raw = json.loads(ctx_file.read_text(encoding="utf-8"))
    schema_ver = _detect_schema_version(raw)

    if schema_ver == "3":
        return MigrationPlan(schema_version_before="3", already_v3=True)

    if schema_ver != "2":
        raise ValueError(
            f"Unknown schema_version '{schema_ver}' in spec_contexts.json for the v3 "
            "migration. Manual intervention required."
        )

    contexts_to_migrate = [
        {
            "name": ctx.get("name"),
            "had_associated_repos": "associated_repos" in ctx,
        }
        for ctx in raw.get("contexts", [])
    ]

    return MigrationPlan(
        schema_version_before="2",
        contexts_to_migrate=contexts_to_migrate,
        already_v3=False,
        backup_path=str(states_dir / _BACKUP_NAME),
    )


def execute_migration(states_dir: Path) -> None:
    """Execute the v2 -> v3 migration atomically, backup-first.

    Actions (in spec order):
    1.  Detect schema_version. No file -> nothing to do.
    2.  Already "3" -> idempotent no-op: no write, no backup.
    3.  Unknown version (not "2"/"3"/missing) -> raise ValueError.
    4.  Backup: copy the v2 file verbatim to ``spec_contexts.v2.bak.json`` *before*
        any mutation (A15.1).
    5.  Add ``associated_repos: []`` to every context row that lacks it.
    6.  Set ``schema_version = "3"``.
    7.  Write atomically (tmp -> os.replace()).
    """
    ctx_file = states_dir / "spec_contexts.json"

    if not ctx_file.exists():
        return

    raw = json.loads(ctx_file.read_text(encoding="utf-8"))
    schema_ver = _detect_schema_version(raw)

    if schema_ver == "3":
        return

    if schema_ver != "2":
        raise ValueError(
            f"Unknown schema_version '{schema_ver}' in spec_contexts.json for the v3 "
            "migration. Manual intervention required."
        )

    # Backup-first: preserve the pre-migration v2 file byte-for-byte before any write.
    backup_file = states_dir / _BACKUP_NAME
    backup_file.write_text(ctx_file.read_text(encoding="utf-8"), encoding="utf-8")

    new_contexts = []
    for ctx in raw.get("contexts", []):
        new_ctx = dict(ctx)
        new_ctx.setdefault("associated_repos", [])
        new_contexts.append(new_ctx)

    migrated: dict[str, object] = {
        "schema_version": "3",
        "contexts": new_contexts,
    }

    tmp = ctx_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(migrated, indent=2), encoding="utf-8")
    os.replace(tmp, ctx_file)
