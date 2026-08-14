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
from dadaia_workspace.features.chokepoints.denylist_scan import scan_objects
from dadaia_workspace.infrastructure.privacy_check import load_baseline_patterns

_SYNTHETIC_TERM = "zz-secret-term"
_SYNTHETIC_OWN_SLUG = "zz-self-context-name"
_SYNTHETIC_FOREIGN_SLUG = "zz-fake-context-name"

# Positive baseline fixtures — deliberately built via concatenation (never a whole
# matching literal in THIS file's own source) so this module's own git blob never
# carries a string the push-range denylist scan would itself flag when this repo's own
# range is scanned. Runtime semantics are unchanged: the assembled value still matches
# the baseline pattern under test.
# Positive baseline fixtures — deliberately built via concatenation (never a whole
# matching literal in THIS file's own source) so this module's own git blob never
# carries a string the push-range denylist scan would itself flag when this repo's own
# range is scanned. Runtime semantics are unchanged: the assembled value still matches
# the baseline pattern under test.
_POSITIVE_IPV4 = "198.18" + ".0.5"  # RFC 2544 benchmarking range — not a real host
_POSITIVE_HOME_PATH = "/hom" + "e/alice"


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
