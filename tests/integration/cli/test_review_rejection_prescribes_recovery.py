"""A rejected review must prescribe its recovery — no gate block is a dead end.

Bug r9-plan-review-missing-operator-command, reported by the consumer-side validator
during a LIVE release of a real data-capture context.

``plan_review`` REJECTED the PLAN for a substantive reason, the one bounded in-run
revision was already spent, and the run blocked with ``operator_command: null``. The
validator's words were that it could not proceed "without inventing a change" — which is
exactly the failure: the operator is handed a rejection and no prescribed way forward.

The engine spends its revision, then returns the reviewer's RAW block unenriched, and a
reviewer never fills ``operator_command``. Every other gate prescribes its recovery; the
one a real release hits most often did not.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind, BlockedState

pytestmark = pytest.mark.integration


def _blocked_from_reviewer() -> BlockedState:
    """The shape a rejecting reviewer actually produces: no operator_command."""
    return BlockedState(
        reason="review verdict REJECTED: the PLAN does not bind the concrete adapter",
        blocked_at_step="plan_review",
        detail={"verdict": "REJECTED"},
        operator_command=None,
    )


def test_rejected_review_block_is_enriched_with_a_resume_command() -> None:
    from dadaia_workspace.features.lifecycle.workflows._fragment_gate import (
        prescribe_review_recovery,
    )

    enriched = prescribe_review_recovery(
        _blocked_from_reviewer(),
        command="release_definition",
        context="r7livefull",
        release_id="v0.7.0",
        run_id="r7-release-definition-live",
        create_step="plan_create",
        runtime_kind=AgentRuntimeKind.CODEX_EXEC,
    )

    cmd = enriched.operator_command
    assert cmd, "a rejected review must prescribe its recovery"
    # It must be a command the operator can paste: same run, the create step the review
    # consumes, and the run's OWN harness (a remedy that silently switches runtime is the
    # bug r6h-backlog-remedy-command-loses-fake-harness class).
    assert "lifecycle release-definition" in cmd, cmd
    assert "--run-id r7-release-definition-live" in cmd, cmd
    assert "--resume-from plan_create" in cmd, cmd
    assert "--harness codex" in cmd, cmd
    assert "--context r7livefull" in cmd and "--release-id v0.7.0" in cmd, cmd
    # The reviewer's reason must survive — the operator needs to know WHAT to fix.
    assert "does not bind the concrete adapter" in enriched.reason


def test_an_existing_operator_command_is_never_overwritten() -> None:
    """A gate that already prescribed a better, more specific recovery keeps it."""
    from dadaia_workspace.features.lifecycle.workflows._fragment_gate import (
        prescribe_review_recovery,
    )

    original = BlockedState(
        reason="review verdict REJECTED",
        blocked_at_step="plan_review",
        detail={"verdict": "REJECTED"},
        operator_command="dadaia something --specific",
    )
    kept = prescribe_review_recovery(
        original,
        command="release_definition",
        context="c",
        release_id="v0.1.0",
        run_id="r",
        create_step="plan_create",
        runtime_kind=AgentRuntimeKind.FAKE,
    )
    assert kept.operator_command == "dadaia something --specific"


def test_every_prescribed_harness_name_is_one_the_cli_accepts() -> None:
    """A remedy must never name a harness the CLI would reject.

    ``AgentRuntimeKind.CODEX_EXEC.value`` is ``codex_exec``, which ``--harness`` does not
    accept — so rendering the enum value straight into a command produced a line that
    fails the moment it is pasted, exactly the defect these remedies exist to avoid. The
    CLI's parser and every remedy renderer now derive from ONE map; this pins that they
    cannot drift apart.
    """
    from dadaia_workspace.cli.commands.lifecycle import _HARNESS_KINDS, _resolve_harness
    from dadaia_workspace.core.models.lifecycle import HARNESS_CLI_NAMES

    for kind, name in HARNESS_CLI_NAMES.items():
        assert name in _HARNESS_KINDS, f"{name!r} is rendered into remedies but the CLI rejects it"
        assert _resolve_harness(name) is kind, (
            f"--harness {name} must resolve back to {kind}, or a pasted remedy silently "
            "switches runtime"
        )
    # Claude is Layer-1 only and must never be offered as a workflow harness.
    from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind

    assert AgentRuntimeKind.CLAUDE_SDK not in HARNESS_CLI_NAMES
