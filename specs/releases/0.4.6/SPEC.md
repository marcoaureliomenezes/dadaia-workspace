# SPEC — Release: 0.4.6

**Status:** Aprovado
**Release ID:** 0.4.6
**Owner:** product-engineer
**Opened:** 2026-09-03
**Consumes:** slop-law-one-definition-one-home

---

## 1. Problem and context

- `slop` is law on 14 surfaces and defined on none — governance map
  `.dadaia/reports/dadaia-workspace/claude/2026-09-03T023255Z-slop-governance-map/`,
  ratified 2026-09-03, measured on `feature/0.4.6 @ 83af41b0`.
- Four implicit meanings; one rule in up to five homes; zero rules for comments (264 carry
  a governance id) and docstrings (158); constitution §12 held since v0.1.46 and did not hold.
- 231 test files without `Intent:` (unit 143/232, integration 51/78, contract 37/69,
  e2e 0/14); 105 `PREFIX-NN` families; 678 of 902 handoffs older than 30 days.
- `tests/AGENTS.md` and `repos/<slug>/AGENTS.md` never load in Claude Code: only
  `CLAUDE.md -> @AGENTS.md -> @DADAIA.md` loads; no `repos/dadaia-workspace/CLAUDE.md` exists.
- Folded in: architect RETURN `2026-09-03T052000Z` (F1-F12); operator ruling 2026-09-03 (§7).

## 2. Objective and distribution classes

One definition (the deletion test, `DADAIA.md` §7.6); one home per statement in one of two
classes, both enforced by the workspace; detection in one disclosed sibling; four repo-pure
ratchets; net law surface shrinks.

| Class | Homes | Enforced by |
|---|---|---|
| Agentic entities | `DADAIA.md` §7.6, skills, personas, scoped `AGENTS.md` | reprojection, `behavior-map` hashes, `public doctor` |
| Scaffolded specs | fixed sections in `constitution.md`, `memory/ARCHITECTURE.md`, `memory/QUALITY.md` | `specs doctor` FIXED-1/2 (`--fix` heals), memory bootstrap |

The 16 ratified bullets (report §4.2) land one each:

| Ratified bullet | Class | Home |
|---|---|---|
| 1 definition · 2 scope · 3 dies in the change · 4 writer/reviewer/auditor · 15 one home · 16 pointer | agentic | `DADAIA.md` §7.6 |
| 11 SPEC · 12 glossary name · 13 file home + GC · 14 branch, candidate | scaffolded | constitution, fragment `slop-law` |
| 5 comment · 6 docstring · 9 born called · 10 fix replaces | scaffolded | `ARCHITECTURE.md`, fragment `slop-code` |
| 7 test `Intent:` · 8 mock at the frontier | scaffolded | `QUALITY.md`, fragment `slop-tests` |

- `slop-law` bullet 1 cites §7.6 (a pointer); bullet 15 lives in §7.6 only (ruling 13).

## 3. Scope (candidate 3)

### 3.1 The deliverable text

`DADAIA.md` §7.6 — agentic class, 7 bullets, English, each ≤150 chars; the Portuguese text
of report §4.2 is the ratified source. Enters §7 Quality after §7.5.

```
### 7.6 Slop

- Slop is what passes the deletion test without loss: removed, no behavior changes and no decision loses its record.
- The test applies to a file, line, comment, test, spec sentence, acronym, branch, release, rule or handoff.
- Slop dies in the change that finds it; it is never commented out, marked, archived or deferred.
- The writer proves the artifact fails the deletion test; the reviewer applies the test; the auditor measures the balance.
- A rule lives in one home; the second copy is deleted; a consumed handoff is deleted in the same turn.
- Artifact rules live by class: constitution `Slop`, memory `ARCHITECTURE`/`QUALITY` fixed sections; `specs doctor` keeps them byte-exact.
- Detection and ratchets: `dd-code-review` SLOP.md; measured by `tests/contract/test_slop_ratchets.py` and audit pillar 2.
```

Fragment `public/scaffold/fixed/slop-law.md` → `constitution.md` (H2 section):

```
## Slop — workspace law (fixed)
- Slop is what passes the deletion test without loss: removed, no behavior changes and no decision loses its record (`DADAIA.md` §7.6).
- A SPEC declares scope, observable criteria and decisions in domain names; it fits the byte ceiling of `DADAIA.md` §6.7.
- A concept takes a glossary name; a numbered code exists only where a mechanical index reads it (FR, AC, T-).
- Every file has a canonical home and a GC path; summaries, backups, notes and scratch live in `.dadaia/tmp/` or do not exist.
- A branch dies at merge; a candidate exists only with scope that changes behavior.
- Measured by `dadaia specs doctor` (FIXED-1/2) and the slop ratchets; detection signals: `dd-code-review` SLOP.md.
```

Fragment `slop-code.md` → `memory/ARCHITECTURE.md` (last `###` of Part 2):

```
### Slop — code (fixed)
- A comment explains a non-obvious why; the what, the history and any spec, task, ADR or version id live in git and the ledgers.
- A docstring states the contract in at most 3 lines; bug history lives in `BUGS.jsonl`.
- Code is born with a real caller in the same change; without a caller it does not exist.
- A fix replaces the old path; it never wraps it and never opens a second path.
- A port exists only with two production adapters; a parameter exists only when it is read.
- Detection: `dd-code-review` SLOP.md S1, S2, S4, S5; measured by ratchet V32 and `test_protocols_have_two_adapters`.
```

Fragment `slop-tests.md` → `memory/QUALITY.md` (last `###` of Part 2):

```
### Slop — tests (fixed)
- A test is born with `Intent:`, fails for a real regression and asserts a value that comes from outside the code under test.
- A mock exists only at the system boundary (network, clock, randomness); an own module is tested through its interface.
- A test name states current behavior; a tombstone (a test of an absence) and an expired SCAFFOLD die at closure.
- Pruning is a `qa-engineer` verdict executed by `software-engineer`; a deletion cites its criterion and its replacement `file:line`.
- Detection: `dd-code-review` SLOP.md S3; measured by ratchet V31 and `test_test_suite_ratchets.py`.
```

- Heading level is the one edit to the ruling's fragments: memory fragments carry `###`
  because `test_each_memory_file_has_exactly_two_parts_in_order` admits exactly two `## `
  parts per memory file; the constitution fragment stays `##`.

### 3.2 Functional requirements

- FR1 — Law (agentic): `DADAIA.md` gains §7.6 (7 bullets); §7.2 tombstone line becomes
  "Tombstones and expired SCAFFOLD die at closure (§7.6)"; §6.7 gains the SPEC/TASKS byte
  ceiling; §10.2 gains `slop`, `ratchet`, `fixed section`.
- FR2 — Constitution: §12 shrinks to the three bullets the fixed block does not carry
  (memory-write phase ownership; an add-only fix carries its justification; the derivation
  law) plus a pointer to the fixed section; `:11` "A rule stated twice…" deleted; §16's
  closing sentence reduced to "(§12)"; the `slop-law` block appended by `specs doctor --fix`
  (MUTATING, IMPLEMENTATION); `constitution_version` 5.0.0 -> 5.1.0; ADR 0010 proposed —
  its `decision` names §7.6, the three fixed sections, P-24's amendment and P-29.
- FR3 — Memory, closure pass only (`product-engineer`, CLOSURE, MEMORY class): `QUALITY.md`
  Part 2 "CI and anti-slop" -> "CI gates"; new "Slop measurement" (V31-V34 by module; the
  closure GC step; the audit readout); the `slop-tests` block; `tldr`/`summary` drop
  "anti-slop rules". `ARCHITECTURE.md` gains the `slop-code` block. Part 1 — P-24 amended to
  the downward form (V31 per tier) and P-29 added (`Measured by: pytest
  tests/contract/test_slop_ratchets.py`, `ADR: 0010`) — lands in the operator's ADR-0010
  acceptance commit (§6.5), never in a task.
- FR4 — One home per rule (scoped law): `tests/AGENTS.md` + `templates/tests-AGENTS.md` keep
  Architecture, Size tiers and cost, Markers and cost + one pointer bullet; Intent/admission/
  deletion, No Slop, Good Test Standard deleted (homes: `dd-test-stewardship`, §7.6,
  `slop-tests`). `dadaia-AGENTS.md` `:9`/`:61` "is slop" -> "(§7.6)". `repo-AGENTS.md` gains
  "## 5. Source hygiene" (four write-point lines + pointer to `ARCHITECTURE.md`'s block — the
  report's permitted second touch). `releases/AGENTS.md` byte-ceiling bullet;
  `reports-AGENTS.md` §2 prose bullet; `tests/README.md` drops its "Intent taxonomy" citation.
  Scaffold slop lines (constitution `:86`, `:146`; QUALITY `:21-23`) are replaced by FR10's blocks.
- FR5 — Detection: new sibling `dd-code-review/SLOP.md`, S1-S10 (signal, diff check,
  severity, fix direction) as report §4.6; `SKILL.md` §2 pointer + §4 verdict rule; pointer
  lines in `dd-test-stewardship` (mock only at the frontier; expected value from an
  independent source), `dd-release-definition` §3, `dd-codebase-design` §3, `AUTHORING.md` §6.
- FR6 — Audit and personas: `dd-audit-project/PILLAR-SPECS.md` gains "Slop readout" (six
  steps, report §4.7); `project-auditor` §4 the readout line. Personas lose duplicates and
  carry the proof they leave: `software-engineer` "Never fabricate a test…" (`:105`) deleted,
  §1 Owns gains the deletion-test proof line; `qa-engineer` "Never accept: magic-mock
  inflation…" (`:95`) -> SLOP.md §Tests pointer; `software-architect` §5 -> S4/S5 pointer;
  `code-reviewer` §3 step 5 + `slop` finding category; `product-engineer` §1 Owns SPEC line.
  `behavior-map.json` tuples re-recorded; no new row.
- FR7 — Ratchets and bridges. (a) V31 replaces V27 in place in
  `tests/contract/test_test_suite_ratchets.py`: same enumeration (`tracked_test_files()`),
  assertion inverted to a ceiling on undeclared files per tier (unit, integration, contract,
  e2e), `e2e = 0`, down only; `tests/scripts/check_test_intent_declared.py` and
  `tests/integration/scripts/test_check_test_intent_declared.py` deleted in the same commit.
  (b) New `tests/contract/test_slop_ratchets.py` carries V32-V34 only — measure, pin at
  birth, down only, one mutation fixture each, tree walks through the shared helper.
  (c) Two harness bridges via `features/spec_context/scoped_law.py::install_scoped_law`:
  `<repo>/CLAUDE.md` <- `templates/repo-CLAUDE.md`, `<repo>/tests/CLAUDE.md` <-
  `templates/tests-CLAUDE.md`, both exactly `@AGENTS.md`, install-if-absent, called from
  `dadaia context alive`; the two hand-written blocks collapse into one loop over a four-row
  `(template, dest)` table; the templates enter the manifest at `public stage`
  (`build_manifest` walks `templates/`). `public install` never writes under `repos/`.
- FR8 — Closure GC: `dd-release-implementation/RC-FLOW.md` step 8 gains
  `dadaia reports cleanup --older-than 30d` and `dadaia tmp gc`; its scope line becomes "this
  candidate's own artifacts, plus the 30-day sweep"; both run once now on the instance
  (runtime, no commit); the `closure-artifact-gc` log entry reports handoffs >30 d = 0. V35 is
  that readout plus the audit pillar-2 re-measure — never a `pytest` ratchet.
- FR9 — Test curation, batch 1 = `tests/contract` (37 of 69 files without `Intent:`):
  `qa-engineer` verdict per file (declare, or delete with the criterion and the replacement
  `file:line`), `software-engineer` executes; V31's contract pin drops to 0 in the same
  commit. Unit (143) and integration (51) re-enter via the closure deferral record
  (`DADAIA.md` §6.6) under new task ids.
- FR10 — Fixed law sections. One home: `public/scaffold/fixed/<id>.md`, the three fragments
  of §3.1. `FIXED_SECTIONS` in `features/specs/memory_canon.py` maps `constitution.md` ->
  `slop-law`, `memory/ARCHITECTURE.md` -> `slop-code`, `memory/QUALITY.md` -> `slop-tests`.
  Marker grammar `<!-- dadaia:fixed <id> -->` … `<!-- /dadaia:fixed <id> -->`; the text
  between equals the fragment byte-for-byte; scaffold templates carry the pair at the
  canonical position (constitution: last section; memory: last subsection). Two pure functions:
  `render_fixed_section(text, id, fragment)` (append when absent, replace the body when
  present) used by `canon.scaffold` and the doctor fix; `extract_fixed_section(text, id)`
  used by the doctor check and the injection hook — a leaf the hook imports without the
  container. Rule family FIXED-1 (block missing) / FIXED-2 (body drifted), ERROR,
  `fixable=True`, after the memory checks. `hooks/ctx_inject.py::_build_memory` appends
  `=== workspace law (fixed) ===` + the ARCHITECTURE and QUALITY blocks (bounded by fragment
  size, no digest). No new CLI verb, no new hook. The lib's `specs/constitution.md` receives
  its block in T-046-18 via `specs doctor --fix`; the lib's memory files in the CLOSURE pass.

## 4. Change ledger (one line per file)

| File (library source) | Action | Delta |
|---|---|---|
| `public/data/DADAIA.md` | §7.6 (7); §7.2, §6.7, §10.2 | +11 |
| `specs/constitution.md` | §12 -> 3 bullets + pointer; `:11`; §16; 5.1.0; block via `--fix` | -17/+9 |
| `specs/memory/QUALITY.md` (CLOSURE; P-24/P-29 at ADR-0010 acceptance) | CI gates; Slop measurement; block; tldr | +16 |
| `specs/memory/ARCHITECTURE.md` (CLOSURE) | block | +8 |
| `specs/ADRs/decisions.jsonl` | ADR 0010 `proposed` | +1 |
| `public/scaffold/fixed/{slop-law,slop-code,slop-tests}.md` | new fragments | +22 |
| `public/scaffold/{constitution,memory/ARCHITECTURE,memory/QUALITY}.md` | slop lines out; marker pairs in | +1 |
| `tests/AGENTS.md` + `public/templates/tests-AGENTS.md` | 3 sections out; pointer bullet | -52 |
| `tests/README.md` · `public/data/dadaia-AGENTS.md` | citation / "is slop" -> "(§7.6)" | 0 |
| `public/templates/repo-AGENTS.md` · `{repo,tests}-CLAUDE.md` · `shipped-hashes.json` | §5; bridges; re-record | +8 |
| `public/scaffold/releases/AGENTS.md` · `public/data/reports-AGENTS.md` | ceiling bullet; prose bullet | +2 |
| `public/skills/dd-code-review/SLOP.md` + `SKILL.md` | S1-S10; §2 + §4 | +47 |
| `dd-test-stewardship` · `dd-audit-project/PILLAR-SPECS.md` · 3 pointer skills · `RC-FLOW.md` | bullets; readout; step 8 | +16 |
| six personas · `public/entities/behavior-map.json` | proof lines; tuples re-recorded | 0 |
| `features/specs/{memory_canon,canon,rules,doctor_memory}.py` · `hooks/ctx_inject.py` | `FIXED_SECTIONS`; render/extract; FIXED-1/2; bootstrap | +80 |
| `features/spec_context/scoped_law.py` + its unit test | two blocks -> one 4-row loop | -10/+8 |
| `tests/contract/test_test_suite_ratchets.py` | V31 replaces V27 | 0 |
| `tests/scripts/check_test_intent_declared.py` + its integration test | deleted | -120 |
| `tests/contract/test_slop_ratchets.py` | V32-V34 | +80 |
| `tests/contract/test_fixed_sections_canon.py` · `tests/unit/features/specs/**` · doctor golden | new | +90 |

Net: always-on law +11; six duplicate homes deleted; projected law -45; +47 on invocation
only; one Intent counter instead of three (-120); mechanism +80 production, +170 tests.

## 5. Out of scope

- No new hook, gate stage or CLI verb; no fourth review axis or audit pillar; no
  `.claude/rules/*.md` with `paths:` (a third rule-file kind).
- No rewrite of the 15-rule authoring standard, `dd-test-stewardship`'s lifecycle, or V26/V28-V30.
- Intent backfill of unit (143) and integration (51) — deferred at closure, new task ids.
- Consumer repos keep legacy lowercase memory names (`architecture.md`,
  `quality-assurance.md`): a `specs upgrade` matter; the constitution block applies there.
- Existing consumers' `tests/AGENTS.md` (ruling 8) is not re-projected.
- Operator-private instance rules; the reference corpus under `.dadaia/references/`.

## 6. Acceptance

- AC1 (FR1) — `grep -c '^- '` over the §7.6 block in `dadaia_workspace/public/data/DADAIA.md`
  = 7; `grep -rIn -i slop` on that file returns only §4.2's verdict line, §6.7, §7.2, §7.6, §10.2.
- AC2 (FR2) — `constitution_version` = `5.1.0`; `grep -c 'is slop' specs/constitution.md` = 0;
  §12 ≤ 4 bullets; the `dadaia:fixed slop-law` pair present, body byte-equal to the fragment;
  `grep -c '"id":"0010"' specs/ADRs/decisions.jsonl` = 1; `dadaia specs doctor` reports no
  error other than FIXED-1 on `memory/{ARCHITECTURE,QUALITY}.md` (cleared by AC11).
- AC3 (FR3, closure / ADR-0010 acceptance) — `grep -c 'CI and anti-slop'
  specs/memory/QUALITY.md` = 0; both memory blocks byte-equal to their fragments; P-24 in the
  downward form and P-29 with `Measured by:` once ADR 0010 is accepted;
  `pytest -k "memory_two_tier_shape or quality_principles"` green.
- AC4 (FR4) — `grep -c '^## ' tests/AGENTS.md` = 3; `wc -l tests/AGENTS.md` ≤ 70;
  `grep -c 'dd-test-stewardship' tests/AGENTS.md` ≥ 1; `grep -rc 'is slop'
  dadaia_workspace/public/scaffold dadaia_workspace/public/data` = 0;
  `grep -rn 'Intent taxonomy' tests dadaia_workspace | wc -l` = 0 (completes at T-046-20).
- AC5 (FR5) — `dd-code-review/SLOP.md` exists, `grep -cE '^\| S[0-9]'` = 10;
  `grep -rl 'SLOP.md' dadaia_workspace/public` lists `dd-code-review`, `dd-audit-project` and
  the four personas of FR6 that point at it.
- AC6 (FR6) — `pytest -k "behavior_map or reviewer_persona_review_allowlist"` green;
  `dadaia public stage && dadaia public install --target all && dadaia public doctor` reports
  `[ok] public-privacy`.
- AC7 (FR7) — `pytest tests/contract/test_test_suite_ratchets.py -k v31` green, four
  per-tier pins, e2e = 0, `grep -c V27` = 0 in that file; `pytest
  tests/contract/test_slop_ratchets.py -q` green, three pins, each mutation fixture RED on
  growth; `tests/scripts/check_test_intent_declared.py` absent; after `dadaia context alive
  dadaia-workspace`, `repos/dadaia-workspace/CLAUDE.md` and `…/tests/CLAUDE.md` exist with
  exactly `@AGENTS.md`; `test_scoped_law.py` proves the four rows; both templates are in
  `.dadaia/agentic/manifest.json`.
- AC8 (FR8) — `RC-FLOW.md` step 8 names both commands with `--older-than 30d`;
  `find .dadaia/handoff -name '*.handoff.json' -mtime +30 | wc -l` = 0 after the run.
- AC9 (FR9) — `grep -rL 'Intent:' tests/contract` empty; V31's contract pin = 0, same commit.
- AC10 (all) — local CI preflight green (`ruff format --check`, `ruff check`, `mypy --strict`,
  `pytest`); the trio's own bytes obey V34.
- AC11 (FR10) — `dadaia specs init` in a fresh dir, then `dadaia specs doctor`: no FIXED-*;
  on the lib's `specs/` after the closure pass the three blocks are byte-equal to the
  fragments and `dadaia specs doctor` reports 0 errors; `pytest
  tests/contract/test_fixed_sections_canon.py` green; the bootstrap prefix of `dadaia context
  bind dadaia-workspace` contains `=== workspace law (fixed) ===` with both memory blocks;
  `test_doctor_golden` updated in T-046-23's commit.

## 7. Operator rulings (grill record)

The Part-4 ratification (2026-09-03) is the grill outcome; 10-13 come from the architect's
RETURN and the operator's 2026-09-03 ruling.

1. **Definition** — the deletion test; the three parallel formulations collapse into it.
2. **Always-on home** — agentic statements live in `DADAIA.md` §7.6, not only in a skill.
3. **Governance ids in code** — only `Intent: CONTRACT — <ref>` on a test docstring's first
   line; zero in production (V32 excludes `tests/`).
4. **Byte ceiling** — SPEC ≤ 24 KB, TASKS ≤ 12 KB per candidate (V34).
5. **Numbered families** — only FR, AC, T- are mechanical; every other concept takes a name.
6. **Intent backfill** — by directory, one commit each; undefended tests die.
7. **`tests/AGENTS.md`** — Architecture + Size tiers + Markers, with pointers.
8. **Consumers** — `tests-AGENTS.md` is installed once by `context alive`, then
   operator-owned; never added to TREE-5 (an overwrite path re-opens bug 108's class).
9. **Bridges** — `<repo>/CLAUDE.md` and `<repo>/tests/CLAUDE.md` (`@AGENTS.md`) via
   `scoped_law.py`, the root's adapter; `.claude/rules` with `paths:` rejected.
10. **Accept ADR 0010** — operator step: `status: accepted` with `measured_by`, at trio
    approval or at closure; carries the P-24/P-29 hunk (§6.5). Not accepted: the Part-1 hunk
    waits; Part 2 and the fixed blocks land regardless.
11. **Two distribution classes** (ruled 2026-09-03) — agentic entities and scaffolded specs;
    fixed sections projected by the scaffold, validated and healed by `specs doctor`,
    reinforced by the memory bootstrap.
12. **Batch 1 = `tests/contract`** (37 files) — architect-recommended, decided here.
13. **Bullet 15 has one home** — §7.6 bullet 5; `slop-law` carries no copy (rules and
    handoffs are agentic artifacts). Ruled at definition by the dispatcher under the
    operator's 2026-09-03 implementation order.

## 8. Ratchet baselines (V31-V34)

Measured 2026-09-03 on `feature/0.4.6`; the modules re-measure and pin at birth.

| Ratchet | Home | Counts | Baseline | Direction |
|---|---|---|---|---|
| V31 | `test_test_suite_ratchets.py` (replaces V27) | test files without `Intent:`, per tier | unit 143, integration 51, contract 37, e2e 0 | down only, e2e = 0 |
| V32 | `test_slop_ratchets.py` | governance ids in production comments + docstrings | 264 + 158 = 422 | down only |
| V33 | `test_slop_ratchets.py` | `PREFIX-NN` families without a mechanical reader | 105 | down only |
| V34 | `test_slop_ratchets.py` | SPEC.md + TASKS.md bytes of the live candidate | ceiling 24 KB / 12 KB | fixed ceiling |

- V33: a family is a distinct prefix of tokens matching `\b[A-Z]{1,4}-?[0-9]{2,3}\b` over
  `specs/**` (minus `_archive/`), `dadaia_workspace/**`, `tests/**` (SLOP.md included); a
  family has a reader when a regex or string constant in `dadaia_workspace/**` or `tests/**`,
  outside the counting test, matches its prefix. S1-S10 count as one orphan family — ratified.
- V35 (handoffs older than 30 days: 678 of 902 pre-GC) is not a ratchet — it reads
  `.dadaia/handoff` outside the repo by wall clock; home: the `closure-artifact-gc` log entry
  (target 0) and the audit pillar-2 readout.

## 9. Dependencies and risks

- ADR 0010 gates the Part-1 memory hunk only (ruling 10); Part 2 and the fixed blocks are not.
- Between T-046-23 and the closure pass, `dadaia specs doctor` on the lib reports FIXED-1 ×2
  on the memory files by construction (MEMORY class, `DADAIA.md` §3.2): accepted transient,
  named in AC2, cleared by AC11; no rule downgrade to avoid it.
- `public/scaffold/fixed/` is not a canon entry (`canon.scaffold` copies only CANON entries);
  the privacy scan must still cover it — T-046-23 verifies both.
- Reprojection is the proof of every `public/` edit; a hand-edited projection is itself the bug.
