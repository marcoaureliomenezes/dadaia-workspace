"""Unit tests for the v0.1.65 FR5 render-at-install seam (T-65-08).

Covers:
- ``render_claude_agent`` — the D-6 single render seam: deterministic ``model:`` then
  ``effort:`` injection as the LAST frontmatter lines; pre-existing ``model:``/``effort:``
  lines stripped (pack bodies author ``model:``); ``effort:`` OMITTED entirely when
  unresolved (F-6 plugin asymmetry — never empty/placeholder).
- F-3 fail-closed core codex render: ``install_codex_agents`` and
  ``FileSystemPublicAssetManager._codex_toml_from_md`` RAISE a loud typed
  ``PublicAssetError`` for a CORE agent supplied with neither a staged ``model:`` nor a
  resolved policy model (the silent ``claude-sonnet-4-6`` default is removed for core
  agents; kept only for plugin bodies/stubs).
- D-3 clamp: the codex ``model_reasoning_effort`` derives from the RESOLVED effort via
  the fixed clamp map (``xhigh``/``max`` → ``high``).
- F-5: ``--force`` re-RENDERS a diverged claude agent projection back to the render
  output — never to raw staged bytes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.models.agent_model_policy import ResolvedAgentModel
from dadaia_workspace.infrastructure.install_helpers import (
    install_claude_agents,
    install_codex_agents,
    render_claude_agent,
)
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

pytestmark = pytest.mark.unit

_GENERIC_BODY = (
    "---\n"
    "name: software-engineer\n"
    "description: generic implementer\n"
    "dispatch_band: 3\n"
    "---\n"
    "\n"
    "# Body\n"
)

_PACK_BODY = (
    "---\n"
    "name: frontend-engineer\n"
    "description: pack body\n"
    "dispatch_band: 3\n"
    "model: claude-sonnet-5\n"
    "gate_role: implementer\n"
    "---\n"
    "\n"
    "# Pack body\n"
)


def _iter_files(root: Path):  # type: ignore[no-untyped-def]
    if not root.exists():
        return ()
    return (p for p in sorted(root.rglob("*")) if p.is_file())


# ---------------------------------------------------------------------------
# render_claude_agent — the D-6 seam
# ---------------------------------------------------------------------------


def test_render_injects_model_then_effort_as_last_frontmatter_lines() -> None:
    resolved = ResolvedAgentModel(model="claude-sonnet-5", effort="xhigh", source="default")
    rendered = render_claude_agent(_GENERIC_BODY, resolved)
    head, fm, body = rendered.split("---\n", 2)
    fm_lines = fm.splitlines()
    assert fm_lines[-2] == "model: claude-sonnet-5"
    assert fm_lines[-1] == "effort: xhigh"
    assert body == "\n# Body\n"
    # Deterministic: rendering twice is byte-identical.
    assert render_claude_agent(_GENERIC_BODY, resolved) == rendered


def test_render_omits_effort_entirely_when_unresolved_f6() -> None:
    resolved = ResolvedAgentModel(model="claude-sonnet-5", effort=None, source="pack")
    rendered = render_claude_agent(_PACK_BODY, resolved)
    assert "effort" not in rendered
    fm = rendered.split("---\n", 2)[1]
    assert fm.splitlines()[-1] == "model: claude-sonnet-5"


def test_render_strips_authored_model_line_before_injection() -> None:
    """A pack body authors ``model:``; the seam must not emit duplicates."""
    resolved = ResolvedAgentModel(model="claude-opus-4-8", effort="high", source="override")
    rendered = render_claude_agent(_PACK_BODY, resolved)
    assert rendered.count("model:") == 1
    assert "model: claude-opus-4-8" in rendered
    assert "claude-sonnet-5" not in rendered


def test_render_rejects_body_without_frontmatter() -> None:
    resolved = ResolvedAgentModel(model="claude-sonnet-5", effort="high", source="default")
    with pytest.raises(PublicAssetError):
        render_claude_agent("# no frontmatter\n", resolved)


# ---------------------------------------------------------------------------
# F-3 — fail-closed core codex render
# ---------------------------------------------------------------------------


def _staged_tree(tmp_path: Path, name: str, text: str) -> Path:
    agentic = tmp_path / ".dadaia" / "agentic"
    (agentic / "agents").mkdir(parents=True, exist_ok=True)
    (agentic / "agents" / f"{name}.md").write_text(text, encoding="utf-8")
    return agentic


def test_install_codex_agents_fails_closed_for_core_agent_without_model(
    tmp_path: Path,
) -> None:
    """F-3: a core agent with neither staged ``model:`` nor resolved policy model
    raises loudly — never a silent claude-sonnet-4-6 default."""
    agentic = _staged_tree(tmp_path, "software-engineer", _GENERIC_BODY)
    with pytest.raises(PublicAssetError, match="software-engineer"):
        install_codex_agents(agentic, tmp_path, False, [], resolved_models={})


def test_codex_toml_from_md_fails_closed_for_core_agent_without_model(
    tmp_path: Path,
) -> None:
    md = tmp_path / "software-engineer.md"
    md.write_text(_GENERIC_BODY, encoding="utf-8")
    manager = FileSystemPublicAssetManager()
    with pytest.raises(PublicAssetError, match="software-engineer"):
        manager._codex_toml_from_md(md)


def test_codex_toml_from_md_keeps_authored_model_for_plugin_body(tmp_path: Path) -> None:
    """A plugin body that authors ``model:`` keeps working with no resolved policy."""
    md = tmp_path / "frontend-engineer.md"
    md.write_text(_PACK_BODY, encoding="utf-8")
    manager = FileSystemPublicAssetManager()
    rendered = manager._codex_toml_from_md(md)
    assert rendered is not None
    name, toml = rendered
    assert name == "frontend-engineer"
    assert 'model = "gpt-5.3-codex"' in toml


def test_install_codex_agents_uses_d3_clamp_of_resolved_effort(tmp_path: Path) -> None:
    """D-3: resolved ``xhigh`` clamps to codex ``model_reasoning_effort = "high"``."""
    agentic = _staged_tree(tmp_path, "software-engineer", _GENERIC_BODY)
    resolved = {
        "software-engineer": ResolvedAgentModel(
            model="claude-sonnet-5", effort="xhigh", source="default"
        )
    }
    installed: list[str] = []
    install_codex_agents(agentic, tmp_path, False, installed, resolved_models=resolved)
    toml = (tmp_path / ".codex" / "agents" / "software-engineer.toml").read_text(encoding="utf-8")
    assert 'model = "gpt-5.3-codex"' in toml
    assert 'model_reasoning_effort = "high"' in toml


# ---------------------------------------------------------------------------
# F-5 — --force re-renders (never re-copies staged bytes)
# ---------------------------------------------------------------------------


def test_force_rerenders_diverged_claude_projection_to_render_output(
    tmp_path: Path,
) -> None:
    agentic = _staged_tree(tmp_path, "software-engineer", _GENERIC_BODY)
    resolved = {
        "software-engineer": ResolvedAgentModel(
            model="claude-sonnet-5", effort="xhigh", source="default"
        )
    }
    installed: list[str] = []
    install_claude_agents(agentic, tmp_path / ".claude", False, installed, _iter_files, resolved)
    dst = tmp_path / ".claude" / "agents" / "software-engineer.md"
    expected = render_claude_agent(_GENERIC_BODY, resolved["software-engineer"])
    assert dst.read_text(encoding="utf-8") == expected

    dst.write_text("# hand-edited divergence\n", encoding="utf-8")
    install_claude_agents(agentic, tmp_path / ".claude", True, installed, _iter_files, resolved)
    after = dst.read_text(encoding="utf-8")
    assert after == expected, "--force must restore the RENDER output"
    assert after != _GENERIC_BODY, "--force must never re-copy raw staged bytes"
