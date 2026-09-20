---
name: dd-release-definition
description: >
  Turn bugs and backlog items into the live release's next closed-scope candidate:
  pick the set, run the mandatory grill, author the trio. Use at the start of each
  candidate's definition.
---

# dd-release-definition

> `dd-project-manager` drives every step directly (the engineer authors PLAN and TASKS),
> from picking the set through SPEC → PLAN → TASKS. A release has open scope; each
> candidate does not.

## 1. Pick the set

1. Open `specs/releases/AGENTS.md` (the area's scoped law) and follow it.
2. Inspect `specs/bugs/BUGS.jsonl` via `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status`/`stats`.
3. Read `specs/backlog/BACKLOG.json`'s `active[]` — already sanitized by
   `dd-backlog-definition`, consumed with no further triage.
4. Read `specs/audits/**` for undispositioned findings; each enters the SPEC with the
   disposition it will take (`dadaia audit disposition`).
5. Keep picking scoped to `specs/bugs/` + `specs/backlog/` + `specs/audits/` discovery.

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
3. Commit shape 5 (`dd-gitflow-default` §3a): SPEC + PLAN + TASKS + the picked entries
   flipped to `status: picked` + picked bugs, one commit; set the `defined` milestone in `_RELEASE.json`
   (`dd-release-implementation`'s `RELEASE-EVENTS.md`).
4. PLAN names the seams the work will cut — speak `dd-codebase-design`
   (module, seam, deletion test) when declaring what each FR grows or deletes.
5. SPEC in domain names (`dd-domain-modeling`'s `CONTEXT.md`); only FR, AC and T-
   numbered; `wc -c SPEC.md TASKS.md` under the `specs/releases/AGENTS.md` size ceiling before commit
   shape 5.

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
- A picked entry stays in `active[]` as `status: picked`; it exits once, at closure,
  by `dadaia backlog exit` (`dd-release-implementation` RC-FLOW step 7).
- Mechanical backstop: `dadaia doctor`'s `ledgers` section schema-validates
  `BACKLOG.json` and `backlog_histo.jsonl` on every run.

## 6. Done when

- Picked set recorded; the `dd-grill-me` session completed and emitted.
- SPEC authored from the refined set; `**Consumes:**` declared or omitted.
- Traceability: every approved requirement maps into PLAN strategy and >=1 TASKS entry.
- Every unresolved gap routed to the PM's operator-gated intake report — never a
  direct backlog append.

## 7. References

- `dd-backlog-definition` — the sanitized-set source and the histo contract.
- `dd-grill-me` — the mandatory pre-SPEC session.
- `dd-gitflow-default` §3a shape 5 — the definition commit shape.
- `dd-release-implementation` (`RELEASE-EVENTS.md`, `RC-FLOW.md`) — state recipe, gate
  cadence, disposition sweep.
- `specs/releases/AGENTS.md` — release-id format, `_RELEASE.json`, `rc-N/`.
