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
(the CLI-facing live entry point) calls :func:`load_document` — there is no per-entry
fallback.

READER ONLY since 0.4.7 c7 (T-047-65): ``BACKLOG.json`` and its exit ledger have exactly
one writer, the stdlib skill script ``public/skills/dd-backlog-definition/scripts/
backlog.py``. The grammar this module parses is the grammar that script validates before
every replace, so the doctor and the writer cannot disagree about a live document.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.backlog import Intent, parse_intents

__all__ = [
    "ActiveItem",
    "BacklogDocument",
    "DocumentError",
    "load_document",
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
