# PLAN — Release: 0.5.0

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-software-engineer

Candidate 2 — "definition reviews the as-is before it adds". SPEC FR1–FR7; ADR 0041 (grill Q1–Q5).
Paths are relative to `dadaia_workspace/public/` unless they start with `tests/`, `specs/` or `CONTEXT.md`.

## 1. As-is review

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `skills/dd-release-definition` §3.4 "PLAN names the seams …" | the whole as-is duty: one sentence, no procedure, no table | 0 (6 retired lifecycle PLAN-gate bugs resolved by deletion) | DELETE | R1: replaced by the As-is review section; keeping it beside the new section is a second path |
| `skills/dd-release-definition` §1→§2→§3 order | pick → grill → trio | 0 | REBUILD | demand changes the fundamental behaviour (a step enters between pick and grill); sections renumbered, not appended (R2) |
| `skills/dd-release-definition` §4 demolition bullet | expand–contract only for deleting a subsystem | 0 | REBUILD | contract contradicts the demand: every DELETE/REBUILD row precedes ADD (R4); rewritten in place, not duplicated |
| `skills/dd-release-definition` §6 Done when | picked set, grill, SPEC, traceability | 0 | UPDATE | one bullet: PLAN §1 names every touched unit; SPEC `Replaces` present |
| `skills/dd-grill-me` §-pointers to `dd-release-definition` §2 | two pointers to the grill at §2 | 0 | UPDATE | the grill moves to §3 (R7) |
| `skills/dd-release-implementation/scripts/_release_phase.py` `_refuse_unapproved_trio` | admits any Approved PLAN whatever its structure | 0 | UPDATE | R3: one structural check after the Approved check, inside the admission `phase IMPLEMENTATION` already performs; no flag, no verb, no new file (AC2.5, AC7.2) |
| `skills/dd-release-implementation/scripts/_release_new.py` `SPEC_STUB` | stub without `Replaces`; deletes closed PLAN/TASKS | 1 (`release-new-refuses-the-stacked-candidate-the-law-requires`, resolved, not the stub) | UPDATE | one section between Scope and Out of scope (R6); PLAN deletion kept (a stale Approved pair must not pass) |
| `skills/dd-release-implementation/scripts/_release_schema.py` | vocabulary + status parser | 0 | KEEP | the table parse belongs to the one admission that reads it; a shared helper here would be a single-caller seam |
| `skills/dd-code-review` Axis 2 | SPEC/TASKS vs diff | 0 | UPDATE | ≤ 2 bullets: DELETE/REBUILD unit unchanged = HIGH; KEEP unit grown = finding (D7) |
| `skills/dd-bug-resolution/LINEAGE.md` | Phase 0 ends at the `caused_by` link | 0 | UPDATE | D8 rebuild rule stated once here; echo block gains `rebuild:` (R5) |
| `skills/dd-bug-resolution/SKILL.md` Phase 0 + Done when | link only | 0 | UPDATE | one clause pointing at LINEAGE; Done when names `rebuild`/`none` |
| `skills/dd-bug-resolution/scripts/bugs.py` | ledger verbs | 0 | KEEP | AC4.3: judgement, not a count or a field |
| `data/AGENTS.md` §1 Arm A + §2 engineer row | flow starts `demand -> backlog -> release candidate` | 0 | UPDATE | names the step; no bullet added (AC5.1) |
| `scaffold/releases/AGENTS.md` lifecycle line (+ `specs/releases/AGENTS.md` projection) | starts at `grill` | 1 (`releases-agents-projection-stale-vs-scaffold-source`, resolved) | UPDATE | one line; the projection is re-copied in the same change so the prior bug cannot recur |
| `agents/dd-software-engineer.md`, `agents/dd-product-engineer.md` | no as-is duty | 0 | UPDATE | one line each (AC5.3) |
| `CONTEXT.md` Candidate entry + Specs terms | Candidate arc starts at `grill` | 0 | UPDATE | arc names the as-is review; four terms enter (AC6.1) |
| `_release_phase.py` `refuse_unfinished` | single-caller public helper for the CLOSURE open-task refusal | 0 | DELETE | fails the deletion test (one caller); inlined into `set_phase`'s CLOSURE branch to hold the module and V36 ceilings |
| `_release_phase.py` fix lines (Status, TASKS, As-is) | cwd-relative, POSIX-only `sed` commands | 0 | REBUILD | review F1: a fix must work from any cwd — plain pointers to absolute paths derived from `__file__` |
| `_release_new.py` `SPEC_STUB` `---` separators | a horizontal rule between every stub section | 0 | DELETE | carry nothing; removed so the stub gains `Replaces` without growing |
| `skills/dd-release-definition` §1 step 6 | restates steps 2–4 (picking scoped to bugs/backlog/audits) | 0 | DELETE | a restatement; V35 ceiling |
| `skills/dd-release-definition` §6 Consumes bullets + doctor backstop line | three Consumes bullets; the doctor `ledgers` backstop | 0 | UPDATE | Consumes bullets merged; the backstop line is doctor law's, deleted here |
| `skills/dd-release-definition` §8 References | five cross-skill bullets, each already cited inline | 0 | UPDATE | reduced to the releases law; V35 ceiling |
| `skills/dd-bug-resolution` References + LINEAGE "Twenty" line | LINEAGE/RED-LOOP bullets linked inline; cap restated | 0 | UPDATE | duplicates deleted; the audit redirect moved into Cost bound |
| `tests/contract/test_release_script.py` | — | — | ADD | ADR 0041 `measured_by` path; the existing unit file stays the CLI-shape suite, this one pins the teaching ↔ gate contract (AC2.6) |

Verdict counts: DELETE 4 · REBUILD 3 · UPDATE 14 · KEEP 2 · ADD 1.

## 2. Strategy

- Core problem: definition had no step that reads what exists before adding; the one sentence (§3.4) is
  replaced by a procedure, a table and a structural refusal.
- Constraint (operator Q2): the check is structure only — heading, five header cells, ≥ 1 data row,
  verdict vocabulary. It never counts bugs or reads code; it cannot stall: one `fix:` line naming the
  skill section, and its own skeleton is test-proven to pass (`scaffold-artifacts-fail-own-workflow-gates`).
- Deletion test on `_release_phase.py`: the admission already reads the trio; the check lands there
  (≈ 30 lines, one private function) — no new module, the complexity has exactly one caller.
- The parse: find `^## (\d+\.\s*)?As-is review\s*$` (case-insensitive); take lines up to the next `^## `;
  first `|` line is the header, second the separator, the rest data rows; verdict = cell 4 stripped of
  whitespace, `` ` `` and `*`.
- Law text edits are statements; projections move only by `public stage` + `public install`; doctor and
  `CONTEXT-MAP.md` re-recorded when tests demand.

## 3. Traceability

| FR | Tasks |
|---|---|
| FR1 | T-050-01, T-050-03 |
| FR2 | T-050-02 |
| FR3 | T-050-04 |
| FR4 | T-050-04 |
| FR5 | T-050-05 |
| FR6 | T-050-05 (terms), this PLAN (AC6.2), closure (AC6.3) |
| FR7 | every task; T-050-06 greps R1/R2 gone |
