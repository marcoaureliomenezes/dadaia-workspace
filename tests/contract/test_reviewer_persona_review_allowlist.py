"""Intent: CONTRACT — DADAIA §4.2 verdict ownership (security-reviewer alone declares specs/releases/**/verdicts/**)

Contract — the four reviewer personas' declared evidence home.

`software-architect`, `qa-engineer`, `code-reviewer` and `security-reviewer` write their
evidence to the canonical home `DADAIA.md` §5.2 names — `.dadaia/reports/<ctx>/<agent>/**`
plus the handoff under `.dadaia/handoff/<ctx>/**`; `security-reviewer` alone additionally
writes `specs/releases/**/verdicts/**`, the PR-head verdict store the required gate reads
(`DADAIA.md` §4.2). `specs/releases/AGENTS.md` retired the `reviews/` directory, so no
persona may declare `specs/releases/**/reviews/**`. This pins the declared
`paths.write_allowlist` so the fleet's declared scope cannot silently drift from the canon —
the drift class `ai-engineer` exists to prevent (`DADAIA.md` §2).

`write_allowlist` is parsed at *projection* time and is persona documentation, not a
write-time control (`DADAIA.md` §3) — this contract pins the declared documentation, not a
runtime gate.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

import pytest

import dadaia_workspace
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _parse_write_allowlist,
)

pytestmark = pytest.mark.contract

_PUBLIC_AGENTS = Path(dadaia_workspace.__file__).resolve().parent / "public" / "agents"

_REVIEWER_PERSONAS = ("software-architect", "qa-engineer", "code-reviewer", "security-reviewer")

_RETIRED_REVIEWS_GLOB = "specs/releases/**/reviews/**"
_VERDICTS_GLOB = "specs/releases/**/verdicts/**"
_HANDOFF_HOME = ".dadaia/handoff/<ctx>/**"

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


def _every_persona() -> list[str]:
    return sorted(path.stem for path in _PUBLIC_AGENTS.glob("*.md"))


@pytest.mark.parametrize("persona", _every_persona())
def test_no_persona_declares_the_retired_reviews_glob(persona: str) -> None:
    allowlist = _allowlist(persona)
    assert _RETIRED_REVIEWS_GLOB not in allowlist, (
        f"{persona} declares {_RETIRED_REVIEWS_GLOB}; specs/releases/AGENTS.md retired "
        "the reviews/ directory — evidence lives in .dadaia/reports + the handoff (§5.2)"
    )


@pytest.mark.parametrize("persona", _REVIEWER_PERSONAS)
def test_reviewer_persona_declares_the_canonical_evidence_home(persona: str) -> None:
    allowlist = _allowlist(persona)
    reports_home = f".dadaia/reports/<ctx>/{persona}/**"
    assert reports_home in allowlist, (
        f"{persona} must declare {reports_home} in paths.write_allowlist (DADAIA.md §5.2)"
    )
    assert _HANDOFF_HOME in allowlist, (
        f"{persona} must declare {_HANDOFF_HOME} in paths.write_allowlist (DADAIA.md §5.2)"
    )


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
    assert _VERDICTS_GLOB in allowlist
    admitted = "specs/releases/0.5.0/verdicts/abc123.handoff.json"
    assert _admits(allowlist, admitted)


@pytest.mark.parametrize("persona", [p for p in _every_persona() if p != "security-reviewer"])
def test_only_security_reviewer_declares_verdicts_glob(persona: str) -> None:
    allowlist = _allowlist(persona)
    assert _VERDICTS_GLOB not in allowlist, (
        f"{persona} declares {_VERDICTS_GLOB}; DADAIA.md §4.2 reserves it to security-reviewer"
    )
