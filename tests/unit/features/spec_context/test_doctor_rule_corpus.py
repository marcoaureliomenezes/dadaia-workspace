"""``dadaia doctor`` must not read healthy while a by-name law citation dangles.

Bug ``r9-doctor-omits-rule-corpus-reachable`` (found by the consumer-side validator on
R9/F-23): the reachability check landed in ``dadaia public doctor`` only, so the
workspace-state doctor — the one an operator runs to ask "is this tree healthy?" —
printed "All invariants OK" for a workspace whose agent cited a rule that does not
exist. An agent following that citation gets no law and no error, which is the exact
blindness the fix was supposed to remove; fixing it in one verb and not the other just
moved the blind spot.

The scan itself is pure and lives in ``core.rule_corpus`` so both doctors share one
answer — ``features`` may not import ``infrastructure``, and a second implementation
would drift.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace import container
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager


@pytest.fixture
def claude_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(ws, harnesses=("claude",))
    return ws


def _codes(workspace: Path) -> list[str]:
    return [issue.code for issue in container.build_doctor_service(workspace).check()]


def test_a_healthy_projection_raises_no_rule_corpus_issue(claude_workspace: Path) -> None:
    assert not [code for code in _codes(claude_workspace) if code.startswith("RULE-")]


def test_doctor_reports_a_citation_with_no_rule_file(claude_workspace: Path) -> None:
    agent = claude_workspace / ".claude" / "agents" / "software-engineer.md"
    agent.write_text(
        agent.read_text(encoding="utf-8") + "\n\nSegue a `regra-que-nao-existe` rule.\n",
        encoding="utf-8",
    )

    issues = container.build_doctor_service(claude_workspace).check()
    matching = [i for i in issues if "regra-que-nao-existe" in i.description]

    assert matching, (
        "doctor reported nothing for a dangling by-name law citation — "
        f"issues were {[(i.code, i.description[:60]) for i in issues]}"
    )
    assert matching[0].code.startswith("RULE-")
    assert not matching[0].fixable, "dadaia cannot invent the missing rule; this is manual"
