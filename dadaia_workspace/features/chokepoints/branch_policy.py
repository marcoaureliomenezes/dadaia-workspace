"""Branch policy — the project gitflow read by role (ADRs 0037, 0046).

Zero I/O, zero dependency on anything else in this package: :class:`PushRef` (the
parsed pre-push stdin shape) and :func:`check_branch_policy` (the per-ref loop
:func:`~dadaia_workspace.features.chokepoints.push_gate.push_gate_decision` runs first,
before either specs-scan step). Branch names come from the injected
:class:`~dadaia_workspace.core.gitflow.Gitflow`; none is spelled here.
:class:`Decision` — the shared outcome shape every chokepoint gate returns — lives here
too: this module has no internal-package dependency, so every sibling module (``pre_commit``,
``push_gate``) imports it from here rather than duplicating it or reaching
into ``__init__.py`` (which itself re-exports from this module, never the reverse).
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

from dadaia_workspace.core.gitflow import Gitflow

__all__ = [
    "Decision",
    "PushRef",
    "check_branch_policy",
    "parse_push_stdin",
]


@dataclass(frozen=True)
class Decision:
    """Outcome of a chokepoint gate.

    ``allowed`` is the only thing the git hook keys its exit code on. ``warn`` carries an
    advisory line that is logged/printed but never blocks (the DP-4 degradation path).
    ``message`` is the human-facing block/allow explanation.
    """

    allowed: bool
    message: str = ""
    warn: str | None = None


#: A pre-push sha is 40-char (SHA-1) or 64-char (SHA-256) hex (v0.11.0 FR7/A7.3) — an
#: option-shaped value (``--glob=refs/nonexistent``) is malformed, never a silent no-op
#: (CWE-88/CWE-20). The all-zero deletion sentinel is 40 hex characters and already
#: matches — no special case needed.
_SHA_SHAPE_RE = re.compile(r"^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$")

#: git's zero-sha deletion sentinel (40 hex zeros) — imported by ``push_gate`` too.
ZERO_SHA = "0" * 40


def _is_sha_shaped(value: str) -> bool:
    return bool(_SHA_SHAPE_RE.match(value))


@dataclass(frozen=True)
class PushRef:
    """One parsed pre-push stdin ref line.

    git feeds the pre-push hook lines of ``<local-ref> <local-sha> <remote-ref>
    <remote-sha>`` on stdin. The push gate keys ONLY on ``local_sha`` (never
    ``git rev-parse HEAD``): a zero ``local_sha`` is a branch deletion.
    """

    local_ref: str
    local_sha: str
    remote_ref: str
    remote_sha: str

    @property
    def is_deletion(self) -> bool:
        """True when this ref is being deleted (zero local sha) — passes the branch policy."""
        return self.local_sha == ZERO_SHA or not self.local_sha

    @property
    def is_tag(self) -> bool:
        """True when this ref is a tag push — passes the branch policy (DP-5)."""
        return self.local_ref.startswith("refs/tags/")


def parse_push_stdin(stdin_text: str) -> tuple[list[PushRef], int]:
    """Parse pre-push stdin into :class:`PushRef` rows plus a malformed-line count.

    A non-empty line that does not split into exactly four fields is counted, not
    silently dropped — the gate FAILS CLOSED on any malformed line (T-060-07 finding 1:
    a policy gate that skips what it cannot parse is a policy gate that can be
    disabled without a trace; ``git push --no-verify`` is the sanctioned bypass).

    v0.11.0 FR7/A7.1-A7.3: both shas are additionally validated against
    :data:`_SHA_SHAPE_RE` — a violation reuses the SAME malformed-line counter and the
    SAME fail-closed message (no new branch), so an option-shaped ``local_sha`` (the
    measured silent-no-op class) refuses instead of producing a successful empty
    ``git rev-list``.
    """
    refs: list[PushRef] = []
    malformed = 0
    for raw in stdin_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 4:
            malformed += 1
            continue
        local_ref, local_sha, remote_ref, remote_sha = parts
        if not _is_sha_shaped(local_sha) or not _is_sha_shaped(remote_sha):
            malformed += 1
            continue
        refs.append(PushRef(local_ref, local_sha, remote_ref, remote_sha))
    return refs, malformed


HEADS_PREFIX = "refs/heads/"

#: Where the project gitflow is stated — every refusal points there.
_LAW = "project gitflow: specs/constitution.md"


def _blocked(text: str, *fixes: list[str]) -> Decision:
    fix = " && ".join(shlex.join(argv) for argv in fixes)
    return Decision(allowed=False, message=f"[pre-push] BLOCKED: {text} ({_LAW}).\nfix: {fix}")


def _refuse_branch(ref: PushRef, branch: str | None, gitflow: Gitflow) -> Decision:
    """Actionable refusal for a non-pushable ref (*branch* ``None``: not a branch head)."""
    role = gitflow.role_of(branch) if branch is not None else None
    work = gitflow.work_pattern
    if role is not None and ref.remote_sha == ZERO_SHA:
        return _blocked(
            f"creating the {role} branch '{branch}' would publish new objects — a birth may "
            "carry only already-published history or one empty root commit; stale "
            "remote-tracking refs look the same: refresh them, then push again",
            ["git", "fetch", "--all"],
        )
    if role is None:
        return _blocked(
            f"ref '{ref.local_ref}' is outside the gitflow — principal '{gitflow.principal}', "
            f"integration '{gitflow.integration}', work '{work}'; only a work branch is pushable",
            ["git", "checkout", "-b", work, gitflow.principal],
            ["git", "push", "origin", work],
        )
    head = gitflow.integration if role == "principal" else work
    return _blocked(
        f"the {role} branch '{branch}' is never pushed directly — it advances only via a PR "
        f"from '{head}'",
        ["gh", "pr", "create", "--base", str(branch), "--head", head],
    )


def check_branch_policy(
    refs: list[PushRef], gitflow: Gitflow, births: frozenset[str] = frozenset()
) -> Decision | None:
    """Every non-deletion, non-tag ref must be a work branch of *gitflow*, pushed to the
    SAME remote name; the principal and integration branches are PR-only, except their
    birth (ADR 0036): a local sha in *births* (the caller proved it creates the remote
    branch and publishes nothing). Returns the
    first refusal, or ``None`` when every ref clears (the caller has already excluded
    tags and deletions from *refs*).
    """
    for ref in refs:
        if not ref.local_ref.startswith(HEADS_PREFIX):
            return _refuse_branch(ref, None, gitflow)
        branch = ref.local_ref[len(HEADS_PREFIX) :]
        role = gitflow.role_of(branch)
        born = role in ("principal", "integration") and ref.local_sha in births
        if role != "work" and not born:
            return _refuse_branch(ref, branch, gitflow)
        if ref.remote_ref != f"{HEADS_PREFIX}{branch}":
            return _blocked(
                f"refspec aims local '{branch}' at remote '{ref.remote_ref}' — only "
                f"refs/heads/{branch} → refs/heads/{branch} is pushable",
                ["git", "push", "origin", f"{branch}:{branch}"],
            )
    return None
