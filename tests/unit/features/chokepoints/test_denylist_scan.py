"""Pure push-range denylist matcher (SPEC v0.9.0 FR3/FR5/FR6).

Intent: CONTRACT — v0.9.0 A3.1, A3.4, A5.2, A6.2; v0.11.0 A1.1-A1.4, A4.1, A4.4, A4.6;
sa-private-match-rendering-has-three-renderers#B3.

Synthetic ``zz-`` terms only; baseline positives are composed at run time so this
module's own blob never carries a value the push-range scan would flag.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

import pytest

from dadaia_workspace.core.models.git_scan import ScannedObject
from dadaia_workspace.features.chokepoints.denylist_scan import _first_match, scan_objects
from dadaia_workspace.infrastructure.privacy_check import load_baseline_patterns

_TERM = "zz-secret-term"
_TERMS = ((_TERM, "synthetic"),)
_IPV4 = "198.18" + ".0.5"  # RFC 2544 benchmarking range
_HOME_LONG = "/hom" + "e/synthzqwxyz"
_HOME_SHORT = "/hom" + "e/synthzq"  # a substring of _HOME_LONG


def _obj(
    text: str, prior: str | None = None, *, path: str = "notes.md", **kw: object
) -> ScannedObject:
    return ScannedObject(
        path=path, sha="deadbeef", text=text, decodable=True, prior_text=prior, **kw
    )  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("value", "mask"),
    [
        pytest.param(_IPV4, "1…5", id="ipv4-A3.1"),
        pytest.param("/hom" + "e/alice", None, id="home-path-A3.1"),
        pytest.param("bastion" + ".local", None, id="dot-local-host"),
        pytest.param(
            "prod.workspace" + ".local", None, id="not-the-exact-workspace-local-carve-out"
        ),
        pytest.param("nas" + ".home", None, id="dot-home-host"),
    ],
)
def test_baseline_refuses_a_private_value_with_no_operator_terms(
    value: str, mask: str | None
) -> None:
    """The baseline layer alone refuses; the hit never carries the value (B3)."""
    outcome = scan_objects(
        [_obj(f"see {value} now\n")], terms=(), patterns=load_baseline_patterns()
    )

    assert [(h.path, h.line) for h in outcome.hits] == [("notes.md", 1)]
    assert value not in outcome.hits[0].masked_term
    if mask:
        assert outcome.hits[0].masked_term == mask


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("loopback at 127.0.0.1\n", id="loopback"),
        pytest.param("docs live at example.com\n", id="documentation-domain"),
        pytest.param("runner home is /home/runner/work\n", id="placeholder-home"),
        pytest.param("contact definition@dadaia.invalid\n", id="rfc2606-invalid-email"),
        pytest.param("or try someone@sub.example.test\n", id="rfc2606-test-email"),
        pytest.param("identity <dadaia@workspace.local>\n", id="product-synthetic-identity"),
        pytest.param('    return pathlib.Path.home() / ".claude"\n', id="stdlib-path-home"),
    ],
)
def test_baseline_carve_out_never_refuses(text: str) -> None:
    """A3.4: exclude_regex carve-outs apply (the refused neighbours are rows above)."""
    assert scan_objects([_obj(text)], terms=(), patterns=load_baseline_patterns()).hits == ()


@pytest.mark.parametrize(
    ("text", "prior", "terms", "hit_lines"),
    [
        pytest.param(
            f"still {_TERM}\n", f"had {_TERM}\n", _TERMS, [], id="A1.1-same-path-published"
        ),
        pytest.param(f"here {_TERM}\n", None, _TERMS, [1], id="A1.2-new-path"),
        pytest.param(
            f"now {_TERM}\n",
            "had zz-other-term\n",
            (*_TERMS, ("zz-other-term", "s")),
            [1],
            id="A1.3-new-value",
        ),
        pytest.param(
            f"still {_TERM}\n", f"HAD {_TERM.upper()}\n", _TERMS, [], id="A1.4-case-insensitive"
        ),
        pytest.param(
            f"at {_IPV4} still\n", f"at {_IPV4} first\n", None, [], id="baseline-layer-amnestied"
        ),
        pytest.param(
            f"now {_HOME_SHORT}/p\n",
            f"was {_HOME_LONG}/p\n",
            None,
            [1],
            id="superstring-prior-never-amnesties",
        ),
        pytest.param(
            f"at {_HOME_SHORT}/p\n",
            f"was {_HOME_SHORT}/p too\n",
            None,
            [],
            id="equal-anchored-value-amnestied",
        ),
        pytest.param(
            f"{_TERM} one\nnew zz-brand-new\n",
            f"{_TERM} out\n",
            (*_TERMS, ("zz-brand-new", "s")),
            [2],
            id="suppressed-line-continues-to-next",
        ),
    ],
)
def test_amnesty_is_same_path_same_layer_equal_value(
    text: str, prior: str | None, terms: tuple[tuple[str, str], ...] | None, hit_lines: list[int]
) -> None:
    """v0.11.0 FR1: a hit is suppressed iff the same layer re-run on the same path's prior text yields an equal value."""
    patterns = load_baseline_patterns() if terms is None else ()
    outcome = scan_objects([_obj(text, prior)], terms=terms or (), patterns=patterns)

    assert [h.line for h in outcome.hits] == hit_lines
    assert all(
        _TERM not in h.masked_term and _HOME_SHORT not in h.masked_term for h in outcome.hits
    )


class _CountingRegex:
    def __init__(self, inner: re.Pattern[str]) -> None:
        self._inner = inner
        self.calls = 0

    def finditer(self, text: str) -> Iterator[re.Match[str]]:
        self.calls += 1
        return self._inner.finditer(text)


@dataclass(frozen=True)
class _CountingPattern:
    regex: _CountingRegex
    id: str = "zz-synthetic"
    reason: str = "synthetic"
    exclude: re.Pattern[str] | None = None


def test_first_match_short_circuits_at_the_first_hit_line() -> None:
    counting = _CountingRegex(re.compile(re.escape(_TERM)))
    obj = _obj(f"line one has {_TERM}\n" + "noise line\n" * 500)

    hit = _first_match(obj, terms=[], patterns=[_CountingPattern(counting)])  # type: ignore[list-item]

    assert hit is not None and hit.line == 1
    assert counting.calls == 1


def test_unmasked_operator_term_absent_from_every_hit_field() -> None:
    """sa-private-match-rendering-has-three-renderers#B3."""
    outcome = scan_objects(
        [_obj(f"the value is {_TERM} here\n", path="secret.md")], terms=_TERMS, patterns=()
    )

    hit = outcome.hits[0]
    assert all(_TERM not in v for v in (hit.path, hit.masked_term, hit.source_layer))
    assert (hit.masked_term, hit.source_layer) == ("z…m", "operator denylist")


_BIG = {"oversized": True, "size_bytes": 6_000_000, "scanned_bytes": 5_242_880}


@pytest.mark.parametrize(
    ("obj", "hits", "binary", "notes"),
    [
        pytest.param(
            ScannedObject(path="b.dat", sha="d", text="", decodable=False),
            0,
            1,
            [],
            id="A6.2-binary",
        ),
        pytest.param(
            _obj(f"x {_TERM}\n", **_BIG),
            1,
            0,
            [("notes.md", 6_000_000, 5_242_880)],
            id="A4.1-prefix-hit",
        ),
        pytest.param(
            _obj("clean\n", **_BIG),
            0,
            0,
            [("notes.md", 6_000_000, 5_242_880)],
            id="A4.4-note-without-hit",
        ),
        pytest.param(
            ScannedObject(path="b.bin", sha="d", text="", decodable=False, **_BIG),
            0,
            1,
            [],
            id="A4.6-undecodable",  # type: ignore[arg-type]
        ),
        pytest.param(
            _obj(f"x {_TERM}\n", "unrelated\n", **_BIG),
            1,
            0,
            [("notes.md", 6_000_000, 5_242_880)],
            id="oversized-with-prior-not-amnestied",
        ),
    ],
)
def test_binary_and_oversized_objects(
    obj: ScannedObject, hits: int, binary: int, notes: list[tuple[str, int, int]]
) -> None:
    outcome = scan_objects([obj], terms=_TERMS, patterns=())

    assert len(outcome.hits) == hits
    assert outcome.skipped_binary_count == binary
    assert [(n.path, n.size_bytes, n.scanned_bytes) for n in outcome.oversized_notes] == notes
