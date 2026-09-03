# TASKS — Release: 0.4.6

**Status:** Aprovado
**Release ID:** 0.4.6
**Owner:** product-engineer

---

## Candidate 3 — slop law

- [-] T-046-17 — Propose ADR 0010: slop is defined once by the deletion test, distributed
  over two classes (agentic entities; fixed sections in scaffolded specs) and measured by
  downward-only ratchets (`status: proposed`; `context` cites report
  `2026-09-03T023255Z-slop-governance-map` and the 2026-09-03 ruling; `decision` names §7.6,
  the three fixed sections, constitution §12, P-24's amendment, P-29 and
  `dd-code-review/SLOP.md`; `consequences` names the six homes that lose their duplicates and
  "no new hook or CLI verb"; `measured_by: null` until accepted). Owner: product-engineer.
  Commit: `docs(adr): propose slop-deletion-test` — the JSONL line alone.
  Write set: specs/ADRs/decisions.jsonl.
  Blocked by: none. Delivers: the operator has one decision to accept or refuse; every later
  task cites an existing id — `pytest -k adr_canon` green.
- [ ] T-046-23 — FR10, fixed law sections: fragments `public/scaffold/fixed/{slop-law,
  slop-code,slop-tests}.md` (SPEC §3.1, byte-exact); marker pairs in the scaffold
  `constitution.md` (new last section, replacing `:86` and the `:146` phrase) and
  `memory/{ARCHITECTURE,QUALITY}.md` (last subsection, replacing QUALITY `:21-23`);
  `FIXED_SECTIONS` + `render_fixed_section` + `extract_fixed_section` in
  `features/specs/memory_canon.py`; `canon.scaffold` renders the blocks at `specs init`;
  rule family FIXED-1/FIXED-2 (ERROR, fixable) in `rules.py`/`doctor_memory.py`;
  `hooks/ctx_inject.py::_build_memory` appends `=== workspace law (fixed) ===` + the two
  memory blocks via the leaf extractor (no container import); verify nothing enumerates
  `public/scaffold/` recursively for projection/privacy and adjust the ignore rule only if
  it does; tests: unit (render/extract/idempotent re-render, hook prefix), contract
  `tests/contract/test_fixed_sections_canon.py`, `test_doctor_golden` updated deliberately.
  Owner: software-engineer. Commit: `feat(T-046-23): fixed law sections in scaffolded specs`.
  Write set: dadaia_workspace/public/scaffold/fixed/**, dadaia_workspace/public/scaffold/
  {constitution.md,memory/ARCHITECTURE.md,memory/QUALITY.md},
  dadaia_workspace/features/specs/{memory_canon,canon,rules,doctor_memory}.py,
  dadaia_workspace/hooks/ctx_inject.py (+ a leaf extractor under core/ if the import
  contracts require it), dadaia_workspace/infrastructure/public_assets.py (only if the
  walk needs the ignore), tests/unit/features/specs/**, tests/unit/hooks/**,
  tests/contract/test_fixed_sections_canon.py, the doctor golden fixture.
  Blocked by: T-046-17. Delivers: `dadaia specs init` in a fresh dir yields three blocks and
  `dadaia specs doctor` reports no FIXED-*; a bind's bootstrap prefix carries the two memory
  blocks — AC11 (its lib-memory clause completes at closure).
- [ ] T-046-18 — FR1+FR2+FR4, the law in one act: `DADAIA.md` §7.6 (7 bullets), §7.2
  tombstone line, §6.7 byte ceiling, §10.2 glossary (`slop`, `ratchet`, `fixed section`);
  `constitution.md` §12 -> 3 bullets + pointer, `:11` deleted, §16 reduced, 5.1.0, then
  `dadaia specs doctor --fix` appends the `slop-law` block; `tests/AGENTS.md` and
  `templates/tests-AGENTS.md` reduced to Architecture + Size tiers + Markers with one pointer
  bullet; `tests/README.md` citation dropped; `dadaia-AGENTS.md`, `reports-AGENTS.md`,
  `releases/AGENTS.md`, `repo-AGENTS.md` ("## 5. Source hygiene") updated;
  `shipped-hashes.json` re-recorded; `behavior-map.json` section + scoped-source hashes
  re-recorded. Reprojection in this task: `dadaia public stage && dadaia public install
  --target all && dadaia public doctor`. Owner: ai-engineer (projected law, reprojection,
  the `--fix` run) with product-engineer (constitution §12 text).
  Commit: `feat(T-046-18): slop law — one definition, one home`.
  Write set: dadaia_workspace/public/data/**, dadaia_workspace/public/scaffold/releases/
  AGENTS.md, dadaia_workspace/public/templates/{tests-AGENTS.md,repo-AGENTS.md,
  shipped-hashes.json}, dadaia_workspace/public/entities/behavior-map.json (section +
  scoped rows), specs/constitution.md, tests/AGENTS.md, tests/README.md, and the
  reprojected instance law files.
  Blocked by: T-046-23. Delivers: `grep -rIn -i slop` over the law finds one definition plus
  pointers, and the constitution carries its fixed block — AC1, AC2, AC4 (its Intent-taxonomy
  line completes at T-046-20); `public doctor` `[ok]`, `pytest -k "behavior_map or
  memory_two_tier_shape"` green.
- [ ] T-046-19 — FR5+FR6, detection and its readers: new sibling `dd-code-review/SLOP.md`
  (S1-S10: signal, diff check, severity, fix direction; the verdict rule that S4/S5/S8
  findings answer Axis 3 "increased"; the reader list); `dd-code-review/SKILL.md` §2 pointer
  + §4 verdict line; pointer/bullet edits in `dd-test-stewardship` (mock only at the
  frontier; expected value from an independent source, two-line GOOD/BAD example),
  `dd-audit-project/PILLAR-SPECS.md` ("Slop readout", six steps), `dd-release-definition`
  §3 step 5, `dd-codebase-design` §3, `AUTHORING.md` §6; six personas (software-engineer,
  qa-engineer, software-architect, code-reviewer, product-engineer, project-auditor) gain
  one proof line and lose their duplicate statements (sentences per SPEC FR6);
  `behavior-map.json` skill/agent hashes re-recorded only. Reprojection in this task.
  Owner: ai-engineer. Commit: `feat(T-046-19): slop detection signals and their readers`.
  Write set: dadaia_workspace/public/skills/** (except dd-release-implementation/
  RC-FLOW.md), dadaia_workspace/public/agents/**, dadaia_workspace/public/entities/
  behavior-map.json (skill/agent rows), and the reprojected instance skill/agent files.
  Blocked by: T-046-18. Delivers: a reviewer opens one file and names a slop finding with
  `file:line`, signal id and fix direction — AC5, AC6; `pytest -k "behavior_map or
  reviewer_persona_review_allowlist"` green.
- [ ] T-046-20 — FR7, the numbers and the bridges: V31 replaces V27 in place in
  `tests/contract/test_test_suite_ratchets.py` (same `tracked_test_files()` enumeration,
  ceiling on undeclared files per tier, `e2e = 0`, down only, mutation fixture);
  `tests/scripts/check_test_intent_declared.py` and
  `tests/integration/scripts/test_check_test_intent_declared.py` deleted; new
  `tests/contract/test_slop_ratchets.py` with V32 (governance ids in production comments +
  docstrings, `tests/` excluded), V33 (SPEC §8 definition), V34 (live SPEC/TASKS bytes vs
  24 KB / 12 KB) — pin at birth, down only, one mutation fixture each;
  `scoped_law.py::install_scoped_law` collapsed into one loop over a four-row `(template,
  dest)` table adding `<repo>/CLAUDE.md` and `<repo>/tests/CLAUDE.md` from
  `templates/{repo,tests}-CLAUDE.md` (content exactly `@AGENTS.md`), install-if-absent;
  the instance files arrive via `dadaia context alive dadaia-workspace`, never a hand
  write; reprojection in this task (the manifest picks the templates up at `public stage`).
  Owner: software-engineer. Commit: `test(T-046-20): V31 replaces V27, ratchets V32-V34,
  scoped-law bridges`.
  Write set: tests/contract/test_test_suite_ratchets.py, tests/contract/
  test_slop_ratchets.py, tests/scripts/check_test_intent_declared.py (delete),
  tests/integration/scripts/test_check_test_intent_declared.py (delete),
  dadaia_workspace/features/spec_context/scoped_law.py,
  tests/unit/features/spec_context/test_scoped_law.py,
  dadaia_workspace/public/templates/{repo-CLAUDE.md,tests-CLAUDE.md};
  regenerated: .dadaia/agentic/manifest.json, repos/dadaia-workspace/{CLAUDE.md,tests/
  CLAUDE.md}.
  Blocked by: none. Delivers: a push that grows any of the four counts goes red in
  preflight, and `repos/dadaia-workspace/{AGENTS.md,tests/AGENTS.md}` load in Claude Code
  through their `CLAUDE.md` bridges — AC7, AC4's Intent-taxonomy line.
- [ ] T-046-21 — FR8, GC at closure: `dd-release-implementation/RC-FLOW.md` step 8 gains
  `dadaia reports cleanup --older-than 30d` and `dadaia tmp gc`, scope line "this
  candidate's own artifacts, plus the 30-day sweep"; run both once on the instance now
  (runtime, not committed); `behavior-map.json` dd-release-implementation hash re-recorded;
  reprojection in this task. Owner: ai-engineer (skill, hash, reprojection) with
  software-engineer (the run). Commit: `feat(T-046-21): garbage-collect handoffs and tmp at
  candidate closure`.
  Write set: dadaia_workspace/public/skills/dd-release-implementation/RC-FLOW.md,
  dadaia_workspace/public/entities/behavior-map.json (that row), the reprojected skill
  copies; runtime, uncommitted: .dadaia/handoff/**, .dadaia/tmp/**.
  Blocked by: none. Delivers: `find .dadaia/handoff -name '*.handoff.json' -mtime +30 | wc
  -l` = 0, and every future closure repeats it — AC8.
- [ ] T-046-22 — FR9, test curation batch 1 = `tests/contract` (37 files without
  `Intent:`): `qa-engineer` issues the curation verdict per file (declare `Intent:`, or
  delete with the criterion and the `file:line` of the coverage that replaces it);
  `software-engineer` executes; V31's contract pin drops to 0 in the same commit. Unit and
  integration re-enter via the closure deferral record under new task ids.
  Owner: qa-engineer (verdict) -> software-engineer (execution).
  Commit: `test(T-046-22): curate tests/contract — N declared, M deleted (verdict <handoff>)`.
  Write set: tests/contract/** (Intent lines and deletions), tests/contract/
  test_test_suite_ratchets.py (V31 contract pin only).
  Blocked by: T-046-20, T-046-23. Delivers: `grep -rL 'Intent:' tests/contract` is empty and
  the contract tier reads 0 — AC9; the operator sees the curation rate and decides the next
  batch at the next candidate's pick.

## Parallelism

- Disjoint write sets (may hold `[-]` simultaneously): T-046-20 ‖ T-046-19; T-046-20 ‖
  T-046-21; T-046-20 ‖ T-046-23; T-046-21 ‖ T-046-23; T-046-20 ‖ T-046-18.
- Serial: T-046-19 / T-046-21 (share `public/skills/**` and `behavior-map.json`); every
  `Blocked by:` edge above.
- Regenerated outputs (`.dadaia/agentic/manifest.json`, instance projections) are outside the
  disjointness test — reprojection is idempotent and cumulative.
