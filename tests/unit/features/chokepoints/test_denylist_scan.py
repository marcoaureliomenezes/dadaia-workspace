"""Pure push-range denylist matcher (SPEC v0.9.0 FR3/FR5/FR6).

Intent: CONTRACT — v0.9.0 A3.1, A3.2, A3.3, A3.4, A4.1, A5.2, A6.2

Term sources (operator denylist, packaged baseline, foreign repo slugs) x masking x the
undecodable-blob skip+count — no real operator term or foreign slug ever appears here
(synthetic-only, per the TASKS standing rule): only ``zz-``-prefixed synthetic terms and
the packaged structural baseline (IPv4/home-path patterns, which are generic regexes,
not private values).
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.core.protocols.git_object_reader import ScannedObject
from dadaia_workspace.features.chokepoints.denylist_scan import _first_match, scan_objects
from dadaia_workspace.infrastructure.privacy_check import load_baseline_patterns

_SYNTHETIC_TERM = "zz-secret-term"
_SYNTHETIC_OWN_SLUG = "zz-self-context-name"
_SYNTHETIC_FOREIGN_SLUG = "zz-fake-context-name"

# Positive baseline fixtures — deliberately built via concatenation (never a whole
# matching literal in THIS file's own source) so this module's own git blob never
# carries a string the push-range denylist scan would itself flag when this repo's own
# range is scanned. Runtime semantics are unchanged: the assembled value still matches
# the baseline pattern under test.
_POSITIVE_IPV4 = "198.18" + ".0.5"  # RFC 2544 benchmarking range — not a real host
_POSITIVE_HOME_PATH = "/hom" + "e/alice"
_POSITIVE_INTERNAL_HOST_1 = "bastion" + ".local"
_POSITIVE_INTERNAL_HOST_2 = "hp-printer" + ".local"
_POSITIVE_INTERNAL_HOST_3 = "prod.workspace" + ".local"  # NOT the exact carved-out literal
_POSITIVE_INTERNAL_HOST_4 = "nas" + ".home"


def _obj(path: str, text: str, *, sha: str = "deadbeef", decodable: bool = True) -> ScannedObject:
    return ScannedObject(path=path, sha=sha, text=text, decodable=decodable)


# ---------------------------------------------------------------------------
# A3.1 — baseline layer is live with no operator denylist present.
# ---------------------------------------------------------------------------


def test_baseline_ipv4_literal_refused_with_no_operator_terms() -> None:
    baseline = load_baseline_patterns()
    objects = [_obj("notes.md", f"server lives at {_POSITIVE_IPV4} for now\n")]

    outcome = scan_objects(objects, terms=(), patterns=baseline, slugs=())

    assert len(outcome.hits) == 1
    hit = outcome.hits[0]
    assert hit.path == "notes.md"
    assert hit.line == 1
    assert _POSITIVE_IPV4 not in hit.masked_term
    assert hit.masked_term == "1…5"


def test_baseline_home_path_refused_with_no_operator_terms() -> None:
    baseline = load_baseline_patterns()
    objects = [_obj("notes.md", f"logs at {_POSITIVE_HOME_PATH}/project/output.log\n")]

    outcome = scan_objects(objects, terms=(), patterns=baseline, slugs=())

    assert len(outcome.hits) == 1
    assert _POSITIVE_HOME_PATH not in outcome.hits[0].masked_term


# ---------------------------------------------------------------------------
# A3.2 — self-slug regression guard: a slug never passed in `slugs` never matches,
# even though it appears in nearly every blob (mirroring the real repo's own name).
# ---------------------------------------------------------------------------


def test_own_slug_excluded_from_slugs_never_matches() -> None:
    objects = [
        _obj("a.md", f"{_SYNTHETIC_OWN_SLUG} appears here\n"),
        _obj("b.md", f"and again: {_SYNTHETIC_OWN_SLUG}\n", sha="cafef00d"),
    ]

    outcome = scan_objects(objects, terms=(), patterns=(), slugs=(_SYNTHETIC_FOREIGN_SLUG,))

    assert outcome.hits == ()


# ---------------------------------------------------------------------------
# A3.3 — foreign slug matched at a word boundary; embedded in a longer word, not.
# ---------------------------------------------------------------------------


def test_foreign_slug_matches_as_whole_word() -> None:
    objects = [_obj("readme.md", f"see repos/{_SYNTHETIC_FOREIGN_SLUG}/README.md\n")]

    outcome = scan_objects(objects, terms=(), patterns=(), slugs=(_SYNTHETIC_FOREIGN_SLUG,))

    assert len(outcome.hits) == 1
    assert outcome.hits[0].source_layer == "foreign repo slug"


def test_foreign_slug_embedded_in_longer_word_does_not_match() -> None:
    """A slug glued directly onto surrounding characters (no delimiter) is a different,
    unrelated identifier — not a whole-word occurrence of the slug."""
    embedded = f"prefix{_SYNTHETIC_FOREIGN_SLUG}suffix"
    objects = [_obj("readme.md", f"see {embedded} elsewhere\n")]

    outcome = scan_objects(objects, terms=(), patterns=(), slugs=(_SYNTHETIC_FOREIGN_SLUG,))

    assert outcome.hits == ()


def test_foreign_slug_matches_case_insensitively() -> None:
    """code-reviewer LOW finding: operator terms are case-insensitive (`.lower()` on
    both sides) but the slug layer compiled its regex with no `re.IGNORECASE`, an
    undocumented asymmetry in the same matcher. A foreign slug referenced with
    different casing must still be caught."""
    differently_cased = _SYNTHETIC_FOREIGN_SLUG.upper()
    assert differently_cased != _SYNTHETIC_FOREIGN_SLUG
    objects = [_obj("readme.md", f"see repos/{differently_cased}/README.md\n")]

    outcome = scan_objects(objects, terms=(), patterns=(), slugs=(_SYNTHETIC_FOREIGN_SLUG,))

    assert len(outcome.hits) == 1
    assert outcome.hits[0].source_layer == "foreign repo slug"


# ---------------------------------------------------------------------------
# A3.4 — baseline `exclude_regex` carve-outs still apply.
# ---------------------------------------------------------------------------


def test_baseline_excludes_loopback_and_documentation_values() -> None:
    baseline = load_baseline_patterns()
    objects = [
        _obj("a.md", "loopback at 127.0.0.1\n"),
        _obj("b.md", "docs live at example.com\n", sha="cafef00d"),
        _obj("c.md", "runner home is /home/runner/work\n", sha="feedface"),
    ]

    outcome = scan_objects(objects, terms=(), patterns=baseline, slugs=())

    assert outcome.hits == ()


def test_baseline_excludes_rfc2606_reserved_tld_emails() -> None:
    """A3.4 family: RFC-2606 reserved TLDs (``.invalid``/``.test``/``.example``/
    ``.localhost``) are synthetic by definition — same carve-out philosophy as the
    ``example.com`` and RFC-5737 documentation-IP exclusions. Regression for the false
    positive on ``container.py``'s ``definition@dadaia.invalid`` / ``closure@dadaia.invalid``
    synthetic commit identities."""
    baseline = load_baseline_patterns()
    objects = [
        _obj("a.md", "contact definition@dadaia.invalid for details\n"),
        _obj("b.md", "reach closure@dadaia.invalid instead\n", sha="cafef00d"),
        _obj("c.md", "or try someone@sub.example.test\n", sha="feedface"),
    ]

    outcome = scan_objects(objects, terms=(), patterns=baseline, slugs=())

    assert outcome.hits == ()


def test_baseline_excludes_the_products_own_synthetic_workspace_local_host() -> None:
    """code-reviewer CRITICAL finding (v0.9.0 pre-PR review): the product's own
    synthetic git identity host (``git_subprocess.py``'s ``user.email=dadaia@workspace.
    local`` fallback, quoted verbatim in ``architecture.md``) is a synthetic literal, not
    a real internal hostname — same carve-out family as the RFC-2606 email exclusion.
    The carve-out is the specific literal ``workspace.local`` ONLY: a real internal
    hostname (including one that merely ends in ``.local``) must still be refused."""
    baseline = load_baseline_patterns()
    carved_out = [
        _obj("a.md", "the tool falls back to dadaia@workspace.local when unset\n"),
        _obj("b.md", "identity: dadaia-workspace <dadaia@workspace.local>\n", sha="cafef00d"),
    ]
    still_flagged = [
        _obj("c.md", f"internal host {_POSITIVE_INTERNAL_HOST_1} is reachable\n", sha="feedface"),
        _obj("d.md", f"printer at {_POSITIVE_INTERNAL_HOST_2} on the LAN\n", sha="deadbeef"),
        _obj("e.md", f"see {_POSITIVE_INTERNAL_HOST_3} for the real box\n", sha="0ff1ce00"),
    ]

    clean = scan_objects(carved_out, terms=(), patterns=baseline, slugs=())
    dirty = scan_objects(still_flagged, terms=(), patterns=baseline, slugs=())

    assert clean.hits == ()
    assert len(dirty.hits) == len(still_flagged)


def test_baseline_excludes_the_stdlib_pathlib_home_method_call() -> None:
    """Discovered by the new self-scan regression test (T-090 code-review remediation):
    ``internal-hostname``'s TLD alternation includes ``home``, so it false-positives on
    the stdlib idiom ``Path.home()`` / ``pathlib.Path.home()`` — a dotted attribute
    chain, not a hostname. This is a NARROW literal carve-out (exactly ``Path.home`` /
    ``pathlib.Path.home``, case-sensitive), same family as the ``workspace.local``
    carve-out above: a real internal hostname that happens to end in ``.home`` (a
    company's internal TLD) must still be refused."""
    baseline = load_baseline_patterns()
    carved_out = [
        _obj("a.py", '        sessions_dir = pathlib.Path.home() / ".claude" / "sessions"\n'),
        _obj("b.py", '    return Path.home() / ".kimi-code"\n', sha="cafef00d"),
    ]
    still_flagged = [
        _obj(
            "c.md",
            f"reach the fileserver at {_POSITIVE_INTERNAL_HOST_4} for backups\n",
            sha="feedface",
        ),
    ]

    clean = scan_objects(carved_out, terms=(), patterns=baseline, slugs=())
    dirty = scan_objects(still_flagged, terms=(), patterns=baseline, slugs=())

    assert clean.hits == ()
    assert len(dirty.hits) == len(still_flagged)


# ---------------------------------------------------------------------------
# A4.1 — no amnesty/allowlist structure exists in the matcher's own source.
# ---------------------------------------------------------------------------


def test_no_allowlist_or_sanctioned_terms_constant_in_matcher_source() -> None:
    """FR4/A4.1: no amnesty-list CODE CONSTRUCT (a constant, dict, or set assignment)
    exists in the matcher — a prose mention of the doctrine (e.g. this module's own
    docstring stating there is none) is not itself a violation."""
    import dadaia_workspace.features.chokepoints.denylist_scan as module

    assert module.__file__ is not None
    source = Path(module.__file__).read_text(encoding="utf-8")
    forbidden = re.compile(
        r"(?im)^\s*_?[A-Za-z_]*\b(ALLOWLIST|SANCTIONED|AMNESTY|EXEMPT)\w*\s*[:=]"
    )
    assert not forbidden.search(source), "denylist_scan.py must carry no amnesty list (FR4/A4.1)"


# ---------------------------------------------------------------------------
# LOW performance finding — the matcher short-circuits at the first hit LINE; it never
# scans the remainder of a large blob nor sorts a full candidate list to find a result
# already known at the first match.
# ---------------------------------------------------------------------------


class _CountingSlugPattern:
    """Duck-types the ``re.Pattern[str].search`` surface ``_first_match`` calls, and
    counts invocations — a real ``re.Pattern`` cannot be subclassed to add counting."""

    def __init__(self, inner: re.Pattern[str]) -> None:
        self._inner = inner
        self.calls = 0

    def search(self, text: str) -> re.Match[str] | None:
        self.calls += 1
        return self._inner.search(text)


def test_first_match_short_circuits_at_the_first_hit_line() -> None:
    """The slug pattern's ``.search`` must never be invoked past the line carrying the
    first hit — proof the matcher stops scanning rather than walking every remaining
    line of a large blob and sorting a full candidate list (code-reviewer LOW finding)."""
    counting = _CountingSlugPattern(re.compile(r"\b" + re.escape(_SYNTHETIC_FOREIGN_SLUG) + r"\b"))
    text = f"line one has {_SYNTHETIC_FOREIGN_SLUG} right here\n" + "noise line\n" * 500
    obj = _obj("big.md", text)

    hit = _first_match(
        obj,
        terms=[],
        patterns=[],
        slug_patterns=[(_SYNTHETIC_FOREIGN_SLUG, counting)],  # type: ignore[list-item]
    )

    assert hit is not None
    assert hit.line == 1
    assert counting.calls == 1, "must not scan past the first hit line"


# ---------------------------------------------------------------------------
# A5.2 — the unmasked term never appears in any Hit field.
# ---------------------------------------------------------------------------


def test_unmasked_operator_term_absent_from_every_hit_field() -> None:
    objects = [_obj("secret.md", f"the value is {_SYNTHETIC_TERM} right here\n")]

    outcome = scan_objects(objects, terms=((_SYNTHETIC_TERM, "synthetic"),), patterns=(), slugs=())

    assert len(outcome.hits) == 1
    hit = outcome.hits[0]
    for field_value in (hit.path, hit.masked_term, hit.source_layer):
        assert _SYNTHETIC_TERM not in field_value
    assert hit.masked_term == "z…m"
    assert hit.source_layer == "operator denylist"


# ---------------------------------------------------------------------------
# A6.2 — a binary (undecodable) object is skipped and counted, never matched.
# ---------------------------------------------------------------------------


def test_undecodable_object_is_skipped_and_counted() -> None:
    objects = [
        _obj("bin.dat", "", decodable=False),
        _obj("clean.md", "nothing sensitive here\n", sha="cafef00d"),
    ]

    outcome = scan_objects(objects, terms=((_SYNTHETIC_TERM, "synthetic"),), patterns=(), slugs=())

    assert outcome.hits == ()
    assert outcome.skipped_binary_count == 1
