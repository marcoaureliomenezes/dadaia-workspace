"""Contract/regression test: bug-registration-guardrail template carries ``session_id``.

FR-W5-04 (release v0.1.14) — closes bug
``bug-guardrail-template-omits-required-session-id``.

The minimum bug record fenced inside
``dadaia_workspace/public/rules/bug-registration-guardrail.md`` MUST carry a
``session_id:`` frontmatter field. The bug was that the template omitted it, so
agents copy-pasting the template produced bug files that failed the required-field
schema. Two failure modes must stay closed:

1. **Source.** The canonical public rule (source of truth for every consumer) must
   carry ``session_id:`` inside its frontmatter template block.
2. **Post-stage.** ``stage()`` copies ``public/rules/`` verbatim into
   ``.dadaia/agentic/rules/`` — the staged copy that doctor hash-compares and
   ``install`` projects to every runtime. The staged rule must carry it too, so the
   projection cannot silently drop the field.

Staging runs the real ``FileSystemPublicAssetManager`` against a pytest ``tmp_path``
workspace (no real venv, no live workspace) — the existing in-test staging fixture
approach.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RULE_REL = "rules/bug-registration-guardrail.md"
_SOURCE_RULE = _REPO_ROOT / "dadaia_workspace" / "public" / _RULE_REL


def _frontmatter_template_block(text: str) -> str:
    """Extract the fenced ```markdown template block from the rule body.

    The minimum-bug-record template is the only fenced ``markdown`` block in the
    rule. We assert against the fence so the test pins the *template* agents copy,
    not an incidental ``session_id:`` mention elsewhere in the prose.
    """
    fence_open = "```markdown"
    start = text.find(fence_open)
    assert start != -1, "rule must contain a ```markdown template fence"
    body_start = start + len(fence_open)
    end = text.find("```", body_start)
    assert end != -1, "```markdown template fence must be closed"
    return text[body_start:end]


def test_source_rule_template_carries_session_id() -> None:
    """The canonical public rule's template block declares ``session_id:``."""
    assert _SOURCE_RULE.is_file(), f"missing source rule: {_SOURCE_RULE}"
    block = _frontmatter_template_block(_SOURCE_RULE.read_text(encoding="utf-8"))
    assert "session_id:" in block, (
        "bug-record template must declare session_id: (FR-W5-04 regression guard)"
    )


def test_staged_rule_template_carries_session_id(tmp_path: Path) -> None:
    """``stage()`` projects the rule with ``session_id:`` intact (post-stage)."""
    manager = FileSystemPublicAssetManager()
    manager.stage(tmp_path)

    staged_rule = tmp_path / ".dadaia" / "agentic" / "rules" / "bug-registration-guardrail.md"
    assert staged_rule.is_file(), f"rule not staged: {staged_rule}"

    block = _frontmatter_template_block(staged_rule.read_text(encoding="utf-8"))
    assert "session_id:" in block, (
        "staged bug-record template dropped session_id: — projection drift (FR-W5-04)"
    )
