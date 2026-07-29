"""The one place that turns a stuck run into a line the operator can paste.

Bug ``r22-release-review-rejection-deadlocks`` (escapability half) is the fifth report of
one class: a block that is correct, readable, and impossible to act on because its
``operator_command`` describes a command instead of being one —

    re-run the workflow with --resume-from definition_review; inspect the step payload
    for the worker's own output first

Each earlier report was fixed at the call site it arrived on, and eleven other sites kept
the prose. That is how a class survives being fixed. There is exactly one correct way to
spell a resume, every block needs it, so it lives here and every block calls it.

I/O-pure by construction (architect A9): string assembly over values the caller already
holds, no filesystem, no environment, no imports outside ``core``.
"""

from __future__ import annotations

#: Persisted ``LifecycleRun.command`` → the CLI verb that actually re-runs it. The
#: implementation workflow persists ``pipeline``, which is not its verb — omitting that
#: mapping is what handed an implementation run a ``release-definition`` command
#: (bug ``r22-lifecycle-status-pipeline-recovery-wrong-verb``).
VERB_BY_COMMAND: dict[str, str] = {
    "backlog_definition": "backlog-definition",
    "release_definition": "release-definition",
    "implementation_reviews": "implementation-reviews",
    "pipeline": "implementation-reviews",
    "audit": "audit",
}


def resume_command(
    *,
    command: str,
    run_id: str,
    step: str,
    context: str = "",
    release_id: str = "",
    harness: str = "",
    note: str = "",
    env: tuple[str, ...] = (),
) -> str:
    """A complete, pasteable resume line for one run.

    Every argument that is empty is simply left out rather than emitted blank: a command
    carrying ``--context ''`` fails in a way that looks like the operator's mistake.

    An unknown *command* never guesses a verb. ``lifecycle status`` is always real, always
    runnable, and names the step it is stuck on — a correct command that shows the way
    beats a confident one that runs the wrong workflow.

    *env* holds ``NAME=value`` assignments the command needs in order to work, prefixed
    onto the line so pasting it is sufficient. Bug
    ``r23-sandbox-block-operator-command-omits-required-bypass``: a Codex worker killed by
    an uncreatable sandbox namespace got a block that EXPLAINED the fix
    (``DADAIA_CODEX_SANDBOX=danger-bypass``) and a command without it, so pasting the
    command re-ran straight into the same failure. A remedy correct except for a variable
    the operator has to already know is a remedy only for people who did not need it.
    """
    verb = VERB_BY_COMMAND.get(command)
    prefix = "".join(f"{assignment} " for assignment in env)
    if verb is None:
        return f"{prefix}dadaia lifecycle status --run-id {run_id}"
    parts = [f"{prefix}dadaia lifecycle {verb}"]
    if context:
        parts.append(f"--context {context}")
    if release_id:
        parts.append(f"--release-id {release_id}")
    parts.append(f"--run-id {run_id}")
    if harness:
        parts.append(f"--harness {harness}")
    parts.append(f"--resume-from {step}")
    line = " ".join(parts)
    return f"{line}  # {note}" if note else line
