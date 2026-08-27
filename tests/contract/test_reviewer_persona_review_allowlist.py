"""Contract — the four reviewer personas' `specs/releases/**/reviews/**` grant (T-050-03A).

`software-architect`, `qa-engineer`, `code-reviewer` and `security-reviewer` write review
artifacts under a release's `reviews/` subtree; `security-reviewer` additionally writes the
`verdicts/` subtree the required PR gate reads (SPEC §9.2 SEC-R5 / N-3). This pins the
declared `paths.write_allowlist` glob against real candidate paths so the fleet's declared
scope cannot silently drift from what the release actually asks of each persona — the
drift class `ai-engineer` exists to prevent (`DADAIA.md` §2).

`write_allowlist` is parsed at *projection* time and is persona documentation, not a
write-time control (`DADAIA.md` §3) — this contract pins the declared documentation, not a
runtime gate.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

import pytest

import dadaia_workspace
from dadaia_workspace.infrastructure.public_assets import _parse_write_allowlist

pytestmark = pytest.mark.contract

_PUBLIC_AGENTS = Path(dadaia_workspace.__file__).resolve().parent / "public" / "agents"

#: The four reviewer personas this task widens — named directly from T-050-03A's write
#: set, not a separately hand-kept registry.
_REVIEWER_PERSONAS = ("software-architect", "qa-engineer", "code-reviewer", "security-reviewer")

_REVIEWS_ADMITTED = (
    "specs/releases/0.5.0/reviews/software-architect-2026-08-27.md",
    "specs/releases/0.5.0/alpha-1/reviews/qa-verdict.md",
)

_MEMORY_REJECTED = (
    "specs/memory/architecture.md",
    "specs/memory/product/index.md",
    "specs/memory/product/catalog.json",
)


def _allowlist(persona: str) -> list[str]:
    text = (_PUBLIC_AGENTS / f"{persona}.md").read_text(encoding="utf-8")
    return _parse_write_allowlist(text)


def _admits(allowlist: list[str], path: str) -> bool:
    return any(fnmatch.fnmatch(path, glob) for glob in allowlist)


@pytest.mark.parametrize("persona", _REVIEWER_PERSONAS)
def test_reviewer_persona_admits_reviews_glob(persona: str) -> None:
    allowlist = _allowlist(persona)
    assert "specs/releases/**/reviews/**" in allowlist, (
        f"{persona} must declare specs/releases/**/reviews/** in paths.write_allowlist"
    )
    for candidate in _REVIEWS_ADMITTED:
        assert _admits(allowlist, candidate), f"{persona}'s allowlist must admit {candidate}"


@pytest.mark.parametrize("persona", _REVIEWER_PERSONAS)
def test_reviewer_persona_rejects_memory_paths(persona: str) -> None:
    allowlist = _allowlist(persona)
    for candidate in _MEMORY_REJECTED:
        assert not _admits(allowlist, candidate), (
            f"{persona}'s allowlist must NOT admit {candidate} (specs/memory/** is "
            "product-engineer-only)"
        )


def test_security_reviewer_additionally_admits_verdicts_glob() -> None:
    allowlist = _allowlist("security-reviewer")
    assert "specs/releases/**/verdicts/**" in allowlist
    admitted = "specs/releases/0.5.0/verdicts/abc123.handoff.json"
    assert _admits(allowlist, admitted)


@pytest.mark.parametrize("persona", ("software-architect", "qa-engineer", "code-reviewer"))
def test_only_security_reviewer_admits_verdicts_glob(persona: str) -> None:
    allowlist = _allowlist(persona)
    assert "specs/releases/**/verdicts/**" not in allowlist
