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

The tuple also once carried a phantom entry: ``"memory-ctx"`` matched no
``public/skills/`` source skill (T-043-32 scoping note, #37). It was NOT actually
phantom — ``memory-ctx`` is a Codex-only runtime adapter projected from
``public/runtime/codex/memory-ctx/`` to ``.codex/skills/memory-ctx/``, a real,
resolvable asset D-CX-7 already reaches via its ``.codex/skills`` root. But nothing
proved that at the time, so a genuinely dead prefix could have sat in the tuple
gating nothing, forever, with zero test failure. A22.6 binds the WHOLE tuple to the
real on-disk inventory: every entry is either a ``public/skills/`` name/prefix match
or a documented ``_CODEX_SKILL_REF_RUNTIME_ASSET_EXCEPTIONS`` entry backed by a real
``public/runtime/codex/<name>/SKILL.md`` — so a future phantom fails this test
instead of reappearing silently.

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
    _CODEX_SKILL_REF_RUNTIME_ASSET_EXCEPTIONS,
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
        "Follow the `dd-release-implement` skill for this stage.",
    )
    _make_skill(tmp_path, "dd-release-implement")

    assert dcx7_codex_skill_refs(tmp_path) == []


# ---------------------------------------------------------------------------
# A22.6 — the whole tuple binds to the real inventory, not to memory
# ---------------------------------------------------------------------------


def _skill_names(public_dir: Path) -> set[str]:
    return {d.name for d in (public_dir / "skills").iterdir() if d.is_dir()}


def _is_phantom_prefix(prefix: str, skill_names: set[str], public_dir: Path) -> bool:
    """True when *prefix* is backed by NEITHER a real ``public/skills/`` entry NOR a
    documented, on-disk runtime-asset exception. The single detector both the
    inventory-binding test and its own self-test below exercise."""
    if any(name.startswith(prefix) for name in skill_names):
        return False
    if prefix in _CODEX_SKILL_REF_RUNTIME_ASSET_EXCEPTIONS:
        adapter = public_dir / "runtime" / "codex" / prefix / "SKILL.md"
        return not adapter.is_file()
    return True


def test_codex_skill_ref_prefixes_bind_to_the_real_inventory() -> None:
    """A22.6: every ``_CODEX_SKILL_REF_PREFIXES`` entry is backed by a real
    ``public/skills/`` source skill or a documented, on-disk runtime-asset
    exception — derived from the inventory, so a future phantom fails loud."""
    skill_names = _skill_names(_PUBLIC)

    phantoms = [
        prefix
        for prefix in _CODEX_SKILL_REF_PREFIXES
        if _is_phantom_prefix(prefix, skill_names, _PUBLIC)
    ]

    assert not phantoms, (
        f"phantom _CODEX_SKILL_REF_PREFIXES entries (match no public/skills/ name and "
        f"no documented runtime-asset exception): {phantoms}"
    )


def test_runtime_asset_exceptions_are_a_declared_subset_of_the_prefixes() -> None:
    assert set(_CODEX_SKILL_REF_PREFIXES) >= _CODEX_SKILL_REF_RUNTIME_ASSET_EXCEPTIONS


def test_memory_ctx_is_a_documented_exception_backed_by_a_real_runtime_adapter() -> None:
    """The exact drift #37 named: ``memory-ctx`` matches no ``public/skills/`` entry,
    so it must be a documented exception, and that exception must be real."""
    skill_names = _skill_names(_PUBLIC)

    assert not any(name.startswith("memory-ctx") for name in skill_names)
    assert "memory-ctx" in _CODEX_SKILL_REF_RUNTIME_ASSET_EXCEPTIONS
    assert (_PUBLIC / "runtime" / "codex" / "memory-ctx" / "SKILL.md").is_file()


def test_phantom_prefix_detector_catches_a_fabricated_phantom() -> None:
    """Self-test of ``_is_phantom_prefix`` itself: a synthetic prefix backed by
    neither a real skill nor a documented exception must be caught — proving the
    inventory-binding test above would actually fail on a genuine phantom, not just
    happen to pass on today's clean tuple."""
    skill_names = _skill_names(_PUBLIC)

    assert _is_phantom_prefix("totally-fabricated-phantom-prefix-", skill_names, _PUBLIC)


def test_phantom_prefix_detector_honors_an_undocumented_exception_as_phantom(
    tmp_path: Path,
) -> None:
    """A name that would resolve as a runtime adapter but is NOT listed in
    ``_CODEX_SKILL_REF_RUNTIME_ASSET_EXCEPTIONS`` is still phantom — the exception
    list, not disk presence alone, is what the tuple must be honest about."""
    (tmp_path / "skills").mkdir()
    (tmp_path / "runtime" / "codex" / "undeclared-adapter").mkdir(parents=True)
    (tmp_path / "runtime" / "codex" / "undeclared-adapter" / "SKILL.md").write_text(
        "# adapter\n", encoding="utf-8"
    )

    assert _is_phantom_prefix("undeclared-adapter", set(), tmp_path)
