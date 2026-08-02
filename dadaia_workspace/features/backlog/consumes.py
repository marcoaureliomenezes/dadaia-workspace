"""``**Consumes:**`` parser + anchor binder for the producer post-step (v0.1.27, SPEC §3.1).

The producer half of removal-on-release reads a release SPEC's machine-readable
``**Consumes:** slug1, slug2`` line — the same bold-key convention SPEC.md already uses for
``**Status:**`` / ``**Branch:**`` — and binds the declared slugs' ``intents[]`` through the
R1 canonical-subject registry into the verified shipped-anchor set, which is then handed to
:meth:`BacklogRemovalLifecycle.consume`.

Two pure functions, roots injected, never cwd:

* :func:`parse_consumes_line` — extract the ordered, de-duplicated bare-slug list (tolerant
  of surrounding whitespace, a trailing ``.md``, and an absent/empty line ⇒ empty tuple).
* :func:`shipped_anchors_for` — bind exactly the declared slugs (no full-dir scan) and return
  the **union** of their bound anchors. **Fails loud** (:class:`ConsumesBindError`) when a
  declared slug is not a live backlog item, has zero intents, or any intent is unresolvable —
  the producer never writes a ledger built from a partially resolved declaration.
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.features.backlog.preview import bound_anchor_changes, load_backlog_items
from dadaia_workspace.features.backlog.subject_registry import Registry

__all__ = [
    "ConsumesBindError",
    "parse_consumes_line",
    "shipped_anchors_for",
]

#: Matches the bold-key ``**Consumes:** ...`` line, mirroring the ``**Status:**`` convention.
_CONSUMES_RE = re.compile(r"^\s*\*\*Consumes:\*\*\s*(?P<slugs>.*?)\s*$", re.MULTILINE)


class ConsumesBindError(DadaiaError):
    """Raised when a declared ``**Consumes:**`` slug cannot be bound to a shipped anchor set.

    Surfaces the offending slug (and the unresolved ref when applicable) so the producer
    post-step fails loud — no silent skip, no partially resolved ledger.
    """


def parse_consumes_line(spec_text: str) -> tuple[str, ...]:
    """Extract the ``**Consumes:**`` slugs from release SPEC text.

    Returns an ordered, first-occurrence-de-duplicated tuple of bare slugs (a trailing
    ``.md`` and surrounding whitespace are stripped). An absent or empty ``**Consumes:**``
    line yields an empty tuple (the producer then no-ops cleanly).
    """
    match = _CONSUMES_RE.search(spec_text)
    if match is None:
        return ()
    raw = match.group("slugs").strip()
    if not raw:
        return ()
    seen: dict[str, None] = {}
    for part in raw.split(","):
        slug = part.strip()
        if slug.endswith(".md"):
            slug = slug[: -len(".md")]
        slug = slug.strip()
        if slug:
            seen.setdefault(slug, None)
    return tuple(seen)


def shipped_anchors_for(
    slugs: tuple[str, ...],
    *,
    backlog_dir: Path,
    registry: Registry,
) -> frozenset[str]:
    """Return the UNION of the declared slugs' bound canonical anchors.

    Binds **only** the declared slugs (no full-dir scan): each slug must be a live backlog
    item file under ``backlog_dir`` whose ``intents[]`` all resolve through ``registry``.

    Fails loud (:class:`ConsumesBindError`) — never returning a partial set — when:

    * a declared slug is not a live backlog item file (unknown slug);
    * a declared slug binds to zero anchors (no intents, or no intent resolved);
    * any of a declared slug's intents is unresolvable (the unresolved ref is surfaced).
    """
    by_slug = {item.slug: item for item in load_backlog_items(backlog_dir)}
    union: set[str] = set()
    for slug in slugs:
        item = by_slug.get(slug)
        if item is None:
            raise ConsumesBindError(
                f"**Consumes:** slug {slug!r} is not a live backlog item under {backlog_dir}; "
                f"correct the SPEC line or restore the item."
            )
        anchor_changes, unresolved = bound_anchor_changes(item, registry)
        if unresolved:
            raise ConsumesBindError(
                f"**Consumes:** slug {slug!r} has unresolvable intent(s): {'; '.join(unresolved)}"
            )
        if not anchor_changes:
            raise ConsumesBindError(
                f"**Consumes:** slug {slug!r} binds to zero anchors (no intents to ship); "
                f"a consumed slug must declare at least one bound intent."
            )
        union |= set(anchor_changes.keys())
    return frozenset(union)
