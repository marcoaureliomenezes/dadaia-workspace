"""Unit tests for the AI-surface doctor check (v0.1.24 WS-7 / epic §8.6).

Covers the documented rule-set:
- the current dehydrated surface PASSES (real tree, no [drift]);
- the banner-exemption flag matrix (unbannered fails, bannered passes, fragment
  exempt, and — critically — a banner does NOT launder the fully-dehydrated
  AGENTS.md pair);
- the not-flagged negatives (marker legend, descriptive pointer, missing dir).
"""

from __future__ import annotations

from pathlib import Path

import pytest

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


def test_real_dehydrated_surface_passes() -> None:
    reports = check_ai_surface_ritual(_REAL_PUBLIC_DIR)
    assert _drift_lines(reports) == [], (
        "the shipped dehydrated AI surface must carry no reintroduced lifecycle ritual; "
        f"unexpected drift: {_drift_lines(reports)}"
    )
    assert any(r.startswith("[ok] ai-surface") for r in reports)


def test_banner_does_not_exempt_dehydrated_agents_md(tmp_path: Path) -> None:
    """AGENTS.md is fully dehydrated and NOT banner-eligible — the banner must not
    launder ritual back into it. This is the laundering hole the check exists to close."""
    public = tmp_path / "public"
    (public / "scaffold").mkdir(parents=True)
    (public / "scaffold" / "AGENTS.md").write_text(
        f"> {BANNER_MARKER}\n\n" + _SDD_HARD_STOP_BLOCK, encoding="utf-8"
    )
    drifts = _drift_lines(check_ai_surface_ritual(public))
    assert drifts, "a banner must NOT exempt the fully-dehydrated AGENTS.md pair"
    assert "scaffold/AGENTS.md" in drifts[0]


@pytest.mark.parametrize(
    ("relpath", "body_fn", "expect_drift", "expect_code"),
    [
        pytest.param(
            "data/AGENTS.md",
            lambda: "# Root Rules\n\n" + _SDD_HARD_STOP_BLOCK,
            True,
            "AISURF-1",
            id="unbannered-agents-md-hard-stop-fails",
        ),
        pytest.param(
            "skills/some-lifecycle-skill/SKILL.md",
            lambda: "# Lifecycle skill\n\n" + _NUMBERED_RESERVE_RITUAL,
            True,
            "AISURF-2",
            id="unbannered-skill-numbered-reserve-fails",
        ),
        pytest.param(
            "skills/some-lifecycle-skill/SKILL.md",
            lambda: (
                "# Lifecycle skill\n\n"
                f"> {BANNER_MARKER} Ordered execution is owned by the dadaia-workflows.\n\n"
                + _NUMBERED_RESERVE_RITUAL
                + _SDD_HARD_STOP_BLOCK
            ),
            False,
            None,
            id="bannered-skill-with-ritual-passes",
        ),
        pytest.param(
            "lifecycle_fragments/release_definition/spec-create.md",
            lambda: _NUMBERED_RESERVE_RITUAL + _SDD_HARD_STOP_BLOCK,
            False,
            None,
            id="fragment-body-ritual-passes-scope-exempt",
        ),
    ],
)
def test_banner_exemption_flag_matrix(
    tmp_path: Path,
    relpath: str,
    body_fn: object,
    expect_drift: bool,
    expect_code: str | None,
) -> None:
    public = tmp_path / "public"
    target = public / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body_fn(), encoding="utf-8")  # type: ignore[operator]
    drifts = _drift_lines(check_ai_surface_ritual(public))
    if expect_drift:
        assert drifts, f"expected drift for {relpath}, got none"
        if expect_code:
            assert any(expect_code in d for d in drifts)
    else:
        assert drifts == [], f"expected no drift for {relpath}; got: {drifts}"


@pytest.mark.parametrize(
    ("relpath", "content"),
    [
        pytest.param(
            "data/AGENTS.md",
            "# Root Rules\n\n" + _MARKER_LEGEND,
            id="marker-legend-not-flagged",
        ),
        pytest.param(
            "data/AGENTS.md",
            "# Root Rules\n\n"
            "**Ordered lifecycle is owned by the dadaia-workflows, not by this file.** "
            "The ordered ritual — reading SPEC/PLAN/TASKS, reserving a task, the per-phase "
            "definition -> implementation -> review -> closure sequence — is executed by "
            "the dadaia-workflows. Open `dadaia panel` for the full description.\n",
            id="descriptive-pointer-not-flagged",
        ),
    ],
)
def test_not_flagged_negatives(tmp_path: Path, relpath: str, content: str) -> None:
    public = tmp_path / "public"
    target = public / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    drifts = _drift_lines(check_ai_surface_ritual(public))
    assert drifts == [], f"expected no false-positive drift; got: {drifts}"


def test_missing_public_dir_returns_empty(tmp_path: Path) -> None:
    assert check_ai_surface_ritual(tmp_path / "nope") == []
