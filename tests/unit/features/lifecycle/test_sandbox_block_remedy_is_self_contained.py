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
    from dadaia_workspace.features.lifecycle.agent_runner import sandbox_env_for_reason

    assert sandbox_env_for_reason(_SANDBOX_REASON) == ("DADAIA_CODEX_SANDBOX=danger-bypass",)
    assert sandbox_env_for_reason("agent result missing APPROVED verdict") == ()


def test_prose_about_sandboxes_does_not_trigger_it() -> None:
    """Guard: a false positive here hands out an unnecessary privilege downgrade."""
    from dadaia_workspace.features.lifecycle.agent_runner import sandbox_env_for_reason

    assert sandbox_env_for_reason("the plan describes the sandbox strategy for QA") == ()
