"""Branch policy — the project gitflow read by role; zero I/O.

Also home of :class:`Decision`, the outcome every chokepoint gate returns (this module
has no internal-package dependency, so siblings import it from here)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from dadaia_workspace.core import platform
from dadaia_workspace.core.cli_line import cli_words, git_line, spell_fix
from dadaia_workspace.core.gitflow import Gitflow
from dadaia_workspace.core.models.git_scan import SHA_SHAPE_RE, is_zero_sha
from dadaia_workspace.core.platform import act

__all__ = [
    "Decision",
    "GateFixes",
    "PushRef",
    "check_branch_policy",
    "check_ref_policy",
    "parse_push_stdin",
]


@dataclass(frozen=True)
class Decision:
    """``allowed`` keys the hook's exit code; ``warn`` is advisory, never blocks; *listed* are
    the paths a refusal names (a commit message is listed as such): what its remedy may touch."""

    allowed: bool
    message: str = ""
    warn: str | None = None
    listed: frozenset[str] = frozenset()

    @property
    def message_listed(self) -> bool:
        return "(commit message)" in self.listed


@dataclass(frozen=True)
class PushRef:
    """One pre-push stdin line ``<local-ref> <local-sha> <remote-ref> <remote-sha>``;
    the gate keys on ``local_sha`` (never HEAD), zero meaning a deletion."""

    local_ref: str
    local_sha: str
    remote_ref: str
    remote_sha: str

    @property
    def is_deletion(self) -> bool:
        return is_zero_sha(self.local_sha) or not self.local_sha

    @property
    def is_tag(self) -> bool:
        return self.remote_ref.startswith("refs/tags/")


def parse_push_stdin(stdin_text: str) -> tuple[list[PushRef], int]:
    """Rows plus a malformed-line count (not four fields, or a non-sha-shaped sha —
    an option-shaped sha included); the gate fails closed on any malformed line."""
    refs: list[PushRef] = []
    malformed = 0
    for raw in stdin_text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        parts = line.split(" ")
        if len(parts) != 4:
            malformed += 1
            continue
        local_ref, local_sha, remote_ref, remote_sha = parts
        if not (SHA_SHAPE_RE.match(local_sha) and SHA_SHAPE_RE.match(remote_sha)):
            malformed += 1
            continue
        refs.append(PushRef(local_ref, local_sha, remote_ref, remote_sha))
    return refs, malformed


HEADS_PREFIX = "refs/heads/"

#: Where the project gitflow is stated — every refusal points there.
_LAW = "project gitflow: specs/constitution.md"


@dataclass(frozen=True)
class GateFixes:
    """What a fix line names: the repo (``git -C``), the live work branch, whether it
    is cut locally, and HEAD's branch (``""``: detached)."""

    repo: str
    work: str = ""
    cut: bool = False
    head: str = ""


def _pushable(branch: str) -> bool:
    """The worktree grammar's one answer (its owner, through the one loader), loaded only
    for a branch the gitflow does not already name."""
    from dadaia_workspace.infrastructure.ledger_scripts import load_owner

    return bool(load_owner("dd-gitflow-default", "_worktree_names").pushable(branch))


def _blocked(text: str, fix: str) -> Decision:
    """One refusal with one single-command fix (no ``&&``: Windows PowerShell 5.1)."""
    return Decision(
        allowed=False, message=f"[pre-push] BLOCKED: {text} ({_LAW}).\n{spell_fix(fix)}"
    )


def _refuse_branch(
    ref: PushRef, branch: str | None, gitflow: Gitflow, fixes: GateFixes
) -> Decision:
    """Actionable refusal for a non-pushable ref (*branch* ``None``: not a branch head)."""
    role = gitflow.role_of(branch) if branch is not None else None
    if role is not None and is_zero_sha(ref.remote_sha):
        other = gitflow.integration if role == "principal" else gitflow.principal
        return _blocked(
            f"creating the {role} branch '{branch}' on an origin that already holds "
            f"'{other}' would publish new objects — birth it at the published '{other}' tip",
            git_line(fixes.repo, "push", "origin", f"refs/remotes/origin/{other}:{ref.remote_ref}"),
        )
    if role is None:
        return _blocked(
            f"ref '{ref.local_ref}' is outside the gitflow — principal '{gitflow.principal}', "
            f"integration '{gitflow.integration}', work '{fixes.work}'; only a work "
            f"branch is pushable: switch to it, merge {ref.local_sha} into it (never a "
            "rewrite), then push it",
            git_line(fixes.repo, "switch", fixes.work)
            if fixes.cut
            else git_line(fixes.repo, "switch", "-c", fixes.work, ref.local_sha),
        )
    head = gitflow.integration if role == "principal" else fixes.work
    return _blocked(
        f"the {role} branch '{branch}' is never pushed directly — it advances only via a PR "
        f"from '{head}'",
        act("agent", f"open a PR/MR from '{head}' into '{branch}' on your git host"),
    )


def check_branch_policy(
    refs: list[PushRef],
    gitflow: Gitflow,
    fixes: GateFixes,
    births: frozenset[str] = frozenset(),
) -> Decision | None:
    """The first refusal, or ``None``: each ref lands on a work or job branch from the
    same-named local head, or births the principal/integration at a sha in *births*;
    those two are otherwise PR-only."""
    for ref in refs:
        if not ref.remote_ref.startswith(HEADS_PREFIX):
            return _refuse_branch(ref, None, gitflow, fixes)
        branch = ref.remote_ref[len(HEADS_PREFIX) :]
        role = gitflow.role_of(branch)
        if role in ("principal", "integration") and ref.local_sha in births:
            continue
        if role != "work" and not _pushable(branch):
            return _refuse_branch(ref, branch, gitflow, fixes)
        if not ref.local_ref.startswith(HEADS_PREFIX):
            return _refuse_branch(ref, None, gitflow, fixes)
        if ref.local_ref != ref.remote_ref:
            return _blocked(
                f"refspec aims '{ref.local_ref}' at remote '{ref.remote_ref}' — only "
                f"refs/heads/{branch} → refs/heads/{branch} is pushable: name the local "
                "branch as the remote one, then push it",
                git_line(fixes.repo, "branch", "-m", ref.local_ref[len(HEADS_PREFIX) :], branch),
            )
    return None


def _audit_descendant(
    moved: Callable[[str, str], tuple[bool, list[str]]], old: str, new: str
) -> bool:
    """True when *old* is an ancestor of *new* and every changed path, at least one, is in the
    ``audit`` zone; an unreadable fact is False."""
    try:
        descendant, zones = moved(old, new)
    except Exception:  # noqa: BLE001 — a fault in the move check refuses the move
        return False
    return descendant and bool(zones) and set(zones) == {"audit"}


def check_ref_policy(
    lines: list[str],
    gitflow: Gitflow,
    origin: dict[str, str],
    repo: str,
    moved: Callable[[str, str], tuple[bool, list[str]]],
) -> Decision:
    """The first refusal over ``<old> <new> <ref>`` lines: a work-branch update or creation
    (new non-zero, different from old) must land on origin's sha for its ref, or be an audit-only
    descendant move per ``moved(old, new) -> (old is an ancestor of new, zone of each renames-off
    changed path)``, read only for a move that would otherwise be refused; deletions, non-work refs
    and a ref origin does not hold pass. The fix names the tree to open for *repo*."""
    for line in filter(str.strip, lines):
        old, new, ref = line.split()
        branch = ref.removeprefix(HEADS_PREFIX)
        held = origin.get(ref)
        if (
            is_zero_sha(new)
            or old == new
            or gitflow.role_of(branch) != "work"
            or held in ("", None, new)
            or (not is_zero_sha(old) and _audit_descendant(moved, old, new))
        ):
            continue
        fix = (
            platform.command("git", "branch", branch, f"origin/{branch}")
            if is_zero_sha(old)
            else act(
                "agent",
                f"open a tree for this change with {platform.inline(*cli_words(None, 'worktree', 'new', repo))} "
                "and the name of a live job, a backlog slug or a hotfix bug id, then land the change "
                "through that tree's merge",
            )
        )
        return Decision(
            allowed=False,
            message=f"[ref-gate] BLOCKED: '{branch}' would move to {new}, origin holds {held} ({_LAW}).\n"
            f"{spell_fix(fix)}",
        )
    return Decision(allowed=True)
