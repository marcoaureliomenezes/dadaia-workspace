"""``bugs-single-file`` migration — v0.1.73 FR1 (bug
``bugs-store-fragments-into-hourly-files``, HIGH).

The operator specified ONE append-only bug ledger; the v0.1.46 store drifted into
per-hour ``<YYYYMMDDTHH>Z-<n>.jsonl`` rotation, fragmenting history into dozens of
files. This step consolidates:

1. Every legacy hourly file, in chronological ``(hour, n)`` order, is concatenated
   BEFORE any existing ``bugs.jsonl`` content (legacy events predate canonical appends)
   into the single canonical ``specs/bugs/bugs.jsonl``; the legacy files are removed —
   every line preserved, none rewritten.
2. Every ``specs/bugs/_archive/*.md`` legacy bug source is collapsed into ONE
   ``_archive/archive.jsonl`` — one JSON object per file (``{"file": <name>,
   "content": <full text>}``, verbatim) — then the ``.md`` sources are removed.
   Consolidation, never deletion: every byte survives in the JSONL.

Idempotent (re-run finds nothing to do) and dry-run capable (plans, writes nothing).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from dadaia_workspace.features.migrate.tree_v2 import MigrateResult

__all__ = ["migrate_bugs_single_file"]

# Mirrored naming contract (the pure features layer must not import infrastructure).
_CANONICAL = "bugs.jsonl"
_ARCHIVE_JSONL = "archive.jsonl"

_LEGACY_RE = re.compile(r"^(?P<hour>\d{8}T\d{2})Z-(?P<n>\d+)\.jsonl$")


def migrate_bugs_single_file(specs_dir: Path, *, dry_run: bool = False) -> MigrateResult:
    """Consolidate hourly bug logs + archived ``.md`` sources into single files."""
    result = MigrateResult(dry_run=dry_run)
    bugs_dir = specs_dir / "bugs"
    if not bugs_dir.is_dir():
        result.skipped.append("bugs/ not found — nothing to consolidate.")
        return result

    canonical = bugs_dir / _CANONICAL
    legacy = sorted(
        (p for p in bugs_dir.glob("*.jsonl") if _LEGACY_RE.match(p.name)),
        key=lambda p: (
            _LEGACY_RE.match(p.name).group("hour"),  # type: ignore[union-attr]
            int(_LEGACY_RE.match(p.name).group("n")),  # type: ignore[union-attr]
        ),
    )
    if legacy:
        if dry_run:
            result.moved.extend((p, canonical) for p in legacy)
        else:
            legacy_text = "".join(
                _ensure_trailing_newline(p.read_text(encoding="utf-8")) for p in legacy
            )
            existing = (
                _ensure_trailing_newline(canonical.read_text(encoding="utf-8"))
                if canonical.is_file()
                else ""
            )
            tmp = canonical.with_suffix(".jsonl.tmp")
            tmp.write_text(legacy_text + existing, encoding="utf-8")
            tmp.replace(canonical)
            for p in legacy:
                p.unlink()
                result.moved.append((p, canonical))
    else:
        result.skipped.append("no legacy hourly bug logs — ledger already consolidated.")

    archive_dir = bugs_dir / "_archive"
    if archive_dir.is_dir():
        sources = sorted(p for p in archive_dir.glob("*.md") if p.name != "README.md")
        if sources:
            archive_jsonl = archive_dir / _ARCHIVE_JSONL
            if dry_run:
                result.moved.extend((p, archive_jsonl) for p in sources)
            else:
                with archive_jsonl.open("a", encoding="utf-8") as handle:
                    for p in sources:
                        handle.write(
                            json.dumps(
                                {"file": p.name, "content": p.read_text(encoding="utf-8")},
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                for p in sources:
                    p.unlink()
                    result.moved.append((p, archive_jsonl))
        else:
            result.skipped.append("no archived .md bug sources — archive already consolidated.")

    return result


def _ensure_trailing_newline(text: str) -> str:
    if text and not text.endswith("\n"):
        return text + "\n"
    return text
