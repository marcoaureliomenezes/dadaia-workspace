# TASKS — Release v0.2.1 "Vision Fidelity Fold"

**Status:** Aprovado
**Release ID:** v0.2.1
**Owner:** product-engineer (authorship); implementing agents per task
**Date:** 2026-06-07

Marker discipline: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE.
At most one `[-]` per owner at a time. Flip `[ ]` → `[-]` before starting; flip `[-]` →
`[x]` only after qa-engineer has committed the task green.

---

## WS-4 — Doctor Correctness (software-engineer) — FIRST

> WS-4 must complete before other workstreams trust `dadaia specs doctor` as a gate.

### T-021-01 — Fix flat-glob bug in doctor.py (rglob)

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/specs/doctor.py`
- **Precondition:** none
- **Work:** Change `glob(` → `rglob(` at lines 1626 (CAT-1) and 584 (SPEC-DOC-002) so
  nested memory atoms register and phantom CAT-1 warnings stop.
- **Done criterion:** `dadaia specs doctor` on the live workspace produces 0 phantom
  CAT-1 warnings; SPEC-DOC-002 no longer fires on valid nested atoms.

[x] T-021-01

### T-021-02 — Add TREE-3 check: top-level quality-assurance.md

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/specs/doctor.py`
- **Precondition:** T-021-01 done
- **Work:** Add TREE-3 check asserting `specs/memory/quality-assurance.md` exists at
  top-level (not under `product/`). The check must fail gracefully with a clear message
  when the file is absent.
- **Done criterion:** Check fires on a tree lacking `specs/memory/quality-assurance.md`
  at top-level.

[x] T-021-02

### T-021-03 — Add check: specs/memory/AGENTS.md presence

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/specs/doctor.py`
- **Precondition:** T-021-01 done
- **Work:** Add a doctor check asserting `specs/memory/AGENTS.md` exists. Aligned with
  WS-2 which creates the source and projects this file.
- **Done criterion:** Check fires on a tree missing `specs/memory/AGENTS.md`.

[x] T-021-03

### T-021-04 — Regression tests for WS-4 doctor changes

- **Owner:** software-engineer
- **Write set:** `tests/` (new test file for doctor checks)
- **Precondition:** T-021-01, T-021-02, T-021-03 done
- **Work:** Write pytest tests:
  (a) Phantom-warning count == 0 on a canonical tree fixture.
  (b) TREE-3 fails on a tree missing `specs/memory/quality-assurance.md` (top-level).
  (c) AGENTS.md check fails on a tree missing `specs/memory/AGENTS.md`.
  Run `pytest -p no:cacheprovider tests/` — must be green.
- **Done criterion:** All three new tests pass; full suite green.

[x] T-021-04

---

## WS-1 — Constitution & Memory Canonization (product-engineer + ai-engineer)

> WS-1 runs after WS-4 green. Establishes QA path string and root-entry law referenced
> by WS-2/WS-3/WS-5.

### T-021-05 — Constitution §0: reference normative product vision

- **Owner:** product-engineer
- **Write set:** `specs/constitution.md`
- **Precondition:** T-021-04 done (doctor trustworthy)
- **Work:** Add sentence to §0 referencing `docs/01_medium_codex.md` as the normative
  product vision that all agents and contributors must read.
- **Done criterion:** Constitution §0 contains a reference to `docs/01_medium_codex.md`.

[x] T-021-05

### T-021-06 — Constitution: add allowed root-entry section (CLAUDE.md + prompt.md)

- **Owner:** product-engineer
- **Write set:** `specs/constitution.md`
- **Precondition:** T-021-05 done
- **Work:** Add a new section enumerating the 9 allowed root entries from vision §3,
  explicitly including `CLAUDE.md` (item 8) and `prompt.md` (item 9). This is the
  canonical authority for WS-5.
- **Done criterion:** Section present; `CLAUDE.md` and `prompt.md` named as allowed entries.

[x] T-021-06

### T-021-07 — Constitution §11: correct panel/handoff wording

- **Owner:** product-engineer
- **Write set:** `specs/constitution.md`
- **Precondition:** T-021-05 done
- **Work:** Rewrite §11 to state: panel serves only `.dadaia/reports/` HTML;
  `.dadaia/handoff/` JSON is the agent↔agent channel and is never served by the panel.
- **Done criterion:** §11 explicitly states handoffs are never shown in the panel.

[x] T-021-07

### T-021-08 — Constitution §13: correct QA memory path to top-level

- **Owner:** product-engineer
- **Write set:** `specs/constitution.md`
- **Precondition:** T-021-05 done
- **Work:** Change the QA memory path reference in §13 from
  `specs/memory/product/sdd/quality-assurance.md` to `specs/memory/quality-assurance.md`.
- **Done criterion:** §13 references the top-level path.

[x] T-021-08

### T-021-09 — Create product-vision memory atom

- **Owner:** ai-engineer (authors `public/` convention) / product-engineer (writes memory)
- **Write set:** `specs/memory/product/philosophy/product-vision.md`
- **Precondition:** T-021-05 through T-021-08 done (constitution finalized)
- **Work:** Create `specs/memory/product/philosophy/product-vision.md` as a current-truth
  distillation of the normative vision. Required sections: Propósito, Fluxo de uso, Trigger
  típico, Diferencial, Estado runtime tocado, Dependências.
- **Done criterion:** File exists; follows memory atom schema; no changelog sections.

[x] T-021-09

### T-021-10 — Rename non-conformant audit directory

- **Owner:** product-engineer (via PM/operator git mv)
- **Write set:** `specs/audits/` (rename only, no content change)
- **Precondition:** T-021-04 done
- **Work:** Rename `specs/audits/2026-06-06T213731Z/` to a conformant `<ts>-<sid8>` form
  using `git mv` (operator or PM surfaces the command). No content changes.
- **Done criterion:** `specs/audits/` contains no directory with a non-conformant name;
  `dadaia specs doctor` exit 0.

[x] T-021-10
<!-- rename executed by orchestrator (Bash): git mv specs/audits/2026-06-06T213731Z specs/audits/<conformant-ts-sid8> -->

---

## WS-2 — Scoped AGENTS.md Completion (ai-engineer)

> Depends on WS-1 done (canonical QA path + root-entry law established).

### T-021-11 — Create public/data/memory-AGENTS.md source

- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/data/memory-AGENTS.md`
- **Precondition:** T-021-08 done (top-level QA path canonical)
- **Work:** Create the scoped AGENTS.md source for `specs/memory/`. Content: memory
  consumption rules, PE-only write ownership (CLOSURE phase), atom format (Markdown,
  Mermaid, no changelog sections), and link to constitution §13 for gate details.
- **Done criterion:** File exists; projects to `specs/memory/AGENTS.md` after install.

[x] T-021-11

### T-021-12 — Fix backlog-authority line in specs-AGENTS.md template

- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/templates/specs-AGENTS.md`
- **Precondition:** none
- **Work:** Change line 48: `product-engineer` → `project-manager` as the backlog-authority
  (backlog-ownership rule: PM is sole author of specs/backlog/**).
- **Done criterion:** Line 48 names `project-manager` as backlog-authority.

[x] T-021-12

### T-021-13 — Stage, install, and verify all 8 scoped surfaces

- **Owner:** ai-engineer
- **Write set:** (projection only via CLI — no source edits in this task)
- **Precondition:** T-021-11, T-021-12 done
- **Work:** Run `dadaia public stage && dadaia public install --target all && dadaia public
  doctor`. Verify all 8 surfaces from vision §4 are present at expected paths on the live
  workspace. TREE-5 must no longer fire.
- **Done criterion:** `dadaia public doctor` exit 0; 8 scoped AGENTS.md files present.

[x] T-021-13

---

## WS-3 — Canonical Scaffold Completion (software-engineer + ai-engineer)

> Depends on WS-1 done (QA path canonical) and WS-2 done (memory-AGENTS.md source exists).

### T-021-14 — Add canonical tree stubs to public/scaffold/

- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/scaffold/audits/`,
  `dadaia_workspace/public/scaffold/quality-assurance.md`,
  `dadaia_workspace/public/scaffold/memory/AGENTS.md`
- **Precondition:** T-021-11 done (memory-AGENTS.md source exists)
- **Work:** Add to `public/scaffold/`: (a) `audits/` directory stub; (b) top-level
  `quality-assurance.md` stub; (c) `memory/AGENTS.md` stub (can reference the projected
  data source).
- **Done criterion:** Three stubs present in `public/scaffold/`.

[x] T-021-14

### T-021-15 — Fix alive(): safe-preserve existing specs/ on scaffold

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/spec_context/service.py`
- **Precondition:** T-021-14 done
- **Work:** Edit `alive()` to detect a pre-existing `specs/` and move/backup it (e.g.
  `specs.bak.<timestamp>/`) before scaffolding the canonical structure, instead of
  silently skipping or overwriting. Add a log message naming the backup location.
  Scan callers to confirm none rely on the skip behavior.
- **Done criterion:** `alive()` with a pre-existing `specs/` results in backup + fresh
  canonical scaffold; callers unaffected.

[x] T-021-15

### T-021-16 — Confirm TREE-4 covers audits/ auto-create; regression tests

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/specs/doctor.py` (if TREE-4 update needed),
  `tests/` (regression tests)
- **Precondition:** T-021-14, T-021-15 done
- **Work:** Confirm or add TREE-4 entry for `audits/` auto-creation. Write regression
  tests: (a) fresh scaffold yields full canonical tree including `audits/`, `memory/AGENTS.md`,
  top-level `quality-assurance.md`; (b) pre-existing `specs/` is preserved (not clobbered
  or skipped). Run full pytest suite — green.
- **Done criterion:** Both regression tests pass; `dadaia specs doctor` exit 0.

[x] T-021-16

---

## WS-5 — Root-Whitelist + CLAUDE.md Bridge (ai-engineer + product-engineer)

> Depends on WS-1 T-021-06 done (§3 root-entry law in constitution).

### T-021-17 — Whitelist CLAUDE.md and prompt.md in all three sources

- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/scripts/root-whitelist-gate.sh`,
  `dadaia_workspace/public/rules/tmp-file-guardrail.md`,
  `dadaia_workspace/public/data/AGENTS.md`
- **Precondition:** T-021-06 done (root-entry law canonical in constitution)
- **Work:** Add `CLAUDE.md` and `prompt.md` to the allowed-entries enumeration in all
  three sources. All three must agree (single-source enforcement across different files).
- **Done criterion:** All three files name `CLAUDE.md` and `prompt.md` as allowed root
  entries.

[x] T-021-17

### T-021-18 — Add CLAUDE.md scaffold file; upgrade live root CLAUDE.md

- **Owner:** ai-engineer (scaffold) + product-engineer (live upgrade)
- **Write set (ai-engineer):** `dadaia_workspace/public/scaffold/CLAUDE.md`
- **Write set (product-engineer):** workspace root `CLAUDE.md`
- **Precondition:** T-021-17 done
- **Work:** (ai-engineer) Create `public/scaffold/CLAUDE.md` with content `@AGENTS.md`.
  Run `dadaia public stage && install --target all && doctor`.
  (product-engineer) Upgrade live workspace root `CLAUDE.md` from the current stub to
  `@AGENTS.md` bridge (single line: `@AGENTS.md`).
- **Done criterion:** `dadaia public doctor` exit 0; root-whitelist gate does not flag
  `CLAUDE.md` or `prompt.md` on the live workspace; live `CLAUDE.md` contains `@AGENTS.md`.

[x] T-021-18

---

## WS-6 — Dead Allowlist + Asset Hygiene (ai-engineer)

> Independent; can run after WS-4 green.

### T-021-19 — Fix ai-engineer.md write_allowlist

- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/agents/ai-engineer.md`
- **Precondition:** T-021-04 done
- **Work:** Remove `public/hooks/**` and `public/commands/**` from `write_allowlist`
  (these paths do not exist). Add `public/scripts/**` and `public/plugins/**`.
- **Done criterion:** No glob in `write_allowlist` resolves to a non-existent path.

[ ] T-021-19

### T-021-20 — Fix qa-engineer.md dispatch-purity wording

- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/agents/qa-engineer.md`
- **Precondition:** T-021-04 done
- **Work:** Tighten "pair with" wording: workers surface needs to PM; direct
  worker→worker dispatch is a constitution §9 violation.
- **Done criterion:** qa-engineer.md wording aligns with dispatcher-purity law.

[ ] T-021-20

### T-021-21 — Fix software-architect.md dead report-template path

- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/agents/software-architect.md`
- **Precondition:** T-021-04 done
- **Work:** Locate and fix the dead report-template path in the persona. Point to the
  correct existing path or remove the dead reference.
- **Done criterion:** No dead path in software-architect.md persona; `dadaia public doctor`
  exit 0.

[ ] T-021-21

---

## WS-7 — Lifecycle Hygiene (product-engineer + PM)

> Independent; can run after WS-4 green.

### T-021-22 — Archive v0.1.5 release

- **Owner:** product-engineer (via PM/operator for git mv)
- **Write set:** `specs/releases/` (remove v0.1.5), `specs/_archive/releases/` (add v0.1.5)
- **Precondition:** T-021-04 done
- **Work:** Move `specs/releases/v0.1.5/` → `specs/_archive/releases/v0.1.5/` via
  `git mv specs/releases/v0.1.5 specs/_archive/releases/v0.1.5` (operator/PM runs).
  Only `specs/releases/ACTIVE.md` and the live v0.2.1 directory should remain under
  `specs/releases/` after this task.
- **Done criterion:** `specs/releases/v0.1.5/` is absent; archived copy present;
  `dadaia specs doctor` exit 0.

[ ] T-021-22

### T-021-23 — Add status: resolved to semaphore bug frontmatter

- **Owner:** product-engineer
- **Write set:** `specs/bugs/semaphore-no-liveness-reclaim.md`
- **Precondition:** none
- **Work:** Add `status: resolved` to the YAML frontmatter of
  `specs/bugs/semaphore-no-liveness-reclaim.md`. The body already has `resolved_in` and
  `superseded_by`; only the explicit `status:` field is missing.
- **Done criterion:** Frontmatter includes `status: resolved`; file otherwise unchanged.

[ ] T-021-23

---

## CLOSURE

### T-021-LAST — Write CLOSURE.md, update memory, archive v0.2.1

- **Owner:** product-engineer
- **Write set:** `specs/releases/v0.2.1/CLOSURE.md`, `specs/memory/**` (atoms per §7 of
  SPEC), `specs/releases/ACTIVE.md`
- **Precondition:** All tasks T-021-01 through T-021-23 marked `[x]` DONE; ship trio
  (qa + security + code-review) has APPROVED the final commit
- **Parallel:** Not parallel — must be last
- **Work:**
  1. Set `specs/releases/ACTIVE.md` phase to `CLOSURE`.
  2. Write `specs/releases/v0.2.1/CLOSURE.md` using the `dadaia-release-closure` skill
     template — include summary, task table, validation triples, drifts, memory updates,
     backlog returns, archive decision.
  3. Update `specs/memory/` atoms per SPEC §7: move `quality-assurance.md` to top-level,
     update `product/index.md` and `catalog.json`, create or finalize
     `product/philosophy/product-vision.md`, update `product/sdd/specs-doctor.md` to
     reflect new checks.
  4. Set `ACTIVE.md` phase to `ARCHIVED`. Request PM/operator to run:
     `git mv specs/releases/v0.2.1 specs/_archive/releases/v0.2.1`
  5. Update `ACTIVE.md` to `release: none` / `phase: ARCHIVED`.
  6. NO PyPI publish.
- **Done criterion:** CLOSURE.md written; memory atoms updated; `dadaia specs doctor` exit 0;
  release archived.

[ ] T-021-LAST
