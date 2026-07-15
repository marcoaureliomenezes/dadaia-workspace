"""Unit tests for WS-CDX-PROTOCOL doctor checks (T-30-B-01 / T-30-B-02).

check_codex_rule_corpus_reachable (A6): proves every by-name rule cited in a
Codex-projected agent artifact resolves to a reachable on-disk surface at
.claude/rules/<name>.md.

codex_trust_boundary_info (A7): emits the interactive-vs-headless INFO line.

All fixtures are synthesized under tmp_path — no real projection is read.
"""

from __future__ import annotations

import pathlib

import pytest

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


@pytest.mark.parametrize(
    "case",
    [
        "all-reachable-ok",
        "unreachable-reports-error",
        "no-citations-silent",
        "no-codex-dir-silent",
        "unreachable-name-deduped",
    ],
)
def test_rule_corpus_reachable(tmp_path: pathlib.Path, case: str) -> None:
    if case == "all-reachable-ok":
        _make_codex_agent(
            tmp_path,
            "software-engineer",
            "Follow the `workspace-protocol` rule and the `release-governance` rule.",
        )
        _make_rule(tmp_path, "workspace-protocol")
        _make_rule(tmp_path, "release-governance")

        out = check_codex_rule_corpus_reachable(tmp_path)
        assert out == ["[ok] codex:rule-corpus-reachable (WS-CDX-PROTOCOL)"]

    elif case == "unreachable-reports-error":
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

    elif case == "no-citations-silent":
        _make_codex_agent(tmp_path, "lonely", "No rules referenced here.")
        assert check_codex_rule_corpus_reachable(tmp_path) == []

    elif case == "no-codex-dir-silent":
        assert check_codex_rule_corpus_reachable(tmp_path) == []

    else:  # unreachable-name-deduped
        _make_codex_agent(tmp_path, "a", "Use the `missing-rule` rule.")
        _make_codex_agent(tmp_path, "b", "Also the `missing-rule` rule.")

        out = check_codex_rule_corpus_reachable(tmp_path)
        assert len(out) == 1
        assert "missing-rule" in out[0]


def test_trust_boundary_info_line_states_boundary() -> None:
    """A7: INFO line states current parity and independent chokepoints."""
    out = codex_trust_boundary_info()

    assert len(out) == 1
    line = out[0]
    assert line.startswith("[info] codex:trust-boundary")
    assert "interactive and headless Codex" in line
    assert "git chokepoints remain harness-independent" in line
    assert "after Codex CLI upgrades" in line
    assert "WS-CDX-HYGIENE" in line
