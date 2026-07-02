# PLAN — v0.1.48 — Memory Single-Ownership + Truth + English Canon

**Status:** Aprovado

## Ordering & rationale

Strictly sequential waves. W1 and W2 edit overlapping files (tech-stack, architecture,
context-management, sdd-gate-v3, panel, agent-comms) — parallel agents would collide. W2 must
precede W4 so no deleted/merged atom is translated (G3). W3 must precede W4 so the English
heading canon passes LINT-1. No repo writes concurrent with pytest (conftest snapshot guard) —
W3's full-suite run happens with the tree otherwise quiet.

```text
W0 archive+definition → W1 truth → W2 ownership → W3 code(+pytest) → W4 translate → W5 hygiene → W6 ship
```

## Phase management

`ACTIVE.md` stays `phase: DEFINITION` through W1–W5: the SDD gate allows MEMORY-class writes
only in DEFINITION/CLOSURE, and W1/W2/W4 are memory-heavy (v0.1.47 precedent). Flip to CLOSURE
at W6 before CLOSURE.md is written. During DEFINITION with tasks in flight, specs doctor's
SPEC-DOC-024 phase-vs-markers signal is the expected transitional state.

## Execution model

Layer-1 Claude orchestration with per-wave subagents (operator's standing pattern for this
track; dadaia-workflows Layer-2 not used — Claude entry session):

- **W1** one software-engineer-profile agent for memory truth edits, driven by the audit's
  file:line findings; the memory-AGENTS source fix goes through
  `public/data/memory-AGENTS.md` → `dadaia public stage && install --target all && public doctor`.
- **W2** one agent for the delete/merge/archive/re-home moves + wikilink sweep; orchestrator
  verifies unique-fact migration before each deletion; `dadaia memory catalog generate` after.
- **W3** one agent on `features/specs/catalog.py`, `public/scripts/generate-memory-catalog.py`,
  `public/scripts/lint-memory-atoms.py`, `hooks/ctx_inject.py`, `views/assets/js/core.js` +
  tests (incl. a contract test pinning the GFM table shape). Full pytest/ruff/mypy gate.
- **W4** 2 parallel translation agents split by disjoint file sets (they touch only atom files;
  no code, no pytest concurrency), with a shared English glossary: Group-A canon = Purpose /
  Usage flow / Typical trigger / Differentiator / Runtime state touched / Dependencies; then
  catalog regen + lint.
- **W5/W6** orchestrator directly (git mv, deletions, doctors, ritual).

## Risks & mitigations

- **Wikilink breakage on delete/merge/move** — lint-memory-atoms fails on dangling links; run
  after every W2 step, not only at wave end.
- **Consumer LINT-1 regression from allowlist change** — PT legacy entries retained (G2); only
  dead strings pruned; test asserts both canons accepted.
- **`dadaia memory catalog generate` overwrites `index.md`** — expected; never hand-edit either
  generated file; all fixes at generator/atom level.
- **Push gate** — pre-push preflight ~12 min exceeds the 600s Bash cap: push via detached
  `nohup` + Monitor; CI watched until every job green (global rule).
- **Subagent stalls ~200–270k tokens** — findings pre-partitioned into narrow lists; resume via
  message with a finish-list on stall.

## Write sets (enforced as discipline per task, see TASKS.md)

- W1: `specs/memory/**` (existing files only, incl. `specs/memory/AGENTS.md` directly),
  `dadaia_workspace/public/data/memory-AGENTS.md`,
  `dadaia_workspace/public/scaffold/memory/AGENTS.md`, `docs/01_medium_codex.md`.
- W2: `specs/memory/**` (incl. deletes/moves), `specs/constitution.md`,
  `specs/_archive/memory/**` (archive target for sdd-hotfix-track).
- W3: `dadaia_workspace/features/specs/catalog.py`, `dadaia_workspace/features/specs/doctor.py`
  (TREE-5M text), `dadaia_workspace/hooks/ctx_inject.py`,
  `dadaia_workspace/public/scripts/{generate-memory-catalog.py,lint-memory-atoms.py}`,
  `dadaia_workspace/features/panel/views/assets/js/core.js`, `specs/memory/quality-assurance.md`
  (category field), `tests/**`.
- W4: `specs/memory/**` (surviving files), regenerated `catalog.json`/`index.md`.
- W5: `specs/_archive/releases/v0.1.23/` (move), `specs/backlog/img/` (delete), `docs/img` (delete).
- W6: `specs/releases/ACTIVE.md`, `specs/releases/v0.1.48/CLOSURE.md`, `specs/bugs/*.jsonl`,
  `specs/audits/_archive/**`, `specs/backlog/hygiene-and-dead-code-cleanup.md`,
  `.dadaia/handoff/**` (workspace).
