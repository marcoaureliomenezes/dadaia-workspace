"""Intent: CONTRACT — presence-demolition-left-a-dead-advisory-channel-and-docstrings.

The gate is a decision plus a message: the policy takes only the write target and the
bind's scope as data, the hook chain carries a block reason or nothing, and the allow
envelope has no advisory field.
"""

from __future__ import annotations

import inspect

from dadaia_workspace.features.spec_context import gate_policy
from dadaia_workspace.hooks import pre_gate, sdd_gate


def test_evaluate_takes_only_the_target_and_the_scope() -> None:
    params = list(inspect.signature(gate_policy.evaluate).parameters)
    assert params == ["rel_path", "bound_context", "bound_repos", "target_slug", "target_owner"]


def test_evaluate_returns_decision_and_message_only() -> None:
    assert gate_policy.evaluate("repos/x/a.py") == (gate_policy.Decision.ALLOW, "")


def test_hook_chain_has_no_advisory_surface() -> None:
    assert not hasattr(sdd_gate, "evaluate_payload_with_advisory")
    assert not hasattr(pre_gate, "evaluate_payload_with_advisory")
    assert sdd_gate.evaluate_payload in pre_gate._POLICIES  # noqa: SLF001
    assert list(inspect.signature(pre_gate._common.emit_allow).parameters) == []
