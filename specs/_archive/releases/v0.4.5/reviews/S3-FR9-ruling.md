# S3 — FR9 ruling: registry slug-ownership collisions, the healing lane

**Task:** T-045-22 · **Entry:** `doctor-slug-ownership-uniqueness` (AS-4) · **Author:** software-architect · **Date:** 2026-08-26

## Decision

**(a) IMPLEMENT — report-only.** One check, `INV-6`, inside `DoctorService.check()`
(`dadaia_workspace/features/spec_context/doctor.py`), reading the registry once and reporting
every `repos/<slug>` owned by more than one context (main or associated). `fixable=False`.
No `--fix` branch, no new doctor surface, no change to `dead()`, `create`, `add_repo` or the
migration.

Why report-only and not heal: healing requires a disposition policy — which of two owners
loses the slug — and any automatic choice is exactly the "check on the destructive side of a
broken invariant" shape Firing 5 rejected for `dead()`. The registry cannot know which
context's checkout the operator wants kept; the operator does, and already has the verbs
(`context repo remove`, re-`create` with another slug). A doctor that picks for them would
be a new branch with a new partial-failure mode. Report, name both owners, stop.

## Evidence (problem → prior art → choice)

- **Core problem.** The invariant "each `repos/<slug>` has at most one owning context" is
  enforced by construction at the only two store-write seams that write slug ownership —
  `create` (service.py:289, `_store.save`) and `add_repo` (service.py:381, `_store.update`),
  both through `_foreign_slug_owner` (service.py:357). Neither seam ever re-reads existing
  state; `migrate/state_v3.py` is purely additive (`setdefault("associated_repos", [])`) and
  `JsonContextStore` tolerates v2 and v3 on read, so a registry that collided **before**
  `1f50dbdf`/`ed5d64cd` landed carries its collision through unchanged and unreported.
- **Bug history (ledger 985–988).** `context-repo-add-accepts-foreign-context-slug` (HIGH,
  F-1) and `context-create-accepts-slug-owned-by-another-context` (HIGH, F-12) — same
  destroy-foreign-work class as the older `context-alive-sweeps-unrelated-worktree-changes`.
  Two seam fixes, first generation, zero recurrence. Firing 5 check (a) explicitly deferred
  the third lane (historical state) to intake; RELEASE-VERDICT B2 routed it here. No fix in
  this class ever touched `dead()`; this ruling keeps that record intact.
- **Prior art surveyed.** `check()` already holds the exact pattern: `INV-4`/`INV-5`/`CTX-URL-1`
  iterate `self._store.list_all()` and emit `DoctorIssue(code, description, fixable)`. The
  `_foreign_slug_owner` message already states the blast radius in one sentence. Nothing new
  to design; reuse both shapes verbatim.
- **Existing seam inventory.** `grep '_store\.save\|_store\.update'` in `spec_context/`: one
  `save` (`create`), five `update`s (`update_url`, `add_repo`, `remove_repo`, `alive`, `dead`).
  Only `create`/`add_repo` change slug ownership. `dadaia import` restores through
  `ImportService` → re-activation, never a direct registry write. A registry-wide check reads
  the **result**, so it covers all three lanes (two verbs + history) without knowing any verb.
- **Size.** `spec_context/doctor.py` is 533 lines. Note: `_DOCTOR_CEILING = 700` in
  `tests/contract/test_module_size_ceiling.py` globs `features/specs/doctor*.py`, **not**
  `features/spec_context/doctor.py` — the ceiling does not bind here. Estimated +22 LOC
  production, +25 LOC tests → ~555 lines, 145 under the ceiling if it did apply.

## Consequences

- **A9.1** — invariant exists, fixture proves a pre-existing collision is reported.
- **A9.2** — **the F-1/F-12 class has no remaining undecided lane.** Seam 1 (`add_repo`)
  and seam 2 (`create`) are guarded by construction; lane 3 (historical/migrated state) is
  surfaced by `INV-6`. `dead()` stays a pure consumer of a registry the doctor can now vouch for.
- **A9.3** — one check in the existing lane, same `DoctorIssue` shape, same `check()` loop.
- **Bug surface: REDUCED.** Evidence: the class's two HIGH bugs closed with zero recurrence;
  this adds a read-only detector on the same registry with zero new exception shapes, zero
  new flags, zero growth in the destructive lane; one CLI-visible behaviour (a silent
  colliding registry) is deleted. Memory: `context-management.md` gains the outcome at CLOSURE;
  `specs-doctor.md` — no change (this is `dadaia doctor`, not `specs doctor`).

## Residual risk

A collision is reported only when the operator runs `dadaia doctor`; between migration and
that run `dead()` on a colliding context still destroys the other owner's checkout. Accepted:
`dadaia import` already tells the operator to run `doctor` next, and the migration is a
one-time hop. Not accepted as a reason to guard `dead()` — that lane was ruled out in Firing 5.

## Instruction to software-engineer

1. **Insertion point:** `doctor.py` `check()`, immediately after the `INV-5` loop and before
   `# ---- ROOT invariants (T-SANI-05) ----`. Build `owners: dict[str, list[str]]` from
   `contexts`: for each ctx append `ctx.name` under `ctx.repo_slug` and under every
   `r.slug for r in ctx.associated_repos`. For each slug with `len(names) > 1`, append
   `DoctorIssue(code="INV-6", fixable=False, description=f"Repo slug '{slug}' is owned by
   more than one context ({', '.join(sorted(names))}). 'repos/<slug>' is a namespace every
   context shares — 'dadaia context dead' on any owner would commit, push and delete the
   others' working tree. Remove it from all but one owner ('dadaia context repo remove') or
   re-create the context with a different slug.")`. Sort slugs for deterministic output.
2. **Tests** in `tests/unit/test_spec_context_doctor.py`, reusing `_ctx`/`_make_doctor`
   (the FakeContextStore is the "colliding v2 registry": save `_ctx("a", repo_slug="x")` and
   `_ctx("b", repo_slug="x")` — no guard runs on `store.save`, exactly what the migration
   imports): (i) main/main collision → one `INV-6`, both names in the description,
   `fixable is False`; (ii) main-vs-associated collision (`associated_repos=[...]` on `b`) →
   one `INV-6`; (iii) `test_check_clean_state_no_issues` stays green unchanged (no-regression
   pin). Declare intent + size per `dadaia-test-stewardship`.
3. **Do not** touch `fix()`, `dead()`, `service.py`, `state_v3.py`, or the CLI. Commit as
   `feat(T-045-22): registry-wide slug-ownership invariant`. Expected diff: ~+22 production,
   ~+25 tests, 0 deletions — growth is the missing detector itself, not a branch on a verb.
