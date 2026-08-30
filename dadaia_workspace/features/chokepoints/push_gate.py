"""Push-gate orchestration (v0.4.4 FR3 — the gitflow v2 inversion; v0.9.0 FR1/FR2; v0.5.0
specs-canon closure; split out of ``service.py`` at v0.5.1 K7).

:func:`push_gate_decision` is the pre-push half of the chokepoint contract: branch
policy (:mod:`~dadaia_workspace.features.chokepoints.branch_policy`) first, then the
specs/ canon scan, then the range-scoped denylist scan
(:mod:`~dadaia_workspace.features.chokepoints.denylist_scan`) — first refusal wins.
The former FR-W1-02/DP-5 security-verdict-per-pushed-sha check is DELETED from this
path (v0.4.4 A3.4) — it relocates to a PR gate (``dadaia ci verdict-check``, built over
:mod:`~dadaia_workspace.features.chokepoints.verdict`).

This module is business logic: it imports ``core`` only, and NEVER imports
``infrastructure`` and NEVER spawns a subprocess. The canon predicates
(``canon_violations_fn``/``verdict_violations_fn``) and the presence-check counterpart
in ``pre_commit.py`` are INJECTED rather than imported at module scope (v0.5.1 K7):
this is what drops ``chokepoints -> specs.canon`` out of the import-linter
``ignore_imports`` list entirely — the CLI composition root
(``cli/commands/ci.py``) wires ``features.specs.canon.canon_violations``/
``verdict_violations`` straight through, no adapter needed, mirroring how
*object_source* (the injected :class:`ObjectSource`) already works (FR7/A7.2: the
decision function always takes it as a parameter; an unwired production call site is a
CLI defect, never a bypass).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path
from typing import Protocol

from dadaia_workspace.core.models.git_scan import GitObjectReadError, ScannedObject
from dadaia_workspace.features.chokepoints.branch_policy import (
    Decision,
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

#: The law this scan enforces (SPEC v0.9.0 FR5) — quoted verbatim in every refusal.
_DENYLIST_LAW = "DADAIA.md §7 — private names never enter public/pushed material"

#: FR5/A5.4 — at most this many offending objects are listed before a remainder count.
_MAX_LISTED_HITS = 10

#: The fix hint every specs-canon refusal line carries (operator, 2026-08-28) — a
#: canon or verdict violation has exactly one remediation: remove the offending path.
_SPECS_CANON_FIX_HINT = "delete the path; canon: DADAIA.md §6"


class ObjectSource(Protocol):
    """Feature-local structural port over the push-range object reader (ADR-0001: no
    ``core/protocols`` port — the concrete adapter, ``GitSubprocessObjectReader``, is
    the only implementer; this module still never imports ``infrastructure`` or
    spawns a subprocess itself — the CLI composition root (``cli/commands/ci.py``)
    constructs the real adapter and injects it here, exactly as before).
    """

    def new_objects(
        self, repo: Path, local_sha: str, remote_sha: str
    ) -> Iterable[ScannedObject]: ...

    def list_tree_paths(self, repo: Path, sha: str, prefix: str) -> list[str]: ...

    def first_parent(self, repo: Path, sha: str) -> str | None: ...


def _annotate_skip(
    decision: Decision,
    skipped_binary_count: int,
    oversized_notes: tuple[OversizedNote, ...] = (),
    path_masker: PathMasker | None = None,
) -> Decision:
    """Attach the FR6 row-3 skip count AND the v0.11.0 FR4 oversized-blob notes to
    *decision* — reported either way (allow/refuse), and kept honestly DISTINCT: the
    binary count means "not text-decodable at all"; an oversized note means "the first
    N bytes were scanned, the rest genuinely never was — verify it by hand" (grill P13).

    v0.11.0 A6.3: the oversized note's path is masked through *path_masker* — the SAME
    class-wide rule FR6 applies to the denylist refusal, since the note itself began
    naming a path in T-110-06 and is the second channel of the same CWE-532 class
    entry #23 already found once.
    """
    lines: list[str] = []
    if skipped_binary_count > 0:
        lines.append(
            f"[pre-push] {skipped_binary_count} binary blob(s) skipped by the denylist "
            "scan (not text-decodable)."
        )
    for note in oversized_notes:
        masked_path = path_masker.mask_path(note.path) if path_masker is not None else note.path
        lines.append(
            f"[pre-push] {masked_path} is {note.size_bytes} byte(s) — only its first "
            f"{note.scanned_bytes} byte(s) were scanned by the denylist scan; the "
            "remainder was NOT scanned. Verify the rest by hand."
        )
    if not lines:
        return decision
    note_text = "\n".join(lines)
    warn = f"{decision.warn}\n{note_text}" if decision.warn else note_text
    return Decision(allowed=decision.allowed, message=decision.message, warn=warn)


def _compose_denylist_refusal(hits: list[tuple[PushRef, Hit]], path_masker: PathMasker) -> str:
    """FR5: ref, path:line, short blob sha, masked term + source layer, the law, the
    edit + rewrite-before-push remediation, ``--no-verify``, capped at 10 hits.

    v0.11.0 FR6(b): the blob path itself is masked through *path_masker* before
    rendering (entry #23 resolution A) — only offending segments change; the line
    number and short sha stay exactly as today.
    """
    lines = [
        f"[pre-push] BLOCKED: the pushed range publishes {len(hits)} object(s) carrying "
        f"a denylisted term ({_DENYLIST_LAW})."
    ]
    shown = hits[:_MAX_LISTED_HITS]
    remainder = len(hits) - len(shown)
    for ref, hit in shown:
        masked_path = path_masker.mask_path(hit.path)
        lines.append(
            f"  {ref.local_ref} -> {ref.remote_ref}: {masked_path}:{hit.line} "
            f"(blob {hit.sha[:12]}) — masked term '{hit.masked_term}' ({hit.source_layer})"
        )
    if remainder > 0:
        lines.append(f"  ... and {remainder} more offending object(s).")
    lines.append(
        "  Fix: edit the file(s) to remove the term, then rewrite the offending "
        "commit(s) (--amend / interactive rebase / cherry-pick) so no pushed object "
        "carries it, and push again — the range scope means already-published history "
        "never needs a rewrite."
    )
    lines.append(
        "  If this push is a genuine emergency, git's sanctioned, traceable bypass is "
        "`git push --no-verify` (discouraged; leaves a reflog trace)."
    )
    return "\n".join(lines)


def _render_git_read_error(exc: GitObjectReadError, path_masker: PathMasker) -> str:
    """SPEC v0.4.2 FR4/A4.2: render a caught :class:`GitObjectReadError`'s detail with
    its structured ``path`` (if any) masked through *path_masker* — the single render
    boundary for this failure channel. Never ``repr(exc)``, and the path never reaches
    the message unmasked: ``str(exc)`` is the message text the raise site composed
    (already path-free — the path lives on ``exc.path``, not embedded in the string),
    and the masked path is appended structurally here, once.
    """
    detail = str(exc)
    if exc.path is not None:
        detail = f"{detail} (path: {path_masker.mask_path(exc.path)})"
    return detail


def _dedup_new_objects(
    object_source: ObjectSource,
    repo: Path,
    ref: PushRef,
    seen_shas: set[str],
) -> Iterator[ScannedObject]:
    """Yield each object new to *ref*'s range that has not already been seen earlier in
    this scan, recording it into *seen_shas* as it is yielded (A1.4 cross-ref dedupe).

    Streamed straight into :func:`~dadaia_workspace.features.chokepoints.denylist_scan.
    scan_objects` by the caller rather than materialized into a list first
    (code-reviewer MEDIUM performance finding: building the full ``fresh`` list before
    scanning measured ~129 MB resident over a large fallback range) —
    ``scan_objects`` already consumes its ``objects`` argument lazily, one object at a
    time, so nothing downstream needs the list shape.
    """
    for obj in object_source.new_objects(repo, ref.local_sha, ref.remote_sha):
        if obj.sha in seen_shas:
            continue
        seen_shas.add(obj.sha)
        yield obj


def _run_denylist_scan(
    scan_refs: list[PushRef],
    object_source: ObjectSource,
    repo: Path,
    terms: Iterable[tuple[str, str]],
    patterns: Iterable[BaselinePatternLike],
    slugs: Iterable[str],
) -> tuple[Decision | None, int, tuple[OversizedNote, ...], PathMasker]:
    """Run the FR1/FR2 scan over *scan_refs* — every non-deletion ref, tags included.

    Returns ``(refusal_or_None, skipped_binary_count, oversized_notes, path_masker)``.
    A git object-read failure refuses immediately, naming the failure (FR6 row 2) —
    never a silent empty scan. ``oversized_notes`` is deduplicated for free — it is
    built from ``scan_objects`` runs over :func:`_dedup_new_objects`, which shares
    ``seen_shas`` across every ref in this scan, so a blob reachable from two refs
    contributes at most one note (mirrors the existing hit/skip dedup). The returned
    ``path_masker`` (v0.11.0 FR6(b)) is built from the SAME three term sources and is
    reused by the caller for every subsequently rendered oversized note, so a repeated
    offending path segment gets one stable ordinal across the whole invocation.

    code-reviewer MEDIUM finding (v0.11.0 pre-PR review): *terms*, *patterns* and
    *slugs* are each materialized EXACTLY ONCE, right here, before either the
    :class:`PathMasker` or the scan loop below touches them. A one-shot Iterable
    (e.g. a generator) consumed a second time yields nothing — building the masker from
    the raw parameter and separately re-``list()``-ing it later silently emptied the
    second consumption's term set, a latent fail-open. The materialized lists are the
    ONLY thing passed onward from here.
    """
    term_list = list(terms)
    pattern_list = list(patterns)
    slug_list = list(slugs)
    path_masker = PathMasker(term_list, pattern_list, slug_list)
    if not scan_refs:
        return None, 0, (), path_masker
    seen_shas: set[str] = set()
    per_ref_hits: list[tuple[PushRef, Hit]] = []
    skipped_total = 0
    oversized_all: list[OversizedNote] = []
    try:
        for ref in scan_refs:
            fresh = _dedup_new_objects(object_source, repo, ref, seen_shas)
            outcome = scan_objects(fresh, term_list, pattern_list, slug_list)
            skipped_total += outcome.skipped_binary_count
            oversized_all.extend(outcome.oversized_notes)
            per_ref_hits.extend((ref, hit) for hit in outcome.hits)
    except GitObjectReadError as exc:
        return (
            Decision(
                allowed=False,
                message=(
                    f"[pre-push] BLOCKED: reading the pushed-range git objects failed "
                    f"({_render_git_read_error(exc, path_masker)}) — a policy gate never "
                    "skips what it cannot evaluate (fail closed).\n"
                    "  If this push is a genuine emergency, git's sanctioned, traceable "
                    "bypass is `git push --no-verify` (discouraged; leaves a reflog "
                    "trace)."
                ),
            ),
            0,
            (),
            path_masker,
        )
    oversized_notes = tuple(oversized_all)
    if not per_ref_hits:
        return None, skipped_total, oversized_notes, path_masker
    return (
        Decision(allowed=False, message=_compose_denylist_refusal(per_ref_hits, path_masker)),
        skipped_total,
        oversized_notes,
        path_masker,
    )


def _compose_specs_canon_refusal(violations: list[tuple[PushRef, str]]) -> str:
    """FR2 (v0.5.0 specs-canon closure): ref, the offending ``specs/``-relative path,
    the law, one fix hint per offending path, ``--no-verify``, capped at 10 hits —
    the SAME shape :func:`_compose_denylist_refusal` uses."""
    lines = [
        f"[pre-push] BLOCKED: the pushed range publishes {len(violations)} specs/ "
        "path(s) violating the v6 canon or the verdict rule (DADAIA.md §6)."
    ]
    shown = violations[:_MAX_LISTED_HITS]
    remainder = len(violations) - len(shown)
    for ref, path in shown:
        lines.append(
            f"  {ref.local_ref} -> {ref.remote_ref}: specs/{path} — {_SPECS_CANON_FIX_HINT}"
        )
    if remainder > 0:
        lines.append(f"  ... and {remainder} more offending path(s).")
    lines.append(
        "  If this push is a genuine emergency, git's sanctioned, traceable bypass is "
        "`git push --no-verify` (discouraged; leaves a reflog trace)."
    )
    return "\n".join(lines)


def _run_specs_canon_scan(
    scan_refs: list[PushRef],
    object_source: ObjectSource,
    repo: Path,
    canon_violations_fn: Callable[[Sequence[str]], Sequence[str]],
    verdict_violations_fn: Callable[[Sequence[str], str, str | None], Sequence[str]],
) -> Decision | None:
    """SPEC v0.5.0 specs-canon closure (operator ruling 2026-08-28): every pushed
    non-deletion ref's tree is checked for a ``specs/`` path violating the v6 canon
    (or the verdict business rule) — via the INJECTED *canon_violations_fn*/
    *verdict_violations_fn* (v0.5.1 K7: the SAME predicates the doctor's TREE-8 check
    uses, never a second, hand-kept member list — injected rather than imported at
    module scope so this module carries no ``chokepoints -> specs.canon`` edge; the CLI
    composition root wires ``features.specs.canon.canon_violations``/
    ``verdict_violations`` straight through).
    """
    violations: list[tuple[PushRef, str]] = []
    seen: set[tuple[str, str]] = set()
    for ref in scan_refs:
        try:
            raw_paths = object_source.list_tree_paths(repo, ref.local_sha, "specs")
        except GitObjectReadError as exc:
            return Decision(
                allowed=False,
                message=(
                    f"[pre-push] BLOCKED: reading the pushed specs/ tree failed ({exc}) "
                    "— a policy gate never skips what it cannot evaluate (fail "
                    "closed).\n"
                    "  If this push is a genuine emergency, git's sanctioned, "
                    "traceable bypass is `git push --no-verify` (discouraged; "
                    "leaves a reflog trace)."
                ),
            )
        specs_rel = [p[len("specs/") :] for p in raw_paths if p.startswith("specs/")]
        bad = set(canon_violations_fn(specs_rel))
        parent_sha = object_source.first_parent(repo, ref.local_sha)
        bad.update(verdict_violations_fn(specs_rel, ref.local_sha, parent_sha))
        for path in sorted(bad):
            key = (ref.local_sha, path)
            if key in seen:
                continue
            seen.add(key)
            violations.append((ref, path))
    if not violations:
        return None
    return Decision(allowed=False, message=_compose_specs_canon_refusal(violations))


def push_gate_decision(
    refs: list[PushRef],
    *,
    object_source: ObjectSource,
    repo: Path,
    canon_violations_fn: Callable[[Sequence[str]], Sequence[str]],
    verdict_violations_fn: Callable[[Sequence[str], str, str | None], Sequence[str]],
    malformed_lines: int = 0,
    denylist_terms: Iterable[tuple[str, str]] = (),
    baseline_patterns: Iterable[BaselinePatternLike] = (),
    foreign_slugs: Iterable[str] = (),
) -> Decision:
    """Decide whether a push may proceed (v0.4.4 FR3 — the gitflow v2 inversion).

    Policy order, first refusal wins:

    1. **Branch policy** (DADAIA.md §4, :func:`~dadaia_workspace.features.chokepoints.
       branch_policy.check_branch_policy`) — every non-deletion, non-tag ref must be
       ``refs/heads/feature/{M.m.p}``, pushed to the SAME remote name: ``develop`` and
       ``main`` are refused outright (they advance by PR only); names outside the three
       permitted patterns are refused as invalid.
    2. **specs/ canon scan** (v0.5.0 specs-canon closure, operator ruling 2026-08-28)
       — every non-deletion ref, tags included, is checked via *object_source* for a
       ``specs/`` path violating the v6 canon or the verdict business rule (the
       injected *canon_violations_fn*/*verdict_violations_fn*).
    3. **Range-scoped denylist scan** (v0.9.0 FR1/FR2) — every non-deletion ref, tags
       included, is scanned via *object_source* for new objects carrying a denylisted
       term. Runs AFTER branch policy and the canon scan (both free and pure) — under
       v2 this feature push is the first publication to ``origin`` (A3.3).

    There is no fourth step: the former diff-based security-verdict check is DELETED
    from this path (v0.4.4 A3.4) — it relocates to a PR gate covering
    ``feature/{M.m.p}`` → ``develop`` and ``develop`` → ``main`` (``dadaia ci
    verdict-check``, built over
    :func:`~dadaia_workspace.features.chokepoints.verdict.covering_verdict`).

    Deletions (zero sha) are never scanned. Tag pushes ARE scanned but were never
    branch-policy-gated (publishing depends on tag pushes). A malformed stdin line
    fails CLOSED (finding 1) and the REMOTE side of every branch-policy ref must
    match its LOCAL branch name (finding 2: ``push feature/0.0.1:develop``).

    *object_source*, *repo*, *canon_violations_fn* and *verdict_violations_fn* are
    REQUIRED — FR7/A7.2 (extended at v0.5.1 K7 to the canon predicates): the decision
    function always takes every external capability it needs as a parameter; an
    unwired production call site is a CLI defect, never a bypass (FR6 row 4), so there
    is no default that would silently skip a step.
    """
    if malformed_lines > 0:
        return Decision(
            allowed=False,
            message=(
                f"[pre-push] BLOCKED: {malformed_lines} unparseable pre-push stdin "
                "line(s) — a policy gate never skips what it cannot parse (fail "
                "closed).\n"
                "  If this push is a genuine emergency, git's sanctioned, traceable "
                "bypass is `git push --no-verify` (discouraged; leaves a reflog trace)."
            ),
        )

    branch_policy_refs = [r for r in refs if not r.is_deletion and not r.is_tag]
    branch_refusal = check_branch_policy(branch_policy_refs)
    if branch_refusal is not None:
        return branch_refusal

    # Every non-deletion ref (tags included) — computed independently of
    # `branch_policy_refs`, which excludes tags. Runs after branch policy (free and
    # pure, already checked above); shared by both the specs-canon scan (step 2) and
    # the denylist scan (step 3, A3.4).
    scan_refs = [r for r in refs if not r.is_deletion]

    # v0.5.0 specs-canon closure (operator ruling 2026-08-28): step 2.
    canon_refusal = _run_specs_canon_scan(
        scan_refs, object_source, repo, canon_violations_fn, verdict_violations_fn
    )
    if canon_refusal is not None:
        return canon_refusal

    # v0.9.0 FR1/FR2: step 3.
    scan_refusal, skipped_binary_count, oversized_notes, path_masker = _run_denylist_scan(
        scan_refs, object_source, repo, denylist_terms, baseline_patterns, foreign_slugs
    )
    if scan_refusal is not None:
        return _annotate_skip(scan_refusal, skipped_binary_count, oversized_notes, path_masker)

    return _annotate_skip(
        Decision(
            allowed=True,
            message="[pre-push] branch policy + specs-canon scan + denylist scan passed; allow.",
        ),
        skipped_binary_count,
        oversized_notes,
        path_masker,
    )
