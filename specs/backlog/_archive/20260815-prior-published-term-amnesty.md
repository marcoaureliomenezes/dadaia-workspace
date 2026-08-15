---
title: "prior-published-term amnesty: a term already published in the remote-reachable version of the same path must not refuse the push"
status: DELIVERED — v0.11.0
opened: 2026-08-14
description: >-
  Operator-ratified refinement from the v0.9.0 code-review round (CLOSURE, "Backlog
  returns"): whole-blob matching is KEPT, and the structural tension it creates is
  resolved here, not by widening the ruler. Because the push-range denylist scan
  matches whole blobs, ANY edit to a long-lived file that already contains a
  matching line produces a new blob and a refusal — even though the term was
  already published in the remote-reachable version of that same path. Refusing it
  demands a rewrite of content the operator already published, which is exactly
  what the range scope exists to avoid. The refinement: a term present in the
  remote-reachable version of the SAME path does not refuse; the blob is new, but
  the term is not. This is the single item that clears the latent blockers without
  any amnesty list and without narrowing to diff-scoped matching. Sized honestly by
  the round-2 code review: 29 latent blockers under tests/** at the shipped v4
  baseline (14 home-abs-path, 9 email-address, 5 ipv4-literal, 1 secret-token)
  across 450 tracked test files — until picked, editing any of those files refuses
  the push and the only escape is --no-verify, the same failure mode as the round-1
  CRITICAL relocated to a directory the self-scan sentinel does not cover.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/features/chokepoints/denylist_scan.py#scan_objects
    change: >-
      Accept per-object knowledge of the remote-reachable prior content for the
      same path (or an equivalent seam) and suppress a hit whose matched term is
      already present in that prior version of the SAME path. New terms in the same
      file, and any term in a new path, still refuse. No sanctioned-terms list is
      introduced anywhere (FR4/A4.1 invariant preserved — the amnesty derives from
      published git state, never from a curated list).
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/git_objects.py#GitSubprocessObjectReader
    change: >-
      Provide the remote-side blob lookup the matcher needs: for each scanned
      (path, blob) pair, resolve the same path at the remote-reachable base
      (remote_sha when resolvable) through the same batched conversation, keeping
      the fallback shape (--not --remotes) and the fail-closed posture intact.
  - subject:
      kind: code
      ref: tests/integration/test_repo_self_scan.py#test_this_repos_own_tracked_tree_scans_clean
    change: >-
      Per the round-2 reviewer recommendation, consider extending the self-scan
      sentinel to tests/** with an explicit, shrinking allowlist once amnesty
      lands, so the 29-file latent-blocker count can only go down and is pinned by
      a test rather than by a review figure.
---

# prior-published-term amnesty (whole-blob matching, structural tension)

## Description

See frontmatter. Sources, deduplicated into this single entry:

- `specs/_archive/releases/v0.9.0/CLOSURE.md` §"Backlog returns" — the routed
  return, P1 in the closing PE's reading: "without it, every long-lived file that
  already contains a matching line is a latent one-time blocker". Ratified at the
  code-review round (decision 1): whole-blob matching kept; amnesty routed here
  rather than built under close pressure. The ~30 pre-existing `tests/**` fixture
  literals and the archive-tree hits were deliberately NOT suppressed in v0.9.0 and
  are excluded from the self-scan sentinel's scope with this entry named as the
  rationale (CLOSURE §"Drifts › self-scan-guard-surfaced-two-more-baseline-false-positives").
- Code-reviewer round-2 handoff
  `.dadaia/handoff/dadaia-workspace/2026-08-14T222609Z-code-reviewer-v0.9.0-prepr-round2.handoff.json`,
  LOW "29 latent blockers remain under tests/**" — the honest sizing (metric
  `residual_latent_blockers_tests_dir: 29`) and the recommendation to keep this
  item high in the backlog and extend the sentinel with a shrinking allowlist.
- Same handoff, INFO "dotted attribute chains … the class itself is unbounded" —
  when this entry is picked, prefer a structural fix for the `internal-hostname`
  false-positive class (require a hostname-ish context, or exclude chains whose
  preceding label is a capitalised identifier) over a fourth literal carve-out.
  Cross-reference: `baseline-carve-out-review-cadence` owns the cadence half of
  that finding.

## Memory note

At delivery, the `sdd-gate-v3` atom's push-range scan section records the amnesty
semantics as product truth: same-path prior-published terms never refuse; the
FROZEN/rename invariant and the no-amnesty-list invariant both survive unchanged.
(Recorded here rather than as an intent — the doc anchor for that section is bound
by `closure-v14-perf-figure-correction`; the PE lands both in one CLOSURE pass.)

## Motivation

The v0.9.0 gate proved itself by refusing its own author twice; both refusals were
legitimate. What is NOT legitimate long-term is that already-published terms in
long-lived files re-refuse on every subsequent edit: the feature's first year of
production use would otherwise train the `--no-verify` bypass it names as
discouraged. The amnesty is the root-cause resolution the operator chose over the
two wrong alternatives (an amnesty list — forbidden by FR4; diff-scoped matching —
narrows the ruler).

## Acceptance criteria

- A term present in the remote-reachable version of the same path does not refuse;
  the same term in a NEW path still refuses; a NEW term in an edited path still
  refuses — each pinned by unit tests against real git repos.
- Editing a `tests/**` file that carries a pre-existing fixture literal no longer
  refuses the push (integration proof over a real range).
- No sanctioned-terms constant, list, or file exists anywhere in the matcher
  (existing A4.1 contract test still green).
- Scan stays within the fail-closed posture: a failure resolving the remote-side
  blob refuses, never allows.
- Self-scan sentinel extension to `tests/**` (or an explicit decision not to,
  recorded in the entry at pick time).

## Ownership

`software-engineer` implements (`software-architect` may need to rule on where the
remote-side lookup seam lives); `security-reviewer` verifies the amnesty cannot be
abused to smuggle a new term through an edited path.

## Pick provenance (v0.11.0)

**picked — v0.11.0**, 2026-08-15. Delivered as **FR1 (matcher suppression), FR2
(prior-side lookup) and FR3 (sentinel extension)** of release `v0.11.0` "scan-v2";
this entry is the release's P1 core. Provenance record:
`specs/releases/v0.11.0/SPEC.md` §7. Grill refinements binding on the implementation:
the predicate keys on the **matched value**, never the pattern (grill P1); the
`--not --remotes` fallback shape grants no amnesty (ADR D7); the chunked reader
(`git-objects-streamed-batch-reads`) is a **precondition**, not a sibling (ADR D8); the
sentinel's `tests/**` baseline is a test assertion, never a scan suppression (grill P7).
The D6 cross-reference on the `internal-hostname` false-positive class was evaluated and
**declined** for this release (SPEC §4.3) — it stays with
`baseline-carve-out-review-cadence`. Terminal disposition `DELIVERED — v0.11.0` lands at
closure; the entry file is retained per the never-delete law, pending the single-source
`BACKLOG.md` consolidation.

## Delivery (v0.11.0 closure, 2026-08-15)

**Terminal: `DELIVERED — v0.11.0`.** FR1, FR2 and FR3 shipped and QA-verified across
acceptance ids A1.1–A1.6, A2.1–A2.6 and A3.1–A3.6 (`specs/releases/v0.11.0/ALPHA-1-QA.md`,
APPROVED). The predicate is confirmed keyed on the matched value, not the pattern id — the
smuggling-path attack test A1.3 passes — and the fallback shape grants no amnesty (D7). The
sentinel's `tests/**` extension landed with a 29-row shrink-only baseline, so the census this
entry was sized by is now test-pinned rather than review-pinned. Evidence:
`specs/_archive/releases/v0.11.0/CLOSURE.md` §Validations V3/V4/V5/V6 and §Dispositions.
