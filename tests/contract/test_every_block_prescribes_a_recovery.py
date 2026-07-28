"""Every block the lifecycle can emit must carry a way out.

This class of defect has been reported four separate times by the consumer-side
validator — ``a2-release-missing-spec-gate-lacks-resume-remedy``,
``backlog-cli-intent-hallucinated-anchor-045``,
``r15-release-definition-running-after-accepted-draft``,
``r16-release-definition-deterministic-block-has-no-recovery`` — and each time it was
fixed at ONE call site while the next one waited to be found.

Fixing instances of a class one at a time is how a class survives. This is the ratchet:
every ``BlockedState(...)`` constructed anywhere in the lifecycle must pass an
``operator_command``. A block without one is a wall; a block with one is a wall with a
door, and the difference is the whole operator experience.

Structural, deliberately: it cannot prove the command is CORRECT — only that no path can
stop the operator without offering something to run. Correctness of each remedy is the
job of the tests that own that gate.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_LIFECYCLE = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "features" / "lifecycle"


def _blocked_state_calls(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            if name == "BlockedState":
                yield node


def test_no_lifecycle_block_is_constructed_without_an_operator_command() -> None:
    offenders: list[str] = []
    for path in sorted(_LIFECYCLE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for call in _blocked_state_calls(tree):
            keywords = {kw.arg for kw in call.keywords if kw.arg}
            if "operator_command" not in keywords:
                rel = path.relative_to(_LIFECYCLE.parents[2]).as_posix()
                offenders.append(f"{rel}:{call.lineno}")

    assert not offenders, (
        "these blocks stop the operator without prescribing anything to run:\n  "
        + "\n  ".join(offenders)
        + "\n\nEvery block must carry an operator_command — the recovery is part of the "
        "block, not an optional extra. If a path genuinely has no specific remedy, the "
        "floor is re-running the step that produces the artifact."
    )


def test_the_ratchet_would_notice_a_block_without_one() -> None:
    """Prove the scanner can fail, so a green run means something.

    A structural check that cannot detect its own target is decoration.
    """
    tree = ast.parse("BlockedState(reason='x', blocked_at_step='y', resume_token='z')")
    calls = list(_blocked_state_calls(tree))
    assert calls, "the scanner did not even find a BlockedState call"
    assert "operator_command" not in {kw.arg for kw in calls[0].keywords}
