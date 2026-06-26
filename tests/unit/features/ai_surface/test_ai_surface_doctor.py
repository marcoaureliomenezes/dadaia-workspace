"""Unit tests for the AI-surface doctor check (v0.1.24 WS-7 / epic §8.6).

Covers the documented rule-set:
- the current dehydrated surface PASSES (real tree, no [drift]);
- planted ritual in an UN-bannered surface FAILS;
- the same ritual in a BANNERED skill PASSES (banner exemption);
- ritual inside a lifecycle_fragments/ file PASSES (fragment exemption);
- a marker *legend* is NOT a false positive.
"""

from __future__ import annotations

from pathlib import Path

import dadaia_workspace
from dadaia_workspace.features.ai_surface.doctor import (
    BANNER_MARKER,
    check_ai_surface_ritual,
)

_REAL_PUBLIC_DIR = Path(dadaia_workspace.__file__).parent / "public"

_SDD_HARD_STOP_BLOCK = (
    "## SDD HARD STOP\n\n"
    "```\n[SDD HARD STOP]\nCannot proceed without an approved release context.\n```\n"
)

_NUMBERED_RESERVE_RITUAL = (
    "## Task lifecycle\n\n"
    "1. Read ACTIVE.md to confirm release + phase.\n"
    "2. Read SPEC.md, PLAN.md, TASKS.md.\n"
    "3. Reserve your task: flip `[ ]` -> `[-]` before editing.\n"
    "4. Complete the work, then flip `[-]` -> `[x]`.\n"
)

_MARKER_LEGEND = (
    "Use only these markers:\n\n"
    "```text\n[ ] OPEN\n[-] IN PROGRESS\n[x] DONE\n```\n\n"
    "Do not take a task already marked `[-]`.\n"
)


def _drift_lines(reports: list[str]) -> list[str]:
    return [r for r in reports if r.startswith("[drift]")]


# --- (a) the current dehydrated surface passes -------------------------------------


def test_real_dehydrated_surface_passes() -> None:
    reports = check_ai_surface_ritual(_REAL_PUBLIC_DIR)
    assert _drift_lines(reports) == [], (
        "the shipped dehydrated AI surface must carry no reintroduced lifecycle ritual; "
        f"unexpected drift: {_drift_lines(reports)}"
    )
    assert any(r.startswith("[ok] ai-surface") for r in reports)


# --- (b) planted ritual in an UN-bannered surface fails ----------------------------


def test_unbannered_agents_md_with_hard_stop_fails(tmp_path: Path) -> None:
    public = tmp_path / "public"
    (public / "data").mkdir(parents=True)
    (public / "data" / "AGENTS.md").write_text(
        "# Root Rules\n\n" + _SDD_HARD_STOP_BLOCK, encoding="utf-8"
    )
    drifts = _drift_lines(check_ai_surface_ritual(public))
    assert drifts, "an [SDD HARD STOP] block in data/AGENTS.md must be flagged"
    assert "AISURF-1" in drifts[0]
    assert "data/AGENTS.md" in drifts[0]


def test_unbannered_skill_with_numbered_reserve_fails(tmp_path: Path) -> None:
    public = tmp_path / "public"
    skill = public / "skills" / "some-lifecycle-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "# Lifecycle skill\n\n" + _NUMBERED_RESERVE_RITUAL, encoding="utf-8"
    )
    drifts = _drift_lines(check_ai_surface_ritual(public))
    assert drifts, "a numbered reserve ritual in an unbannered skill must be flagged"
    assert any("AISURF-2" in d for d in drifts)


# --- (c) bannered skill with the same ritual passes (exemption) --------------------


def test_bannered_skill_with_ritual_passes(tmp_path: Path) -> None:
    public = tmp_path / "public"
    skill = public / "skills" / "some-lifecycle-skill"
    skill.mkdir(parents=True)
    body = (
        "# Lifecycle skill\n\n"
        f"> {BANNER_MARKER} Ordered execution is owned by the dadaia-workflows.\n\n"
        + _NUMBERED_RESERVE_RITUAL
        + _SDD_HARD_STOP_BLOCK
    )
    (skill / "SKILL.md").write_text(body, encoding="utf-8")
    drifts = _drift_lines(check_ai_surface_ritual(public))
    assert drifts == [], f"a bannered skill must be exempt even with ritual; got drift: {drifts}"


def test_banner_does_not_exempt_dehydrated_agents_md(tmp_path: Path) -> None:
    """AGENTS.md is fully dehydrated and NOT banner-eligible — the banner must not
    launder ritual back into it."""
    public = tmp_path / "public"
    (public / "scaffold").mkdir(parents=True)
    (public / "scaffold" / "AGENTS.md").write_text(
        f"> {BANNER_MARKER}\n\n" + _SDD_HARD_STOP_BLOCK, encoding="utf-8"
    )
    drifts = _drift_lines(check_ai_surface_ritual(public))
    assert drifts, "a banner must NOT exempt the fully-dehydrated AGENTS.md pair"
    assert "scaffold/AGENTS.md" in drifts[0]


# --- (d) ritual inside lifecycle_fragments/ passes --------------------------------


def test_fragment_ritual_passes(tmp_path: Path) -> None:
    """Fragments ARE the ritual by design — a fragment carrying ritual is not scanned.

    The shipped globs do not reach lifecycle_fragments/, so it is exempt by scope; this
    asserts that a fragment SKILL-named file under the fragments tree is never flagged.
    """
    public = tmp_path / "public"
    frag = public / "lifecycle_fragments" / "release_definition"
    frag.mkdir(parents=True)
    (frag / "spec-create.md").write_text(
        _NUMBERED_RESERVE_RITUAL + _SDD_HARD_STOP_BLOCK, encoding="utf-8"
    )
    # Also place a skill-shaped file inside the fragments tree to prove the explicit
    # fragments-dir guard short-circuits even if a glob ever reached it.
    (frag / "SKILL.md").write_text(_SDD_HARD_STOP_BLOCK, encoding="utf-8")
    drifts = _drift_lines(check_ai_surface_ritual(public))
    assert drifts == [], f"fragment bodies must never be flagged; got: {drifts}"


# --- false-positive guards ---------------------------------------------------------


def test_marker_legend_is_not_flagged(tmp_path: Path) -> None:
    public = tmp_path / "public"
    (public / "data").mkdir(parents=True)
    (public / "data" / "AGENTS.md").write_text(
        "# Root Rules\n\n" + _MARKER_LEGEND, encoding="utf-8"
    )
    drifts = _drift_lines(check_ai_surface_ritual(public))
    assert drifts == [], f"a marker legend must not be a false positive; got: {drifts}"


def test_descriptive_pointer_is_not_flagged(tmp_path: Path) -> None:
    """The dehydrated AGENTS.md mentions the ritual to say it's owned elsewhere — a
    prose pointer (no numbered procedure, no hard-stop token, no then-sequenced read)
    must pass."""
    public = tmp_path / "public"
    (public / "data").mkdir(parents=True)
    (public / "data" / "AGENTS.md").write_text(
        "# Root Rules\n\n"
        "**Ordered lifecycle is owned by the dadaia-workflows, not by this file.** "
        "The ordered ritual — reading SPEC/PLAN/TASKS, reserving a task, the per-phase "
        "definition -> implementation -> review -> closure sequence — is executed by "
        "the dadaia-workflows. Open `dadaia panel` for the full description.\n",
        encoding="utf-8",
    )
    drifts = _drift_lines(check_ai_surface_ritual(public))
    assert drifts == [], f"a descriptive owned-elsewhere pointer must not be flagged; got: {drifts}"


def test_missing_public_dir_returns_empty(tmp_path: Path) -> None:
    assert check_ai_surface_ritual(tmp_path / "nope") == []
