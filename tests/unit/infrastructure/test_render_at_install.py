"""T-65-08: the v0.1.65 FR5 render-at-install seam, rewritten at the K3 (v0.5.1)
pure-render interface.

Intent: CONTRACT — v0.1.65 F-3/F-5/F-6/D-3/D-6; K3 (v0.5.1) collapses
``install_claude_agents``/``install_codex_agents`` into pure functions
(``render_claude_agent``, ``resolve_codex_agent_model``,
``projection_rules._codex_agent_toml_bytes``) plus the one ``ProjectionRule``
seam (``install_rules``) — this file tests those directly instead of the
retired per-writer delegators.

Covers:
- ``render_claude_agent`` — the D-6 single render seam: deterministic ``model:`` then
  ``effort:`` injection as the LAST frontmatter lines; pre-existing ``model:``/``effort:``
  lines stripped (pack bodies author ``model:``); ``effort:`` OMITTED entirely when
  unresolved (F-6 — never empty/placeholder); a body without frontmatter raises.
- ``resolve_codex_agent_model`` — fail-closed: ANY persona with neither an authored
  ``model:`` nor a resolved policy model raises a loud typed ``PublicAssetError``
  (sa-staged-assets-without-consumers#44.4); a resolved policy always wins over an
  authored ``model:``; D-3 clamps the resolved effort via ``codex_effort_for_claude_effort``.
- ``projection_rules._codex_agent_toml_bytes`` — the ONE codex-agent TOML renderer
  (mirrors the historical ``install_codex_agents`` per-file body): a plugin body keeps
  its authored model with no resolved policy,
  and D-3's clamp reaches the rendered ``model_reasoning_effort`` field.
- F-5: ``--force`` re-RENDERS a diverged claude agent projection back to the render
  output — never to raw staged bytes — through the real ``ProjectionRule``/
  ``install_rules`` seam every rule (Claude, Codex, guardrail, kimi) now shares.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.models.agent_model_policy import ResolvedAgentModel
from dadaia_workspace.infrastructure.agent_transcodes import codex_agent_toml_bytes
from dadaia_workspace.infrastructure.install_helpers import (
    render_claude_agent,
    resolve_codex_agent_model,
)
from dadaia_workspace.infrastructure.projection import ProjectionRule, install_rules

pytestmark = pytest.mark.unit

_GENERIC_BODY = (
    "---\n"
    "name: dd-software-engineer\n"
    "description: generic implementer\n"
    "read_only: false\n"
    "dispatch_band: 3\n"
    "---\n"
    "\n"
    "# Body\n"
)

_PACK_BODY = (
    "---\n"
    "name: frontend-engineer\n"
    "description: pack body\n"
    "read_only: false\n"
    "dispatch_band: 3\n"
    "model: claude-sonnet-5\n"
    "gate_role: implementer\n"
    "---\n"
    "\n"
    "# Pack body\n"
)


def _staged_agent_md(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / f"{name}.md"
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# render_claude_agent — the D-6 seam
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    [
        "injects-model-then-effort-as-last-lines-deterministic",
        "omits-effort-entirely-when-unresolved-f6",
        "strips-authored-model-line-before-injection",
        "rejects-body-without-frontmatter",
    ],
)
def test_render_claude_agent_seam(case: str) -> None:
    if case == "injects-model-then-effort-as-last-lines-deterministic":
        resolved = ResolvedAgentModel(model="claude-sonnet-5", effort="xhigh", source="default")
        rendered = render_claude_agent(_GENERIC_BODY, resolved)
        head, fm, body = rendered.split("---\n", 2)
        fm_lines = fm.splitlines()
        assert fm_lines[-2] == "model: claude-sonnet-5"
        assert fm_lines[-1] == "effort: xhigh"
        assert body == "\n# Body\n"
        # Deterministic: rendering twice is byte-identical.
        assert render_claude_agent(_GENERIC_BODY, resolved) == rendered

    elif case == "omits-effort-entirely-when-unresolved-f6":
        resolved = ResolvedAgentModel(model="claude-sonnet-5", effort=None, source="pack")
        rendered = render_claude_agent(_PACK_BODY, resolved)
        assert "effort" not in rendered
        fm = rendered.split("---\n", 2)[1]
        assert fm.splitlines()[-1] == "model: claude-sonnet-5"

    elif case == "strips-authored-model-line-before-injection":
        """A pack body authors ``model:``; the seam must not emit duplicates."""
        resolved = ResolvedAgentModel(model="claude-opus-4-8", effort="high", source="override")
        rendered = render_claude_agent(_PACK_BODY, resolved)
        assert rendered.count("model:") == 1
        assert "model: claude-opus-4-8" in rendered
        assert "claude-sonnet-5" not in rendered

    else:  # rejects-body-without-frontmatter
        resolved = ResolvedAgentModel(model="claude-sonnet-5", effort="high", source="default")
        with pytest.raises(PublicAssetError):
            render_claude_agent("# no frontmatter\n", resolved)


@pytest.mark.parametrize(
    ("declared", "claude", "sandbox"),
    [
        (
            "true",
            ("permissionMode: default", "disallowedTools: [Edit, Write, NotebookEdit]"),
            "read-only",
        ),
        ("false", ("permissionMode: acceptEdits",), "workspace-write"),
    ],
)
def test_privilege_derives_from_read_only_on_both_harnesses(
    tmp_path: Path, declared: str, claude: tuple[str, ...], sandbox: str
) -> None:
    """sa-reviewer-persona-body-contradicts-its-tools#B2: read_only is the one privilege
    field — Claude's permission mode and Codex's sandbox both derive from it."""
    body = _GENERIC_BODY.replace("read_only: false", f"read_only: {declared}")
    resolved = ResolvedAgentModel(model="claude-sonnet-5", effort="high", source="default")
    fm = render_claude_agent(body, resolved).split("---\n", 2)[1].splitlines()
    for line in claude:
        assert line in fm
    assert ("disallowedTools" in "\n".join(fm)) == (declared == "true")
    md = tmp_path / "dd-software-engineer.md"
    md.write_text(body, encoding="utf-8")
    toml = codex_agent_toml_bytes(md, "dd-software-engineer", resolved).decode("utf-8")
    assert f'sandbox_mode = "{sandbox}"' in toml


@pytest.mark.parametrize(
    "body",
    [
        _GENERIC_BODY.replace("read_only: false\n", ""),
        _GENERIC_BODY.replace("read_only: false", "read_only: ADDITIVE"),
    ],
)
def test_a_persona_without_read_only_never_renders(tmp_path: Path, body: str) -> None:
    """sa-reviewer-persona-body-contradicts-its-tools#B3: privilege never falls back to
    a silent default (review 0.4.7 c5 F2) — on either harness."""
    resolved = ResolvedAgentModel(model="claude-sonnet-5", effort="high", source="default")
    with pytest.raises(PublicAssetError, match="read_only"):
        render_claude_agent(body, resolved)
    md = tmp_path / "dd-software-engineer.md"
    md.write_text(body, encoding="utf-8")
    with pytest.raises(PublicAssetError, match="read_only"):
        codex_agent_toml_bytes(md, "dd-software-engineer", resolved)


# ---------------------------------------------------------------------------
# resolve_codex_agent_model — F-3 fail-closed, precedence, D-3 clamp
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("agent", ["dd-software-engineer", "frontend-engineer"])
def test_resolve_codex_agent_model_fails_closed_for_any_agent_without_model(agent: str) -> None:
    """sa-staged-assets-without-consumers#44.4: a persona, core or not, with neither an
    authored ``model:`` nor a resolved policy model raises — never a silent default."""
    with pytest.raises(PublicAssetError, match=agent):
        resolve_codex_agent_model(agent, None, None)


def test_resolve_codex_agent_model_prefers_resolved_over_staged() -> None:
    """Precedence: resolved policy wins over an authored staged ``model:``."""
    resolved = ResolvedAgentModel(model="claude-opus-4-8", effort="high", source="override")
    model, effort = resolve_codex_agent_model("dd-software-engineer", "claude-sonnet-5", resolved)
    assert model == "claude-opus-4-8"
    assert effort == "high"


def test_resolve_codex_agent_model_falls_back_to_staged_when_no_resolved_policy() -> None:
    """sa-staged-assets-without-consumers#44.4 + sa-codex-effort-set-by-policy-and-by-tier:
    no policy -> the authored ``model:`` and the resolver's own ``medium`` effort."""
    model, effort = resolve_codex_agent_model("frontend-engineer", "claude-sonnet-5", None)
    assert model == "claude-sonnet-5"
    assert effort == "medium"


def test_resolve_codex_agent_model_uses_d3_clamp_of_resolved_effort() -> None:
    """D-3: resolved ``xhigh`` clamps to codex ``model_reasoning_effort = "high"``."""
    resolved = ResolvedAgentModel(model="claude-sonnet-5", effort="xhigh", source="default")
    _model, effort = resolve_codex_agent_model("dd-software-engineer", None, resolved)
    assert effort == "high"


# ---------------------------------------------------------------------------
# projection_rules._codex_agent_toml_bytes — the ONE codex-agent TOML renderer
# ---------------------------------------------------------------------------


def test_codex_agent_toml_bytes_keeps_authored_model_for_plugin_body(tmp_path: Path) -> None:
    md = _staged_agent_md(tmp_path, "frontend-engineer", _PACK_BODY)
    toml = codex_agent_toml_bytes(md, "frontend-engineer", None).decode("utf-8")
    assert 'model = "gpt-5.6-terra"' in toml


def test_codex_agent_toml_bytes_uses_d3_clamp_of_resolved_effort(tmp_path: Path) -> None:
    md = _staged_agent_md(tmp_path, "dd-software-engineer", _GENERIC_BODY)
    resolved = ResolvedAgentModel(model="claude-sonnet-5", effort="xhigh", source="default")
    toml = codex_agent_toml_bytes(md, "dd-software-engineer", resolved).decode("utf-8")
    assert 'model = "gpt-5.6-terra"' in toml
    assert 'model_reasoning_effort = "high"' in toml


# ---------------------------------------------------------------------------
# F-5 — --force re-renders (never re-copies staged bytes)
# ---------------------------------------------------------------------------


def test_force_rerenders_diverged_claude_projection_to_render_output(
    tmp_path: Path,
) -> None:
    """--force restores a hand-edited (diverged) projection to the RENDER output —
    never to the raw staged source bytes — through the same ``ProjectionRule`` seam
    every Claude agent rule uses (``projection_rules._claude_agent_rules``)."""
    resolved = ResolvedAgentModel(model="claude-sonnet-5", effort="xhigh", source="default")
    dst = tmp_path / ".claude" / "agents" / "dd-software-engineer.md"
    expected = render_claude_agent(_GENERIC_BODY, resolved)

    def _render(_current: bytes | None) -> bytes:
        return expected.encode("utf-8")

    rule = ProjectionRule(
        label="claude:agents/dd-software-engineer.md", harness="claude", dst=dst, render=_render
    )
    install_rules((rule,), force=False)
    assert dst.read_text(encoding="utf-8") == expected

    dst.write_text("# hand-edited divergence\n", encoding="utf-8")
    install_rules((rule,), force=True)
    after = dst.read_text(encoding="utf-8")
    assert after == expected, "--force must restore the RENDER output"
    assert after != _GENERIC_BODY, "--force must never re-copy raw staged bytes"


def test_install_rules_rewrites_a_read_only_projection(tmp_path: Path) -> None:
    """Windows CI at 4ffc06b3: os.replace onto a 0o444 law file raised PermissionError.
    A changed read-only projection is made writable, rewritten, and re-pinned."""
    from dadaia_workspace.infrastructure.projection import ProjectionRule, install_rules

    dst = tmp_path / "AGENTS.md"
    dst.write_bytes(b"old")
    dst.chmod(0o444)
    rule = ProjectionRule(
        label="law",
        harness="claude",
        dst=dst,
        render=lambda _current: b"new",
        compare="bytes",
        mode=0o444,
    )

    transcript = install_rules([rule], force=False)

    assert dst.read_bytes() == b"new"
    assert [line.status for line in transcript.lines] == ["ok"]
    assert (dst.stat().st_mode & 0o777) == 0o444
