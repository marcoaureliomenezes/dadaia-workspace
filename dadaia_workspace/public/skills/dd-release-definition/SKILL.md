---
name: dd-release-definition
description: >
  Turn bugs and backlog items into the live release's next closed-scope candidate:
  pick the set, review the as-is, run the mandatory grill, author the trio. Use at the start of each
  candidate's definition.
---

# dd-release-definition

> `dd-product-engineer` authors the SPEC, the engineer the as-is review, PLAN and TASKS. A release has open scope; each candidate does not.

## 1. Pick the set

1. Open `specs/releases/AGENTS.md` (the area's scoped law) and follow it.
2. Inspect `specs/bugs/BUGS.jsonl` via `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status`/`stats`.
3. Read `specs/backlog/BACKLOG.json`'s `active[]` — sanitized by `dd-backlog-definition`, consumed untriaged.
4. Read `specs/audits/**` for undispositioned findings; each enters the SPEC with the
   disposition it will take (`python3 .agents/skills/dd-audit-project/scripts/audit.py disposition`).
5. Name the SPEC's `**Origin:**`: `operator-demand`, `backlog:<ids>` or `bugs:<ids>`.

**Done when** the picked set is recorded; it becomes the SPEC's scope.

## 2. As-is review

- `dd-software-engineer` runs it read-only (no write to code, specs or tests), dispatched by the main thread after the pick and before the grill.
- Read every unit the picked set touches and its ledger slice (`python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status`/`stats`, `git log` on the unit); return the table in the handoff — the main thread carries it into the grill; it lands as PLAN §1.
- One row per touched unit, columns `unit | today | bugs | verdict | why`; DELETE vs KEEP is `dd-codebase-design`'s deletion test; consider DELETE → REBUILD → UPDATE → KEEP, then ADD rows only for what no existing unit can carry (`today` `—`, `why` says why no unit can carry it).
- REBUILD is mandatory when the unit carries ≥ 2 bugs, the demand changes its fundamental behaviour, the change would need a flag, branch, special case or second path, or its contract contradicts the demand; the engineer and the reviewer judge these triggers — no script counts bugs or reads code.
- The PLAN §1 skeleton — `release.py phase IMPLEMENTATION` refuses a PLAN without it:

```markdown
## 1. As-is review

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `features/x/service.py` `run` | what it does today | 2 (`bug-a`, `bug-b`) | REBUILD | two prior fixes on this unit |
```

**Done when** every touched unit has one row and one As-is verdict.

## 3. The mandatory grill

Call the Skill tool with `dd-grill-me` on the picked set — never skipped, even when
scope "looks obvious". Sharpen terminology as it surfaces (`dd-domain-modeling`):
a fuzzy term in the demand becomes a canonical term before it reaches the SPEC.

## 4. Author the trio

1. Author the SPEC (Draft) only after the grill: the picked bug+backlog set, their
   acceptance, every `superseded_by` link.
2. Definition runs on the work branch (`<work>M.m.p`, the constitution's `gitflow:`); the trio's place is the releases law's.
3. Commit shape 5 (`dd-gitflow-default` §3a): SPEC + PLAN + TASKS + the picked entries
   flipped to `status: picked` + picked bugs, one commit; set the `defined` milestone in `_RELEASE.json`
   (`dd-release-implementation`'s `RELEASE-EVENTS.md`).
4. PLAN opens with §1 As-is review (§2); SPEC carries `Replaces` — one bullet per current behaviour a
   DELETE/REBUILD row removes, or `none` with its reason.
5. SPEC in domain names (`dd-domain-modeling`'s `CONTEXT.md`); only FR, AC and T- numbered; sizes per the releases law.

## 5. TASKS as tracer bullets

- Every task carries two keys beside its write set: `blocked by:` (explicit
  dependency edge, may be `none`) and `delivers:` (the observable end-to-end slice —
  "after this task the operator can …").
- Order the group so the FIRST tasks cut a thin end-to-end path; a group that
  delivers no verifiable slice until the last task is misordered.
- Tasks realizing DELETE/REBUILD rows precede tasks realizing ADD rows, each authored
  expand–contract: add the new path, switch consumers, delete the old — each task
  independently green.
- A task whose `delivers:` cannot be stated is either not a task (fold it) or not
  understood yet (back to the SPEC).

## 6. Declaring consumption

- Declare a backlog slug in the SPEC (`**Consumes:** slug-a, slug-b`) only when fully consumed (all its bound anchors shipped); omit the line when none; an unknown slug is fixed before it lands.
- `**Consumes:**` is SPEC provenance only — no library/CLI verb reads it.
- A picked entry stays in `active[]` as `status: picked`; it exits once, at closure,
  by `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py exit` (`dd-release-implementation` RC-FLOW step 7).

## 7. Done when

- Picked set recorded; the `dd-grill-me` session completed and emitted.
- PLAN §1 names every unit the picked set touches; SPEC authored from the refined set, `Replaces` present, `**Consumes:**` declared or omitted.
- Traceability: every approved requirement maps into PLAN strategy and >=1 TASKS entry.
- Every unresolved gap routed to the main thread's operator-gated intake report — never a
  direct backlog append.

## 8. References

- `specs/releases/AGENTS.md` — release-id format, `_RELEASE.json`, the promote act; every other skill is cited where it is used.
