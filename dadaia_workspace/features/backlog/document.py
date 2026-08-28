"""Pure single-source ``BACKLOG.json`` reader/writer (operator ruling 2026-08-28:
"BACKLOG.md e BACKLOG.json — estruturado. Nao essa merda solta de MD sem padrao." —
schema: ``public/schemas/backlog/backlog-v1.schema.json``).

**Supersession of the Markdown grammar (recorded, same "delete the retired subject's
tests" pattern this feature already used at the T-120-08 cutover — see this module's
own historical git log).** Through v0.5.0 this module parsed ``## ACTIVE`` /
``### <slug>`` Markdown subsections with fence-aware regexes and a fenced ```yaml
**Intents:** block per item (PyYAML, CSafeLoader-when-available). That whole grammar —
section/subsection splitting, CommonMark fence-close matching, the intents YAML
fence — is DELETED, not kept as a fallback: ``BACKLOG.md`` support does not exist any
more, there is no dual read path. The document is now ``specs/backlog/BACKLOG.json``, one
JSON object ``{"schema": "backlog-v1", "active": [...]}``: ``active`` is a native JSON
array, one object per item, carrying the SAME five required keys the old
``### <slug>`` subsections carried (``id`` replaces the ``### <slug>`` heading; ``title``/
``opened``/``status``/``description``/``provenance`` are unchanged in name and meaning)
plus one optional key, ``intents``, now a native JSON array fed straight to
:func:`core.models.backlog.parse_intents` — no more fenced-YAML indirection, so this
module no longer needs PyYAML at all.

Parsing is **diagnostic, never throwing**: a malformed entry and an unparseable
``intents`` value are each captured as a located :class:`DocumentError` (section, slug,
index, message) on the returned model — the caller (the doctor) reports instead of
crashing. An absent ``BACKLOG.json`` (or an absent ``backlog_dir`` itself) yields an EMPTY
model, not an error (A1.2) — a context with no backlog is legitimate (the
consumer-scaffold case). ``DocumentError.index`` replaces the retired ``line`` field —
JSON has no meaningful "file line" for a diagnostic to point at, so a located error names
the ``active[]`` array position instead (``-1`` for a document-level error with no single
entry to blame).

Pure module: the only root is the injected ``backlog_dir`` (SPEC §3.8 #6); no cwd reads,
no subprocess. The single reading path: ``features.backlog.doctor.run_backlog_doctor``
(the CLI-facing live entry point) and ``features.specs.doctor_governance``'s
SPEC-DOC-031 check both call :func:`load_document` — there is no per-entry fallback.

``backlog_new`` (SPEC v0.4.2 FR1, GRILL D1) lives here too: one feature owns the grammar
for BOTH reading and writing — a fresh entry is appended at the end of the ``active``
array — and checks slug membership by calling :func:`load_document` itself rather than
re-deriving the check with a second, private parser. Every write verifies itself: after
writing, the writer re-parses its own output and raises if the fresh slug is absent
(write-then-verify). :func:`remove_active_subsection`/:func:`backlog_exit` (v0.5.0 FR5,
A5.3, unchanged over the new storage) are the writer's mirror image: they remove exactly
one ``active[]`` entry and, for :func:`backlog_exit`, append its histo record through an
injected :class:`~dadaia_workspace.core.protocols.record_store.RecordStore` (DI via
``core.protocols`` — this module never imports ``infrastructure`` directly, per the
``features-no-infrastructure`` import-linter contract). ``entry_md`` (the histo record's
removed-entry snapshot field, name unchanged — ``core/models/backlog.py`` is out of this
module's write set) now holds a pretty-printed JSON snapshot of the removed ``active[]``
object instead of Markdown subsection source text.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.models.backlog import BacklogHistoRecord, Intent, parse_intents
from dadaia_workspace.core.protocols.record_store import RecordStore

__all__ = [
    "ActiveItem",
    "BacklogDocument",
    "BacklogNewResult",
    "DocumentError",
    "backlog_exit",
    "backlog_new",
    "load_document",
    "remove_active_subsection",
]

#: Backlog-slug validation, shared by the writer's own check (dd-backlog-definition §2):
#: lowercase, starts with a letter, then letters/digits/hyphens. ``fullmatch`` (not
#: ``match``) so a trailing newline is refused (v0.4.2 A1.4 rider) — the caller must
#: supply exactly a slug, nothing trailing.
_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]+$")

#: The six required keys every ``active[]`` entry MUST carry (``dd-backlog-definition``
#: §2 — ``id`` is the JSON-native replacement for the retired ``### <slug>`` heading).
_REQUIRED_KEYS: tuple[str, ...] = ("id", "title", "opened", "status", "description", "provenance")

#: The document schema id this reader/writer speaks (``public/schemas/backlog/
#: backlog-v1.schema.json``).
_SCHEMA_ID = "backlog-v1"


@dataclass(frozen=True)
class DocumentError:
    """One located, non-fatal parse diagnostic (section, slug, ``active[]`` index,
    message). ``index`` is ``-1`` for a document-level error with no single entry to
    blame (e.g. malformed JSON, or ``active`` not being an array)."""

    section: str
    slug: str | None
    index: int
    message: str


@dataclass(frozen=True)
class ActiveItem:
    """One ``active[]`` entry (the JSON-native replacement for a ``### <slug>``
    Markdown subsection)."""

    slug: str
    title: str
    opened: str
    status: str | None
    description: str
    provenance: str
    intents: tuple[Intent, ...] = ()
    intents_error: str | None = None
    index: int = 0


@dataclass(frozen=True)
class BacklogDocument:
    """The typed ``BACKLOG.json`` model: ``active`` items + errors."""

    active: tuple[ActiveItem, ...] = ()
    errors: tuple[DocumentError, ...] = ()


def _string_or_default(entry: dict[str, Any], key: str, default: str) -> str:
    value = entry.get(key)
    return value if isinstance(value, str) else default


def _string_or_none(entry: dict[str, Any], key: str) -> str | None:
    value = entry.get(key)
    return value if isinstance(value, str) else None


def _parse_active_entry(entry: object, index: int) -> tuple[ActiveItem, list[DocumentError]]:
    """Parse one ``active[]`` entry into an :class:`ActiveItem`. Never raises (A1.4): a
    non-object entry, a missing required key, or a structurally invalid ``intents``
    shape is captured as a located :class:`DocumentError` and the item still parses with
    whatever fields it does carry."""
    errors: list[DocumentError] = []
    if not isinstance(entry, dict):
        errors.append(
            DocumentError(
                section="ACTIVE",
                slug=None,
                index=index,
                message=f"active[{index}] must be a JSON object, got {type(entry).__name__}",
            )
        )
        return (
            ActiveItem(
                slug="",
                title="",
                opened="",
                status=None,
                description="",
                provenance="",
                index=index,
            ),
            errors,
        )

    missing = [key for key in _REQUIRED_KEYS if not (_string_or_none(entry, key) or "").strip()]
    slug = _string_or_none(entry, "id") or ""
    if missing:
        errors.append(
            DocumentError(
                section="ACTIVE",
                slug=slug or None,
                index=index,
                message=f"missing required key(s): {', '.join(missing)}",
            )
        )

    intents: tuple[Intent, ...] = ()
    intents_error: str | None = None
    intents_raw = entry.get("intents")
    if intents_raw is not None:
        try:
            intents = tuple(parse_intents(intents_raw))
        except ValueError as exc:
            intents_error = f"malformed intents[] frontmatter: {exc}"
            errors.append(
                DocumentError(
                    section="ACTIVE", slug=slug or None, index=index, message=intents_error
                )
            )

    item = ActiveItem(
        slug=slug,
        title=_string_or_default(entry, "title", ""),
        opened=_string_or_default(entry, "opened", ""),
        status=_string_or_none(entry, "status"),
        description=_string_or_default(entry, "description", ""),
        provenance=_string_or_default(entry, "provenance", ""),
        intents=intents,
        intents_error=intents_error,
        index=index,
    )
    return item, errors


def load_document(backlog_dir: Path) -> BacklogDocument:
    """Parse ``<backlog_dir>/BACKLOG.json`` into a typed :class:`BacklogDocument`.

    Absent file (or absent ``backlog_dir`` itself) ⇒ an empty document, never an error
    (A1.2). Unreadable file, malformed JSON, a document that is not a JSON object, or an
    ``active`` field that is not a JSON array ⇒ one document-level :class:`DocumentError`
    (``index=-1``). No exception ever escapes.
    """
    path = backlog_dir / "BACKLOG.json"
    if not path.is_file():
        return BacklogDocument()

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        # A1.5 (v0.4.2): the diagnostic names the file, never the absolute filesystem
        # path it lives at — ``path`` may embed an operator-local directory tree.
        return BacklogDocument(
            errors=(
                DocumentError(
                    section="DOCUMENT",
                    slug=None,
                    index=-1,
                    message=f"cannot read {path.name}: {exc.__class__.__name__}",
                ),
            )
        )

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        return BacklogDocument(
            errors=(
                DocumentError(
                    section="DOCUMENT",
                    slug=None,
                    index=-1,
                    message=f"cannot parse {path.name}: {exc}",
                ),
            )
        )

    if not isinstance(raw, dict):
        return BacklogDocument(
            errors=(
                DocumentError(
                    section="DOCUMENT",
                    slug=None,
                    index=-1,
                    message=f"{path.name} must contain a JSON object, got {type(raw).__name__}",
                ),
            )
        )

    active_raw: object = raw.get("active", [])
    if not isinstance(active_raw, list):
        return BacklogDocument(
            errors=(
                DocumentError(
                    section="DOCUMENT",
                    slug=None,
                    index=-1,
                    message=(
                        f"{path.name} 'active' must be a JSON array, got "
                        f"{type(active_raw).__name__}"
                    ),
                ),
            )
        )

    items: list[ActiveItem] = []
    errors: list[DocumentError] = []
    seen: dict[str, int] = {}
    for index, entry in enumerate(active_raw):
        item, item_errors = _parse_active_entry(entry, index)
        items.append(item)
        errors.extend(item_errors)
        if item.slug:
            if item.slug in seen:
                errors.append(
                    DocumentError(
                        section="ACTIVE",
                        slug=item.slug,
                        index=index,
                        message=(
                            f"duplicate id {item.slug!r} — already used at "
                            f"active[{seen[item.slug]}]"
                        ),
                    )
                )
            else:
                seen[item.slug] = index

    return BacklogDocument(active=tuple(items), errors=tuple(errors))


def _serialize_item(item: ActiveItem) -> dict[str, Any]:
    """Serialize an :class:`ActiveItem` back to its ``active[]`` JSON shape."""
    from dadaia_workspace.core.models.backlog import serialize_intents

    entry: dict[str, Any] = {
        "id": item.slug,
        "title": item.title,
        "opened": item.opened,
        "status": item.status,
        "description": item.description,
        "provenance": item.provenance,
    }
    if item.intents:
        entry["intents"] = serialize_intents(item.intents)
    return entry


def _dump_document(active: list[dict[str, Any]]) -> str:
    return json.dumps({"schema": _SCHEMA_ID, "active": active}, indent=2, ensure_ascii=False) + "\n"


def _read_raw_document(target: Path) -> tuple[str, dict[str, Any]]:
    """Read the current ``BACKLOG.json`` text plus its parsed-as-JSON ``active`` list
    (``[]``/``""`` when absent). Malformed JSON is never expected here — callers only
    reach this after :func:`load_document` has already reported the tree clean, so a
    stray write between the two reads is the only way a decode could fail; that race is
    exactly what ``atomic_write``'s ``expected_previous`` refuses at swap time."""
    if not target.is_file():
        return "", {"schema": _SCHEMA_ID, "active": []}
    previous_text = target.read_text(encoding="utf-8")
    try:
        raw = json.loads(previous_text)
    except json.JSONDecodeError:
        raw = {"schema": _SCHEMA_ID, "active": []}
    if not isinstance(raw, dict) or not isinstance(raw.get("active"), list):
        raw = {"schema": _SCHEMA_ID, "active": []}
    return previous_text, raw


# ═════════════════════════════════════════════════════════════════════════════════
# ── backlog_new — the single writer (SPEC v0.4.2 FR1, GRILL D1) ────────────────────
# ═════════════════════════════════════════════════════════════════════════════════


@dataclass
class BacklogNewResult:
    """Outcome of :func:`backlog_new` — the path written and whether it was freshly
    created."""

    path: Path
    created: bool = True


def _today() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%d")


def backlog_new(specs_dir: Path, slug: str) -> BacklogNewResult:
    """Append one ``active[]`` entry to ``specs/backlog/BACKLOG.json`` (SPEC v0.4.2 FR1)
    — creating the document with the ``{"schema": "backlog-v1", "active": []}``
    skeleton first when it does not yet exist.

    Slug membership (A1.7/A3.3) is checked by calling :func:`load_document` itself —
    the parser this writer shares its grammar with — rather than re-deriving the check
    with a second, private lookup. Every write verifies itself: after writing, the
    fresh output is re-parsed and the slug's presence in ``active`` is asserted, raising
    :class:`RuntimeError` otherwise (write-then-verify, A1.2) — a write that silently
    failed to round-trip is reported as a failure, never as ``[ok] created:``.

    The fresh entry is born at ``status: "idea"`` — an unbound brainstorm. ``backlog
    doctor`` exempts ``idea`` from the typed-``intents`` requirement (v0.1.55 FR5), so a
    fresh entry is doctor-clean with no further edits; ``intents`` is simply omitted
    (JSON has no comment syntax to carry the old Markdown stub's inline teaching text —
    the shape is documented in ``specs/backlog/AGENTS.md`` and
    ``dd-backlog-definition``).

    Args:
        specs_dir: Absolute path to the ``specs/`` directory.
        slug:      Backlog entry slug. Must ``fullmatch`` ``^[a-z][a-z0-9-]+$`` (A1.4 —
            a trailing newline is refused).

    Returns:
        :class:`BacklogNewResult` with the path to ``BACKLOG.json``.

    Raises:
        ValueError:      If ``slug`` does not match the slug pattern (A1.7/A3.4,
            unchanged message).
        FileExistsError: If ``slug`` already names an ``active[]`` entry (A1.7/A3.3 —
            the slug-uniqueness invariant within ``active``; uniqueness against a
            slug's own past exit lives in ``backlog_histo.jsonl``, not this document,
            since v0.5.0 FR5).
        RuntimeError:    If a re-parse of the fresh write does not contain the fresh
            slug (A1.2, write-then-verify).
        core.atomic_write.ConcurrentModificationError:
            If ``BACKLOG.json`` changed since it was read (F-14, T-050-36 security
            review): the write routes through :func:`core.atomic_write.atomic_write`
            with ``expected_previous`` set to the exact bytes just read, closing the
            plain-``write_text`` lost-update window a concurrent writer under the
            NO-LOCKS DOCTRINE could otherwise silently clobber. Surfaced to the
            caller verbatim — never swallowed here.
    """
    if not _SLUG_RE.fullmatch(slug):
        raise ValueError(
            f"Invalid slug {slug!r}. "
            "Must match ^[a-z][a-z0-9-]+$ "
            "(lowercase letters, digits, and hyphens; must start with a letter)."
        )

    backlog_dir = specs_dir / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    target = backlog_dir / "BACKLOG.json"

    existing_doc = load_document(backlog_dir)
    if any(item.slug == slug for item in existing_doc.active):
        raise FileExistsError(
            f"Backlog slug already exists: {slug!r} is already present in active of "
            f"{target}. Use a different slug."
        )

    previous_text, raw = _read_raw_document(target)
    active_list = list(raw["active"])
    active_list.append(
        {
            "id": slug,
            "title": slug,
            "opened": _today(),
            "status": "idea",
            "description": "(one-line description of the need)",
            "provenance": "operator request",
        }
    )
    atomic_write(
        target, _dump_document(active_list), expected_previous=previous_text, ensure_parent=True
    )

    # Write-then-verify (A1.2): re-parse the fresh output and confirm the slug is
    # really there before reporting success.
    verify_doc = load_document(backlog_dir)
    if not any(item.slug == slug for item in verify_doc.active):
        raise RuntimeError(
            f"backlog_new wrote {target.name} but a re-parse of that write does not "
            f"show slug {slug!r} in active — refusing to report success"
        )

    return BacklogNewResult(path=target, created=True)


# ═════════════════════════════════════════════════════════════════════════════════
# ── backlog_exit — the writer's mirror image (v0.5.0 FR5, A5.3) ────────────────────
# ═════════════════════════════════════════════════════════════════════════════════


def remove_active_subsection(specs_dir: Path, slug: str) -> str:
    """Remove exactly one ``active[]`` entry named *slug* from
    ``specs/backlog/BACKLOG.json`` and return its removed source as pretty-printed JSON
    text (``entry_md``, A5.1 — name unchanged, ``core/models/backlog.py`` is out of this
    module's write set) — every other entry survives unchanged.

    Raises:
        KeyError: If *slug* does not name a live ``active[]`` entry.
        core.atomic_write.ConcurrentModificationError:
            If ``BACKLOG.json`` changed since it was read (F-14, T-050-36 security
            review): the write routes through :func:`core.atomic_write.atomic_write`
            with ``expected_previous`` set to the exact bytes just read, closing the
            plain-``write_text`` lost-update window a concurrent writer under the
            NO-LOCKS DOCTRINE could otherwise silently clobber. Surfaced to the
            caller verbatim — never swallowed here.
    """
    backlog_dir = specs_dir / "backlog"
    target = backlog_dir / "BACKLOG.json"
    previous_text, raw = _read_raw_document(target)
    active_list = list(raw["active"])

    for i, entry in enumerate(active_list):
        if not isinstance(entry, dict) or entry.get("id") != slug:
            continue
        removed = active_list.pop(i)
        atomic_write(
            target, _dump_document(active_list), expected_previous=previous_text, ensure_parent=True
        )
        return json.dumps(removed, indent=2, ensure_ascii=False)

    raise KeyError(f"backlog slug {slug!r} does not name a live active[] entry in {target}")


def backlog_exit(
    specs_dir: Path,
    slug: str,
    *,
    histo_store: RecordStore[BacklogHistoRecord],
    disposition: str,
    reason: str | None,
    release: str | None,
    by: str,
    denylist_terms: list[tuple[str, str]] | tuple[tuple[str, str], ...],
    ts: str | None = None,
) -> BacklogHistoRecord:
    """Retire *slug* out of ``active[]`` and append its one histo record (v0.5.0 FR5,
    A5.3) — the atomic pair :func:`remove_active_subsection` (the removal) and
    ``histo_store.append`` (the record) — through an INJECTED
    :class:`~dadaia_workspace.core.protocols.record_store.RecordStore` (DI via
    ``core.protocols`` — this module never imports ``infrastructure`` directly; the
    concrete store is composed at ``container.build_backlog_histo_store``).

    ``entry_md`` is the exact removed entry's pretty-printed JSON text; there is
    nothing to "recover" for a live exit (only the historical migration reaches for an
    archived snapshot).

    ``denylist_terms`` is redacted through :meth:`BacklogHistoRecord.redact` BEFORE the
    record is appended (bug ``backlog-histo-writer-skips-write-time-denylist-redaction``)
    — the SAME write-time seam ``BugService.register``/``apply_update`` already enforce
    for ``BugRecord`` (SPEC v0.4.5 FR6/T-045-19). REQUIRED, no default (F-13, T-050-36
    security review): a default of ``()`` silently reintroduces the exact bug this
    parameter exists to fix the moment a future caller omits the keyword, with no error,
    no warning and no test failure — the type checker now enforces at every call site
    what the docstring can only request. This module still never imports
    ``infrastructure``/``container`` (``features-no-infrastructure``), so the caller
    wires the real operator denylist in via ``container.load_denylist_terms()``,
    mirroring how ``cli/commands/bugs.py`` wires ``BugService`` today.
    """
    entry_md = remove_active_subsection(specs_dir, slug)
    record = BacklogHistoRecord(
        id=slug,
        ts=ts if ts is not None else _today(),
        disposition=disposition,
        reason=reason,
        release=release,
        by=by,
        entry_md=entry_md,
        entry_md_source="live exit (backlog_exit) — exact removed active[] entry, as pretty-printed JSON",
    ).redact(denylist_terms)
    histo_store.append(record)
    return record
