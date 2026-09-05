"""The ONE verdict store (v0.5.1 K7): a security-reviewer APPROVED handoff covering a
commit sha, read from the COMMITTED evidence under ``specs/releases/<id>/verdicts/``
(live) and ``specs/releases/_archive/<id>/verdicts/`` (archived) — never
``.dadaia/handoff/``, a workspace-local, gitignored directory a CI checkout never sees.

Before this module, a verdict was read by FOUR independent readers keyed on TWO stores:
``.dadaia/handoff/`` (``chokepoints.service.iter_security_approvals`` /
``gc_consumed_push_verdicts``, now DELETED — the push-verdict GC lifecycle they served
served no live security-authorization purpose once the security verdict itself
relocated to a PR gate at v0.4.4 A3.4) and the committed ``specs/releases/**/verdicts/``
tree (``.github/scripts/pr-verdict-check.sh``'s bash re-implementation, and
``features.specs.doctor_release``'s structural SPEC-DOC-044 staleness check via
``features.specs.canon.verdict_violations``). Cluster D (7 bug-ledger records) traces
directly to this split: a fix landing in one reader did not reach the next.

:func:`covering_verdict` is the ONE rule this module keeps: given the verdict files a
caller has already discovered (:func:`discover_verdict_candidates`) and the sha it
needs coverage for, return the single qualifying :class:`Verdict`, or ``None``. A
committed verdict is always the FIRST commit after the reviewed sha (committing the
file changes the tree, hence the sha of whatever commit carries it — a real
chicken-and-egg git property), so "covers" is deliberately the two-hop model
doctor_release's SPEC-DOC-044 already established (head itself, or head's first
parent) — never an arbitrary-depth ancestor walk. ``dadaia ci verdict-check``
(``cli/commands/ci.py``) is this module's CLI-facing consumer, replacing the bash
script's own re-derivation of the same rule.

Zero I/O beyond reading the candidate paths handed to it (via ``core.handoff_index``,
never ``infrastructure`` — this module NEVER imports it and NEVER spawns a
subprocess, exactly like the rest of ``features/chokepoints/**``).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from dadaia_workspace.core.handoff_index import Handoff, discover_handoff_paths
from dadaia_workspace.core.specs_version import RELEASE_SEMVER_RE, VERDICT_EVIDENCE_ROOT_TEMPLATES

__all__ = [
    "INTEGRATION_TIP_REF",
    "ShaSource",
    "Verdict",
    "covering_verdict",
    "discover_verdict_candidates",
    "live_verdict_shas",
]

#: The integration branch's remote-tracking ref (DADAIA.md §4: every feature merges into
#: ``develop`` — the same branch name ``branch_policy.py`` refuses a direct push to). Its
#: tip is the sha the ship-PR verdict names (§4.2 / dd-gitflow-default §3b) while that
#: verdict sits on the feature branch, so it is one of the LIVE shas.
INTEGRATION_TIP_REF = "refs/remotes/origin/develop"

#: The ``"verdict"`` value a security-reviewer handoff must carry to authorize a push/PR.
_APPROVED = "APPROVED"

#: The handoff ``"agent"`` whose verdict this store honors.
_SECURITY_REVIEWER = "security-reviewer"


@dataclass(frozen=True)
class Verdict:
    """One APPROVED security-reviewer verdict, and the commit sha it covers."""

    commit_sha: str
    path: Path


class ShaSource(Protocol):
    """The two git reads :func:`live_verdict_shas` needs — a structural port the
    push gate's ``ObjectSource`` and the concrete ``GitSubprocessObjectReader`` both
    satisfy; this module still never imports ``infrastructure``."""

    def first_parent(self, repo: Path, sha: str) -> str | None: ...

    def resolve_ref(self, repo: Path, ref: str) -> str | None: ...


def live_verdict_shas(source: ShaSource, repo: Path, head_sha: str) -> tuple[str, ...]:
    """The ONE on-disk liveness set: the shas a committed verdict under
    ``specs/releases/<id>/verdicts/`` may name and not be stale.

    ``head_sha`` itself; its first parent (the committed-verdict shape — the verdict
    file lands in the commit right after the reviewed sha); and the integration branch
    tip (:data:`INTEGRATION_TIP_REF` — the ship-PR verdict DADAIA.md §4.2 stages on the
    feature branch names develop's tip, which becomes the merge commit's first parent
    only after the merge). Anything unresolvable is simply absent; duplicates collapse;
    order is head, parent, tip. ``features.specs.canon.verdict_violations`` (the doctor's
    SPEC-DOC-044 and the pre-push specs-canon scan) consumes exactly this set — the rule
    has one home, so the shape the law mandates is never refused by one gate and
    accepted by another.
    """
    shas: list[str] = [head_sha]
    for sha in (source.first_parent(repo, head_sha), source.resolve_ref(repo, INTEGRATION_TIP_REF)):
        if sha and sha not in shas:
            shas.append(sha)
    return tuple(shas)


def discover_verdict_candidates(repo_root: Path, release_glob: str = "*") -> list[Path]:
    """Every ``*.handoff.json`` under the two canon verdict-evidence roots (live and
    archived, :data:`~dadaia_workspace.core.specs_version.VERDICT_EVIDENCE_ROOT_TEMPLATES`
    — the SAME two roots ``pr-verdict-check.sh`` used to derive by shelling out to
    ``core.specs_version`` itself), relative to *repo_root*.

    *release_glob* narrows the release-id path segment (default ``"*"`` — every
    release). Each template carries exactly ONE ``{glob}`` segment at the release-id
    position, and ``pathlib.Path.glob`` never crosses a ``/`` boundary for a single
    ``*`` wildcard — unlike a bash ``case`` pattern's ``fnmatch`` (the F-17 class the
    bash script needed explicit hardening against), a directory placed at the WRONG
    nesting depth (e.g. a ``verdicts/`` two levels under ``specs/releases/``) can
    never match either template's shape at all, structurally. A bare ``*`` DOES
    still match a single-segment name at the release-id position, though — including
    ``_ideas`` (the F-16 class): every raw hit is therefore additionally validated
    against :data:`~dadaia_workspace.core.specs_version.RELEASE_SEMVER_RE`, the SAME
    canon the bash script derived from, so a ``verdicts/`` directory placed directly
    under ``specs/releases/_ideas/`` (a freely-writable MUTATING directory, never a
    trust root of a required check) is refused as a candidate.
    """
    candidates: list[Path] = []
    for template in VERDICT_EVIDENCE_ROOT_TEMPLATES:
        prefix = template.split("{glob}")[0]
        root_glob = template.format(glob=release_glob)
        for path in discover_handoff_paths(repo_root, f"{root_glob}/*.handoff.json"):
            rel = path.relative_to(repo_root).as_posix()
            release_segment = rel[len(prefix) :].split("/", 1)[0]
            if RELEASE_SEMVER_RE.match(release_segment):
                candidates.append(path)
    return sorted(set(candidates))


def covering_verdict(
    candidates: Iterable[Path], head_sha: str, parent_sha: str | None = None
) -> Verdict | None:
    """The ONE APPROVED security-reviewer verdict covering *head_sha*, or ``None``.

    A candidate qualifies when its handoff parses, ``agent == "security-reviewer"``,
    ``verdict == "APPROVED"``, and ``metrics.commit_sha`` is a non-empty string — the
    SAME qualification the deleted ``iter_security_approvals`` applied. A qualifying
    candidate whose sha equals *head_sha* wins outright; failing that, a UNIQUE
    qualifying candidate whose sha equals *parent_sha* covers it instead (the
    immediate-next-commit shape a committed verdict always takes). Two or more
    qualifying candidates matching the SAME sha are an unusual double-verdict state —
    ambiguous, so this covers nothing (``None``), identical to no match at all
    (stale). A candidate matching neither sha is simply not a match; it is never an
    error for :func:`covering_verdict` itself to see one (the caller decides what "no
    covering verdict" means for its own gate).
    """
    head_matches: list[Verdict] = []
    parent_matches: list[Verdict] = []
    for path in candidates:
        handoff = Handoff.load(path)
        if handoff.agent != _SECURITY_REVIEWER or handoff.verdict != _APPROVED:
            continue
        sha = handoff.commit_sha
        if not sha:
            continue
        if sha == head_sha:
            head_matches.append(Verdict(commit_sha=sha, path=path))
        elif parent_sha is not None and sha == parent_sha:
            parent_matches.append(Verdict(commit_sha=sha, path=path))
    if len(head_matches) == 1:
        return head_matches[0]
    if not head_matches and len(parent_matches) == 1:
        return parent_matches[0]
    return None
