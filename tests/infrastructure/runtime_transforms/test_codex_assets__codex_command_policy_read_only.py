"""The rendered Codex ``.rules`` auto-allows only the closed readers ``ls`` and
``cat``. Native ``codex execpolicy`` checks cover the rendered policy when available.
"""

from __future__ import annotations

import ast
import itertools
import json
import re
import shutil
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _render_codex_command_policy_rules,
)
from tests.helpers.oslib import read_text, run, write_text

_REGISTRY = Path(__file__).resolve().parents[3] / "dadaia_workspace/public/entities/registry.json"
_RULE = re.compile(r"prefix_rule\((.*?)\n\)", re.S)
_FIELD = re.compile(r"^\s*(\w+) = (.*?),?$", re.M)


def _allowed_prefixes() -> set[tuple[str, ...]]:
    """Every argv prefix a rule with ``decision = "allow"`` expands to."""
    allowed: set[tuple[str, ...]] = set()
    for body in _RULE.findall(_render_codex_command_policy_rules()):
        fields = dict(_FIELD.findall(body))
        if ast.literal_eval(fields["decision"]) != "allow":
            continue
        tokens = [t if isinstance(t, list) else [t] for t in ast.literal_eval(fields["pattern"])]
        allowed.update(itertools.product(*tokens))
    return allowed


def test_b3_read_only_inspection_stays_allowed() -> None:
    """The allow set is exactly the read-only one, so no allowed prefix is
    write- or exec-capable."""
    assert _allowed_prefixes() == {("ls",), ("cat",)}


@pytest.mark.skipif(shutil.which("codex") is None, reason="codex CLI not on PATH")
@pytest.mark.parametrize(
    ("argv", "allowed"),
    [
        (["sed", "-i", "s/a/b/", "AGENTS.md"], False),
        (["find", ".", "-exec", "rm", "{}", ";"], False),
        (["sed", "-n", "1e touch x", "AGENTS.md"], False),
        (["rg", "--pre", "./x.sh", "pat", "."], False),
        (["cat", "AGENTS.md"], True),
    ],
)
def test_b1_codex_execpolicy_allows_only_read_only_commands(
    tmp_path: Path, argv: list[str], allowed: bool
) -> None:
    rules = tmp_path / "dadaia-command-policy.rules"
    write_text(rules, _render_codex_command_policy_rules())
    out = run(
        ["codex", "execpolicy", "check", "--rules", str(rules), "--", *argv], check=True, timeout=60
    ).stdout
    assert (json.loads(out).get("decision") == "allow") is allowed


@pytest.mark.skipif(shutil.which("codex") is None, reason="codex CLI not on PATH")
@pytest.mark.parametrize("executable", [".dadaia/.venv/bin/dadaia", "dadaia"])
def test_public_install_inherits_host_policy_while_force_prompts(
    tmp_path: Path, executable: str
) -> None:
    rules = tmp_path / "dadaia-command-policy.rules"
    write_text(rules, _render_codex_command_policy_rules())

    def decision(*options: str) -> str | None:
        out = run(
            [
                "codex",
                "execpolicy",
                "check",
                "--rules",
                str(rules),
                "--",
                executable,
                "public",
                "install",
                *options,
            ],
            check=True,
            timeout=60,
        ).stdout
        value = json.loads(out).get("decision")
        assert value is None or isinstance(value, str)
        return value

    assert decision() is None
    assert decision("--force") == "prompt"


@pytest.mark.skipif(shutil.which("codex") is None, reason="codex CLI not on PATH")
def test_git_push_leaves_the_decision_to_workspace_gitflow(tmp_path: Path) -> None:
    rules = tmp_path / "dadaia-command-policy.rules"
    write_text(rules, _render_codex_command_policy_rules())
    out = run(
        [
            "codex",
            "execpolicy",
            "check",
            "--rules",
            str(rules),
            "--",
            "git",
            "push",
            "origin",
            "feature/0.5.0",
        ],
        check=True,
        timeout=60,
    ).stdout
    decision = json.loads(out).get("decision")
    assert decision != "allow"
    assert decision is None


def test_b4_the_registry_mandate_describes_the_rendered_file() -> None:
    rules = json.loads(read_text(_REGISTRY))["rules"]
    mandate = next(r["mandate"] for r in rules if r["id"] == "codex-command-policy")
    assert "venv-guard" not in mandate
    assert all(token in mandate for token in ("ls", "cat")) and " sed" not in mandate
