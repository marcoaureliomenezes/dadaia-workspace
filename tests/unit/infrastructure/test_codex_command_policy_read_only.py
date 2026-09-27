"""Intent: CONTRACT — sa-codex-policy-allows-write-capable-commands (0.5.0 WP-13, AC1.5).

The rendered Codex ``.rules`` allows no write- or exec-capable prefix (#B1, #B2), keeps
read-only inspection unprompted (#B3), and registry.json's mandate says what the file is
(#B4). The allow set is SPEC row 13's: ``rg ls cat`` and ``sed -n``.
Size: SMALL (parses the rendered text); #B1 also asks the real ``codex execpolicy`` when
the binary is on PATH.
"""

from __future__ import annotations

import ast
import itertools
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _render_codex_command_policy_rules,
)

pytestmark = pytest.mark.unit

_REGISTRY = Path(__file__).resolve().parents[3] / "dadaia_workspace/public/entities/registry.json"
_RULE = re.compile(r"prefix_rule\((.*?)\n\)", re.S)
_FIELD = re.compile(r"^\s*(\w+) = (.*?),?$", re.M)
#: Write- or exec-capable first tokens (sed is admissible only as ``sed -n``).
_WRITE_OR_EXEC = {"sed", "find", "awk", "xargs", "sh", "bash", "python", "perl", "tee"}


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


def test_b2_no_allow_prefix_starts_with_a_write_or_exec_capable_command() -> None:
    offenders = {p for p in _allowed_prefixes() if p[0] in _WRITE_OR_EXEC and p != ("sed", "-n")}
    assert offenders == set()


def test_b3_read_only_inspection_stays_allowed() -> None:
    assert _allowed_prefixes() == {("rg",), ("ls",), ("cat",), ("sed", "-n")}


@pytest.mark.skipif(shutil.which("codex") is None, reason="codex CLI not on PATH")
@pytest.mark.parametrize(
    ("argv", "allowed"),
    [
        (["sed", "-i", "s/a/b/", "AGENTS.md"], False),
        (["find", ".", "-exec", "rm", "{}", ";"], False),
        (["sed", "-n", "1,80p", "AGENTS.md"], True),
        (["rg", "Codex"], True),
    ],
)
def test_b1_codex_execpolicy_allows_only_read_only_commands(
    tmp_path: Path, argv: list[str], allowed: bool
) -> None:
    rules = tmp_path / "dadaia-command-policy.rules"
    rules.write_text(_render_codex_command_policy_rules(), encoding="utf-8")
    out = subprocess.run(
        ["codex", "execpolicy", "check", "--rules", str(rules), "--", *argv],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout
    assert (json.loads(out).get("decision") == "allow") is allowed


def test_b4_the_registry_mandate_describes_the_rendered_file() -> None:
    rules = json.loads(_REGISTRY.read_text(encoding="utf-8"))["rules"]
    mandate = next(r["mandate"] for r in rules if r["id"] == "codex-command-policy")
    assert "venv-guard" not in mandate
    assert all(token in mandate for token in ("rg", "ls", "cat", "sed -n"))
