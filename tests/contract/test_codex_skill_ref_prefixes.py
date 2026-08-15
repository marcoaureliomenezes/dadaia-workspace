"""Contract — D-CX-7 stays live for the ``dd-`` skill family (SPEC v0.10.0 FR13(b)).

Intent: CONTRACT — v0.10.0 A13.3

``_CODEX_SKILL_REF_PREFIXES`` (``codex_assets.py:42``) gates which backtick-quoted
skill references a projected Codex persona's ``developer_instructions`` are even
checked for existence (``codex_doctor.py:269``, ``dcx7_codex_skill_refs``). The
tuple used to carry the literal ``"drift-detection"`` — after the family rename to
``dd-*`` (ADR #12/E-6), that literal no longer matches anything, and unless the
tuple also gains a ``"dd-"`` prefix, D-CX-7 silently stops validating the entire
new family: no error, no drift line, just quiet fail-open.

This test proves the gate is alive for ``dd-`` names by construction: a projected
Codex persona citing a non-existent ``dd-`` skill must produce the D-CX-7
``missing skill`` ERROR line, and one citing a real family skill must not.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.codex_doctor import dcx7_codex_skill_refs

pytestmark = pytest.mark.contract


def _rendered(result: object) -> list[str]:
    """Legacy string view of a typed doctor result (DoctorReport | list[DoctorLine])."""
    if hasattr(result, "rendered"):
        return result.rendered()  # type: ignore[attr-defined, no-any-return]
    return [
        line.render() if hasattr(line, "render") else str(line)
        for line in result  # type: ignore[union-attr]
    ]


def _make_codex_agent(workspace: Path, name: str, body: str) -> None:
    agents = workspace / ".codex" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / f"{name}.toml").write_text(
        f'name = "{name}"\ndeveloper_instructions = """\n{body}\n"""\n',
        encoding="utf-8",
    )


def _make_skill(workspace: Path, slug: str) -> None:
    skill_dir = workspace / ".agents" / "skills" / slug
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"---\nname: {slug}\n---\n", encoding="utf-8")


def test_dcx7_reports_a_non_existent_dd_skill_reference(tmp_path: Path) -> None:
    """A citation of a synthetic ``dd-nonexistent`` skill trips the D-CX-7 ERROR line."""
    _make_codex_agent(
        tmp_path,
        "software-engineer",
        "Follow the `dd-nonexistent` skill for this stage.",
    )

    out = _rendered(dcx7_codex_skill_refs(tmp_path))

    assert len(out) == 1
    assert out[0].startswith("[error] codex:agents/software-engineer.toml:")
    assert "missing skill 'dd-nonexistent'" in out[0]
    assert "(D-CX-7)" in out[0]


def test_dcx7_does_not_report_a_real_dd_family_skill_reference(tmp_path: Path) -> None:
    """A citation of a real, installed ``dd-`` skill produces no D-CX-7 finding."""
    _make_codex_agent(
        tmp_path,
        "software-engineer",
        "Follow the `dd-release-implement` skill for this stage.",
    )
    _make_skill(tmp_path, "dd-release-implement")

    assert dcx7_codex_skill_refs(tmp_path) == []
