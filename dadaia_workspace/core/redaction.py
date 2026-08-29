"""Stdlib-pure masking primitives (SPEC v0.11.0 FR6/ADR D1-a; :func:`redact_text`
relocated here at the bug ``backlog-histo-writer-skips-write-time-denylist-redaction``
fix — see below).

Extracted mechanically from ``cli/redact.py#ContextRedactor`` (v0.9.0 FR8a) so the SAME
masking primitive can be consumed both by the CLI's ``--redact`` rendering
(``cli/redact.py``) AND by the push-range denylist gate's own render boundary
(``features/chokepoints/service.py``'s ``_compose_denylist_refusal`` /
``_annotate_skip``), which may import ``core`` but never ``cli``
(``architecture.md`` ring purity) — the extension entry #23's resolution A requires
would otherwise be unimplementable in either direction (grill P4).

Word-boundary alternation, longest-first ordering, and stable first-appearance ordinal
placeholders are the whole of the :class:`Redactor` primitive; everything
caller-specific (which candidates to mask, what to exclude, JSON-tree recursion) stays
in the consumer. :func:`redact_text` is a SEPARATE, older primitive (SPEC v0.4.5 FR6/
FR7, T-045-19) with different semantics — plain case-insensitive substring masking (no
word-boundary restriction, mirroring ``features.chokepoints.denylist_scan``'s own
``operator_terms_match`` exactly, A6.3) plus unconditional control/format-character
stripping and IP/home-path scrubbing. It lived only in ``core/models/bugs.py`` until
the bug above: a SECOND write-time record model (``core.models.backlog
.BacklogHistoRecord``) needed the identical seam, and duplicating ~40 lines of
denylist-masking regex logic per domain model is exactly the hand-kept-copy defect
class A2.10 forbids for field lists — so the primitive itself moves to this shared,
domain-agnostic module (neither ``core/models/bugs.py`` nor ``core/models/backlog.py``
imports the other; both import this one, stdlib-pure sibling). ``core/models/bugs.py``
re-exports :func:`redact_text` unchanged for every existing caller.

Zero I/O — ``core/`` stays stdlib-pure; the file-I/O authorized set
(``specs_backup``/``specs_repair``/``specs_version``/``workspace_resolver``/
``atomic_write``/``invocation``/``session_store``) is unaffected.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

__all__ = ["Redactor", "compile_candidates", "redact_text"]

# ============================================================================
# redact_text — case-insensitive substring masking (SPEC v0.4.5 FR6/FR7, T-045-19).
# ============================================================================

# Redaction patterns (privacy rules): operator-local home paths + IPs never land in a
# committed record. The username segment of a home path is scrubbed; the IPv4 form is
# masked wholesale. (A version token like v0.1.46 has only three numeric groups and is
# never matched.)
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_POSIX_HOME_RE = re.compile(r"(/home/|/Users/)[^/\s:]+")
_WIN_HOME_RE = re.compile(r"([A-Za-z]:\\Users\\)[^\\\s:]+")

#: The C0/C1/DEL control range MINUS TAB (0x09), LF (0x0A) and CR (0x0D), plus the
#: Unicode LINE/PARAGRAPH SEPARATORS (U+2028/U+2029). Stripped — never escaped — FIRST
#: inside :func:`redact_text`, before any masking pass (v0.4.5 FR7/A7.3/A7.6, narrowed
#: by bug ``bug-event-sanitation-strips-tab-lf-cr-from-free-text``; bundles bug
#: ``bug-event-field-with-unicode-line-separator-silently-drops-the-event``).
#: A caller serializing with ``json.dumps(..., ensure_ascii=False)`` already escapes
#: the WHOLE C0/C1/DEL range as a JSON string escape — a literal TAB/LF/CR inside a
#: field value can never fragment a JSONL line, as long as the reader splits on a
#: literal ``"\\n"`` character, never on ``str.splitlines()``'s wider terminator set
#: (v0.4.5 FR7 read-side fix). TAB/LF/CR carry neither hazard this class exists to
#: close and must round-trip intact — deleting them only destroyed the word boundaries
#: of every multi-line free-text field, silently, on the live write path (bug
#: ``bug-event-sanitation-strips-tab-lf-cr-from-free-text``). What DOES still need
#: stripping: (a) U+0085/U+2028/U+2029 — the only bytes ``json.dumps`` leaves raw AND a
#: naive ``str.splitlines()``-style reader would treat as a terminator, the actual
#: fragmentation hazard (A7.1); (b) ESC and the rest of C0/C1/DEL — a raw ESC forges an
#: ANSI escape sequence or a fake second output line in any consumer that ever decodes
#: a folded record back to a terminal (CWE-117, A7.2). Deleted rather than escaped,
#: unlike that precedent: a denylisted term an attacker interrupts with one of these
#: bytes must re-join into a contiguous substring for the masking pass immediately
#: below to still catch it (A7.6) — an escape sequence (``"\\x1b"``) would leave the
#: two halves apart.
_UNSAFE_FORMAT_CHARS_RE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f\u2028\u2029]")


def redact_text(text: str, denylist_terms: Sequence[tuple[str, str]] = ()) -> str:
    """Return ``text`` with unsafe control/format characters stripped, then
    operator-local home-path usernames, IPv4 addresses, and any operator denylist term
    masked.

    The control/format strip (see :data:`_UNSAFE_FORMAT_CHARS_RE`) runs FIRST, before
    every masking pass (v0.4.5 FR7/A7.6) — so a denylisted term an attacker split with
    an embedded ESC or Unicode line/paragraph separator still gets matched below, and
    no such byte ever survives into a persisted field.

    ``denylist_terms`` is ``(term, reason)`` pairs from the SAME operator-term source
    the push-time scan already refuses on
    (``infrastructure.privacy_check.load_privacy_terms`` /
    ``features.chokepoints.denylist_scan.operator_terms_match``) — threaded in by the
    caller since this module is pure core and must never import ``infrastructure``
    (v0.4.5 FR6/T-045-19, `core-no-upper-layers`). Matched case-insensitively as a
    literal substring, mirroring the push-time scan's own semantics exactly (A6.3), so
    a term that would refuse a push is masked before it is ever committed. Defaults to
    ``()`` — a no-op for the denylist pass — so every pre-FR6 caller keeps masking
    IP/home paths; the control/format strip is unconditional and a no-op on clean text.
    """
    out = _UNSAFE_FORMAT_CHARS_RE.sub("", text)
    out = _IPV4_RE.sub("[REDACTED-IP]", out)
    out = _POSIX_HOME_RE.sub(r"\1[REDACTED]", out)
    out = _WIN_HOME_RE.sub(r"\1[REDACTED]", out)
    for term, _reason in denylist_terms:
        if term:
            out = re.sub(re.escape(term), "[REDACTED-TERM]", out, flags=re.IGNORECASE)
    return out


# ============================================================================
# Redactor — word-boundary ordinal-placeholder masking (SPEC v0.11.0 FR6/ADR D1-a).
# ============================================================================

#: Characters that make an adjacent match "not a whole word". Hyphens are
#: deliberately treated as WORD characters (not boundaries): a candidate (a context
#: name, a repo slug, a path segment) commonly contains them, and a short candidate
#: that is merely a substring/prefix of a longer, unrelated hyphenated string must
#: never be partially matched.
_WORD_CHARS = "A-Za-z0-9_-"


def compile_candidates(terms: Iterable[str]) -> re.Pattern[str] | None:
    """Word-boundary alternation over *terms*, longest-first so a short candidate that
    happens to be a prefix of a longer one never shadows the longer match.

    Returns ``None`` when *terms* carries no non-empty candidate — nothing to mask.
    """
    ordered = sorted({t for t in terms if t}, key=len, reverse=True)
    if not ordered:
        return None
    body = "|".join(
        rf"(?<![{_WORD_CHARS}]){re.escape(term)}(?![{_WORD_CHARS}])" for term in ordered
    )
    return re.compile(body)


class Redactor:
    """Stateful per-invocation masker: stable first-appearance ordinal placeholders.

    Construct ONE instance per rendering pass with the full candidate set. Reuse the
    SAME instance across every piece of output that pass renders, in rendering order,
    so the ordinal map accumulates in the TRUE first-appearance order of the pass.
    """

    def __init__(self, candidates: Iterable[str], *, placeholder_fmt: str) -> None:
        self._pattern = compile_candidates(candidates)
        self._placeholder_fmt = placeholder_fmt
        self._map: dict[str, str] = {}

    @property
    def active(self) -> bool:
        """True when at least one candidate exists to mask."""
        return self._pattern is not None

    def mask(self, value: str) -> str:
        """Mask every candidate substring found inside *value*."""
        if not value or self._pattern is None:
            return value

        def _sub(match: re.Match[str]) -> str:
            term = match.group(0)
            placeholder = self._map.get(term)
            if placeholder is None:
                placeholder = self._placeholder_fmt.format(n=len(self._map) + 1)
                self._map[term] = placeholder
            return placeholder

        return self._pattern.sub(_sub, value)
