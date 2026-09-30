"""Push-gate orchestration: branch policy, then the specs/ canon scan over the paths
the push nets in and the denylist scan over ONE object walk — first refusal wins. Business logic only: the
canon predicate and the :class:`ObjectSource` are injected by ``cli/commands/ci.py``."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path
from typing import Protocol

from dadaia_workspace.core.cli_line import git_line
from dadaia_workspace.core.gitflow import Gitflow
from dadaia_workspace.core.models.git_scan import (
    ZERO_SHA,
    GitObjectReadError,
    GitRunError,
    ScannedObject,
)
from dadaia_workspace.features.chokepoints.branch_policy import (
    HEADS_PREFIX,
    Decision,
    GateFixes,
    PushRef,
    check_branch_policy,
)
from dadaia_workspace.features.chokepoints.denylist_scan import (
    BaselinePatternLike,
    Hit,
    OversizedNote,
    PathMasker,
    scan_objects,
)

__all__ = ["push_gate_decision"]

_DENYLIST_LAW = "dd-release-implementation §2a — private names never enter public/pushed material"
_MAX_LISTED_HITS = 10
_BYPASS = (
    "The sanctioned, traceable emergency bypass is `git push --no-verify` "
    "(discouraged; leaves a reflog trace)."
)
#: R13, N3: every range is uncommitted to its oldest unpublished commit and amended.
_REWRITE = (
    "Uncommit the unpublished range down to its oldest commit (origin's history is never "
    "rewritten), remove what is listed, `git commit --amend` and push:"
)


class ObjectSource(Protocol):
    """The push-range object reader, injected by the CLI (``GitSubprocessObjectReader``)."""

    def new_objects(
        self, repo: Path, local_sha: str, remote_sha: str
    ) -> Iterable[ScannedObject]: ...

    def unpublished(self, repo: Path, sha: str) -> list[str]: ...

    def remote_branch(self, repo: Path, branch: str) -> bool: ...

    def netted_specs(self, repo: Path, local_sha: str, remote_sha: str) -> list[str]: ...

    def law_deletions(self, repo: Path, local_sha: str, remote_sha: str) -> list[tuple[str, str]]:
        """ADR 0151 M3: (commit, path) per range commit deleting a law line uncited."""
        ...


def _refusal(head: str, rows: Sequence[str] = (), noun: str = "", advice: str = "") -> str:
    """The one pre-push refusal shape: head, rows capped at 10 plus a remainder count,
    then the advice and the ``--no-verify`` bypass."""
    lines = [f"[pre-push] BLOCKED: {head}", *rows[:_MAX_LISTED_HITS]]
    if len(rows) > _MAX_LISTED_HITS:
        lines.append(f"  ... and {len(rows) - _MAX_LISTED_HITS} more offending {noun}.")
    return "\n".join([*lines, f"  {advice}{_BYPASS}"])


def _fail_closed(what: str) -> str:
    return _refusal(f"{what} — a policy gate never skips what it cannot evaluate (fail closed).")


def _notes(
    decision: Decision, binaries: int, oversized: Sequence[OversizedNote], masker: PathMasker
) -> Decision:
    """Attach the skipped-binary count and the oversized-blob notes (path masked,
    CWE-532) as a warning, allow or refuse alike."""
    lines = [
        f"[pre-push] {binaries} binary blob(s) skipped by the denylist scan (not text-decodable)."
    ] * (binaries > 0)
    lines += [
        f"[pre-push] {masker.mask_path(n.path)} is {n.size_bytes} byte(s) — only its first "
        f"{n.scanned_bytes} byte(s) were scanned by the denylist scan; the remainder was NOT "
        "scanned. Verify the rest by hand."
        for n in oversized
    ]
    if not lines:
        return decision
    warn = "\n".join([decision.warn, *lines] if decision.warn else lines)
    return Decision(allowed=decision.allowed, message=decision.message, warn=warn)


def _rewrite_fix(ref: PushRef, object_source: ObjectSource, repo: Path, fixes: GateFixes) -> str:
    """The one fix for the first refused ref (R13: origin is never rewritten)."""
    if ref.local_ref.startswith("refs/tags/") or not fixes.head:
        return "Operator action: a tag or a detached HEAD has no branch to amend; push a branch."
    branch = ref.local_ref.removeprefix(HEADS_PREFIX)
    if branch != ref.local_ref and branch != fixes.head:
        return f"fix: {git_line(fixes.repo, 'switch', branch)}"
    oldest = object_source.unpublished(repo, ref.local_sha)[-1]
    return f"fix: {git_line(fixes.repo, 'reset', '--soft', oldest)}"


def _run_denylist_scan(
    scan_refs: list[PushRef],
    object_source: ObjectSource,
    repo: Path,
    terms: list[tuple[str, str]],
    patterns: list[BaselinePatternLike],
    masker: PathMasker,
) -> tuple[list[tuple[PushRef, Hit]], int, list[OversizedNote]] | Decision:
    """ONE streamed walk over every ref's new objects (deduplicated across refs; a
    materialized range measured ~129 MB): denylist hits and skip counts. A read failure
    refuses (fail closed)."""
    seen: set[str] = set()

    def fresh(ref: PushRef) -> Iterator[ScannedObject]:
        for obj in object_source.new_objects(repo, ref.local_sha, ref.remote_sha):
            if obj.sha not in seen:
                seen.add(obj.sha)
                yield obj

    hits: list[tuple[PushRef, Hit]] = []
    binaries, oversized = 0, list[OversizedNote]()
    try:
        for ref in scan_refs:
            outcome = scan_objects(fresh(ref), terms, patterns)
            binaries += outcome.skipped_binary_count
            oversized.extend(outcome.oversized_notes)
            hits.extend((ref, hit) for hit in outcome.hits)
    except GitObjectReadError as exc:
        return _read_failure(exc, masker, repo)
    return hits, binaries, oversized


def _read_failure(exc: GitObjectReadError, masker: PathMasker, repo: Path) -> Decision:
    """A git read failure refuses (fail closed), its path masked."""
    masked = f" (path: {masker.mask_path(exc.path)})" if exc.path is not None else ""
    return Decision(
        allowed=False,
        message=_fail_closed(f"reading the pushed-range git objects failed ({exc}{masked})")
        + "\nfix: "
        + (  # a run failure is not corruption: no fsck for it
            "Operator action: make git runnable here, then push again"
            if isinstance(exc, GitRunError)
            else git_line(repo, "fsck")
        ),
    )


def push_gate_decision(
    refs: list[PushRef],
    *,
    object_source: ObjectSource,
    repo: Path,
    canon_violations_fn: Callable[[Sequence[str]], Sequence[str]],
    gitflow: Gitflow,
    fixes: GateFixes,
    malformed_lines: int = 0,
    denylist_terms: Iterable[tuple[str, str]] = (),
    baseline_patterns: Iterable[BaselinePatternLike] = (),
) -> Decision:
    """Decide a push, first refusal wins: a malformed stdin line (fail closed); branch
    policy over every non-deletion, non-tag ref (a principal/integration birth allowed
    when origin holds no gitflow branch or it publishes nothing); then ONE walk over
    every non-deletion ref's new objects (tags included) for the denylist scan, while
    the specs/ canon scan (refused first) judges only the paths each ref nets in; an unreadable object store refuses. Every
    capability is a required parameter: an unwired call site is a CLI defect, never a
    bypass."""
    if malformed_lines > 0:
        return Decision(
            allowed=False,
            message=_fail_closed(f"{malformed_lines} unparseable pre-push stdin line(s)")
            + "\nPush one explicit refspec.\n"
            f"fix: {git_line(fixes.repo, 'push', 'origin', gitflow.work_pattern)}",
        )
    branch_refs = [r for r in refs if not r.is_deletion and not r.is_tag]
    roles = (gitflow.principal, gitflow.integration)
    unborn = [
        r
        for r in branch_refs
        if r.remote_sha == ZERO_SHA and r.remote_ref.removeprefix(HEADS_PREFIX) in roles
    ]
    bootstrap = bool(unborn) and not any(object_source.remote_branch(repo, b) for b in roles)
    births = frozenset(
        r.local_sha for r in unborn if bootstrap or not object_source.unpublished(repo, r.local_sha)
    )
    if refusal := check_branch_policy(branch_refs, gitflow, fixes, births):
        return refusal
    scan_refs = [r for r in refs if not r.is_deletion]
    terms, patterns = list(denylist_terms), list(baseline_patterns)  # one-shot iterables
    masker = PathMasker(terms, patterns)
    scan = _run_denylist_scan(scan_refs, object_source, repo, terms, patterns, masker)
    if isinstance(scan, Decision):
        return scan
    hits, binaries, oversized = scan
    try:
        laws = [
            (r, c, p)
            for r in scan_refs
            for c, p in object_source.law_deletions(repo, r.local_sha, r.remote_sha)
        ]
        canon = [
            (r, p)
            for r in scan_refs
            for p in canon_violations_fn(
                [s[6:] for s in object_source.netted_specs(repo, r.local_sha, r.remote_sha)]
            )
        ]
    except GitObjectReadError as exc:
        return _read_failure(exc, masker, repo)
    if canon:
        message = _refusal(
            f"the pushed range publishes {len(canon)} specs/ path(s) violating the v6 canon "
            "or the verdict rule (specs/AGENTS.md).",
            [
                f"  {r.local_ref} -> {r.remote_ref}: specs/{p} — delete the path; "
                "canon: specs/AGENTS.md"
                for r, p in canon
            ],
            "path(s)",
        )
    elif laws:
        message = _refusal(
            f"{len(laws)} pushed commit(s) delete a law line citing no `ADR NNNN` (ADR 0151).",
            [f"  {r.local_ref}: commit {c[:12]} deletes a line of {p}" for r, c, p in laws],
            "commit(s)",
            "Cite the ADR that rules each deletion in that commit's message. ",
        )
    elif hits:
        message = _refusal(
            f"the pushed range publishes {len(hits)} object(s) carrying a denylisted term "
            f"({_DENYLIST_LAW}).",
            [
                f"  {r.local_ref} -> {r.remote_ref}: {masker.mask_path(h.path)}:{h.line} "
                f"(blob {h.sha[:12]}) — masked term '{h.masked_term}' ({h.source_layer})"
                for r, h in hits
            ],
            "object(s)",
            "A test fixture that needs a secret shape composes it at runtime (string "
            "concatenation), never as a tracked literal. The range scope means "
            "already-published history never needs a rewrite. ",
        )
    else:
        message = ""
    decision = Decision(
        allowed=True,
        message="[pre-push] branch policy + specs-canon scan + denylist scan passed; allow.",
    )
    if message:
        first = (canon or laws or hits)[0][0]
        fix = _rewrite_fix(first, object_source, repo, fixes)
        decision = Decision(allowed=False, message=f"{message}\n{_REWRITE}\n{fix}")
    return _notes(decision, binaries, oversized, masker)
