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

_ROOT = Path(__file__).resolve().parents[2] / "dadaia_workspace"
_LIFECYCLE = _ROOT / "features" / "lifecycle"

#: Trees the prose scan sweeps. `cli/` was outside the original ratchet, which is how a
#: prose FALLBACK inside `lifecycle status` survived every earlier pass — the verb whose
#: whole job is telling a stuck operator what to do next. A ratchet that stops at a package
#: boundary stops at the boundary the defect walks across.
_PROSE_SCAN_ROOTS = (_LIFECYCLE, _ROOT / "cli")


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


_PLACEHOLDERS = ("<this step>", "<that step>", "<step>", "<name>", "<run-id>", "TODO")


def test_no_recovery_is_a_placeholder_instead_of_a_command() -> None:
    """A remedy the operator cannot paste is not a remedy.

    Bug ``r18-r20-missing-spec-recovery-placeholder``: the bulk fix for the previous
    report satisfied the ratchet above by passing an ``operator_command`` — whose text was
    the literal ``--resume-from <this step>``. The field was present and the line was
    printed and it still left the operator with nothing to run. The check that existed
    measured presence; presence was never the point.
    """
    offenders: list[str] = []
    for path in sorted(_LIFECYCLE.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for call in _blocked_state_calls(tree):
            for kw in call.keywords:
                if kw.arg != "operator_command":
                    continue
                rendered = ast.unparse(kw.value)
                for token in _PLACEHOLDERS:
                    if token in rendered:
                        rel = path.relative_to(_LIFECYCLE.parents[2]).as_posix()
                        offenders.append(f"{rel}:{call.lineno} -> {token}")

    assert not offenders, (
        "these recoveries hand the operator a placeholder instead of a command:\n  "
        + "\n  ".join(offenders)
        + "\n\nInterpolate the real step label. A remedy that cannot be pasted is a "
        "remedy nobody can follow, which is the whole defect this ratchet exists for."
    )


#: Literal openings that mean the field holds INSTRUCTIONS about a command rather than a
#: command. Each is a shape the validator actually received.
_PROSE_OPENINGS = (
    "re-run ",
    "rerun ",
    "run the ",
    "re-execute ",
    "inspect ",
    "see ",
    "ask ",
    "contact ",
)


def _literal_prefix(node: ast.expr) -> str | None:
    """The leading literal text of a string expression, or None if it starts dynamic."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                return value.value
            return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _literal_prefix(node.left)
    return None


def test_no_recovery_is_prose_about_a_command_instead_of_the_command() -> None:
    """Bug ``r22-release-review-rejection-deadlocks`` (the escapability half).

    The generic agent-runner block — the single most-hit block in the product, since every
    worker-noncompliance path funnels through it — prescribed:

        re-run the workflow with --resume-from definition_review; inspect the step
        payload for the worker's own output first

    which is an instruction to assemble a command, not a command. The validator hit it on a
    review that could not produce a compliant verdict and reported a deadlock: the block was
    real and correct, and there was still nothing to paste.

    The two ratchets above measure presence and then non-placeholder-ness. Each was written
    after the previous one was satisfied in letter and defeated in spirit. This one measures
    the only property that was ever the point: the field begins with a command.
    """
    offenders: list[str] = []
    paths = sorted({p for root in _PROSE_SCAN_ROOTS for p in root.rglob("*.py")})
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for call in _blocked_state_calls(tree):
            for kw in call.keywords:
                if kw.arg != "operator_command":
                    continue
                prefix = _literal_prefix(kw.value)
                if prefix is None:
                    # Starts with an interpolation — a builder call or a passed-in command.
                    # Those are covered by the tests that own the gate they belong to.
                    continue
                lowered = prefix.lstrip().lower()
                if any(lowered.startswith(opening) for opening in _PROSE_OPENINGS):
                    rel = path.relative_to(_ROOT.parent).as_posix()
                    offenders.append(f"{rel}:{call.lineno} -> {prefix.strip()[:60]!r}")

    assert not offenders, (
        "these recoveries describe a command instead of being one:\n  "
        + "\n  ".join(offenders)
        + "\n\nEmit the line the operator pastes. Everything needed is on the run record, "
        "so there is no reason to make them reassemble it while something is already wrong."
    )
