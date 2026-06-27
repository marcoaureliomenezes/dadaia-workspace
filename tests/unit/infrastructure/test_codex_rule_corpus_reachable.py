"""Unit tests for WS-CDX-PROTOCOL doctor checks (T-30-B-01 / T-30-B-02).

check_codex_rule_corpus_reachable (A6): proves every by-name rule cited in a
Codex-projected agent artifact resolves to a reachable on-disk surface at
.claude/rules/<name>.md.

codex_trust_boundary_info (A7): emits the interactive-vs-headless INFO line.

All fixtures are synthesized under tmp_path — no real projection is read.
"""

from __future__ import annotations

import pathlib

from dadaia_workspace.infrastructure.codex_doctor import (
    check_codex_rule_corpus_reachable,
    codex_trust_boundary_info,
)


def _make_codex_agent(workspace: pathlib.Path, name: str, body: str) -> None:
    agents = workspace / ".codex" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / f"{name}.toml").write_text(
        f'name = "{name}"\ndeveloper_instructions = """\n{body}\n"""\n',
        encoding="utf-8",
    )


def _make_rule(workspace: pathlib.Path, name: str) -> None:
    rules = workspace / ".claude" / "rules"
    rules.mkdir(parents=True, exist_ok=True)
    (rules / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")


class TestRuleCorpusReachable:
    def test_all_citations_reachable_reports_ok(self, tmp_path: pathlib.Path) -> None:
        """Every by-name rule resolving to .claude/rules/<name>.md → single [ok] line."""
        _make_codex_agent(
            tmp_path,
            "software-engineer",
            "Follow the `workspace-protocol` rule and the `release-governance` rule.",
        )
        _make_rule(tmp_path, "workspace-protocol")
        _make_rule(tmp_path, "release-governance")

        out = check_codex_rule_corpus_reachable(tmp_path)

        assert out == ["[ok] codex:rule-corpus-reachable (WS-CDX-PROTOCOL)"]

    def test_unreachable_citation_reports_error(self, tmp_path: pathlib.Path) -> None:
        """A cited rule with no on-disk surface produces an [error] line."""
        _make_codex_agent(
            tmp_path,
            "software-engineer",
            "See the `workspace-protocol` rule and the `nonexistent-rule` rule.",
        )
        _make_rule(tmp_path, "workspace-protocol")
        # nonexistent-rule.md deliberately absent.

        out = check_codex_rule_corpus_reachable(tmp_path)

        assert len(out) == 1
        assert "nonexistent-rule" in out[0]
        assert out[0].startswith("[error] codex:rule-corpus")
        assert "WS-CDX-PROTOCOL" in out[0]

    def test_no_citations_is_silent(self, tmp_path: pathlib.Path) -> None:
        """A Codex agent that cites no by-name rule yields no output."""
        _make_codex_agent(tmp_path, "lonely", "No rules referenced here.")

        out = check_codex_rule_corpus_reachable(tmp_path)

        assert out == []

    def test_no_codex_dir_is_silent(self, tmp_path: pathlib.Path) -> None:
        """Absent .codex/agents/ → empty (not an error)."""
        assert check_codex_rule_corpus_reachable(tmp_path) == []

    def test_each_unreachable_name_reported_once(self, tmp_path: pathlib.Path) -> None:
        """A name cited by multiple agents but unreachable is reported once."""
        _make_codex_agent(tmp_path, "a", "Use the `missing-rule` rule.")
        _make_codex_agent(tmp_path, "b", "Also the `missing-rule` rule.")

        out = check_codex_rule_corpus_reachable(tmp_path)

        assert len(out) == 1
        assert "missing-rule" in out[0]


class TestTrustBoundaryInfo:
    def test_info_line_states_boundary(self) -> None:
        """A7: INFO line names interactive-fire and headless-no-fire honestly."""
        out = codex_trust_boundary_info()

        assert len(out) == 1
        line = out[0]
        assert line.startswith("[info] codex:trust-boundary")
        assert "interactive hooks fire and block" in line
        assert "`codex exec` headless does not" in line
        assert "WS-CDX-HYGIENE" in line
