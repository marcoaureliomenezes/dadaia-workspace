"""F006 (20260830-design-bug-surface-audit): the projection lane's three K3 residues.

- dcx6 is LEAK-only: the ProjectionRule table already owns missing/drift for
  ``.codex/skills/<slug>/SKILL.md`` — a second decider re-deriving the same fact is
  exactly the install/doctor-disagreement class K3 retired.
- The guardrail fan-out returns TYPED managed paths; the ledger reconciler consumes
  them instead of re-parsing ``"[ok]   "``/``"[skip] "`` strings (which silently
  dropped ``[updated]`` restores from the ledger).

Intent: contract; size: unit.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.codex_doctor import dcx6_codex_runtime_adapters
from dadaia_workspace.infrastructure.workspace_guardrail import _install_guardrail_pair


def _adapter_tree(tmp_path: Path) -> tuple[Path, Path]:
    public = tmp_path / "public"
    (public / "runtime" / "codex" / "memory-ctx").mkdir(parents=True)
    (public / "runtime" / "codex" / "memory-ctx" / "SKILL.md").write_text(
        "# skill\n", encoding="utf-8"
    )
    return tmp_path, public


def test_dcx6_is_leak_only_missing_and_drift_belong_to_the_rule_table(tmp_path: Path) -> None:
    ws, public = _adapter_tree(tmp_path)
    # Installed copy ABSENT and no leak: the rule table reports [missing]; dcx6 says nothing.
    assert dcx6_codex_runtime_adapters(ws, public) == []
    # Drift: installed copy diverges — still not dcx6's business.
    installed = ws / ".codex" / "skills" / "memory-ctx" / "SKILL.md"
    installed.parent.mkdir(parents=True)
    installed.write_text("# stale\n", encoding="utf-8")
    assert dcx6_codex_runtime_adapters(ws, public) == []


def test_dcx6_still_reports_a_claude_side_leak(tmp_path: Path) -> None:
    ws, public = _adapter_tree(tmp_path)
    leak = ws / ".claude" / "skills" / "memory-ctx" / "SKILL.md"
    leak.parent.mkdir(parents=True)
    leak.write_text("# leaked\n", encoding="utf-8")
    lines = dcx6_codex_runtime_adapters(ws, public)
    assert len(lines) == 1
    assert "must not appear here" in lines[0].render()


def test_guardrail_pair_returns_typed_managed_paths(tmp_path: Path) -> None:
    source = tmp_path / "AGENTS-src.md"
    source.write_text("> **AI agent rules.** canonical\n", encoding="utf-8")
    ws = tmp_path / "ws"
    (ws / ".dadaia" / "states").mkdir(parents=True)
    installed: list[str] = []
    managed = _install_guardrail_pair(source, ws, False, installed, targets={"workspace"})
    assert sorted(p.name for p in managed) == ["AGENTS.md", "CLAUDE.md"]
    assert all(p.is_absolute() for p in managed)


def test_ledger_reconciler_no_longer_parses_prefix_strings() -> None:
    from dadaia_workspace.infrastructure import public_assets

    src = Path(public_assets.__file__).read_text(encoding="utf-8")
    assert 'startswith("[ok]' not in src
    assert 'startswith("[skip]' not in src
