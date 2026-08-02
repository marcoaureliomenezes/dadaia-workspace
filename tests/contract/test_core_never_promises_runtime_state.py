"""``core/`` may not describe runtime state it is structurally unable to observe.

Bug ``r25-block-reason-claims-missing-diagnostic-ref``. ``core/worker_failure.py`` is pure
text in, text out — the purity ratchet forbids it touching the filesystem — and it appended
"the full transcript is in the persisted diagnostic referenced by detail.diagnostic_ref" to
every truncated reason. Whether that ref exists depends on two runtime facts core cannot
see: whether the adapter attached a diagnostic, and whether a runtime-file writer is wired.
The validator found ``detail`` was ``{}``.

The purity ratchet catches core reaching for the filesystem. It does not catch core making
CLAIMS about the filesystem, which is the same boundary crossed in the other direction and
lands in front of the operator instead of in a stack trace.

Narrow on purpose. It names the keys a pure module has no way to confirm, rather than trying
to judge English — a check that tried to would either miss the next one or block honest
prose. When a new runtime-only key appears in operator-facing text, add it here.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_CORE = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "core"

#: Keys whose presence is decided at runtime, by a layer core cannot reach.
_RUNTIME_ONLY_KEYS = ("diagnostic_ref", "payload_ref", "artifact_refs")


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """Every string that is a docstring — those explain the rule, they do not emit it."""
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr):
                value = body[0].value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    out.add(id(value))
    return out


def _operator_facing_strings(tree: ast.AST):
    """Prose a human could be shown — not dict keys, not docstrings.

    A bare ``"payload_ref"`` is a serialization key and says nothing to anyone; the defect
    is a SENTENCE asserting where something lives. Filtering on "contains whitespace" is
    what separates the two, and keeps this ratchet aimed at its actual target.
    """
    docstrings = _docstring_nodes(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docstrings or " " not in node.value:
            continue
        yield node


def test_no_core_message_promises_a_runtime_only_key() -> None:
    offenders: list[str] = []
    for path in sorted(_CORE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in _operator_facing_strings(tree):
            for key in _RUNTIME_ONLY_KEYS:
                if key in node.value:
                    rel = path.relative_to(_CORE.parents[1]).as_posix()
                    offenders.append(f"{rel}:{node.lineno} -> {key}")

    assert not offenders, (
        "these core strings describe runtime state core cannot observe:\n  "
        + "\n  ".join(offenders)
        + "\n\nA pure module cannot know whether the referenced artifact was written. Let "
        "the layer that writes it say so — otherwise the message is a guess presented to "
        "the operator as a fact."
    )


def test_the_ratchet_would_catch_the_string_that_shipped() -> None:
    """A structural check that cannot detect its own target is decoration."""
    tree = ast.parse(
        'x = "worker output truncated; the full transcript is in the persisted "'
        ' "diagnostic referenced by detail.diagnostic_ref"'
    )
    found = [n.value for n in _operator_facing_strings(tree) if "diagnostic_ref" in n.value]
    assert found, "the scanner did not find the exact string that shipped"
