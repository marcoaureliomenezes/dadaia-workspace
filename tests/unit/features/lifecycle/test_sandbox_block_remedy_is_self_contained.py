"""A remedy must carry everything needed to work, including the environment.

Bug ``r23-sandbox-block-operator-command-omits-required-bypass`` (validator R23 / R-23):
when a Codex worker dies because the sandbox namespace cannot be created, the block
explains the fix in its reason — set ``DADAIA_CODEX_SANDBOX=danger-bypass`` — and then
prints an ``operator_command`` WITHOUT it. Pasting the command re-runs the workflow into
exactly the same failure. The validator's words: "colar o comando não aplica a correção".

This is the same invariant as ``r22-release-review-rejection-deadlocks`` and
``graph-block-prescribes-the-command-that-just-failed``, arriving through the environment
instead of through the arguments: the remedy must be able to FIX the cause it names. A
command that is correct except for a variable the operator has to know about is a command
that fails for everyone who did not already know the answer.

The reason text keeps explaining WHY — the prefix is not a substitute for the explanation,
it is what makes the explanation actionable without reading it.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.lifecycle_recovery import resume_command

pytestmark = pytest.mark.unit

_SANDBOX_REASON = (
    "codex exec exited 0 but its stderr carries a sandbox-failure signature "
    "('no permissions to create a new namespace'): the sandbox namespace (bwrap/landlock) "
    "could not be created or denied workspace writes, so the worker inspected/wrote nothing."
)


def _command(**kwargs: object) -> str:
    return resume_command(
        command="release_definition",
        run_id="rid",
        step="definition_draft",
        context="ctx",
        release_id="v0.1.0",
        **kwargs,  # type: ignore[arg-type]
    )


def test_a_sandbox_block_prefixes_the_variable_that_makes_it_work() -> None:
    command = _command(env=("DADAIA_CODEX_SANDBOX=danger-bypass",))

    assert command.startswith("DADAIA_CODEX_SANDBOX=danger-bypass dadaia lifecycle "), command
    assert "--resume-from definition_draft" in command


def test_an_ordinary_block_is_not_decorated_with_an_environment() -> None:
    """The prefix must appear only where it is the actual fix.

    Putting a sandbox bypass on every recovery would teach the operator to paste a
    privilege downgrade they never needed, which is a worse outcome than the bug.
    """
    assert _command().startswith("dadaia lifecycle "), _command()


def test_the_runner_prefixes_it_when_the_reason_names_the_sandbox() -> None:
    """End of the wire: the runner must decide this, not the caller.

    The detection has to live where the block is BUILT. Any other placement means the next
    call site that constructs a sandbox block forgets it, which is how every recovery
    defect in this ledger got a second life.
    """
    from dadaia_workspace.features.lifecycle.agent_runner import remedy_env_for_reason

    assert remedy_env_for_reason(_SANDBOX_REASON, {}) == ("DADAIA_CODEX_SANDBOX=danger-bypass",)
    assert remedy_env_for_reason("agent result missing APPROVED verdict", {}) == ()


def test_prose_about_sandboxes_does_not_trigger_it() -> None:
    """Guard: a false positive here hands out an unnecessary privilege downgrade."""
    from dadaia_workspace.features.lifecycle.agent_runner import remedy_env_for_reason

    assert remedy_env_for_reason("the plan describes the sandbox strategy for QA", {}) == ()


# ── bug r25-block-remedy-omits-the-env-var-its-own-reason-names (validator R25 / R-23) ──
#
# Round 25, live Codex, backlog-definition: the run BLOCKED at backlog_author with the
# reason "CODEX_HOME points to a directory that did not exist", and the emitted remedy
# omitted CODEX_HOME entirely. A remedy that does not carry the variable its own reason
# blames is guaranteed to reproduce the block it came from.
#
# The earlier fix taught this module ONE variable, DADAIA_CODEX_SANDBOX, because that was
# the one instance the validator had reported. Fixing an instance of a class is how the
# class survives — this file's own docstring says so — and the very next round produced the
# next instance. The rule is now the class: if the reason names an environment variable
# that was in effect, the remedy carries it.


def test_a_block_that_blames_codex_home_carries_codex_home() -> None:
    from dadaia_workspace.features.lifecycle.agent_runner import remedy_env_for_reason

    env = remedy_env_for_reason(
        "codex worker failed: CODEX_HOME points to a directory that did not exist",
        {"CODEX_HOME": "/opt/data/state/round25/codexhome"},
    )

    assert "CODEX_HOME=/opt/data/state/round25/codexhome" in env, (
        "the remedy omitted the very variable its reason blamed, so pasting it re-runs "
        f"into the identical failure: {env}"
    )


def test_the_sandbox_bypass_still_rides_along() -> None:
    from dadaia_workspace.features.lifecycle.agent_runner import remedy_env_for_reason

    assert remedy_env_for_reason(_SANDBOX_REASON, {}) == ("DADAIA_CODEX_SANDBOX=danger-bypass",)


def test_both_causes_are_carried_together() -> None:
    """A live block named both; carrying only one leaves the operator half-stuck."""
    from dadaia_workspace.features.lifecycle.agent_runner import remedy_env_for_reason

    env = remedy_env_for_reason(
        _SANDBOX_REASON + " and CODEX_HOME points to a directory that did not exist",
        {"CODEX_HOME": "/tmp/ch"},
    )

    assert "DADAIA_CODEX_SANDBOX=danger-bypass" in env
    assert "CODEX_HOME=/tmp/ch" in env


def test_a_variable_the_reason_never_mentions_is_not_dragged_in() -> None:
    """The remedy must reproduce the CAUSE, not dump the environment on the operator."""
    from dadaia_workspace.features.lifecycle.agent_runner import remedy_env_for_reason

    assert (
        remedy_env_for_reason("agent result missing APPROVED verdict", {"CODEX_HOME": "/tmp/ch"})
        == ()
    )


def test_a_named_variable_that_was_not_set_is_not_invented() -> None:
    """Emitting `CODEX_HOME=` would be a blank the operator has to fill — the r18 defect."""
    from dadaia_workspace.features.lifecycle.agent_runner import remedy_env_for_reason

    assert remedy_env_for_reason("CODEX_HOME points to a directory that did not exist", {}) == ()
