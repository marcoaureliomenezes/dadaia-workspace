"""Pure single-source ``BACKLOG.md`` parser (SPEC v0.12.0 FR1, PLAN §5, ADR #14).

The document has exactly two top-level sections. ``## ACTIVE`` holds one ``###
<slug>`` subsection per live item, carrying the five ratified ``dd-backlog-definition``
§2 keys (``**Title:**``, ``**Opened:**``, ``**Status:**``, ``**Description:**``,
``**Provenance:**``) plus one optional key, ``**Intents:**``, whose value is a fenced
YAML code span fed to :func:`core.models.backlog.parse_intents` (grill D7). ``##
LEDGER`` holds one bullet line per closed item, the four-field ``·``-separated grammar
``<slug> · <disposition> · <release-or-reason> · <date>``.

Parsing is **diagnostic, never throwing**: a malformed subsection, an unparseable
intents block, and an ungrammatical LEDGER line are each captured as a located
:class:`DocumentError` (section, slug, line, message) on the returned model, exactly as
``preview.BacklogItem`` captures ``intents_error``/``frontmatter_error`` today — the
caller (the doctor, T-120-05) reports instead of crashing. An absent ``BACKLOG.md`` (or
an absent ``backlog_dir`` itself) yields an EMPTY model, not an error (A1.2) — a context
with no backlog is legitimate (the consumer-scaffold case).

Pure module: the only root is the injected ``backlog_dir`` (SPEC §3.8 #6); no cwd reads,
no subprocess. Not wired to anything yet (T-120-04) — the live CLI still reads per-entry
files via ``features/backlog/preview.load_backlog_items`` until the T-120-08 cutover.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from dadaia_workspace.core.models.backlog import Intent, is_terminal_disposition, parse_intents
from dadaia_workspace.features.backlog.preview import _format_yaml_error

__all__ = [
    "ActiveItem",
    "BacklogDocument",
    "DocumentError",
    "LedgerRow",
    "load_document",
]

#: The five keys every ACTIVE subsection MUST carry (``dd-backlog-definition`` §2).
_REQUIRED_KEYS: tuple[str, ...] = ("Title", "Opened", "Status", "Description", "Provenance")

#: A top-level ``## <name>`` heading (exactly two ``#``, never the ``### <slug>``
#: subsection marker, which starts with three).
_TOP_HEADING_RE = re.compile(r"^##[ \t]+(?P<name>\S.*?)[ \t]*$", re.MULTILINE)

#: An ACTIVE ``### <slug>`` subsection heading.
_SUBSECTION_RE = re.compile(r"^###[ \t]+(?P<slug>\S.*?)[ \t]*$", re.MULTILINE)

#: One ``- **Key:** value`` bullet line inside an ACTIVE subsection.
_KEY_LINE_RE = re.compile(
    r"^-[ \t]+\*\*(?P<key>Title|Opened|Status|Description|Provenance|Intents):\*\*[ \t]*(?P<value>.*)$",
    re.MULTILINE,
)

#: The fenced code span following an ``**Intents:**`` key line (```yaml ... ``` or a
#: bare ``` ... ``` fence — the language tag is optional and ignored).
_FENCE_RE = re.compile(r"```[^\n]*\n(?P<body>.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)

#: A LEDGER bullet line — one closed item per line, ``<slug> · <disposition> ·
#: <release-or-reason> · <date>``.
_LEDGER_LINE_RE = re.compile(r"^-[ \t]+(?P<rest>\S.*?)[ \t]*$", re.MULTILINE)


def _line_no(text: str, offset: int) -> int:
    """1-based file line number of *offset* within *text*."""
    return text.count("\n", 0, offset) + 1


@dataclass(frozen=True)
class DocumentError:
    """One located, non-fatal parse diagnostic (section, slug, file line, message)."""

    section: str
    slug: str | None
    line: int
    message: str


@dataclass(frozen=True)
class ActiveItem:
    """One ``## ACTIVE`` subsection (PLAN §5)."""

    slug: str
    title: str
    opened: str
    status: str | None
    description: str
    provenance: str
    intents: tuple[Intent, ...] = ()
    intents_error: str | None = None
    line: int = 0


@dataclass(frozen=True)
class LedgerRow:
    """One ``## LEDGER`` line (PLAN §5)."""

    slug: str
    disposition: str
    release_or_reason: str
    date: str
    line: int


@dataclass(frozen=True)
class BacklogDocument:
    """The typed ``BACKLOG.md`` model: ``ACTIVE`` items + ``LEDGER`` rows + errors."""

    active: tuple[ActiveItem, ...] = ()
    ledger: tuple[LedgerRow, ...] = ()
    errors: tuple[DocumentError, ...] = ()


def _top_level_sections(text: str) -> dict[str, tuple[int, int]]:
    """Map each top-level ``## <name>`` heading to its body's ``(start, end)`` offsets."""
    headings = list(_TOP_HEADING_RE.finditer(text))
    sections: dict[str, tuple[int, int]] = {}
    for i, heading in enumerate(headings):
        name = heading.group("name").strip()
        start = heading.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        # First occurrence wins if a heading name repeats — not a case this parser
        # otherwise validates; downstream (BL-DUP-style) duplicate detection is the
        # doctor's job, not this pure parser's.
        sections.setdefault(name, (start, end))
    return sections


def _parse_intents_block(
    text: str, key_end: int, body_end: int
) -> tuple[tuple[Intent, ...], str | None]:
    """Parse the fenced YAML block following an ``**Intents:**`` key line.

    Returns ``(intents, intents_error)``. Never raises (A1.4): a missing fence, invalid
    YAML, or a structurally invalid ``intents[]`` shape is captured as ``intents_error``
    and ``intents`` stays empty.
    """
    fence = _FENCE_RE.search(text, key_end, body_end)
    if fence is None:
        return (), "**Intents:** key present but no fenced code block follows"
    body = fence.group("body")
    try:
        raw = yaml.safe_load(body)
    except yaml.YAMLError as exc:
        return (), f"malformed intents[] YAML: {_format_yaml_error(exc)}"
    try:
        intents = tuple(parse_intents(raw))
    except ValueError as exc:
        return (), f"malformed intents[] frontmatter: {exc}"
    return intents, None


def _parse_active_subsection(
    text: str, slug: str, body_start: int, body_end: int, heading_line: int
) -> tuple[ActiveItem, tuple[DocumentError, ...]]:
    """Parse one ``### <slug>`` subsection body into an :class:`ActiveItem`."""
    values: dict[str, str] = {}
    intents: tuple[Intent, ...] = ()
    intents_error: str | None = None
    errors: list[DocumentError] = []

    for key_match in _KEY_LINE_RE.finditer(text, body_start, body_end):
        key = key_match.group("key")
        if key == "Intents":
            intents, intents_error = _parse_intents_block(text, key_match.end(), body_end)
            if intents_error is not None:
                errors.append(
                    DocumentError(
                        section="ACTIVE",
                        slug=slug,
                        line=_line_no(text, key_match.start()),
                        message=intents_error,
                    )
                )
            continue
        values[key] = key_match.group("value").strip()

    missing = [key for key in _REQUIRED_KEYS if key not in values]
    if missing:
        errors.append(
            DocumentError(
                section="ACTIVE",
                slug=slug,
                line=heading_line,
                message=f"missing required key(s): {', '.join(missing)}",
            )
        )

    item = ActiveItem(
        slug=slug,
        title=values.get("Title", ""),
        opened=values.get("Opened", ""),
        status=values.get("Status"),
        description=values.get("Description", ""),
        provenance=values.get("Provenance", ""),
        intents=intents,
        intents_error=intents_error,
        line=heading_line,
    )
    return item, tuple(errors)


def _parse_active(
    text: str, start: int, end: int
) -> tuple[tuple[ActiveItem, ...], tuple[DocumentError, ...]]:
    subsections = list(_SUBSECTION_RE.finditer(text, start, end))
    items: list[ActiveItem] = []
    errors: list[DocumentError] = []
    for i, sub in enumerate(subsections):
        slug = sub.group("slug").strip()
        body_start = sub.end()
        body_end = subsections[i + 1].start() if i + 1 < len(subsections) else end
        item, item_errors = _parse_active_subsection(
            text, slug, body_start, body_end, _line_no(text, sub.start())
        )
        items.append(item)
        errors.extend(item_errors)
    return tuple(items), tuple(errors)


def _parse_ledger(
    text: str, start: int, end: int
) -> tuple[tuple[LedgerRow, ...], tuple[DocumentError, ...]]:
    rows: list[LedgerRow] = []
    errors: list[DocumentError] = []
    for line_match in _LEDGER_LINE_RE.finditer(text, start, end):
        line_no = _line_no(text, line_match.start())
        content = line_match.group("rest")
        parts = [part.strip() for part in content.split("·")]
        if len(parts) != 4 or not all(parts):
            errors.append(
                DocumentError(
                    section="LEDGER",
                    slug=None,
                    line=line_no,
                    message=(
                        "malformed LEDGER line (expected 'slug · DISPOSITION · "
                        f"release-or-reason · date'): {content!r}"
                    ),
                )
            )
            continue
        slug, disposition, release_or_reason, date = parts
        if not is_terminal_disposition(disposition):
            errors.append(
                DocumentError(
                    section="LEDGER",
                    slug=slug,
                    line=line_no,
                    message=(
                        f"LEDGER disposition {disposition!r} is not one of the six "
                        "canonical terminal tokens (DELIVERED, SUPERSEDED, RESOLVED, "
                        "CONSUMED, DEFERRED, REJECTED)"
                    ),
                )
            )
            continue
        rows.append(
            LedgerRow(
                slug=slug,
                disposition=disposition.strip().upper(),
                release_or_reason=release_or_reason,
                date=date,
                line=line_no,
            )
        )
    return tuple(rows), tuple(errors)


def load_document(backlog_dir: Path) -> BacklogDocument:
    """Parse ``<backlog_dir>/BACKLOG.md`` into a typed :class:`BacklogDocument`.

    Absent file (or absent ``backlog_dir`` itself) ⇒ an empty document, never an error
    (A1.2). Unreadable file ⇒ one :class:`DocumentError`. No exception ever escapes.
    """
    path = backlog_dir / "BACKLOG.md"
    if not path.is_file():
        return BacklogDocument()

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return BacklogDocument(
            errors=(
                DocumentError(
                    section="ACTIVE", slug=None, line=0, message=f"cannot read {path}: {exc}"
                ),
            )
        )

    sections = _top_level_sections(text)
    active_items: tuple[ActiveItem, ...] = ()
    ledger_rows: tuple[LedgerRow, ...] = ()
    errors: list[DocumentError] = []

    if "ACTIVE" in sections:
        start, end = sections["ACTIVE"]
        active_items, active_errors = _parse_active(text, start, end)
        errors.extend(active_errors)

    if "LEDGER" in sections:
        start, end = sections["LEDGER"]
        ledger_rows, ledger_errors = _parse_ledger(text, start, end)
        errors.extend(ledger_errors)

    return BacklogDocument(active=active_items, ledger=ledger_rows, errors=tuple(errors))
