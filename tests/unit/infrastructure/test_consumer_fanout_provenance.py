"""FR9 (v0.1.60) — provenance-gated consumer AGENTS.md fan-out (AC-14 / AC-11(g)).

Resolves the HIGH bug ``public-install-clobbers-consumer-repo-agents-md`` (AMENDS v0.1.58
Ruling L): a consumer root ``AGENTS.md`` is lib-owned ONLY when it carries the generated
provenance banner. A hand-authored (no-banner) consumer AGENTS.md is repo-owned and is NEVER
overwritten; no ``CLAUDE.md`` orphan is dropped beside it; and BOTH paired doctor lines are
``[foreign]`` so ``public doctor`` exits 0 (Ruling 16).

Three-way install classification for a consumer AGENTS.md:
  * **absent** → create + ``[ok]``;
  * **banner-match** (stale canonical projection) → restore + ``[updated]``;
  * **no banner** (hand-authored) → ``[foreign] — left untouched`` (the bug fix).

The fixture consumer is REGISTERED in ``spec_contexts.json`` (schema-v2 via ``_write_registry``,
QA-4) so the fan-out actually reaches it — otherwise AC-11(g) could not go RED.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import (
    _CANONICAL_AGENTS_BANNER,
    _CLAUDE_MD_STUB,
    _doctor_guardrail_pair,
    _install_workspace_guardrail_pair,
)

# A realistic BANNERED source (production data/AGENTS.md starts with the banner).
_SOURCE = _CANONICAL_AGENTS_BANNER + "\n# dadaia-workspace — Root Rules\n\nBody.\n"
_HAND_AUTHORED = "# My Game Repo\n\nHand-authored, repo-specific rules. NOT lib-originated.\n"


def _write_registry(workspace_root: Path, slug: str) -> None:
    states = workspace_root / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": slug,
                        "state": "alive",
                        "repo_slug": slug,
                        "repo_url": f"https://example.test/{slug}.git",
                        "created_at": "2026-07-04T00:00:00Z",
                        "alive_since": "2026-07-04T00:00:00Z",
                        "dead_since": None,
                        "current_branch": "main",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _source(tmp_path: Path) -> Path:
    src = tmp_path / "_src" / "AGENTS.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(_SOURCE, encoding="utf-8")
    return src


def _consumer(tmp_path: Path, slug: str = "game") -> Path:
    repo = tmp_path / "repos" / slug
    repo.mkdir(parents=True, exist_ok=True)
    _write_registry(tmp_path, slug)
    return repo


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _public_doctor_would_exit_nonzero(lines: list[str]) -> bool:
    """Replicate public.py:161-172 — exit 1 iff any line is [missing]/[drift]."""
    return any(ln.startswith("[missing]") or ln.startswith("[drift]") for ln in lines)


# ---------------------------------------------------------------------------
# Install classification (three-way)
# ---------------------------------------------------------------------------


def test_hand_authored_consumer_agents_survives_untouched(tmp_path: Path) -> None:
    """AC-14 / AC-11(g): a registered hand-authored consumer AGENTS.md is NEVER overwritten."""
    src = _source(tmp_path)
    repo = _consumer(tmp_path)
    (repo / "AGENTS.md").write_text(_HAND_AUTHORED, encoding="utf-8")

    installed: list[str] = []
    _install_workspace_guardrail_pair(src, tmp_path, force=False, installed=installed)

    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == _HAND_AUTHORED
    assert not (repo / "CLAUDE.md").exists(), "no CLAUDE.md orphan beside a foreign AGENTS.md"
    assert any(e.startswith("[foreign]") and str(repo / "AGENTS.md") in e for e in installed), (
        installed
    )
    assert not any(e.startswith("[updated]") for e in installed), installed


def test_hand_authored_survives_even_under_force(tmp_path: Path) -> None:
    """force=True must NOT override the provenance gate — foreign stays foreign."""
    src = _source(tmp_path)
    repo = _consumer(tmp_path)
    (repo / "AGENTS.md").write_text(_HAND_AUTHORED, encoding="utf-8")

    _install_workspace_guardrail_pair(src, tmp_path, force=True)

    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == _HAND_AUTHORED


def test_stale_canonical_consumer_is_restored_with_updated_line(tmp_path: Path) -> None:
    """A banner-bearing (lib-owned) stale copy is restored to canonical + [updated]."""
    src = _source(tmp_path)
    repo = _consumer(tmp_path)
    # Stale canonical: carries the banner but an older body.
    (repo / "AGENTS.md").write_text(_CANONICAL_AGENTS_BANNER + "\n# OLD body\n", encoding="utf-8")

    installed: list[str] = []
    _install_workspace_guardrail_pair(src, tmp_path, force=False, installed=installed)

    assert _sha(repo / "AGENTS.md") == _sha(src), "stale canonical must be restored"
    assert any(
        e.startswith("[updated]") and "overwrote divergent workspace-law copy" in e
        for e in installed
    ), installed
    # Its CLAUDE.md sibling is created (restored pass).
    assert (repo / "CLAUDE.md").read_text(encoding="utf-8") == _CLAUDE_MD_STUB


def test_absent_consumer_agents_is_created(tmp_path: Path) -> None:
    """Absent consumer AGENTS.md → create + [ok] (an empty slot has nothing to clobber)."""
    src = _source(tmp_path)
    repo = _consumer(tmp_path)  # no AGENTS.md written

    installed: list[str] = []
    _install_workspace_guardrail_pair(src, tmp_path, force=False, installed=installed)

    assert _sha(repo / "AGENTS.md") == _sha(src)
    assert (repo / "CLAUDE.md").read_text(encoding="utf-8") == _CLAUDE_MD_STUB
    assert any(e.startswith("[ok]") and str(repo / "AGENTS.md") in e for e in installed), installed


def test_foreign_claude_md_left_untouched_when_agents_foreign(tmp_path: Path) -> None:
    """A foreign (non-stub) CLAUDE.md beside a foreign AGENTS.md is [foreign], untouched."""
    src = _source(tmp_path)
    repo = _consumer(tmp_path)
    (repo / "AGENTS.md").write_text(_HAND_AUTHORED, encoding="utf-8")
    foreign_claude = "# hand-authored CLAUDE\n"
    (repo / "CLAUDE.md").write_text(foreign_claude, encoding="utf-8")

    installed: list[str] = []
    _install_workspace_guardrail_pair(src, tmp_path, force=True, installed=installed)

    assert (repo / "CLAUDE.md").read_text(encoding="utf-8") == foreign_claude
    assert any(e.startswith("[foreign]") and str(repo / "CLAUDE.md") in e for e in installed)


# ---------------------------------------------------------------------------
# Doctor — provenance-aware ON THE PAIR (Ruling 16) → public doctor EXITS 0
# ---------------------------------------------------------------------------


def test_doctor_pair_foreign_for_hand_authored_repo_exits_zero(tmp_path: Path) -> None:
    """AC-14: hand-authored consumer → BOTH paired lines [foreign], no [missing]/[drift]."""
    src = _source(tmp_path)
    repo = _consumer(tmp_path)
    (repo / "AGENTS.md").write_text(_HAND_AUTHORED, encoding="utf-8")
    _install_workspace_guardrail_pair(src, tmp_path, force=False)  # leaves it foreign

    lines = _doctor_guardrail_pair(src, tmp_path)

    assert "[foreign] repos/game:AGENTS.md" in lines, lines
    assert "[foreign] repos/game:CLAUDE.md" in lines, lines
    assert not any("[missing]" in ln for ln in lines), lines
    assert not _public_doctor_would_exit_nonzero(lines), (
        f"public doctor must EXIT 0 for a hand-authored consumer repo. lines: {lines}"
    )


def test_doctor_pair_ok_for_fresh_canonical_consumer(tmp_path: Path) -> None:
    """A freshly-installed (bannered) consumer → both lines [ok]."""
    src = _source(tmp_path)
    _consumer(tmp_path)
    _install_workspace_guardrail_pair(src, tmp_path, force=True)

    lines = _doctor_guardrail_pair(src, tmp_path)

    assert "[ok] repos/game:AGENTS.md" in lines, lines
    assert "[ok] repos/game:CLAUDE.md" in lines, lines


def test_doctor_flags_drift_for_stale_canonical_consumer(tmp_path: Path) -> None:
    """A banner-bearing but out-of-date consumer copy is [drift] (needs restore)."""
    src = _source(tmp_path)
    repo = _consumer(tmp_path)
    (repo / "AGENTS.md").write_text(_CANONICAL_AGENTS_BANNER + "\n# OLD body\n", encoding="utf-8")
    (repo / "CLAUDE.md").write_text(_CLAUDE_MD_STUB, encoding="utf-8", newline="")

    lines = _doctor_guardrail_pair(src, tmp_path)

    assert "[drift] repos/game:AGENTS.md" in lines, lines
