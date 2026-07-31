"""Every verb that accepts ``--resume-from`` must reject an unknown step before reading state.

This class has now been reported twice, on two different verbs, one round apart:

* ``r24-invalid-resume-implementation-preflight-mask`` — ``implementation-reviews``
  answered "active release mismatch" and sent the operator to repair a context bind.
* ``r25-audit-resume-invalid-step-validates-target-first`` — ``audit`` answered
  "release not found" and sent them to define a release.

Both for a command that could never have run, because the step name was wrong on its face.
The second one exists purely because the first fix was applied to the verbs that had been
reported and not to the one that had not — the same instance-instead-of-class mistake that
this repository's recovery ratchets were written to stop.

So the rule is structural: a command function that takes a ``resume_from`` parameter must
call the shared validator. Deliberately a source-level check rather than a behavioural one
— a behavioural test can only cover the verbs someone thought to parametrize, which is
exactly how ``audit`` slipped through.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_CLI = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "cli" / "commands"
_VALIDATOR = "_reject_unknown_resume_step"


def _functions_taking_resume_from(tree: ast.AST):
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        args = [a.arg for a in node.args.args] + [a.arg for a in node.args.kwonlyargs]
        if "resume_from" in args and node.name != _VALIDATOR:
            yield node


def _calls(node: ast.AST) -> set[str]:
    out: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            name = getattr(child.func, "id", None) or getattr(child.func, "attr", None)
            if name:
                out.add(name)
    return out


def test_every_cli_verb_taking_resume_from_validates_it() -> None:
    offenders: list[str] = []
    for path in sorted(_CLI.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for func in _functions_taking_resume_from(tree):
            if _VALIDATOR not in _calls(func):
                offenders.append(f"{path.name}:{func.lineno} {func.name}")

    assert not offenders, (
        "these verbs accept --resume-from without rejecting an unknown step first:\n  "
        + "\n  ".join(offenders)
        + f"\n\nCall {_VALIDATOR}() right after the harness is resolved and before any "
        "workspace state is read. Whether a token names a real step is knowable without "
        "touching the workspace, so answering anything else first misdirects the operator."
    )


def test_the_ratchet_finds_the_verbs_it_is_meant_to_guard() -> None:
    """A structural check that matches nothing is decoration.

    Round 25 found ``audit`` unguarded while three other verbs were fine, so this asserts
    the scanner actually sees a realistic population rather than silently matching zero.
    """
    found = [
        func.name
        for path in sorted(_CLI.rglob("*.py"))
        for func in _functions_taking_resume_from(ast.parse(path.read_text(encoding="utf-8")))
    ]
    assert len(found) >= 4, f"expected the four lifecycle verbs, scanner saw: {found}"
