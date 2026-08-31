---
name: dd-release-definition
description: >
  Turn bugs and backlog items into the live release's next closed-scope candidate:
  pick the set, enforce bug-always-solved, run the mandatory grill, author the trio.
  Use at the start of each candidate's definition.
---

# dd-release-definition

> `product-engineer` (dispatched by `project-manager`) drives every step directly,
> from picking the set through SPEC → PLAN → TASKS. A release has open scope; each
> candidate does not.

## 1. Pick the set

1. Inspect `specs/bugs/BUGS.jsonl` via `dadaia bugs status`/`stats`.
2. Read `specs/backlog/BACKLOG.json`'s `active[]` — already sanitized by
   `dd-backlog-definition`, consumed with no further triage.
3. Open bugs and undispositioned audits outrank fresh backlog (`DADAIA.md` §6);
   keep picking scoped to `specs/bugs/` + `specs/backlog/` discovery.
4. Solve every picked bug in the candidate, with exactly one exception —
   subsumption by a picked backlog item: run
   `dadaia bugs supersede <slug> --by <backlog-slug>`, note it in the SPEC, and
   ensure the backlog item's TASKS cover the bug's acceptance criteria. A bug
   neither fixed nor subsumed stays `open` — never silently dropped.

**Done when** the picked set is recorded; it becomes the SPEC's scope.

## 2. The mandatory grill

Call the Skill tool with `dd-grill-me` on the picked set — never skipped, even when
scope "looks obvious". Sharpen terminology as it surfaces (`dd-domain-modeling`):
a fuzzy term in the demand becomes a canonical term before it reaches the SPEC.

## 3. Author the trio

1. Author the SPEC (Draft) only after the grill: the picked bug+backlog set, their
   acceptance, every `superseded_by` link.
2. Definition runs on `feature/{M.m.p}`; the trio lives at the RELEASE ROOT
   (`specs/releases/<v>/`) — after a prior candidate, `dadaia release rc-archive`
   has already cleared it.
3. Commit shape 5 (`dd-gitflow-default` §3a): SPEC + PLAN + TASKS + purge-on-pick +
   picked bugs, one commit; append the `defined` note in `_RELEASE.json`
   (`dd-release-implementation`'s `RELEASE-EVENTS.md`).
4. PLAN names the seams the work will cut — speak `dd-codebase-design`
   (module, seam, deletion test) when declaring what each FR grows or deletes.

## 4. TASKS as tracer bullets

- Every task carries two keys beside its write set: `blocked by:` (explicit
  dependency edge, may be `none`) and `delivers:` (the observable end-to-end slice —
  "after this task the operator can …").
- Order the group so the FIRST tasks cut a thin end-to-end path; a group that
  delivers no verifiable slice until the last task is misordered.
- A demolition (deleting a subsystem) is authored expand–contract: add the new
  path, switch consumers, contract by deleting the old — three tasks, each
  independently green.
- A task whose `delivers:` cannot be stated is either not a task (fold it) or not
  understood yet (back to the SPEC).

## 5. Declaring consumption

- Declare fully-consumed backlog items in the SPEC: `**Consumes:** slug-a, slug-b`;
  omit the line when the candidate consumes none.
- `**Consumes:**` is SPEC provenance only — no library/CLI verb reads it.
- Declare a slug only when fully consumed (all its bound anchors shipped); abort on
  an unknown slug — fix it before it lands in the SPEC.
- Purge-on-pick executes consumption at definition (same commit as the SPEC);
  `dd-release-implementation`'s disposition sweep rewrites the histo record to its
  terminal token at closure.
- Mechanical backstops for a fallen-through slug: `backlog doctor`'s BL-STALE and
  `specs doctor`'s SPEC-DOC-031.

## 6. Done when

- Picked set recorded; every picked bug fixed-in-candidate OR `superseded_by` a
  picked backlog item.
- The `dd-grill-me` session completed and emitted.
- SPEC authored from the refined set; `**Consumes:**` declared or omitted.

## 7. References

- `dd-backlog-definition` — the sanitized-set source and the histo contract.
- `dd-grill-me` — the mandatory pre-SPEC session.
- `dd-gitflow-default` §3a shape 5 — the definition commit shape.
- `dd-release-implementation` (`RELEASE-EVENTS.md`, `RC-FLOW.md`) — state recipe, gate
  cadence, disposition sweep.
- `specs/releases/AGENTS.md` — release-id format, `_ideas/`'s pre-approval role.
