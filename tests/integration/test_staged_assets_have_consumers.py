"""Every staged asset has a real consumer; what has none is not produced or checked.

Intent: CONTRACT — sa-staged-assets-without-consumers#44.1, #44.2, #44.3, #44.4, #44.5.
Size: MEDIUM (a real stage + install into tmp_path; the public doctor through the CLI).
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.infrastructure.agent_transcodes import codex_agent_toml_bytes
from dadaia_workspace.infrastructure.json_agent_model_policy_store import _RETIRED_AGENT_NAMES
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.helpers.harness_profile import register_all

pytestmark = pytest.mark.slow(reason="real public stage + install into tmp_path")

_PKG = Path(__file__).resolve().parents[2] / "dadaia_workspace"

#: 44.2 — every staged family and the production module that reads it from
#: ``.dadaia/agentic/`` (literal; the check is that the reader names the family).
_READERS = {
    "agents": "infrastructure/projection_rules.py",
    "skills": "infrastructure/projection_rules.py",
    "data": "infrastructure/projection_rules.py",
    "schemas": "core/handoff_index.py",
    "manifest.json": "infrastructure/public_assets.py",
}


def _installed(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    register_all(ws)
    FileSystemPublicAssetManager().install(ws)
    return ws


def test_public_doctor_neither_needs_nor_names_an_agents_index(tmp_path: Path) -> None:
    """sa-staged-assets-without-consumers#44.1."""
    ws = _installed(tmp_path)
    (ws / ".dadaia" / "agentic" / "agents.index.json").unlink(missing_ok=True)

    with patch("dadaia_workspace.cli.commands.public.resolve_workspace_root", return_value=ws):
        result = CliRunner().invoke(app, ["public", "doctor"])

    assert "agents.index" not in result.output
    assert result.exit_code == 0, result.output


def test_every_staged_family_has_a_registered_production_reader(tmp_path: Path) -> None:
    """sa-staged-assets-without-consumers#44.2."""
    ws = tmp_path / "ws"
    FileSystemPublicAssetManager().stage(ws)
    staged = sorted(p.name for p in (ws / ".dadaia" / "agentic").iterdir())

    assert staged == sorted(_READERS)
    for family, reader in _READERS.items():
        assert family.split(".")[0] in (_PKG / reader).read_text(encoding="utf-8"), family


def test_rules_is_no_claude_family_and_only_the_codex_policy(tmp_path: Path) -> None:
    """sa-staged-assets-without-consumers#44.3."""
    ws = _installed(tmp_path)
    with patch("dadaia_workspace.cli.commands.public.resolve_workspace_root", return_value=ws):
        result = CliRunner().invoke(app, ["public", "doctor"])

    assert not (ws / ".claude" / "rules").exists()
    assert "rule-corpus" not in result.output
    assert sorted(p.name for p in (ws / ".codex" / "rules").iterdir()) == [
        "dadaia-command-policy.rules"
    ]


def _persona_without_model(tmp_path: Path) -> Path:
    persona = tmp_path / "dd-extra.md"
    persona.write_text(
        "---\nname: dd-extra\ndescription: x\nactivity_class: MUTATING\n---\n# body\n",
        encoding="utf-8",
    )
    return persona


def test_a_persona_without_a_model_is_refused_on_codex(tmp_path: Path) -> None:
    """sa-staged-assets-without-consumers#44.4 (Codex): no silent default model."""
    with pytest.raises(PublicAssetError):
        codex_agent_toml_bytes(_persona_without_model(tmp_path), "dd-extra", None)


def test_a_persona_without_a_model_is_refused_on_claude(tmp_path: Path) -> None:
    """sa-staged-assets-without-consumers#44.4 (Claude): no session-model inheritance."""
    ws = tmp_path / "ws"
    register_all(ws)
    manager = FileSystemPublicAssetManager()
    manager.stage(ws)
    staged = ws / ".dadaia" / "agentic" / "agents" / "dd-extra.md"
    staged.write_bytes(_persona_without_model(tmp_path).read_bytes())

    with pytest.raises(PublicAssetError):
        manager.install(ws)


#: Retired persona names: the code's own rename table plus the pre-consolidation roles.
_RETIRED_ROLES = frozenset(_RETIRED_AGENT_NAMES) | {
    "qa-engineer",
    "software-architect",
    "security-reviewer",
}
_COUNT = re.compile(
    r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve) core "
    r"(agents|personas)\b",
    re.IGNORECASE,
)
_FIXTURE_AGENT = re.compile(r"""\bagent"?\s*[:=]\s*["']([a-z-]+)["']""")


def test_no_persona_count_literal_and_no_retired_fixture_role() -> None:
    """sa-staged-assets-without-consumers#44.5: a persona count derives from CORE_AGENTS —
    no count literal in public/** or infrastructure docstrings — and no retired role is
    a fixture agent under tests/ or in production."""
    counted = [
        f"{path.relative_to(_PKG)}"
        for root in (_PKG / "public", _PKG / "infrastructure")
        for path in sorted(root.rglob("*"))
        if path.suffix in {".md", ".py", ".json"}
        and _COUNT.search(path.read_text(encoding="utf-8", errors="replace"))
    ]
    assert counted == []
    tests = Path(__file__).resolve().parents[1]
    retired = [
        f"{path}:{name}"
        for root in (tests, _PKG)
        for path in sorted(root.rglob("*"))
        if path.suffix in {".py", ".json"} and path.name != Path(__file__).name
        for name in _FIXTURE_AGENT.findall(path.read_text(encoding="utf-8", errors="replace"))
        if name in _RETIRED_ROLES
    ]
    assert retired == []
