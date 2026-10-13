"""The render-at-install seam at its pure-render interface:
``render_claude_agent``, ``resolve_codex_agent_model``, ``codex_agent_toml_bytes`` and the
one ``ProjectionRule``/``install_rules`` seam.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.model_registry import ResolvedAgentModel

_BUG = "merge-gate-accepts-verdict-written-by-the-merger"

_GENERIC_BODY = (
    "---\n"
    "name: dd-sw-engineer-sr\n"
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
    "model: sonnet\n"
    "gate_role: implementer\n"
    "---\n"
    "\n"
    "# Pack body\n"
)


def _staged_agent_md(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / f"{name}.md"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "case",
    [
        "injects-model-then-effort-as-last-lines-deterministic",
        "omits-effort-entirely-when-unresolved-f6",
        "strips-authored-model-line-before-injection",
        "rejects-body-without-frontmatter",
    ],
)
def test_render_claude_agent_seam(case: str, tmp_path: Path) -> None:
    from dadaia_workspace.infrastructure.agent_transcodes import (
        codex_agent_toml_bytes,
        copilot_agent_md_bytes,
    )
    from dadaia_workspace.infrastructure.install_helpers import render_claude_agent

    if case == "injects-model-then-effort-as-last-lines-deterministic":
        resolved = ResolvedAgentModel(model="sonnet", effort="xhigh", source="default")
        rendered = render_claude_agent(_GENERIC_BODY, resolved)
        head, fm, body = rendered.split("---\n", 2)
        fm_lines = fm.splitlines()
        assert fm_lines[-2] == "model: sonnet"
        assert fm_lines[-1] == "effort: xhigh"
        assert body == "\n# Body\n"
        # Deterministic: rendering twice is byte-identical.
        assert render_claude_agent(_GENERIC_BODY, resolved) == rendered

    elif case == "omits-effort-entirely-when-unresolved-f6":
        resolved = ResolvedAgentModel(model="sonnet", effort=None, source="default")
        rendered = render_claude_agent(_PACK_BODY, resolved)
        assert "effort" not in rendered
        fm = rendered.split("---\n", 2)[1]
        assert fm.splitlines()[-1] == "model: sonnet"

    elif case == "strips-authored-model-line-before-injection":
        """A pack body authors ``model:``; the seam must not emit duplicates."""
        resolved = ResolvedAgentModel(model="opus", effort="high", source="template")
        rendered = render_claude_agent(_PACK_BODY, resolved)
        assert rendered.count("model:") == 1
        assert "model: opus" in rendered
        assert "sonnet" not in rendered

    else:  # rejects-body-without-frontmatter
        """One splitter, so the Claude render, the Copilot view and the Codex TOML all refuse the
        same unclosed block."""
        resolved = ResolvedAgentModel(model="sonnet", effort="high", source="default")
        unclosed = "---\nname: x\nread_only: false\n\n# Body\n"
        md = _staged_agent_md(tmp_path, "x", unclosed)
        for render in (
            lambda: render_claude_agent(unclosed, resolved),
            lambda: copilot_agent_md_bytes(md),
            lambda: codex_agent_toml_bytes(md, "x", resolved),
        ):
            with pytest.raises(PublicAssetError, match="no closed YAML frontmatter"):
                render()


@pytest.mark.parametrize(
    ("declared", "claude", "sandbox"),
    [
        ("false", ("permissionMode: acceptEdits",), "workspace-write"),
    ],
)
def test_privilege_derives_from_read_only_on_both_harnesses(
    tmp_path: Path, declared: str, claude: tuple[str, ...], sandbox: str
) -> None:
    """read_only is the one privilege field: Claude's permission mode derives from it, and so
    does the sandbox of a writer (a read_only reviewer's Codex sandbox is pinned apart)."""
    from dadaia_workspace.infrastructure.agent_transcodes import codex_agent_toml_bytes
    from dadaia_workspace.infrastructure.install_helpers import render_claude_agent

    body = _GENERIC_BODY.replace("read_only: false", f"read_only: {declared}")
    resolved = ResolvedAgentModel(model="sonnet", effort="high", source="default")
    fm = render_claude_agent(body, resolved).split("---\n", 2)[1].splitlines()
    for line in claude:
        assert line in fm
    assert ("disallowedTools" in "\n".join(fm)) == (declared == "true")
    md = tmp_path / "dd-sw-engineer-sr.md"
    md.write_text(body, encoding="utf-8")
    toml = codex_agent_toml_bytes(md, "dd-sw-engineer-sr", resolved).decode("utf-8")
    assert f'sandbox_mode = "{sandbox}"' in toml


def test_a_read_only_persona_gets_the_workspace_write_codex_sandbox(tmp_path: Path) -> None:
    """The reviewer (read_only: true) runs ``verdict.py`` on Codex, so its sandbox is
    workspace-write; Claude still denies its edit tools."""
    from dadaia_workspace.infrastructure.agent_transcodes import codex_agent_toml_bytes
    from dadaia_workspace.infrastructure.install_helpers import render_claude_agent

    body = _GENERIC_BODY.replace("read_only: false", "read_only: true")
    resolved = ResolvedAgentModel(model="sonnet", effort="high", source="default")
    fm = render_claude_agent(body, resolved).split("---\n", 2)[1].splitlines()
    assert "permissionMode: default" in fm
    assert "disallowedTools: [Edit, Write, NotebookEdit]" in fm
    md = tmp_path / "dd-sw-engineer-sr.md"
    md.write_text(body, encoding="utf-8")
    toml = codex_agent_toml_bytes(md, "dd-sw-engineer-sr", resolved).decode("utf-8")
    assert 'sandbox_mode = "workspace-write"' in toml


@pytest.mark.parametrize(
    "body",
    [
        _GENERIC_BODY.replace("read_only: false\n", ""),
        _GENERIC_BODY.replace("read_only: false", "read_only: ADDITIVE"),
    ],
)
def test_a_persona_without_read_only_never_renders(tmp_path: Path, body: str) -> None:
    """Privilege never falls back to a silent default, on either harness."""
    from dadaia_workspace.infrastructure.agent_transcodes import codex_agent_toml_bytes
    from dadaia_workspace.infrastructure.install_helpers import render_claude_agent

    resolved = ResolvedAgentModel(model="sonnet", effort="high", source="default")
    with pytest.raises(PublicAssetError, match="read_only"):
        render_claude_agent(body, resolved)
    md = tmp_path / "dd-sw-engineer-sr.md"
    md.write_text(body, encoding="utf-8")
    with pytest.raises(PublicAssetError, match="read_only"):
        codex_agent_toml_bytes(md, "dd-sw-engineer-sr", resolved)


@pytest.mark.parametrize(
    ("agent", "persona"),
    [
        ("dd-sw-engineer-sr", "---\nname: dd-sw-engineer-sr\n---\nmodel: sonnet\n"),
        ("frontend-engineer", "---\nname: frontend-engineer\nmodel: ghost\n---\n"),
    ],
)
def test_resolve_codex_agent_model_fails_closed_for_any_agent_without_model(
    agent: str, persona: str
) -> None:
    """A persona, core or not, with neither an authored ``model:`` nor a resolved policy model
    raises, never a silent default. The one frontmatter reader is the only reader (a body
    ``model:`` line is no declaration), and an unregistered model is refused."""
    from dadaia_workspace.core.frontmatter import Frontmatter, parse
    from dadaia_workspace.infrastructure.install_helpers import resolve_codex_agent_model

    parsed = parse(persona)
    assert isinstance(parsed, Frontmatter)
    with pytest.raises(PublicAssetError, match=agent):
        resolve_codex_agent_model(agent, parsed.data.get("model"), None)


def test_an_inline_comment_is_not_part_of_the_declared_model() -> None:
    """YAML ``model: x # note`` declares ``x``."""
    from dadaia_workspace.core.frontmatter import Frontmatter, parse

    parsed = parse("---\nname: a\nmodel: sonnet # tier\n---\n")
    assert isinstance(parsed, Frontmatter)
    assert parsed.data["model"] == "sonnet"


def test_resolve_codex_agent_model_falls_back_to_staged_when_no_resolved_policy() -> None:
    """No policy: the authored ``model:`` and the resolver's own ``medium`` effort."""
    from dadaia_workspace.infrastructure.install_helpers import resolve_codex_agent_model

    model, effort = resolve_codex_agent_model("frontend-engineer", "sonnet", None)
    assert model == "gpt-5.6-terra"
    assert effort == "medium"


@pytest.mark.parametrize(
    ("staged", "effort", "model", "codex_model", "codex_effort"),
    [
        pytest.param("sonnet", "high", "opus", "gpt-5.6-sol", "high", id="policy-wins"),
        pytest.param(None, "xhigh", "sonnet", "gpt-5.6-terra", "high", id="D-3-xhigh-clamps"),
        pytest.param(None, "low", "haiku", "gpt-5.3-codex-spark", "low", id="haiku-low"),
    ],
)
def test_resolve_codex_agent_model_with_a_resolved_policy(
    staged: str | None, effort: str, model: str, codex_model: str, codex_effort: str
) -> None:
    """A resolved policy wins over an authored ``model:``; the alias becomes its Codex id and
    the effort is clamped."""
    from dadaia_workspace.infrastructure.install_helpers import resolve_codex_agent_model

    resolved = ResolvedAgentModel(model=model, effort=effort, source="template")
    got = resolve_codex_agent_model("dd-sw-engineer-sr", staged, resolved)
    assert got == (codex_model, codex_effort)


@pytest.mark.parametrize(
    ("body", "resolved", "effort"),
    [
        pytest.param(_PACK_BODY, None, None, id="plugin-body-keeps-authored-model"),
        pytest.param(
            _GENERIC_BODY,
            ResolvedAgentModel(model="sonnet", effort="xhigh", source="default"),
            "high",
            id="D-3-clamp-reaches-the-toml",
        ),
    ],
)
def test_codex_agent_toml_bytes_renders_the_mapped_model(
    tmp_path: Path, body: str, resolved: ResolvedAgentModel | None, effort: str | None
) -> None:
    from dadaia_workspace.infrastructure.agent_transcodes import codex_agent_toml_bytes

    md = _staged_agent_md(tmp_path, "agent", body)
    toml = codex_agent_toml_bytes(md, "agent", resolved).decode("utf-8")
    assert 'model = "gpt-5.6-terra"' in toml
    assert effort is None or f'model_reasoning_effort = "{effort}"' in toml


def test_force_rerenders_diverged_claude_projection_to_render_output(
    tmp_path: Path,
) -> None:
    """--force restores a hand-edited (diverged) projection to the RENDER output —
    never to the raw staged source bytes — through the same ``ProjectionRule`` seam
    every Claude agent rule uses (``projection_rules._claude_agent_rules``)."""
    from dadaia_workspace.infrastructure.install_helpers import render_claude_agent
    from dadaia_workspace.infrastructure.projection import ProjectionRule, install_rules

    resolved = ResolvedAgentModel(model="sonnet", effort="xhigh", source="default")
    dst = tmp_path / ".claude" / "agents" / "dd-sw-engineer-sr.md"
    expected = render_claude_agent(_GENERIC_BODY, resolved)

    def _render(_current: bytes | None) -> bytes:
        return expected.encode("utf-8")

    rule = ProjectionRule(
        label="claude:agents/dd-sw-engineer-sr.md", harness="claude", dst=dst, render=_render
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


def test_persona_read_only_compares_the_typed_value_and_fails_closed() -> None:
    """``read_only`` is the bool the frontmatter reader types, never a string."""
    from dadaia_workspace.infrastructure.install_helpers import persona_read_only

    assert persona_read_only({"read_only": True}) is True
    assert persona_read_only({"read_only": False}) is False
    for bad in ("true", "false", 1, None, "yes"):
        with pytest.raises(PublicAssetError, match="read_only"):
            persona_read_only({"read_only": bad})
    with pytest.raises(PublicAssetError, match="read_only"):
        persona_read_only({})


def test_the_real_personas_parse_to_a_typed_read_only() -> None:
    """The shim already types through PyYAML; it must keep doing so."""
    from dadaia_workspace.core.frontmatter import Frontmatter, parse

    personas = sorted(
        Path(__file__).resolve().parents[2].glob("dadaia_workspace/public/agents/*.md")
    )
    assert len(personas) == 5
    for persona in personas:
        parsed = parse(persona.read_text(encoding="utf-8"))
        assert isinstance(parsed, Frontmatter), persona.name
        assert type(parsed.data["read_only"]) is bool, persona.name
