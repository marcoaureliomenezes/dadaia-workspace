---
slug: workspace-doctor
title: workspace-doctor
category: product
tldr: Diagnoses root hygiene, venv health, context coherence, slug-ownership collisions, stale presence, lock residue; repairs deterministic state only.
summary: >-
  `dadaia doctor` checks workspace-root law, forbidden caches, required state layout,
  workspace venv health, context repository coherence, repo URLs, registry-wide repo-slug
  ownership uniqueness (report-only), stale presence, and
  legacy lock/pointer residue. It is the after-the-fact backstop by design, because hooks
  validate only at the publication boundary and never block a commit.
  `.dadaia/references/` is a sanctioned operator-owned subtree
  outside the context lifecycle. `--fix` performs bounded deterministic cleanup and
  `--redact` masks foreign Spec Context names in the reported issues.
tags:
- workspace
- doctor
- health
- repair
- privacy
last_updated: '2026-08-27'
release_origin: 0.5.0
---

## Purpose

Workspace doctor is the after-the-fact backstop for state and hygiene invariants that
cannot all be enforced by write hooks — and, deliberately, for many that could be.

**The hook posture makes the backstop load-bearing.** Git pre-commit is advisory and always
exits zero, on any staged set; pre-push refuses exactly three things — an invalid branch name,
a denylist hit, an unresolvable runner — and the CI preflight left the hook to become an
always-on rule ([[sdd-gate-v3]]). Nothing in the commit path blocks a human any more. So the
diagnoses this verb reports, the specs doctor's, the backlog doctor's and the public doctor's
are the surface where hygiene is actually observed, and each of them **reports**: an exit code
here informs an agent or the operator, it never stops work mid-flow.

## Checks

- `ROOT-1..4`: root whitelist, forbidden repo caches/state, required workspace
  directories, and tool configuration placement.
- `VENV-1`: `.dadaia/.venv` Python, pip, and dadaia import/entrypoint health.
- `INV-4`, `INV-5`, `CTX-URL-1`: ALIVE/DEAD repository and URL coherence.
- `INV-6`: registry-wide repo-slug ownership uniqueness.
- `PRESENCE-GC`: expired advisory presence records.
- `RETIRED-LOCK-STATE`: any legacy `.dadaia/states/ctx_locks/` or
  `.dadaia/sessions/runtime/` residue.
- `EFF-1`: overdue efficiency-audit signal.

## Independent Boundaries

**`INV-6` reads the registry, not a verb.** Slug ownership is enforced by construction at
the two seams that can introduce a slug from an argument, but neither seam re-reads
existing state, so a registry that already collided — imported verbatim by the schema
migration — carried its collision in unreported. `INV-6` folds the whole registry once and
reports every `repos/<slug>` owned by more than one context, main or associated, naming
both owners and the blast radius. It is deliberately **report-only** (`fixable=False`):
healing would mean choosing which owner loses the slug, and only the operator knows that;
the verbs to act on the answer (`context repo remove`, re-create under another slug) exist
already. The destructive lifecycle verb stays a pure consumer of a registry the doctor can
now vouch for. The residual is honest: between a migration and the operator's next doctor
run a collision is unreported, which the import path already tells the operator to close by
running doctor next.

**`.dadaia/references/` is operator-owned and outside the context lifecycle.** ROOT-4's
allowed-subdirectory set derives from the single workspace-layout authority in `core`, and
`references` is in it: an operator's reference clone under `.dadaia/references/<clone>/` is
never flagged as slop, never garbage-collected, and never treated as a managed context. No
lifecycle verb — resolve, bind, alive, dead, or a GC sweep — acts on a reference clone, and
that clause is asserted on the executed path, because lifecycle verbs reaching into foreign
trees destroyed work before. The sanction is one entry in one canonical set, and the legacy
quarantine list is **computed** as its own candidates minus that set, so a name sanctioned
in one place can no longer be quarantined as legacy in another. `specs/` is untouched by
any of it.

## Redacted Output

`dadaia doctor --redact` renders every issue with each Spec Context name and repo slug
other than the caller's resolved context replaced by a stable `[REDACTED-CONTEXT-<n>]`
placeholder, ordinal by first appearance within the invocation. It exists because
doctor's own diagnostics — stale-presence lines and the ALIVE/DEAD repository coherence
checks — name foreign contexts, and that output gets transcribed into authored documents
([[quality-assurance]]). The flag is opt-in and applies at the render boundary only:
without it the output is unchanged, and the checks themselves always operate on true
names.

## Repair

`dadaia doctor --fix` removes stale presence and retired lock-state trees, repairs
deterministic scaffold/state issues, and leaves ambiguous or operator-authored material
untouched. It never creates, adopts, steals, or releases a concurrency lock because no
such runtime mechanism exists.

## Runtime State

Reads workspace state under `.dadaia/states/` and registered repositories. Repairs are
confined to deterministic workspace-owned state.

## Dependencies

[[context-management]], [[sdd-gate-v3]], [[workspace-init]], [[quality-assurance]].
