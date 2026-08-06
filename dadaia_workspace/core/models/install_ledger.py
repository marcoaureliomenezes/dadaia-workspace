"""Install-ledger domain model — the projection's MEMORY of what it installed.

Bug class (``retired-lib-asset-leaves-orphan-projection``): projection reconciliation
used to derive the desired state from the CURRENT source tree only — ``copy_tree``
returned before its orphan-prune loop when the source dir no longer existed, so
retiring an entire asset family never propagated to the instance. Without a record of
what was installed, no reconciler can distinguish "asset the library stopped shipping"
(remove) from "file the operator authored" (never touch).

This ledger is that record: one entry per file the installer wrote or verified as its
own, with the sha256 of the content the installer owns. The reconciliation invariant it
enables (enforced in ``infrastructure/public_assets.py``):

    prune a path only when it (a) appears in the PREVIOUS ledger, (b) is absent from
    the CURRENT projection set, and (c) still carries the ledgered sha on disk.
    An operator-modified orphan is retained and surfaced, never deleted.

Pure ``core`` value object — no I/O, no ``json``/``pathlib`` coupling (the A-seam
discipline of :mod:`dadaia_workspace.core.models.plugin_pack`). The JSON adapter is
``infrastructure/json_install_ledger_store.py`` (``.dadaia/states/install_ledger.json``).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

#: On-disk schema version of ``install_ledger.json``.
CURRENT_SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class LedgerEntry:
    """One installed file: workspace-root-relative path, owned content sha, family.

    ``family`` names the projection group that wrote the file (``claude``, ``codex``,
    ``agents``, ``pi``, ``kimi-code``, ``scripts``, ``guardrail``, ``law``,
    ``plugin:<pack>``, …) — diagnostics and scoped operations only; the reconciliation
    invariant never depends on it.
    """

    relpath: str
    sha256: str
    family: str


@dataclass(frozen=True)
class InstallLedger:
    """The persisted install record. Absent file ⇒ no ledger ⇒ bootstrap semantics
    (record everything, prune nothing)."""

    schema_version: str
    entries: tuple[LedgerEntry, ...]

    @classmethod
    def of(cls, entries: Iterable[LedgerEntry]) -> InstallLedger:
        return cls(schema_version=CURRENT_SCHEMA_VERSION, entries=tuple(entries))

    @classmethod
    def empty(cls) -> InstallLedger:
        return cls(schema_version=CURRENT_SCHEMA_VERSION, entries=())

    def by_relpath(self) -> dict[str, LedgerEntry]:
        """Index by relpath (last entry wins — the writer deduplicates upstream)."""
        return {entry.relpath: entry for entry in self.entries}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> InstallLedger:
        """Parse the persisted mapping; raises ``ValueError`` on a malformed record."""
        version = data.get("schema_version")
        raw_entries = data.get("entries")
        if not isinstance(version, str) or not isinstance(raw_entries, list):
            raise ValueError("install_ledger: schema_version/entries malformed")
        entries: list[LedgerEntry] = []
        for raw in raw_entries:
            if not isinstance(raw, Mapping):
                raise ValueError("install_ledger: entry is not a mapping")
            relpath = raw.get("relpath")
            sha256 = raw.get("sha256")
            family = raw.get("family")
            if (
                not isinstance(relpath, str)
                or not isinstance(sha256, str)
                or not isinstance(family, str)
            ):
                raise ValueError("install_ledger: entry fields malformed")
            entries.append(LedgerEntry(relpath=relpath, sha256=sha256, family=family))
        return cls(schema_version=version, entries=tuple(entries))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "entries": [
                {"relpath": e.relpath, "sha256": e.sha256, "family": e.family} for e in self.entries
            ],
        }
