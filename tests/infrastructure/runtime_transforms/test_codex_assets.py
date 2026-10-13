"""Every ``_CODEX_SKILL_REF_PREFIXES`` entry binds to a real ``public/skills/`` name, and the
D-CX-7 check stays live for the ``dd-`` family.

``_CODEX_SKILL_REF_PREFIXES`` (``codex_assets.py``) gates which backtick-quoted skill references a
projected Codex persona's ``developer_instructions`` are checked for existence
(``codex_doctor.py``, ``dcx7_codex_skill_refs``). A phantom prefix would gate nothing, silently.

A projected Codex persona citing a non-existent ``dd-`` skill must produce the D-CX-7
``missing skill`` ERROR line, and one citing a real family skill must not.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.model_registry import ResolvedAgentModel
from dadaia_workspace.infrastructure.agent_transcodes import codex_agent_toml_bytes
from dadaia_workspace.infrastructure.codex_doctor import dcx7_codex_skill_refs
from dadaia_workspace.infrastructure.runtime_config import codex_config
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _CODEX_SKILL_REF_PREFIXES,
)

_PUBLIC = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"


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
        "dd-sw-engineer-sr",
        "Follow the `dd-nonexistent` skill for this stage.",
    )

    out = _rendered(dcx7_codex_skill_refs(tmp_path))

    assert len(out) == 1
    assert out[0].startswith("[error] codex:agents/dd-sw-engineer-sr.toml:")
    assert "missing skill 'dd-nonexistent'" in out[0]
    assert "(D-CX-7)" in out[0]


def test_dcx7_does_not_report_a_real_dd_family_skill_reference(tmp_path: Path) -> None:
    """A citation of a real, installed ``dd-`` skill produces no D-CX-7 finding."""
    _make_codex_agent(
        tmp_path,
        "dd-sw-engineer-sr",
        "Follow the `dd-release-implementation` skill for this stage.",
    )
    _make_skill(tmp_path, "dd-release-implementation")

    assert dcx7_codex_skill_refs(tmp_path) == []


# ---------------------------------------------------------------------------
# The whole tuple binds to the real inventory, not to memory
# ---------------------------------------------------------------------------


def _skill_names(public_dir: Path) -> set[str]:
    return {d.name for d in (public_dir / "skills").iterdir() if d.is_dir()}


def _is_phantom_prefix(prefix: str, skill_names: set[str]) -> bool:
    """True when *prefix* is backed by no real ``public/skills/`` entry. The single
    detector both the inventory-binding test and its own self-test below exercise."""
    return not any(name.startswith(prefix) for name in skill_names)


def test_codex_skill_ref_prefixes_bind_to_the_real_inventory() -> None:
    """Every ``_CODEX_SKILL_REF_PREFIXES`` entry is backed by a real
    ``public/skills/`` source skill — derived from the inventory, so a future phantom
    fails loud."""
    skill_names = _skill_names(_PUBLIC)

    phantoms = [
        prefix for prefix in _CODEX_SKILL_REF_PREFIXES if _is_phantom_prefix(prefix, skill_names)
    ]

    assert not phantoms, (
        f"phantom _CODEX_SKILL_REF_PREFIXES entries (match no public/skills/ name): {phantoms}"
    )


def test_a_bom_crlf_persona_projects_the_same_codex_bytes_as_its_lf_twin(tmp_path: Path) -> None:
    """A BOM or CRLF persona projects the same Codex bytes as its LF twin."""
    name = "dd-sw-engineer-sr"
    lf = (_PUBLIC / "agents" / f"{name}.md").read_bytes()
    crlf = b"\xef\xbb\xbf" + lf.replace(b"\n", b"\r\n")
    for flavour, raw in (("lf", lf), ("crlf", crlf)):
        agents = tmp_path / flavour / "agents"
        agents.mkdir(parents=True)
        (agents / f"{name}.md").write_bytes(raw)

    blocks = {f: codex_config(tmp_path / f, tmp_path) for f in ("lf", "crlf")}
    assert f'[agents."{name}"]\nconfig_file = "agents/{name}.toml"\n' in blocks["lf"]
    assert blocks["crlf"] == blocks["lf"]
    resolved = ResolvedAgentModel(model="sonnet", effort="high", source="default")
    assert codex_agent_toml_bytes(
        tmp_path / "crlf" / "agents" / f"{name}.md", name, resolved
    ) == codex_agent_toml_bytes(tmp_path / "lf" / "agents" / f"{name}.md", name, resolved)
