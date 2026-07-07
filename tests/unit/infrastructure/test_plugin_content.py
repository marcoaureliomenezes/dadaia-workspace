"""Plugin-pack CONTENT contract (T-60-30, v0.1.60 W3) — AC-6 + AC-7.

W3 delivers the minimal-viable pack *content*: 3 real plugin agent bodies + exactly one
skill per pack + the install-gated ``plugin-scope`` rule rewrite. W2 (``test_plugin_projection``)
already locked the projection MECHANISM with a synthetic body; this module asserts the REAL
shipped content:

* **AC-6** — each pack agent carries the required frontmatter (``name`` matching ``pack.json``,
  ``tier: 3``, ``model: claude-sonnet-4-6``, a ``tools`` list); a real in-tmp install +
  ``install_plugin`` renders the projected ``.codex/agents/<name>.toml`` on the sonnet/plugin
  tier — ``model = "gpt-5.3-codex"``, NOT ``gpt-5.5`` (ARCH-2: the Codex ``model`` field is the
  discriminator, ``model_reasoning_effort`` is not); ``[ok] public-privacy`` holds with the pack
  content staged; EXACTLY the two named skills exist; the codex ``frontend-ctx``/``design-ctx``
  adapters are referenced, not inline-duplicated.
* **AC-7** — the PROJECTED ``.claude/rules/plugin-scope.md`` is install-gated: it names
  ``dadaia plugin install`` and the retired ``not yet distributed`` / ``no install command
  exists`` wording is GONE. RED-first: before the source rewrite lands, an in-tmp install
  projects the old wording and this test fails.

Layer: the pure-content assertions are ``unit``; the install-based assertions run a real
stage/install/doctor in ``tmp_path`` (``integration``). The file lives under
``tests/unit/infrastructure/`` per the T-60-30 write set (content-focused test).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PUBLIC = _REPO_ROOT / "dadaia_workspace" / "public"
_PLUGINS = _PUBLIC / "plugins"

# The exact enumerated pack surface — per-pack skill ROSTERS (hard ceiling).
# v0.1.60 Ruling 12 shipped exactly one skill per pack; v0.1.63 ADR-C1 amends the
# ceiling as a deliberate recorded amendment (SPEC v0.1.63 FR4/FR5, AC-6):
# frontend-design grows to 4 (T-63-20); devops grows to 4 (T-63-30).
_PACK_SKILLS: dict[str, list[str]] = {
    "frontend-design": [
        "browser-frontend-implementation",
        "design-system-authoring",
        "frontend-component-architecture",
        "visual-review-protocol",
    ],
    "devops": [
        "github-actions-cicd",
        "gitflow-release-engineering",
        "container-build-and-deploy",
        "cicd-security-hardening",
    ],
}
_EXPECTED_SKILLS = {skill for roster in _PACK_SKILLS.values() for skill in roster}

# Claude → Codex model mapping under test (registry single source of truth).
_PLUGIN_CLAUDE_MODEL = "claude-sonnet-4-6"
_PLUGIN_CODEX_MODEL = "gpt-5.3-codex"
_OPUS_CODEX_MODEL = "gpt-5.5"


# ---------------------------------------------------------------------------
# Minimal frontmatter scalar parser (stdlib-only, mirrors the no-PyYAML rule).
# `_parse_agent_frontmatter` drops `tier`, so parse the scalars directly here.
# ---------------------------------------------------------------------------


def _frontmatter_scalars(text: str) -> dict[str, str]:
    """Extract simple ``key: value`` scalar fields from the leading ``---`` block."""
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    scalars: dict[str, str] = {}
    for line in text[4 : end + 1].splitlines():
        if line[:1] in (" ", "-", "") or ":" not in line:
            continue  # skip nested list items / indented continuations
        key, _, value = line.partition(":")
        scalars[key.strip()] = value.strip().strip('"').strip("'")
    return scalars


def _has_tools_list(text: str) -> bool:
    """A ``tools:`` key with at least one ``  - `` item in the frontmatter block."""
    end = text.find("\n---\n", 4)
    block = text[4 : end + 1] if end != -1 else ""
    lines = block.splitlines()
    for i, line in enumerate(lines):
        if line.rstrip() == "tools:":
            return any(rest.lstrip().startswith("- ") for rest in lines[i + 1 : i + 2])
    return False


def _pack_names() -> list[str]:
    return sorted(_PACK_SKILLS)


def _pack_agents(pack: str) -> list[str]:
    data = json.loads((_PLUGINS / pack / "pack.json").read_text(encoding="utf-8"))
    agents = data["agents"]
    assert isinstance(agents, list) and agents, f"pack.json for {pack} declares no agents"
    return list(agents)


def _agent_pack_body(pack: str, agent: str) -> Path:
    return _PLUGINS / pack / "agents" / f"{agent}.md"


def _projected_codex_toml(ws: Path, agent: str) -> str:
    return (ws / ".codex" / "agents" / f"{agent}.toml").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# AC-6 — pure content: each pack agent carries the required frontmatter.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_every_pack_agent_carries_required_frontmatter() -> None:
    """AC-6: name matches pack.json, tier: 3, model: claude-sonnet-4-6, tools list present."""
    seen: list[str] = []
    for pack in _pack_names():
        for agent in _pack_agents(pack):
            body = _agent_pack_body(pack, agent)
            assert body.is_file(), f"missing pack agent body: {body}"
            text = body.read_text(encoding="utf-8")
            fm = _frontmatter_scalars(text)
            assert fm.get("name") == agent, (
                f"{pack}/{agent}: frontmatter name '{fm.get('name')}' != pack.json '{agent}'"
            )
            assert fm.get("tier") == "3", f"{pack}/{agent}: tier must be 3, got {fm.get('tier')!r}"
            assert fm.get("model") == _PLUGIN_CLAUDE_MODEL, (
                f"{pack}/{agent}: model must be {_PLUGIN_CLAUDE_MODEL}, got {fm.get('model')!r}"
            )
            assert _has_tools_list(text), f"{pack}/{agent}: frontmatter carries no tools list"
            seen.append(agent)
    # The three enumerated plugin agents, no more.
    assert sorted(seen) == ["design-specialist", "devops-engineer", "frontend-engineer"], seen


@pytest.mark.unit
def test_all_pack_agent_skill_refs_resolve_full_sweep() -> None:
    """T-63-40 full-sweep contract (FR6/AC-6): every pack-agent ``skills:`` ref for BOTH
    shipped packs resolves via the plugin-aware ``check_agent_skill_refs`` sweep — proving
    the W2/W3 wiring doctor-side. Zero plugin-agent ``[drift]`` lines on the real tree."""
    from dadaia_workspace.infrastructure.codex_doctor import check_agent_skill_refs

    plugin_drift = [
        r for r in check_agent_skill_refs(_PUBLIC) if r.startswith("[drift] plugin-agent:")
    ]
    assert plugin_drift == [], plugin_drift
    # The sweep actually covered both packs (agents exist where we claim they resolve).
    for pack in _PACK_SKILLS:
        assert list((_PLUGINS / pack / "agents").glob("*.md")), f"{pack}: no pack agents swept"


@pytest.mark.unit
def test_exactly_the_two_named_skills_ship_per_pack() -> None:
    """AC-6 (ADR-C1 ceiling): roster map == pack.json skills[] == on-disk skill dirs."""
    skill_dirs = {p.parent.name for p in _PLUGINS.glob("*/skills/*/SKILL.md")}
    assert skill_dirs == _EXPECTED_SKILLS, (
        f"pack skill set drifted from the ADR-C1 ceiling: {sorted(skill_dirs)}"
    )
    # Each pack ships exactly its enumerated roster (pack.json == roster == disk).
    for pack, roster in _PACK_SKILLS.items():
        declared = json.loads((_PLUGINS / pack / "pack.json").read_text(encoding="utf-8"))["skills"]
        assert declared == roster, f"{pack}/pack.json skills {declared} != roster {roster}"
        on_disk = sorted(p.parent.name for p in (_PLUGINS / pack / "skills").glob("*/SKILL.md"))
        assert on_disk == sorted(roster), f"{pack} on-disk skill dirs {on_disk} != roster"
        for skill in roster:
            assert (_PLUGINS / pack / "skills" / skill / "SKILL.md").is_file()


@pytest.mark.unit
@pytest.mark.parametrize(
    "skill_dir",
    ["browser-frontend-implementation", "visual-review-protocol"],
)
def test_pack_skills_reference_ctx_adapters_without_duplicating_them(skill_dir: str) -> None:
    """AC-6: ctx-referencing skills name frontend-ctx/design-ctx, never inline-copy them."""
    skill = _PLUGINS / "frontend-design" / "skills" / skill_dir / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    # Referenced by name.
    assert "frontend-ctx" in text and "design-ctx" in text, "adapters not referenced by name"
    # NOT duplicated: the adapters' distinctive emit-block markers must be absent.
    assert "=== frontend-ctx: Session Context ===" not in text, "frontend-ctx body inlined"
    assert "=== design-ctx: Session Context ===" not in text, "design-ctx body inlined"


@pytest.mark.unit
def test_every_pack_skill_no_ctx_emit_block_and_frontmatter_law() -> None:
    """AC-6 (generalized): every pack skill — name == dir slug, description present,
    and no skill inlines a ctx adapter's distinctive emit-block marker."""
    for pack, roster in _PACK_SKILLS.items():
        for skill in roster:
            path = _PLUGINS / pack / "skills" / skill / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            fm = _frontmatter_scalars(text)
            assert fm.get("name") == skill, (
                f"{pack}/{skill}: frontmatter name {fm.get('name')!r} != dir slug"
            )
            assert "description" in fm, f"{pack}/{skill}: frontmatter carries no description"
            assert "=== frontend-ctx: Session Context ===" not in text, (
                f"{path}: emit block inlined"
            )
            assert "=== design-ctx: Session Context ===" not in text, f"{path}: emit block inlined"


# ---------------------------------------------------------------------------
# AC-6 — install-based: the Codex model field is the plugin-tier discriminator.
# ---------------------------------------------------------------------------


def _install_pack(tmp_path: Path, pack: str) -> Path:
    """Real stage/install (all targets) from the package source, then enable *pack*."""
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="all")
    mgr.install_plugin(ws, pack)
    return ws


@pytest.mark.integration
@pytest.mark.parametrize(
    ("pack", "agent"),
    [("frontend-design", "frontend-engineer"), ("devops", "devops-engineer")],
)
def test_pack_agent_codex_toml_is_plugin_tier_not_opus(
    tmp_path: Path, pack: str, agent: str
) -> None:
    """AC-6 (ARCH-2): projected .codex TOML renders gpt-5.3-codex (sonnet/plugin), NOT gpt-5.5."""
    ws = _install_pack(tmp_path, pack)
    toml = _projected_codex_toml(ws, agent)
    assert f'model = "{_PLUGIN_CODEX_MODEL}"' in toml, toml
    assert _OPUS_CODEX_MODEL not in toml, (
        f"{agent}.toml leaked the opus Codex model {_OPUS_CODEX_MODEL} — model field must "
        f"discriminate the plugin tier"
    )


@pytest.mark.integration
def test_pack_content_keeps_public_privacy_ok(tmp_path: Path) -> None:
    """AC-6: with the pack content staged, doctor reports [ok] public-privacy (generic assets)."""
    ws = _install_pack(tmp_path, "frontend-design")
    report = FileSystemPublicAssetManager().doctor(ws)
    privacy = [ln for ln in report if ln.startswith("[ok] public-privacy")]
    assert privacy, f"no [ok] public-privacy line in doctor report: {report}"
    assert not [ln for ln in report if ln.startswith("[error] public-privacy")], report


# ---------------------------------------------------------------------------
# AC-7 — the PROJECTED plugin-scope rule is install-gated (RED-first).
# ---------------------------------------------------------------------------

_RETIRED_WORDING = ("not yet distributed", "no install command exists")


def _projected_plugin_scope(tmp_path: Path) -> str:
    ws = tmp_path / "ws"
    ws.mkdir()
    FileSystemPublicAssetManager().install(ws, target="all")
    return (ws / ".claude" / "rules" / "plugin-scope.md").read_text(encoding="utf-8")


@pytest.mark.integration
def test_projected_plugin_scope_names_install_command(tmp_path: Path) -> None:
    """AC-7: the projected rule names `dadaia plugin install`."""
    text = _projected_plugin_scope(tmp_path)
    assert "dadaia plugin install" in text, "plugin-scope rule does not name the install command"


@pytest.mark.integration
def test_projected_plugin_scope_drops_retired_wording(tmp_path: Path) -> None:
    """AC-7 (RED-first): the retired 'not yet distributed'/'no install command exists' is gone."""
    text = _projected_plugin_scope(tmp_path).lower()
    offenders = [phrase for phrase in _RETIRED_WORDING if phrase in text]
    assert not offenders, f"projected plugin-scope still carries retired wording: {offenders}"
