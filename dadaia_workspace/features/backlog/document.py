"""Pure single-source ``BACKLOG.md`` parser (SPEC v0.12.0 FR1, PLAN §5, ADR #14).

The document has exactly one top-level section (v0.5.0 FR5, A5.2 — the in-file ``##
LEDGER`` section retired: an exit now appends one record to
``specs/backlog/_archive/backlog_histo.jsonl`` instead, see :func:`backlog_exit`).
``## ACTIVE`` holds one ``### <slug>`` subsection per live item, carrying the five
ratified ``dd-backlog-definition`` §2 keys (``**Title:**``, ``**Opened:**``,
``**Status:**``, ``**Description:**``, ``**Provenance:**``) plus one optional key,
``**Intents:**``, whose value is a fenced YAML code span fed to
:func:`core.models.backlog.parse_intents` (grill D7).

Parsing is **diagnostic, never throwing**: a malformed subsection and an unparseable
intents block are each captured as a located :class:`DocumentError` (section, slug,
line, message) on the returned model — the caller (the doctor) reports instead of
crashing. An absent ``BACKLOG.md`` (or an absent ``backlog_dir`` itself) yields an EMPTY
model, not an error (A1.2) — a context with no backlog is legitimate (the
consumer-scaffold case).

Section/subsection splitting is **fence-aware** (code-reviewer M1, v0.12.0 pre-PR): a
``## ``/``### `` line that appears inside an open ``` ``` ``` or ``~~~`` fence (any
length ≥ 3, CommonMark's same-character/at-least-as-long close rule — including a
longer outer fence wrapping a nested fenced example) is fenced CONTENT, never real
document structure. Zero silent truncation: an unclosed fence running to end-of-file is
a structural anomaly this parser cannot attribute to any section, so it is always
captured as a located :class:`DocumentError` rather than silently shrinking the model.
A document is never expected to carry more than one top-level heading NAME, but the
generic duplicate-heading detection below is not name-specific — it fires on ANY
repeated ``## <name>`` heading, ``## ACTIVE`` above all.

Pure module: the only root is the injected ``backlog_dir`` (SPEC §3.8 #6); no cwd reads,
no subprocess. The single reading path: ``features.backlog.doctor.run_backlog_doctor``
(the CLI-facing live entry point, wired since the T-120-08 cutover) and
``cli/commands/newartifacts.py``'s ``--explain`` both call :func:`load_document` — there
is no per-entry fallback.

``backlog_new`` (SPEC v0.4.2 FR1, GRILL D1) lives here too: one feature owns the grammar
for BOTH reading and writing — new subsections are appended at end-of-file (the single
``## ACTIVE`` section IS the whole document body now, so there is no later heading to
insert ahead of) — and checks slug membership by calling :func:`load_document` itself
rather than re-deriving the grammar a second time. Every write verifies itself: after
writing, the writer re-parses its own output and raises if the fresh slug is absent
(write-then-verify). :func:`remove_active_subsection`/:func:`backlog_exit` (v0.5.0 FR5,
A5.3) are the writer's mirror image: they remove exactly one ``### <slug>`` subsection
and, for :func:`backlog_exit`, append its histo record through an injected
:class:`~dadaia_workspace.core.protocols.record_store.RecordStore` (DI via
``core.protocols`` — this module never imports ``infrastructure`` directly, per the
``features-no-infrastructure`` import-linter contract).
"""

from __future__ import annotations

import re
from bisect import bisect_right
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

from dadaia_workspace.core.models.backlog import BacklogHistoRecord, Intent, parse_intents
from dadaia_workspace.core.protocols.record_store import RecordStore
from dadaia_workspace.features.backlog.preview import format_yaml_error

#: PyYAML's C-accelerated loader when the libyaml bindings are available, else the
#: pure-Python fallback (SPEC v0.4.2 FR11/D7) — one module-level constant so every
#: ``yaml.load`` call in this module (today: the ``**Intents:**`` fenced block) benefits
#: uniformly, with no behavioural difference between the two (A11.3).
try:
    # ``CSafeLoader`` is not a subclass of ``SafeLoader`` under types-PyYAML's stubs
    # (CSafeLoader mixes in the C-extension ``CParser``; SafeLoader mixes in the
    # pure-Python ``Reader``/``Scanner``/``Parser``/``Composer`` — the two share only
    # ``SafeConstructor``/``Resolver``, not a common Loader base), so the module-level
    # constant must be typed as the union of both concrete loader types, never narrowed
    # to either alone.
    _YAML_LOADER: type[yaml.SafeLoader] | type[yaml.CSafeLoader] = yaml.CSafeLoader
except AttributeError:  # pragma: no cover — exercised via the forced-fallback test
    _YAML_LOADER = yaml.SafeLoader

__all__ = [
    "ActiveItem",
    "BacklogDocument",
    "BacklogNewResult",
    "DocumentError",
    "backlog_exit",
    "backlog_new",
    "fenced_ranges",
    "load_document",
    "remove_active_subsection",
]

#: Backlog-slug validation, shared by the writer's own check (dd-backlog-definition §2):
#: lowercase, starts with a letter, then letters/digits/hyphens. ``fullmatch`` (not
#: ``match``) so a trailing newline is refused (v0.4.2 A1.4 rider) — the caller must
#: supply exactly a slug, nothing trailing.
_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]+$")

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

#: A fence-marker line: three-or-more backticks or tildes (optionally indented up to
#: 3 columns), plus whatever trailing text shares that line (an info string for an
#: OPENING fence; must be blank for a line to count as a CLOSING fence — the CommonMark
#: rule this module approximates). Both characters and any length ≥ 3 are tracked so a
#: Description can safely quote a fenced example by wrapping it in a longer outer fence
#: (M1's "4-backtick outer fence" case) without a nested shorter fence closing it early.
_FENCE_MARKER_RE = re.compile(
    r"^[ \t]{0,3}(?P<marker>`{3,}|~{3,})(?P<trailing>[^\n]*)$", re.MULTILINE
)


def _line_no(text: str, offset: int) -> int:
    """1-based file line number of *offset* within *text*."""
    return text.count("\n", 0, offset) + 1


def fenced_ranges(text: str) -> tuple[tuple[tuple[int, int], ...], tuple[DocumentError, ...]]:
    """Scan the WHOLE document once for fenced code spans, pairing each opening fence
    marker with the next marker of the SAME character and length ≥ its own that carries
    no other content on its line (CommonMark's close rule).

    Returns ``(ranges, errors)``. A range is a ``(start, end)`` offset pair spanning
    from the opening marker line through the closing marker line inclusive; a heading
    match starting inside one of these ranges is fenced content, not structure. An
    unclosed fence — reaching end-of-file still inside one — is a structural anomaly
    this pure parser cannot attribute to any section: it is captured as one located
    :class:`DocumentError` (never raised, never silently dropped) and its range still
    runs to end-of-text, so every heading from the opening marker onward stays
    fence-shadowed rather than reappearing as phantom structure.

    Public (v0.4.2 FR1): the SAME fence scanner every fence-aware caller in this module
    shares — one scanner, not a second private copy.
    """
    ranges: list[tuple[int, int]] = []
    errors: list[DocumentError] = []
    open_char: str | None = None
    open_len = 0
    open_start = 0
    for match in _FENCE_MARKER_RE.finditer(text):
        marker = match.group("marker")
        char, length = marker[0], len(marker)
        if open_char is None:
            open_char, open_len, open_start = char, length, match.start()
            continue
        is_close = (
            char == open_char and length >= open_len and match.group("trailing").strip() == ""
        )
        if is_close:
            ranges.append((open_start, match.end()))
            open_char = None
    if open_char is not None:
        ranges.append((open_start, len(text)))
        errors.append(
            DocumentError(
                section="DOCUMENT",
                slug=None,
                line=_line_no(text, open_start),
                message=(
                    f"unclosed code fence (opened with {open_char * open_len!r} at "
                    f"line {_line_no(text, open_start)}) — everything from there to "
                    "end of file is treated as fenced content, not document structure"
                ),
            )
        )
    return tuple(ranges), tuple(errors)


def _outside_fences(
    matches: Iterable[re.Match[str]], ranges: Sequence[tuple[int, int]]
) -> list[re.Match[str]]:
    """Keep only the matches whose start offset falls OUTSIDE every fenced range.

    SPEC v0.4.2 FR11/GRILL P5: *ranges* comes from :func:`fenced_ranges`, which
    discovers fenced spans by a single left-to-right scan and can only ever pair an
    opening marker with a LATER closing marker — the returned ranges are therefore
    already sorted by start offset and mutually non-overlapping. That invariant is what
    lets this function ``bisect`` over the sorted starts instead of rescanning every
    range per match (the O(headings × fences) rescan GRILL P5 measured): one
    ``bisect_right`` locates the single candidate range that COULD contain the match,
    replacing the previous ``any(...)`` linear scan over the whole range list.
    """
    if not ranges:
        return list(matches)
    starts = [start for start, _end in ranges]
    kept: list[re.Match[str]] = []
    for m in matches:
        offset = m.start()
        idx = bisect_right(starts, offset) - 1
        if idx >= 0 and ranges[idx][0] <= offset < ranges[idx][1]:
            continue
        kept.append(m)
    return kept


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
class BacklogDocument:
    """The typed ``BACKLOG.md`` model: ``ACTIVE`` items + errors (v0.5.0 FR5, A5.2 — the
    ``LEDGER`` rows retired with the in-file ``## LEDGER`` section; an exit's record now
    lives in ``backlog_histo.jsonl``, see :func:`backlog_exit`)."""

    active: tuple[ActiveItem, ...] = ()
    errors: tuple[DocumentError, ...] = ()


def _top_level_sections(
    text: str, ranges: Sequence[tuple[int, int]]
) -> tuple[dict[str, list[tuple[int, int]]], tuple[DocumentError, ...]]:
    """Map each top-level ``## <name>`` heading to EVERY occurrence's body ``(start,
    end)`` offsets — one range per occurrence, never dropped.

    The document schema states exactly one top-level section (``## ACTIVE``, module
    docstring, v0.5.0 A5.2); ANY top-level heading name occurring more than once is a
    structural violation, captured here as a located :class:`DocumentError` (bug
    ``backlog-doctor-silent-on-duplicate-top-level-sections``: the pre-fix
    ``dict.setdefault`` kept only the FIRST occurrence's range and silently discarded
    every later one, so a duplicated ``## ACTIVE`` block — and any duplicate slug inside
    it — was never even handed to the caller, let alone compared). This detection is
    generic over the heading NAME (never hardcoded to ``ACTIVE``), so it still catches a
    duplicate of any stray non-canonical heading too. Every occurrence's range is still
    returned so the caller parses ALL of them: duplicate content is compared (and
    flagged by the doctor's BL-SCHEMA/duplicate-slug checks), never silently dropped.

    A heading whose match starts inside a fenced span (*ranges*, M1) is fenced
    content, not real structure, and is excluded before offsets are derived.
    """
    headings = _outside_fences(_TOP_HEADING_RE.finditer(text), ranges)
    sections: dict[str, list[tuple[int, int]]] = {}
    errors: list[DocumentError] = []
    for i, heading in enumerate(headings):
        name = heading.group("name").strip()
        start = heading.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        if name in sections:
            errors.append(
                DocumentError(
                    section="DOCUMENT",
                    slug=None,
                    line=_line_no(text, heading.start()),
                    message=(
                        f"duplicate top-level section heading {name!r} — the document "
                        "schema states exactly one top-level section ('## ACTIVE'); "
                        f"merge this section's content into the single existing {name!r} "
                        "section"
                    ),
                )
            )
        sections.setdefault(name, []).append((start, end))
    return sections, tuple(errors)


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
        raw = yaml.load(body, Loader=_YAML_LOADER)
    except yaml.YAMLError as exc:
        return (), f"malformed intents[] YAML: {format_yaml_error(exc)}"
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
    text: str, start: int, end: int, ranges: Sequence[tuple[int, int]]
) -> tuple[tuple[ActiveItem, ...], tuple[DocumentError, ...]]:
    """A ``### <slug>`` match inside a fenced span (*ranges*, M1) is fenced
    content, not a real subsection heading, and is excluded before splitting."""
    subsections = _outside_fences(_SUBSECTION_RE.finditer(text, start, end), ranges)
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
        # A1.5 (v0.4.2): the diagnostic names the file, never the absolute filesystem
        # path it lives at — ``path`` may embed an operator-local directory tree.
        return BacklogDocument(
            errors=(
                DocumentError(
                    section="ACTIVE",
                    slug=None,
                    line=0,
                    message=f"cannot read {path.name}: {exc.__class__.__name__}",
                ),
            )
        )

    ranges, fence_errors = fenced_ranges(text)
    sections, section_errors = _top_level_sections(text, ranges)
    active_items: list[ActiveItem] = []
    errors: list[DocumentError] = [*fence_errors, *section_errors]

    # Every occurrence of a repeated top-level heading is still parsed (never just the
    # first) so duplicate content — a duplicated slug above all — reaches the caller
    # and can be compared, not silently dropped (bug
    # backlog-doctor-silent-on-duplicate-top-level-sections).
    for start, end in sections.get("ACTIVE", []):
        items, active_errors = _parse_active(text, start, end, ranges)
        active_items.extend(items)
        errors.extend(active_errors)

    return BacklogDocument(active=tuple(active_items), errors=tuple(errors))


# ═════════════════════════════════════════════════════════════════════════════════
# ── backlog_new — the single writer (SPEC v0.4.2 FR1, GRILL D1) ────────────────────
#
# Moved from ``features/spec_artifacts/new_artifacts.py`` (v0.12.0 FR3): that module's
# own comment recorded why the writer previously could NOT import this parser —
# ``features/spec_artifacts`` and ``features/backlog`` are independent sibling
# features under the ``features-no-cross-feature`` import-linter contract, and no
# accepted edge existed for that pair (GRILL P2). Moving the writer into the feature
# that already owns the grammar removes the need for an edge at all (D1) — one feature,
# one reader, one writer, no new ``setup.cfg`` exception.
# ═════════════════════════════════════════════════════════════════════════════════


@dataclass
class BacklogNewResult:
    """Outcome of :func:`backlog_new` — the path written and whether it was freshly
    created (mirrors ``features.spec_artifacts.new_artifacts.NewArtifactResult``'s
    shape without a cross-feature import; both are duck-typed the same way by every
    caller: ``.path`` / ``.created``)."""

    path: Path
    created: bool = True


def _today() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%d")


#: The document skeleton a from-scratch ``BACKLOG.md`` starts from — the single
#: ``## ACTIVE`` heading, nothing else (v0.5.0 FR5, A5.2). MUST stay byte-identical to
#: ``features.specs.scaffolder._BACKLOG_STUB`` (pinned by
#: ``tests/unit/features/specs/test_scaffolder.py``): a fresh ``specs init`` scaffold
#: and a fresh ``backlog new`` share one skeleton shape, and both round-trip through
#: :func:`load_document` with zero errors.
_BACKLOG_DOCUMENT_SKELETON = "## ACTIVE\n"

# The subsection is born at ``status: idea`` — an unbound brainstorm. ``backlog doctor``
# exempts ``idea`` from the typed-intents requirement (v0.1.55 FR5, preserved verbatim
# over the new shape — SPEC v0.12.0 A2.3), so a fresh subsection is doctor-clean; the
# commented template TEACHES the ``**Intents:**`` fenced-YAML shape a maturing entry
# must adopt at `candidate` and beyond (a teaching template, NOT a live dummy subject
# that would gate-game). No ``.format`` field braces appear inside it beyond ``{slug}``/
# ``{today}``, so no escaping is needed.
_ACTIVE_SUBSECTION_TEMPLATE = """\
### {slug}
- **Title:** {slug}
- **Opened:** {today}
- **Status:** idea
- **Description:** (one-line description of the need)
- **Provenance:** operator request

<!--
An `idea` needs no `**Intents:**` block. Before promoting this entry to
`**Status:** candidate`, add one more bullet, ABOVE this comment: the bold key
`Intents` (followed by a colon and a fenced ```yaml block, the same way `Title`/
`Status` above are written) whose fenced content binds each change to a canonical
subject anchor, shaped like the fenced example below (copy it above this comment,
under its own `Intents` bullet, to make it live):

```yaml
- subject:
    kind: code
    ref: path/to/module.py#Symbol
  change: what changes about this subject
- subject:
    kind: cli
    ref: dadaia some-command
  change: what changes about this command
```

Discover bindable anchors with `dadaia backlog subjects`. Subject kinds: code | cli |
catalog | doc | invariant (code anchors are derived from Python sources only — in a
non-Python repo bind catalog/doc/invariant anchors instead).
-->

"""


def _append_active_subsection(text: str, block: str) -> str:
    """Append *block* at end-of-file.

    Since ``## ACTIVE`` is the document's ONLY top-level section (v0.5.0 FR5, A5.2 —
    the ``## LEDGER`` heading this writer used to insert ahead of is retired), there is
    no later heading to splice ahead of any more: the document body ENDS where
    ``## ACTIVE``'s content ends, so appending at end-of-file lands the fresh subsection
    inside the same section every time. Every byte before the insertion point is
    untouched (A3.2's byte-diff guarantee).
    """
    return text.rstrip("\n") + "\n\n" + block


def backlog_new(specs_dir: Path, slug: str) -> BacklogNewResult:
    """Append one ``### <slug>`` ACTIVE subsection to ``specs/backlog/BACKLOG.md``
    (SPEC v0.4.2 FR1 — moved from ``features.spec_artifacts.new_artifacts``, v0.12.0
    FR3/ADR #14) — creating the document with the ``## ACTIVE`` section heading first
    when it does not yet exist.

    Slug membership (A1.7/A3.3) is checked by calling :func:`load_document` itself —
    the parser this writer shares its grammar with — rather than re-deriving the check
    with a second, private regex pair. Every write verifies itself: after writing, the
    fresh output is re-parsed and the slug's presence in ``ACTIVE`` is asserted, raising
    :class:`RuntimeError` otherwise (write-then-verify, A1.2) — a write that silently
    failed to round-trip is reported as a failure, never as ``[ok] created:``.

    Args:
        specs_dir: Absolute path to the ``specs/`` directory.
        slug:      Backlog entry slug. Must ``fullmatch`` ``^[a-z][a-z0-9-]+$`` (A1.4 —
            a trailing newline is refused, unlike the pre-v0.4.2 ``.match``).

    Returns:
        :class:`BacklogNewResult` with the path to ``BACKLOG.md``.

    Raises:
        ValueError:      If ``slug`` does not match the slug pattern (A1.7/A3.4,
            unchanged message).
        FileExistsError: If ``slug`` already names an ACTIVE subsection (A1.7/A3.3 —
            the slug-uniqueness invariant within ``ACTIVE``; uniqueness against a
            slug's own past exit lives in ``backlog_histo.jsonl``, not this document,
            since v0.5.0 FR5).
        RuntimeError:    If a re-parse of the fresh write does not contain the fresh
            slug (A1.2, write-then-verify).
    """
    if not _SLUG_RE.fullmatch(slug):
        raise ValueError(
            f"Invalid slug {slug!r}. "
            "Must match ^[a-z][a-z0-9-]+$ "
            "(lowercase letters, digits, and hyphens; must start with a letter)."
        )

    backlog_dir = specs_dir / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    target = backlog_dir / "BACKLOG.md"

    existing_doc = load_document(backlog_dir)
    if any(item.slug == slug for item in existing_doc.active):
        raise FileExistsError(
            f"Backlog slug already exists: {slug!r} is already present in ACTIVE of "
            f"{target}. Use a different slug."
        )

    if target.is_file():
        existing_text = target.read_text(encoding="utf-8")
    else:
        existing_text = _BACKLOG_DOCUMENT_SKELETON
    block = _ACTIVE_SUBSECTION_TEMPLATE.format(slug=slug, today=_today())
    target.write_text(_append_active_subsection(existing_text, block), encoding="utf-8")

    # Write-then-verify (A1.2): re-parse the fresh output and confirm the slug is
    # really there before reporting success.
    verify_doc = load_document(backlog_dir)
    if not any(item.slug == slug for item in verify_doc.active):
        raise RuntimeError(
            f"backlog_new wrote {target.name} but a re-parse of that write does not "
            f"show slug {slug!r} in ACTIVE — refusing to report success"
        )

    return BacklogNewResult(path=target, created=True)


# ═════════════════════════════════════════════════════════════════════════════════
# ── backlog_exit — the writer's mirror image (v0.5.0 FR5, A5.3) ────────────────────
#
# An entry exit (any disposition) removes exactly one ``### <slug>`` ACTIVE subsection
# and appends exactly one record to ``backlog_histo.jsonl`` — never a second record for
# the same slug (the retired in-file ``## LEDGER`` duplicate-line class this replaces,
# BL-DUP, becomes structurally impossible, A5.2). ``entry_md`` is the removed
# subsection's own source text (``### <slug>`` through its last byte before the next
# subsection/EOF) — the full snapshot A5.1 asks for.
# ═════════════════════════════════════════════════════════════════════════════════


def remove_active_subsection(specs_dir: Path, slug: str) -> str:
    """Remove exactly one ``### <slug>`` ``## ACTIVE`` subsection from
    ``specs/backlog/BACKLOG.md`` and return its removed source text verbatim
    (``entry_md``, A5.1) — every other byte of the file survives unchanged.

    Pure string-slice removal: locates the subsection heading and body via the SAME
    fence-aware machinery :func:`load_document` parses with
    (:func:`_SUBSECTION_RE`/:func:`fenced_ranges`), not a second, private regex.

    Raises:
        KeyError: If *slug* does not name a live ``## ACTIVE`` subsection.
    """
    backlog_dir = specs_dir / "backlog"
    target = backlog_dir / "BACKLOG.md"
    text = target.read_text(encoding="utf-8") if target.is_file() else ""

    ranges, _ = fenced_ranges(text)
    sections, _ = _top_level_sections(text, ranges)
    active_ranges = sections.get("ACTIVE", [])

    for start, end in active_ranges:
        subsections = _outside_fences(_SUBSECTION_RE.finditer(text, start, end), ranges)
        for i, sub in enumerate(subsections):
            if sub.group("slug").strip() != slug:
                continue
            body_end = subsections[i + 1].start() if i + 1 < len(subsections) else end
            removed = text[sub.start() : body_end]
            new_text = text[: sub.start()] + text[body_end:]
            target.write_text(new_text, encoding="utf-8")
            return removed.rstrip("\n")

    raise KeyError(f"backlog slug {slug!r} does not name a live ACTIVE subsection in {target}")


def backlog_exit(
    specs_dir: Path,
    slug: str,
    *,
    histo_store: RecordStore[BacklogHistoRecord],
    disposition: str,
    reason: str | None,
    release: str | None,
    by: str,
    ts: str | None = None,
) -> BacklogHistoRecord:
    """Retire *slug* out of ``## ACTIVE`` and append its one histo record (v0.5.0 FR5,
    A5.3) — the atomic pair :func:`remove_active_subsection` (the removal) and
    ``histo_store.append`` (the record) — through an INJECTED
    :class:`~dadaia_workspace.core.protocols.record_store.RecordStore` (DI via
    ``core.protocols`` — this module never imports ``infrastructure`` directly; the
    concrete store is composed at ``container.build_backlog_histo_store``).

    ``entry_md`` is the exact removed subsection text; there is nothing to "recover"
    for a live exit (only the historical migration reaches for an archived snapshot).
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
        entry_md_source="live exit (backlog_exit) — exact removed ACTIVE subsection text",
    )
    histo_store.append(record)
    return record
