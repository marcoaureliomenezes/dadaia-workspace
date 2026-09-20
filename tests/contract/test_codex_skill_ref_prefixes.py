"""Contract — D-CX-7 stays live for the ``dd-`` skill family (SPEC v0.10.0 FR13(b)),
and every ``_CODEX_SKILL_REF_PREFIXES`` entry binds to a real asset (v0.4.3 A22.6).

Intent: CONTRACT — v0.10.0 A13.3; v0.4.3 A22.6

``_CODEX_SKILL_REF_PREFIXES`` (``codex_assets.py``) gates which backtick-quoted
skill references a projected Codex persona's ``developer_instructions`` are even
checked for existence (``codex_doctor.py``, ``dcx7_codex_skill_refs``). The tuple
used to carry the literal ``"drift-detection"`` — after the family rename to
``dd-*`` (ADR #12/E-6), that literal no longer matches anything, and unless the
tuple also gains a ``"dd-"`` prefix, D-CX-7 silently stops validating the entire
new family: no error, no drift line, just quiet fail-open.

The tuple also once carried ``"memory-ctx"``, backed by the Codex-only runtime
adapter family. 0.4.7 FR3 retired that family with the ``.codex/skills`` copy — Codex
reads the shared ``.agents/skills`` tree natively — so the only backing left is a real
``public/skills/`` name. A22.6 binds the WHOLE tuple to that on-disk inventory, so a
future phantom fails this test instead of gating nothing, forever, in silence.

This file also proves the gate is alive for ``dd-`` names by construction: a
projected Codex persona citing a non-existent ``dd-`` skill must produce the D-CX-7
``missing skill`` ERROR line, and one citing a real family skill must not.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.codex_doctor import dcx7_codex_skill_refs
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _CODEX_SKILL_REF_PREFIXES,
)

pytestmark = pytest.mark.contract

_PUBLIC = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public"


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
        "Follow the `dd-release-implementation` skill for this stage.",
    )
    _make_skill(tmp_path, "dd-release-implementation")

    assert dcx7_codex_skill_refs(tmp_path) == []


# ---------------------------------------------------------------------------
# A22.6 — the whole tuple binds to the real inventory, not to memory
# ---------------------------------------------------------------------------


def _skill_names(public_dir: Path) -> set[str]:
    return {d.name for d in (public_dir / "skills").iterdir() if d.is_dir()}


def _is_phantom_prefix(prefix: str, skill_names: set[str]) -> bool:
    """True when *prefix* is backed by no real ``public/skills/`` entry. The single
    detector both the inventory-binding test and its own self-test below exercise."""
    return not any(name.startswith(prefix) for name in skill_names)


def test_codex_skill_ref_prefixes_bind_to_the_real_inventory() -> None:
    """A22.6: every ``_CODEX_SKILL_REF_PREFIXES`` entry is backed by a real
    ``public/skills/`` source skill — derived from the inventory, so a future phantom
    fails loud."""
    skill_names = _skill_names(_PUBLIC)

    phantoms = [
        prefix for prefix in _CODEX_SKILL_REF_PREFIXES if _is_phantom_prefix(prefix, skill_names)
    ]

    assert not phantoms, (
        f"phantom _CODEX_SKILL_REF_PREFIXES entries (match no public/skills/ name): {phantoms}"
    )


def test_phantom_prefix_detector_catches_a_fabricated_phantom() -> None:
    """Self-test of ``_is_phantom_prefix`` itself: a synthetic prefix backed by no
    real skill must be caught — proving the inventory-binding test above would
    actually fail on a genuine phantom, not just happen to pass on today's clean
    tuple."""
    skill_names = _skill_names(_PUBLIC)

    assert _is_phantom_prefix("totally-fabricated-phantom-prefix-", skill_names)
