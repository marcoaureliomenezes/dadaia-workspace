"""Pure push-range denylist matcher (SPEC v0.9.0 FR3/FR5/FR6).

Intent: CONTRACT — v0.9.0 A3.1, A3.2, A3.3, A3.4, A4.1, A5.2, A6.2; v0.11.0 A4.1, A4.4,
A4.6, A1.1, A1.2, A1.3, A1.4

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


def _obj_with_prior(
    path: str, text: str, prior_text: str | None, *, sha: str = "deadbeef"
) -> ScannedObject:
    return ScannedObject(path=path, sha=sha, text=text, decodable=True, prior_text=prior_text)


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
# v0.11.0 FR1/A1.1-A1.4 — the amnesty suppression predicate: a hit is suppressed iff
# the candidate's MATCHED VALUE (never the pattern id or the layer) occurs
# case-insensitively in the SAME path's published prior text.
# ---------------------------------------------------------------------------


def test_amnesty_suppresses_a_value_already_published_at_the_same_path() -> None:
    """A1.1: same-path prior-published value never refuses."""
    obj = _obj_with_prior(
        "notes.md",
        f"still here: {_SYNTHETIC_TERM}\n",
        prior_text=f"had {_SYNTHETIC_TERM} before\n",
    )

    outcome = scan_objects([obj], terms=((_SYNTHETIC_TERM, "synthetic"),), patterns=(), slugs=())

    assert outcome.hits == ()


def test_amnesty_does_not_apply_to_a_new_path_carrying_the_same_value() -> None:
    """A1.2: the same value in a path with NO prior content (a genuinely new path)
    still refuses — the amnesty is bound to the path, not the value."""
    obj = _obj_with_prior("new-path.md", f"here: {_SYNTHETIC_TERM}\n", prior_text=None)

    outcome = scan_objects([obj], terms=((_SYNTHETIC_TERM, "synthetic"),), patterns=(), slugs=())

    assert len(outcome.hits) == 1


def test_amnesty_does_not_apply_to_a_new_value_in_an_edited_path() -> None:
    """A1.3: a value ABSENT from the prior version of an edited path still refuses —
    even though a DIFFERENT value of the same term source was present there. This is
    the smuggling-path attack the security review is asked to attempt: a predicate
    keyed on the pattern/source instead of the exact matched value would wrongly
    amnesty this."""
    other_term = "zz-other-published-term"
    obj = _obj_with_prior(
        "notes.md",
        f"now has {_SYNTHETIC_TERM}\n",
        prior_text=f"used to have {other_term}\n",
    )

    outcome = scan_objects(
        [obj],
        terms=((_SYNTHETIC_TERM, "synthetic"), (other_term, "synthetic")),
        patterns=(),
        slugs=(),
    )

    assert len(outcome.hits) == 1
    assert _SYNTHETIC_TERM not in outcome.hits[0].masked_term  # A5.2 still holds.


def test_amnesty_suppression_is_case_insensitive_on_both_sides() -> None:
    """A1.4: suppression is case-insensitive on both sides, matching the matcher's
    existing case-insensitivity on every layer."""
    obj = _obj_with_prior(
        "notes.md",
        f"still: {_SYNTHETIC_TERM}\n",
        prior_text=f"BEFORE: {_SYNTHETIC_TERM.upper()}\n",
    )

    outcome = scan_objects([obj], terms=((_SYNTHETIC_TERM, "synthetic"),), patterns=(), slugs=())

    assert outcome.hits == ()


def test_amnesty_applies_to_the_baseline_pattern_layer_too() -> None:
    """FR1's suppression predicate is applied UNIFORMLY across all three term
    layers — proven here for the baseline structural-pattern layer, not just the
    operator-term layer the other A1.x cases exercise."""
    baseline = load_baseline_patterns()
    obj = _obj_with_prior(
        "notes.md",
        f"server at {_POSITIVE_IPV4} still\n",
        prior_text=f"server at {_POSITIVE_IPV4} originally\n",
    )

    outcome = scan_objects([obj], terms=(), patterns=baseline, slugs=())

    assert outcome.hits == ()


def test_amnesty_applies_to_the_foreign_slug_layer_too() -> None:
    """FR1's suppression predicate applied to the foreign-slug layer."""
    obj = _obj_with_prior(
        "readme.md",
        f"see repos/{_SYNTHETIC_FOREIGN_SLUG}/README.md again\n",
        prior_text=f"see repos/{_SYNTHETIC_FOREIGN_SLUG}/README.md\n",
    )

    outcome = scan_objects([obj], terms=(), patterns=(), slugs=(_SYNTHETIC_FOREIGN_SLUG,))

    assert outcome.hits == ()


# ---------------------------------------------------------------------------
# code-reviewer MEDIUM finding (v0.11.0 pre-PR review) — the amnesty predicate must
# suppress a candidate ONLY when the SAME layer's matcher, re-run against prior_text,
# produces a matched value EQUAL (case-normalized) to the current matched value — never
# raw substring containment, which lets a DIFFERENT, longer prior-published value
# amnesty an unrelated new value that happens to be one of its substrings.
# ---------------------------------------------------------------------------

_POSITIVE_HOME_PATH_SUPERSTRING = "/hom" + "e/synthxabcd"  # a DIFFERENT prior value
_POSITIVE_HOME_PATH_SUBSTRING = "/hom" + "e/synthxa"  # substring of the value above
_SYNTHETIC_SLUG_SUPERSTRING_PRIOR = "the zz-fake-context-namecorp bundle"  # no \b match
_SYNTHETIC_SLUG_STANDALONE = "zz-fake-context-name"


def test_amnesty_does_not_suppress_a_baseline_hit_via_a_different_superstring_prior_value() -> None:
    """code-reviewer repro 1: a prior home-path value that is a SUPERSTRING of the new
    one (``_POSITIVE_HOME_PATH_SUPERSTRING`` extends ``_POSITIVE_HOME_PATH_SUBSTRING``
    by four characters) must NOT suppress the new, DIFFERENT, standalone value merely
    because it is an unanchored substring of the old one — the SAME `home-abs-path`
    pattern re-run against prior_text must produce a matched value EQUAL to the current
    one, and here it does not (the pattern's own boundary makes the prior match the
    FULL superstring, never the shorter substring)."""
    baseline = load_baseline_patterns()
    obj = _obj_with_prior(
        "notes.md",
        f"now at {_POSITIVE_HOME_PATH_SUBSTRING}/project\n",
        prior_text=f"was at {_POSITIVE_HOME_PATH_SUPERSTRING}/project\n",
    )

    outcome = scan_objects([obj], terms=(), patterns=baseline, slugs=())

    assert len(outcome.hits) == 1
    assert _POSITIVE_HOME_PATH_SUBSTRING not in outcome.hits[0].masked_term  # A5.2 still holds.


def test_amnesty_still_suppresses_the_exact_same_anchored_baseline_value() -> None:
    """Contrast/legitimate case: when prior_text carries the EXACT SAME anchored value
    (not merely a superstring), the hit is still suppressed — the fix narrows the
    predicate to value-equality, it does not disable the amnesty."""
    baseline = load_baseline_patterns()
    obj = _obj_with_prior(
        "notes.md",
        f"still at {_POSITIVE_HOME_PATH_SUBSTRING}/project\n",
        prior_text=f"was at {_POSITIVE_HOME_PATH_SUBSTRING}/project too\n",
    )

    outcome = scan_objects([obj], terms=(), patterns=baseline, slugs=())

    assert outcome.hits == ()


def test_amnesty_does_not_suppress_a_slug_hit_lacking_a_word_boundary_match_in_prior_text() -> None:
    """code-reviewer repro 2: prior text carrying `zz-fake-context-namecorp` (the
    synthetic slug glued to a longer word, so `\\bzz-fake-context-name\\b` never matches
    it) must NOT suppress a new STANDALONE occurrence of the slug — the slug layer's own
    word-boundary pattern, re-run against prior_text, finds no match at all, so there is
    no equal matched value to amnesty against."""
    obj = _obj_with_prior(
        "readme.md",
        f"see {_SYNTHETIC_SLUG_STANDALONE} here\n",
        prior_text=f"{_SYNTHETIC_SLUG_SUPERSTRING_PRIOR}\n",
    )

    outcome = scan_objects([obj], terms=(), patterns=(), slugs=(_SYNTHETIC_SLUG_STANDALONE,))

    assert len(outcome.hits) == 1
    assert outcome.hits[0].source_layer == "foreign repo slug"


def test_amnesty_short_circuit_continues_to_next_line_when_every_candidate_suppressed() -> None:
    """A line whose every candidate is suppressed continues to the next line rather
    than returning early — the short-circuit property survives the new guard."""
    obj = _obj_with_prior(
        "notes.md",
        f"{_SYNTHETIC_TERM} on line one\nnew-here: {_SYNTHETIC_TERM}\n",
        prior_text=f"{_SYNTHETIC_TERM} already published\n",
    )

    outcome = scan_objects([obj], terms=((_SYNTHETIC_TERM, "synthetic"),), patterns=(), slugs=())

    # Line 1 is fully suppressed (its only candidate is amnestied); line 2 carries the
    # SAME term but is amnestied too (same value, same prior text) -- both lines
    # suppressed, zero hits. Rebuilt below with a genuinely NEW value on line 2 to
    # prove the scan does not stop dead after the first suppressed line.
    assert outcome.hits == ()

    obj_with_new_value_on_line_two = _obj_with_prior(
        "notes.md",
        f"{_SYNTHETIC_TERM} on line one\nnew-here: zz-brand-new-value\n",
        prior_text=f"{_SYNTHETIC_TERM} already published\n",
    )
    outcome_two = scan_objects(
        [obj_with_new_value_on_line_two],
        terms=((_SYNTHETIC_TERM, "synthetic"), ("zz-brand-new-value", "synthetic")),
        patterns=(),
        slugs=(),
    )
    assert len(outcome_two.hits) == 1
    assert outcome_two.hits[0].line == 2


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


# ---------------------------------------------------------------------------
# v0.11.0 FR4 — an oversized (partially-scanned) object: its scanned prefix still
# produces a hit (A4.1), it always contributes a structured note independent of a hit
# (A4.4), and an oversized object whose prefix failed to decode falls back to the SAME
# binary skip class rather than a separate note (A4.6).
# ---------------------------------------------------------------------------


def _oversized_obj(
    path: str,
    text: str,
    *,
    sha: str = "deadbeef",
    decodable: bool = True,
    size_bytes: int = 6_000_000,
    scanned_bytes: int = 5_242_880,
    prior_text: str | None = None,
) -> ScannedObject:
    return ScannedObject(
        path=path,
        sha=sha,
        text=text,
        decodable=decodable,
        oversized=True,
        size_bytes=size_bytes,
        scanned_bytes=scanned_bytes,
        prior_text=prior_text,
    )


def test_oversized_object_produces_a_hit_when_its_scanned_prefix_matches() -> None:
    """A4.1: an oversized (partially-scanned) TEXT object still produces a hit when its
    scanned prefix carries a matching value — the fail-open is now partial coverage,
    not zero coverage."""
    obj = _oversized_obj("big.md", f"leading noise {_SYNTHETIC_TERM} here\n")

    outcome = scan_objects([obj], terms=((_SYNTHETIC_TERM, "synthetic"),), patterns=(), slugs=())

    assert len(outcome.hits) == 1
    assert outcome.hits[0].path == "big.md"


def test_oversized_object_always_produces_a_note_even_with_no_hit() -> None:
    """A4.4: every oversized (decodable) object produces a structured note — path,
    total size and scanned bytes — independent of whether a hit was found."""
    obj = _oversized_obj("big.md", "nothing sensitive here\n")

    outcome = scan_objects([obj], terms=(), patterns=(), slugs=())

    assert outcome.hits == ()
    assert len(outcome.oversized_notes) == 1
    note = outcome.oversized_notes[0]
    assert note.path == "big.md"
    assert note.size_bytes == 6_000_000
    assert note.scanned_bytes == 5_242_880


def test_oversized_object_with_undecodable_prefix_counts_as_binary_only() -> None:
    """A4.6: an oversized object whose prefix failed to decode (``decodable=False``)
    falls back to the SAME binary skip class as any other undecodable blob — it does
    NOT also produce an oversized note (there is nothing honest to report about a scan
    that never ran)."""
    obj = _oversized_obj("big.bin", "", decodable=False)

    outcome = scan_objects([obj], terms=((_SYNTHETIC_TERM, "synthetic"),), patterns=(), slugs=())

    assert outcome.hits == ()
    assert outcome.skipped_binary_count == 1
    assert outcome.oversized_notes == ()


# ---------------------------------------------------------------------------
# code-reviewer MEDIUM finding M3 support (v0.11.0 pre-PR review) — pin the matcher
# side of the "oversized-never-amnestied" boundary: the suppression predicate is
# evaluated identically for an oversized object exactly as for any other — `oversized`
# never special-cases it. The real product-level guarantee that an oversized CURRENT
# object never carries prior_text is enforced at the ADAPTER
# (git_objects.py, pinned by
# test_new_objects_oversized_current_object_never_carries_prior_text_even_with_resolvable_base
# in tests/unit/infrastructure/test_git_object_reader.py); this test composes an
# oversized object WITH prior_text set (the shape the matcher-level tests were
# previously missing) and proves a value absent from that prior text still refuses.
# ---------------------------------------------------------------------------


def test_oversized_object_carrying_prior_text_still_hits_when_value_not_amnestied() -> None:
    obj = _oversized_obj(
        "big.md",
        f"leading noise {_SYNTHETIC_TERM} here\n",
        prior_text="unrelated prior content\n",
    )

    outcome = scan_objects([obj], terms=((_SYNTHETIC_TERM, "synthetic"),), patterns=(), slugs=())

    assert len(outcome.hits) == 1
    assert outcome.hits[0].path == "big.md"
    assert len(outcome.oversized_notes) == 1  # A4.4: the note is independent of the hit.
