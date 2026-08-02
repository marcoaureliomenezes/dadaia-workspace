"""By-name rule citations must be verified on the Claude path too, not only Codex.

Bug ``rule-corpus-reachability-unchecked-on-claude-path``: the reachability check bailed
out when ``.codex/agents`` was absent, so a claude-only workspace verified nothing — even
though the corpus *lives* at ``.claude/rules`` and its citers are ``.claude/agents/*.md``
and ``.claude/skills/*/SKILL.md``. Two consequences went unseen:

* a skill cited a ``bug-always-solved`` rule that does not exist (and contradicts
  ``bug-hotfix-doctrine``) — invisible because the Codex-only regex required backticks;
* ``dadaia-workspace-dev-guardrail`` was cited by nothing at all.

An agent that follows a citation to a rule that is not there gets no law and no error.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.codex_doctor import check_rule_corpus_reachable


@pytest.fixture
def claude_only(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    (ws / ".claude" / "rules").mkdir(parents=True)
    (ws / ".claude" / "agents").mkdir(parents=True)
    (ws / ".claude" / "skills" / "some-skill").mkdir(parents=True)
    (ws / ".claude" / "rules" / "real-rule.md").write_text("# real-rule\n", encoding="utf-8")
    return ws


def test_claude_only_workspace_is_actually_checked(claude_only: Path) -> None:
    (claude_only / ".claude" / "agents" / "a.md").write_text(
        "Follow the `real-rule` rule.\n", encoding="utf-8"
    )
    lines = check_rule_corpus_reachable(claude_only)
    assert any("[ok]" in line and "rule-corpus" in line for line in lines), (
        f"a claude-only workspace must be verified, not skipped; got {lines}"
    )


def test_a_citation_with_no_rule_file_is_an_error(claude_only: Path) -> None:
    (claude_only / ".claude" / "agents" / "a.md").write_text(
        "Follow the `ghost-rule` rule.\n", encoding="utf-8"
    )
    lines = check_rule_corpus_reachable(claude_only)
    assert any("[error]" in line and "ghost-rule" in line for line in lines), lines


def test_an_unbackticked_citation_is_still_a_citation(claude_only: Path) -> None:
    """The Codex regex required backticks, so prose citations were invisible.

    This is the exact shape that hid ``bug-always-solved``: a heading, not code span.
    """
    (claude_only / ".claude" / "skills" / "some-skill" / "SKILL.md").write_text(
        "### 3. Apply the bug-always-solved rule\n", encoding="utf-8"
    )
    lines = check_rule_corpus_reachable(claude_only)
    assert any("[error]" in line and "bug-always-solved" in line for line in lines), lines


def test_a_multiword_phrase_that_is_not_a_slug_is_not_treated_as_a_citation(
    claude_only: Path,
) -> None:
    """Guard against the loosened regex turning ordinary prose into false errors."""
    (claude_only / ".claude" / "agents" / "a.md").write_text(
        "This is the golden rule and the review gate rule of thumb.\n", encoding="utf-8"
    )
    assert not [line for line in check_rule_corpus_reachable(claude_only) if "[error]" in line]


def test_a_rule_nobody_cites_is_surfaced(claude_only: Path) -> None:
    (claude_only / ".claude" / "rules" / "orphan-rule.md").write_text("x\n", encoding="utf-8")
    (claude_only / ".claude" / "agents" / "a.md").write_text(
        "Follow the `real-rule` rule.\n", encoding="utf-8"
    )
    lines = check_rule_corpus_reachable(claude_only)
    assert any("orphan-rule" in line and "[warn]" in line for line in lines), (
        f"a rule no artifact cites is dead law — say so; got {lines}"
    )
