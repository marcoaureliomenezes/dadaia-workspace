# PLAN — Release: 0.4.6

**Status:** Aprovado
**Release ID:** 0.4.6
**Owner:** product-engineer

---

## Candidate 3 — slop law

### Method

1. **Decision before law.** ADR 0010 lands first and alone; later edits cite an existing id.
2. **Mechanism before law.** T-046-23 lands the fixed-section seam before T-046-18 heals the
   constitution with `specs doctor --fix`.
3. **Law before pointers.** §7.6 exists before any file points at it.
4. **Pointers replace copies in the same commit.** No deprecation window; two homes never
   coexist across a task boundary.
5. **Detection after law, ratchets independent.** `SLOP.md` cites §7.6; the ratchets read
   the tree, not the law, and run in parallel.
6. **Memory in its phase.** Part 2 and the fixed blocks land in the CLOSURE pass; the Part-1
   hunk (P-24, P-29) rides the operator's ADR-0010 acceptance commit (`DADAIA.md` §6.5).
7. **Curation last, closed-scope.** Batch 1 = `tests/contract`; the rest re-enters via the
   closure deferral, never under a reopened task id.

### Seams

| FR | Seam it cuts | Grows / deletes |
|---|---|---|
| FR1 | `DADAIA.md` §7 — always-on law; §7.6 a new sibling section | +11 lines; makes 6 homes deletable |
| FR2 | constitution §12 + the `slop-law` marker pair | -17; §12 becomes an interface; the block is rendered, not written |
| FR3 | memory Part 1/Part 2 seam, CLOSURE only | +24; `Measured by:` moves numbers into test modules |
| FR4 | scoped-`AGENTS.md` seam — the write point | -52 -3 scaffold; `tests/AGENTS.md` stops being a second law file |
| FR5 | skill sibling `dd-code-review/SLOP.md`, loaded on invocation | +47 off the always-on budget; persona smell lists deleted |
| FR6 | persona `§1 Owns` — proof, not rule | net 0 across 6 personas; hashes re-recorded, no new row |
| FR7a | `test_test_suite_ratchets.py` — the one Intent counter | V31 replaces V27 (±0); e2e script pair deleted (-120) |
| FR7b | `tests/contract/` — repo-pure V32-V34 | +80; every walk through the shared helper |
| FR7c | `scoped_law.py::install_scoped_law` — the only repo-tree write seam | two blocks -> one 4-row loop; no new seam |
| FR8 | `RC-FLOW.md` step 8 — closure GC | +2; 678 handoffs deleted from the instance |
| FR9 | `tests/contract` — the suite itself | undefended tests deleted; the rest declared |
| FR10 | `memory_canon.py` — the one home of memory-tree shape facts | +1 leaf table, +2 pure functions, +1 rule family; -3 scaffold slop lines |

### Deletion ledger — what leaves, and from where

- `tests/AGENTS.md` -52: "Intent taxonomy, admission, deletion" (37), "No Slop" (11), "Good
  Test Standard" (6) — homes: `dd-test-stewardship`, §7.6, `slop-tests`.
- `specs/constitution.md` -17: §12's paragraphs -> 3 bullets + pointer; `:11` "A rule stated
  twice…"; §16's closing sentence -> "(§12)".
- `public/scaffold/` -3: constitution `:86`, the `:146` "(slop, §8)" phrase, `memory/QUALITY.md`
  `:21-23` — replaced by rendered marker blocks, not by pointers.
- `tests/scripts/check_test_intent_declared.py` + `tests/integration/scripts/
  test_check_test_intent_declared.py` -120, and `V27` (`_V27_INTENT_DECLARED_FLOOR`) — V31
  is V27 with the assertion inverted and per-tier; three Intent counters become one.
- V35 leaves the ratchet table: a wall-clock count of a directory outside the repo is not a
  property of the tree.
- `scoped_law.py`: two hand-written install blocks -> one loop over a table.
- Personas: "Never fabricate a test…" (software-engineer); §5 smells -> one S4/S5 pointer
  (software-architect); "Never accept: magic-mock inflation…" -> SLOP.md pointer (qa-engineer).
- `.dadaia/handoff/**` — 678 handoffs older than 30 days, deleted at T-046-21.
- `tests/contract` — every undefended test in batch 1, each deletion citing its criterion and
  the replacement `file:line`.

### Bug-surface answer: reduced, on all three touched features

- **Law surface** — six homes -> one; -52/-17/-3 lines. Ledger:
  `scoped-agents-md-stale-active-md-dual-write-text-past-t-050-21a`,
  `releases-agents-projection-stale-vs-scaffold-source`,
  `audits-agents-contradicts-dadaia-6-8-on-directory-disposal` — duplicated rule text drifted
  three times in one week, each fix a text re-sync (symptom). Deleting the copies is the
  first structural fix; the fixed sections make the surviving copies doctor-validated.
- **Ratchets** — one Intent counter instead of three; four repo-pure ratchets; no wall-clock,
  no out-of-repo read, no private walk. Ledger:
  `tmp-gc-tests-age-files-by-the-real-clock-against-a-frozen-now`,
  `frozen-clock-ratchet-scans-tests-tmp-scratch-dir`,
  `v26-ratchet-scans-tests-tmp-scratch-dir-xdist-race` — the family V35-as-pytest would have
  rejoined.
- **Projection** — the bridges land in the one seam that already writes repo trees,
  install-if-absent. Ledger: `public-install-clobbers-consumer-repo-agents-md` (HIGH),
  `public-doctor-flags-hand-authored-consumer-agents-md`,
  `repo-agents-md-law-gate-contradicts-template`, `sdd-gate-blocks-fresh-repo-root-agents-md`
  — a scoped-law row inherits their classification; a manifest projection would not.
- Additions against replace-don't-layer: §7.6 replaces six copies; `SLOP.md` replaces persona
  lists; V32-V34 force numbers down; the fixed-section seam replaces three hand-copied
  scaffold lines and makes `specs doctor` validate content it only counted before. No branch,
  flag, hook, CLI verb or second code path.

### Execution order

1. T-046-17 — ADR 0010 (no dependency).
2. T-046-23 — fixed-section mechanism + fragments. Depends on T-046-17.
3. T-046-18 — the law: DADAIA, constitution (§12 + `--fix`), scoped/scaffold/template
   files, section + scoped hashes. Depends on T-046-23.
4. T-046-19 — SLOP.md, skill pointers, personas, skill/agent hashes. Depends on T-046-18.
5. T-046-20 — V31 in place, V32-V34, scoped-law bridges. Independent; parallel to 2-4.
6. T-046-21 — RC-FLOW step 8 + one GC run. Independent; serial with T-046-19 only.
7. T-046-22 — curation of `tests/contract`. Depends on T-046-20 and T-046-23.
8. Closure — memory pass (Part 2 + fixed blocks), P-24/P-29 with the acceptance commit,
   deferral record for unit/integration batches, GC sweep, trio review.
   Disjointness is declared per pair in `TASKS.md` §Parallelism.

### Technical risks and controls

- **Pointer to a not-yet-existing section.** T-046-18 lands §7.6 before any pointer;
  `grep -n '§7.6'` across `public/` resolves after each task.
- **Marker block outside its phase.** The lib's memory blocks are MEMORY class: FIXED-1 ×2
  is red on the lib between T-046-23 and closure by construction — accepted, named in AC2,
  never downgraded to WARNING.
- **Behavior-map red mid-arc.** Each task re-records the rows it changes (T-046-18 sections +
  scoped; T-046-19 skills/agents; T-046-21 RC-FLOW) — never deferred to the next task.
- **Ratchet false positives.** V32 excludes `tests/`; V33 is defined in SPEC §8; one
  mutation fixture per ratchet.
- **Curation used to go green.** Deleting a test is a `qa-engineer` verdict (`DADAIA.md`
  §7.2); `software-engineer` executes, never decides.

### Validation plan

- Per task: the ACs in its `Delivers:` line plus the local CI preflight.
- Candidate close: `dadaia specs doctor` 0 errors (after the memory pass), `dadaia public
  doctor` `[ok]`, `pytest` green including V31-V34 and the fixed-sections contract, trio
  review with the bug-surface axis answering "reduced" against this ledger.
