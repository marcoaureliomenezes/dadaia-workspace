# PLAN — Release: 0.4.7 · Candidate 11 "memory that cannot stack"

**Status:** Approved
**Release ID:** 0.4.7
**Owner:** dd-software-engineer

---

## 1. Assumptions

- **A1 — The canonical hunk arrives from the PM, not from a task.** `specs/memory/**` never
  appears in a task `Write set:` (SPEC-DOC-047). Before T-047-99's RED test can go green the PM
  must have placed `ARCHITECTURE.md` and `QUALITY.md` (the v7 drafts), deleted
  `specs/memory/TECHSTACK.md`, and appended the ADR 0023 line. The engineer implements FR1's code
  and tests in the working tree and does **not** commit them; the PM stages code + tests + the
  memory hunk + the ADR line as ONE commit `docs(adr): accept 0023-memory-canon-v7`.
- **A2 — `ARCHITECTURE.md`'s `## Tech Stack` section is the only tech-stack source** after FR1;
  `ctx_inject` extracts it by heading, so its absence must be fail-open (empty bootstrap part),
  never a traceback on a v6 consumer tree.
- **A3 — The drift verb reads `catalog.json`, not 23 frontmatter blocks.** `sources` lands in the
  catalog (FR2), so `_memory_drift.py` loads one generated document and matches globs. This is
  what keeps it inside the V36 budget (§5).
- **A4 — The bug-history reading below is evidence, not decoration.** 63 of 518 ledger records
  mention memory (surfaces: `specs` 21, `unknown` 17, `tests` 6, `hooks` 2). The recurring shapes:
  closure generating atoms (`product add` writing files nobody reconciled), catalog/index drift
  (two generated files, two writers), the frontmatter schema rejecting live atoms, and a lint
  blaming the wrong cause. Every one of those is a *second mechanism* bug, not a logic bug.
- **A5 — Upgrade 6 → 7 needs a lane that does not exist today.** `features/migrate/registry.py`
  currently *refuses* `current < goal` outright (the chain was retired at v0.5.1 K10). FR1's lane
  is therefore a new single hop, not a resurrection of `MigrationStep`/`run_chain`.

## 2. Design — per FR, in codebase-design vocabulary

**FR1 — canon v7.** The seam is `core/workspace_layout.MEMORY_TOPLEVEL_FILES`: one tuple, already
the single source the canon rows, `memory_canon`, TREE-3 and the scaffold copy-map are built from.
Dropping `"TECHSTACK.md"` from it is a one-token edit that propagates to every reader — the module
is deep and this candidate proves it. **Deletes:** the third canonical file and its 12 readers'
special cases; `ctx_inject._TECH_STACK_DIGEST_MAX_LINES`, `_digest_tech_stack`'s truncation branch
and the self-pull pointer (a bounded digest is a second, lossy representation of a file the agent
can read — pure pass-through once the file itself is 8–15 lines); `ARCHITECTURE.md`'s "One decider
per fact" table and the SpecsDoctor class diagram (text that drifts every candidate and no rule
measures). `test_memory_two_tier_shape.py` is *renamed and rewritten*, not wrapped:
`test_memory_canonical_shape.py` asserts the v7 headings and order for two files. Deletion test:
delete `TECHSTACK.md` and no complexity reappears at any caller — the section survives inside a
file that already had readers. **Bug surface: shrinks** — one fewer file in the canon, one fewer
digest representation, one fewer schema clause; the `unknown`/`specs` memory-shape bug family
loses the file it was mostly about.

**FR2 — sources + drift.** The seam is the atom's frontmatter, projected into `catalog.json`.
`sources:` makes "which code does this atom describe" a *declared* fact instead of a guess, and the
new sibling `_memory_drift.py` is a pure function of (catalog, `git diff --name-only`,
`git ls-files`). It creates no new state and no new file format. **Deletes:** `_memory_add.py` and
the `product add` verb — an atom generator is exactly the stacking mechanism the SPEC measured
(closure ran `product add`, the atom existed, nobody reconciled it); the add step of a
reconciliation is writing a file, which `check` already validates. `_memory_index.py` is folded
into `_memory_catalog.py` (they are already one act — `_generate` writes both or neither), paying
the rest of the V36 line budget. Deletion test on the drift verb: delete it and the whole FR3 gate
degenerates to free prose again — it earns its keep.

**FR3 — the closure gate.** Two seams, deliberately disjoint: the *writer* (`release.py memory`,
a skill script, where `subprocess`/git is legal) and the *reader* (`RELEASE-TREE-MEMORY`, a doctor
rule over `release_tree.py`, which reads the state document and nothing else — P-02/P-03 hold, no
git in a feature). Scripts never call each other; the worklist crosses as JSON on the operator's
command line. **Deletes:** the free-prose `kind: memory` entry as an accepted shape — after this,
an entry without `since`/`reviewed`/`changed` is a doctor ERROR, so the old five prose entries are
history, not a supported form. `release-state-v1` stays `additionalProperties: false` (P-15): the
three fields are admitted on the `memory` log-entry object only.

**FR4 — MEM-NARRATIVE-1.** One regex table, one home: `features/specs/memory_lint.py`, run
in-process by the doctor as LINT-1. `doctor_memory.py` is at exactly 699 lines — the ceiling — so
this is not a choice between homes, it is the only home, and it is also the right one (the lint
already owns per-line body rules; the doctor owns tree rules). **Deletes:** nothing structurally,
but it makes the existing `FORBIDDEN_MEMORY_HEADING_RE` a subset rule — the heading check stays
where it is; the line check does not duplicate it. This FR only adds; justification against
replace-don't-layer: it adds *one table in the module that already runs per-line body checks*, no
new module, no flag, no second code path, and it retires 38 lines of memory prose at closure.

**FR5 — law follows code.** `MEMORY-UPDATE.md` is *replaced* by the reconciliation protocol (not
amended), `PILLAR-MEMORY.md` §1–§3 likewise, and every `TECHSTACK` citation follows with
`dead_citations` + the derived-docs test as the oracle. **Deletes:** 13 lines of unscored audit
prose, the "every 5 releases, never mandatory" cadence, and the `TECHSTACK` name from the corpus.

## 3. Order of work — tracer bullets

1. **See the worklist before moving anything.** T-047-93 (`sources` in schema + `check` + catalog)
   then T-047-95 (`memory.py drift --json`) run over the LIVE tree: the operator gets the real
   list of drifted atoms and uncovered packages before a single canonical byte moves. T-047-94
   (the deletions that pay for it) lands first so the ratchet is never breached mid-candidate.
2. **Close the loop end to end.** T-047-96 (`release.py memory`) + T-047-97 (`RELEASE-TREE-MEMORY`)
   make the gate real: doctor red → run the two verbs → doctor green, demonstrable on this
   candidate before FR1 touches the canon.
3. **Then the canon** (T-047-98 lint, T-047-99..T-047-102 FR1, uncommitted, PM-staged).
4. **Then the law** (T-047-103..T-047-105), whose oracle is the derived-docs/citation tests.
5. FR6 is the closure procedure — no task, run by the PM with the machinery tasks 1–2 built.

## 4. Verification — the RED test per task

| Task | RED test | What it proves |
|---|---|---|
| T-047-93 | `tests/unit/skills/test_spec_navigator_memory_script.py` — `check` passes an atom with no `sources` | the field is required and a no-match glob is refused |
| T-047-94 | `test_v36_skill_script_corpus_is_pinned` + the `product add` CLI test | the verb is gone and the corpus shrank |
| T-047-95 | new `test_memory_drift.py` over a fixture repo | drift lists changed-source atoms and uncovered packages, exit 1 |
| T-047-96 | `tests/unit/skills/test_release_implementation_release_script.py` | the verb refuses an uncovered worklist, a byte-identical `changed`, a non-CLOSURE phase |
| T-047-97 | `tests/unit/features/specs/` release-tree rule test | doctor ERRORs on a CLOSURE release with no stamped `memory` entry |
| T-047-98 | `tests/unit/features/specs/test_memory_lint.py` | a date/`M.m.p`/`c11`/`T-047-93`/`FR1` line errors; the `ADR:` line does not |
| T-047-99 | `tests/contract/test_memory_canonical_shape.py` | two files, the three headings each, ids unique, no history heading |
| T-047-100 | `tests/unit/hooks/test_ctx_inject_digest.py` | the bootstrap carries the `## Tech Stack` section verbatim; no pointer, no cap |
| T-047-101 | `tests/e2e/features/test_specs_upgrade_e2e.py` | a v6 tree reaches 7 with `TECHSTACK` body appended and the file deleted; a `## Part 1` tree is left alone and named |
| T-047-102 | `test_memory_canonical_shape` scaffold assertions + `dadaia public doctor` | the projected scaffold states the two tiers |
| T-047-103/104 | `tests/contract/test_slop_ratchets.py::test_v35…` + the skill-reference tests | the law moved without growing the corpus |
| T-047-105 | `test_docs_derived_from_memory.py` + `citations`/`dead_citations` | no live `TECHSTACK` citation survives |

## 5. Ratchets — down only

**V34.** SPEC.md is 12,859 B (≤ 24 KiB). TASKS.md is measured with `wc -c` before the definition
commit and stays ≤ 12,288 B.

**V35** (18 dirs / 2,876 lines, at the pin today). `PILLAR-MEMORY.md` 66 → 53 = **−13**;
`MEMORY-UPDATE.md` 28 → 30 = **+2**; `RELEASE-EVENTS.md` ≤ **+5** (the `memory` entry shape);
`dd-spec-navigator/SKILL.md` ≤ **+1** (drift verb, `TECHSTACK` line replaced in place); `RC-FLOW.md`
**±0**. Net **≈ −5 → 2,871**. Dirs unchanged. The scaffold `specs/memory/AGENTS.md` and the
`dd-software-engineer` persona are NOT in `public/skills/**` and do not score. Re-pin V35 to the
measured post-candidate value at T-047-105.

**V36** (31 files / 3,657 lines, ceiling 3,658 — one line of headroom today).

```
3657  base
 -84  delete _memory_add.py                     (-1 file)
 -17  memory.py: product-add parser + dispatch + import
 -16  fold _memory_index.py into _memory_catalog.py  (-1 file, ~60 lines survive)
----
3540  after deletions, 29 files          budget to the ceiling: 118 lines
 +85  _memory_drift.py                          (+1 file -> 30)
 +14  memory.py drift wiring
 +16  release.py memory verb wiring
 +50  _release_check.py memory append + refusals (no new file: 30 files final)
  +6  _release_schema.py optional since/reviewed/changed
----
3711  ESTIMATE — 53 lines OVER the ceiling
```

**Resolved by the PM (SPEC D5):** the named lever is taken. `_memory_schema.py`'s validate half
and `_memory_check.py`'s atom half re-implement the frontmatter validation the library lint
(`features/specs/memory_lint.py`, LINT-1) already owns — a duplicated decider. They die;
`sources` is required by the lint; `memory.py check` keeps only the generated-pair check;
`_memory_schema.py` keeps `parse`/`find_specs` for the catalog writer. Measured deletion ≥ 90
lines, so the estimate lands at ≤ 3,621 with the drift sibling capped at 85 and the release side
at 72. If any task's measurement still breaks 3,657, that task stops and escalates — the ceiling
is never raised.

**Doctor module ceiling 699.** `doctor_memory.py` is at 699 — it gains nothing. MEM-NARRATIVE-1
lives in `memory_lint.py` (303) as the SPEC directs.

**P-20 / `test_specs_cli_complexity_ratchet.py`.** The 6 → 7 lane edits
`features/migrate/upgrade.py`, whose sha256 is pinned byte-identical. T-047-101 re-pins the hash
**in the same commit** with the written justification (FR1's upgrade lane is the authorized
change), exactly as the ratchet's own docstring requires.

**import-linter.** No new edge: `_memory_drift.py` and `release.py` are skill scripts (stdlib +
`subprocess`, outside the package); `RELEASE-TREE-MEMORY` lives in `features/specs/release_tree.py`
and reads `_RELEASE.json` only — P-02 (no subprocess from a feature) and P-03 hold untouched.

## 6. Risks

- **R1 — the V36 budget (§5).** Mitigated by escalation, never by a ceiling raise.
- **R2 — FR1's uncommitted working tree.** Four tasks' code sits uncommitted until the PM's single
  ADR commit; a `git add -A` anywhere in that window corrupts the commit shape. Every task stages
  explicit paths; the FR1 tasks stage nothing.
- **R3 — the upgrade lane writes operator prose.** Bounded by A5 and by the SPEC: a tree still
  carrying `## Part 1 — Principles` is *named by the doctor and left alone*. The e2e test asserts
  the left-alone case, not only the happy one.
- **R4 — MEM-NARRATIVE-1 false positives.** An ISO date or `FR3` inside a code fence or a
  `Measured by:` line would blame the wrong cause — the historical failure mode of this lint. The
  RED test carries the exemption cases (`ADR: NNNN (accepted)`) before the positive cases.
- **R5 — drift's `--since` default** reads the live release's `implemented.sha` else `defined.sha`;
  on a tree with neither, the verb must refuse with a `fix:` naming `--since`, never default to
  the root commit and list the entire tree.
