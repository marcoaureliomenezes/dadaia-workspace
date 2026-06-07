# PLAN — Release v0.2.1 "Vision Fidelity Fold"

**Status:** Aprovado
**Release ID:** v0.2.1
**Owner:** product-engineer
**Date:** 2026-06-07

---

## 1. Strategy

Single `feature/0.2.1` branch. Seven workstreams in a fixed dependency order so each
workstream's output is trustworthy before the next depends on it. The lib-guardrail loop
applies to all `public/**` edits: edit source → `dadaia public stage && install --target
all` → `dadaia public doctor` → proceed.

`specs/backlog/` is gitignored — the picked backlog file exists only on disk, not in git
history. Agents must not attempt to commit files under `specs/backlog/`.

**Implementer map (per agent):**
- `software-engineer` — library code under `dadaia_workspace/features/` and regression
  tests under `tests/`.
- `ai-engineer` — agentic-surface assets under `dadaia_workspace/public/**`.
- `product-engineer` — `specs/constitution.md`, `specs/memory/**`, `specs/releases/**`,
  `specs/bugs/` frontmatter; lifecycle archive via `git mv`.

---

## 2. Implementation Order

```
WS-4 (doctor fix — rglob, TREE-3, AGENTS.md check)
  → WS-1 (constitution + memory canon — QA path, §11, root-entry law, product-vision atom, audit rename)
    → WS-2 (scoped AGENTS.md — memory-AGENTS.md source, specs-AGENTS.md authority line)
    → WS-3 (scaffold — audits/ stub, QA stub, memory/AGENTS.md; alive() safe-preserve)
    → WS-5 (root-whitelist + CLAUDE.md bridge — depends on §3 root-entry law from WS-1)
  → WS-6 (dead allowlist + asset hygiene — independent; can land anytime after WS-4 green)
  → WS-7 (lifecycle hygiene — v0.1.5 archive, bug frontmatter; independent)
```

WS-4 is first so the test suite is trustworthy (rglob fix eliminates phantom warnings that
would otherwise obscure real failures). WS-1 is second because it establishes the
canonical QA path string and the root-entry law that WS-2/WS-3/WS-5 reference.

---

## 3. WS-4 — Doctor Correctness (software-engineer)

**Write set:** `dadaia_workspace/features/specs/doctor.py`, `tests/` (new regression tests)

Steps:
1. Locate line 1626 (CAT-1 check) and line 584 (SPEC-DOC-002): replace `glob(` with
   `rglob(` where nested memory atoms need recursive discovery.
2. Add TREE-3 check: assert `specs/memory/quality-assurance.md` exists (top-level,
   not under `product/`).
3. Add check: assert `specs/memory/AGENTS.md` exists.
4. Write regression tests:
   - phantom warning count == 0 on a healthy canonical tree fixture.
   - TREE-3 fails when `specs/memory/quality-assurance.md` is absent.
   - New AGENTS.md check fails when `specs/memory/AGENTS.md` is absent.
5. Run `pytest -p no:cacheprovider tests/` — must be green before advancing.

Gate: `qa-engineer` commit; `security-reviewer` push.

---

## 4. WS-1 — Constitution & Memory Canonization (ai-engineer + product-engineer)

**Write set (ai-engineer):** no `public/**` changes for WS-1 (constitution is a specs
file). **Write set (product-engineer):** `specs/constitution.md`,
`specs/memory/product/philosophy/product-vision.md`, `specs/audits/` (rename).

Steps:
1. Edit `specs/constitution.md`:
   a. §0: add sentence referencing `docs/01_medium_codex.md` as normative product vision.
   b. Add new section (after §2 or as §3-bis): enumerate allowed root entries per vision
      §3 items 1–9, including `CLAUDE.md` and `prompt.md`.
   c. §11: rewrite panel/handoff sentence — panel serves only `.dadaia/reports/` HTML;
      `.dadaia/handoff/` is agent↔agent only, never served by the panel.
   d. §13: correct QA memory path → `specs/memory/quality-assurance.md`.
2. Create `specs/memory/product/philosophy/product-vision.md` — current-truth distillation
   of vision §1–§13 (2–3 paragraphs of what the product is, for agent grounding).
3. Rename `specs/audits/2026-06-06T213731Z/` to a conformant `<ts>-<sid8>` name via
   `git mv` (operator or PM surfaces the command).
4. Run `dadaia specs doctor` — must exit 0.

Note: `quality-assurance.md` physical move (product/sdd/ → top-level) is coordinated with
WS-3 scaffold so the file is placed once in the right location, not moved twice.

Gate: `qa-engineer` commit; `security-reviewer` push.

---

## 5. WS-2 — Scoped AGENTS.md Completion (ai-engineer)

**Write set:** `dadaia_workspace/public/data/memory-AGENTS.md` (new),
`dadaia_workspace/public/templates/specs-AGENTS.md` (edit line 48).

Steps:
1. Create `dadaia_workspace/public/data/memory-AGENTS.md` — scoped instructions for agents
   working with `specs/memory/`: memory consumption rules, ownership (PE only in CLOSURE),
   atom format, and Mermaid/screenshot conventions. Projects to `specs/memory/AGENTS.md`.
2. Edit `dadaia_workspace/public/templates/specs-AGENTS.md` line 48: change
   `product-engineer` → `project-manager` as the backlog-authority.
3. Run `dadaia public stage && dadaia public install --target all && dadaia public doctor`.
4. Verify all 8 scoped surfaces (vision §4) are present on the live workspace.

Gate: `qa-engineer` commit; `security-reviewer` push; `dadaia public doctor` exit 0.

---

## 6. WS-3 — Canonical Scaffold Completion (software-engineer + ai-engineer)

**Write set (software-engineer):** `dadaia_workspace/features/spec_context/service.py`,
`tests/` (regression tests). **Write set (ai-engineer):**
`dadaia_workspace/public/scaffold/`.

Steps:
1. (ai-engineer) Add to `public/scaffold/`:
   - `audits/` directory stub (`.gitkeep` or equivalent).
   - `quality-assurance.md` stub (top-level, matching decision 1 path).
   - `memory/AGENTS.md` stub.
2. (software-engineer) Edit `features/spec_context/service.py` `alive()`: when a
   pre-existing `specs/` is detected, move/backup it before scaffolding the canonical
   structure. Document the backup location in a log message.
3. Add TREE-4 entry for `audits/` auto-creation in doctor (or confirm existing TREE-4 covers it).
4. Regression tests:
   - Fresh scaffold produces `audits/`, `memory/AGENTS.md`, top-level
     `quality-assurance.md`.
   - Pre-existing `specs/` is preserved (renamed/backed up), not clobbered or silently
     skipped.
5. Run `pytest -p no:cacheprovider tests/` — green.

Gate: `qa-engineer` commit; `security-reviewer` push.

---

## 7. WS-5 — Root-Whitelist + CLAUDE.md Bridge (ai-engineer)

**Write set:** `dadaia_workspace/public/scripts/root-whitelist-gate.sh`,
`dadaia_workspace/public/rules/tmp-file-guardrail.md`,
`dadaia_workspace/public/data/AGENTS.md`,
`dadaia_workspace/public/scaffold/CLAUDE.md` (new scaffold file).
**Live-repo write (product-engineer):** workspace root `CLAUDE.md` upgrade.

Steps:
1. Add `CLAUDE.md` and `prompt.md` to the whitelist in:
   - `public/scripts/root-whitelist-gate.sh` (allowed-entries array).
   - `public/rules/tmp-file-guardrail.md` (workspace root whitelist table).
   - `public/data/AGENTS.md` (root whitelist enumeration section).
2. Create `public/scaffold/CLAUDE.md` containing `@AGENTS.md` (the CC bridge).
3. Run `dadaia public stage && install --target all && doctor`.
4. (product-engineer) Upgrade the live workspace root `CLAUDE.md` from stub to `@AGENTS.md`
   bridge form (single line: `@AGENTS.md`).
5. Confirm root-whitelist gate no longer flags `CLAUDE.md` or `prompt.md`.

Gate: `qa-engineer` commit; `security-reviewer` push; `dadaia public doctor` exit 0.

---

## 8. WS-6 — Dead Allowlist + Asset Hygiene (ai-engineer)

**Write set:** `dadaia_workspace/public/agents/ai-engineer.md`,
`dadaia_workspace/public/agents/qa-engineer.md`,
`dadaia_workspace/public/agents/software-architect.md`.

Steps:
1. `ai-engineer.md` `write_allowlist`: remove `public/hooks/**` and `public/commands/**`;
   add `public/scripts/**` and `public/plugins/**`.
2. `qa-engineer.md`: tighten "pair with" wording — workers surface needs to PM, not
   direct worker→worker dispatch (constitution §9 dispatcher purity).
3. `software-architect.md`: fix dead report-template path.
4. Run `dadaia public stage && install --target all && doctor` — must exit 0.

Gate: `qa-engineer` commit; `security-reviewer` push; `dadaia public doctor` exit 0.

---

## 9. WS-7 — Lifecycle Hygiene (product-engineer + PM)

**Write set (product-engineer):** `specs/releases/` (archive move via `git mv`),
`specs/bugs/semaphore-no-liveness-reclaim.md` (frontmatter add).

Steps:
1. (product-engineer) Add `status: resolved` to frontmatter of
   `specs/bugs/semaphore-no-liveness-reclaim.md`.
2. (product-engineer, via PM/operator for git mv) Archive v0.1.5:
   `git mv specs/releases/v0.1.5 specs/_archive/releases/v0.1.5`
3. Run `dadaia specs doctor` — must exit 0 (no closed release under live `specs/releases/`).

Gate: `qa-engineer` commit; `security-reviewer` push.

---

## 10. Technical Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| `alive()` callers expect skip (not backup) on existing specs | Regression test before merge; scan callers with grep |
| Audit dir rename loses git history | Must be `git mv`, not OS `mv`; operator/PM runs the command |
| quality-assurance.md path move breaks catalog.json | CLOSURE updates catalog + index atomically; doctor validates links |
| rglob change in doctor fires new real warnings | Run doctor on the live workspace after fix; triage any new warnings before closing WS-4 |

---

## 11. Validation Plan

1. `pytest -p no:cacheprovider tests/` passes (≥ 2209 tests) after WS-3/WS-4 regression
   tests are added.
2. `dadaia specs doctor` exits 0 on the live workspace (WS-4 fix enables this as a
   trustworthy gate).
3. `dadaia public doctor` exits 0 after each `public/` change is staged and installed.
4. Manual: all 8 scoped AGENTS.md surfaces present at expected paths.
5. Manual: root-whitelist gate does not flag `CLAUDE.md` or `prompt.md`.
6. Manual: `specs/releases/v0.1.5/` absent from `specs/releases/`.
