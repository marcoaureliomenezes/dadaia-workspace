# TASKS: v0.1.9 alpha-1 — Spec/Memory Fidelity Remediation

**Status:** Aprovado
**Release ID:** v0.1.9
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-09

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

Parallel execution is safe across tracks (T-MEM-*, T-SPEC-*, T-CODE-*, T-AI-*)
because each track touches disjoint file sets. Within the T-MEM-* cluster,
product-engineer should execute sequentially (single agent, single session) to
avoid edit collisions on large files.

---

## Track A — product-engineer (memory atoms + spec)

### T-MEM-01 — workspace-doctor.md: fix LEASE check codes

- **Status:** [x]
- **Owner:** product-engineer
- **Findings:** HIGH — `specs/memory/product/platform/workspace-doctor.md:40-44`
- **Acceptance:** AC-MEM-01 — File contains no LEASE-1..4. Documents LOCK-NEW,
  INV-4, INV-5, SENTINEL-GC with correct `features/spec_context/doctor.py` line
  references. `dadaia specs doctor` exits 0.
- **Write set:** `specs/memory/product/platform/workspace-doctor.md`
- **Preconditions:** SPEC + PLAN Aprovado; phase = DEFINITION or CLOSURE.

---

### T-MEM-02 — architecture.md: CLI + protocol + features coverage

- **Status:** [x]
- **Owner:** product-engineer
- **Findings:** MEDIUM `architecture.md:41` (CLI 10→21); LOW omissions
  (features/: 5 modules; core/protocols/ 4→20; transitional-debt conflation;
  `:362` sdd-spec-gate.sh enforcer reference)
- **Acceptance:** AC-MEM-04 — architecture.md lists all 21 CLI subcommands; lists
  20 core/protocols; adds reports_next, reports_retention, spec_artifacts,
  ci_preflight, migrate to features list; no `sdd-spec-gate.sh` reference at line
  362 or elsewhere. `dadaia specs doctor` exits 0.
- **Write set:** `specs/memory/architecture.md`
- **Preconditions:** T-MEM-01 done (same session, avoid edit collision).

---

### T-MEM-03 — sdd-gate-v3.md: bash→Python + stale release_origin

- **Status:** [x]
- **Owner:** product-engineer
- **Findings:** MEDIUM `sdd-gate-v3.md:22-27,:66,:77,:130,:144-146` bash refs;
  LOW stale release_origin (v0.2.0)
- **Acceptance:** AC-MEM-02, AC-MEM-07(1/4) — No `sdd-spec-gate.sh`,
  `sdd-post-gate.sh`, `/tmp/sdd-gate.log` in file. Python hook path present.
  `release_origin` reflects v0.1.8 or later.
- **Write set:** `specs/memory/product/sdd/sdd-gate-v3.md`
- **Preconditions:** T-MEM-01 done.

---

### T-MEM-04 — Stale release_origin: context-management, panel, workspace-init

- **Status:** [x]
- **Owner:** product-engineer
- **Findings:** LOW stale release_origin in context-management.md (v0.2.0),
  panel.md (v0.1.5), workspace-init.md (memory-markdown-source-v1)
- **Acceptance:** AC-MEM-07 (remaining 3/4) — `release_origin` in each of the three
  files updated to reflect the release that last meaningfully changed them (v0.1.8 or
  v0.1.9 as appropriate). `dadaia specs doctor` exits 0.
- **Write set:**
  `specs/memory/product/platform/context-management.md`,
  `specs/memory/product/panel.md`,
  `specs/memory/product/workspace-init.md`
- **Preconditions:** T-MEM-01 done.
- **Parallel note:** Independent of T-MEM-02 and T-MEM-03; may run in same session.

---

### T-MEM-05 — cross-platform-portability.md: Phase 2/3 CI section

- **Status:** [x]
- **Owner:** product-engineer
- **Findings:** MEDIUM `cross-platform-portability.md:136-148` Phase 2/3 pending
- **Acceptance:** AC-MEM-03 — Phase 2/3 section describes hard-gated 3-OS matrix
  with no `continue-on-error` or GRADUATION-GATE prose. `dadaia specs doctor`
  exits 0.
- **Write set:** `specs/memory/product/platform/cross-platform-portability.md`
- **Preconditions:** T-MEM-01 done.

---

### T-MEM-06 — specs-doctor.md: check-ID enumeration

- **Status:** [x]
- **Owner:** product-engineer
- **Findings:** MEDIUM `specs-doctor.md` SPEC-DOC/TREE ranges wrong
- **Acceptance:** AC-MEM-05 — SPEC-DOC IDs listed as 001-009, 012, 016. TREE IDs
  include TREE-5M; TREE-8 not listed. `dadaia specs doctor` exits 0.
- **Write set:** `specs/memory/product/sdd/specs-doctor.md`
- **Preconditions:** T-MEM-01 done.

---

### T-MEM-07 — tech-stack.md: PM model + CLI commands

- **Status:** [x]
- **Owner:** product-engineer
- **Findings:** MEDIUM `tech-stack.md:59` PM model sonnet→opus; LOW CLI omissions
- **Acceptance:** AC-MEM-06 — project-manager model recorded as `claude-opus-4-8`.
  CLI tooling section lists all commands present in `dadaia --help`. `dadaia specs
  doctor` exits 0.
- **Write set:** `specs/memory/tech-stack.md`
- **Preconditions:** T-MEM-01 done.

---

### T-MEM-08 — Skill count: catalog.json + index.md

- **Status:** [x]
- **Owner:** product-engineer
- **Findings:** LOW skill count 17 vs 18 in catalog.json, index.md, and one other
  location
- **Acceptance:** AC-MEM-10 — All occurrences of "17 skills" replaced with 18.
  catalog.json and index.md reflect correct count. `dadaia specs doctor` exits 0.
- **Write set:**
  `specs/memory/product/catalog.json`,
  `specs/memory/product/index.md`,
  plus any additional memory location storing the skill count.
- **Preconditions:** T-AI-01 completed or confirmed wired (so final skill count is
  stable before recording it).
- **Parallel note:** Must run after T-AI-01..T-AI-05 to count final skill set.

---

## Track B — product-engineer (spec constitution)

### T-SPEC-03 — 0.1.6 CLOSURE backfill: add canonical sections

- **Status:** [x]
- **Owner:** product-engineer
- **Findings:** SPEC-DOC-006 ERROR on `specs/_archive/releases/0.1.6/CLOSURE.md` —
  missing required sections (`## Summary`, `## Validations`, `## Drifts`,
  `## Memory updates`). `dadaia specs doctor` exits non-zero until resolved.
- **Acceptance:** `dadaia specs doctor` no longer emits SPEC-DOC-006 on
  `specs/_archive/releases/0.1.6/CLOSURE.md` and exits with 0 errors.
  The `## Validations` table is reconstructed from the 0.1.6 release narrative
  (full suite 2358 passed; ruff + mypy --strict clean).
- **Write set:** `specs/_archive/releases/0.1.6/CLOSURE.md`
- **Preconditions:** SPEC + PLAN Aprovado. Operator authorization per the archival
  convention (see SPEC §Spec artifacts delta — _archive edits are an archival
  convention requiring approval, not a machine gate block).
- **Parallel note:** Independent of all other tracks; may run concurrently.
  0.1.8 CLOSURE description drifts (hooks overcount, file_permission_windows row,
  GRADUATION-GATE addendum row) remain accepted-historical: 0.1.8 CLOSURE already
  passes doctor structurally — the discrepancies are descriptive overcounts only,
  not missing required sections. No backfill required for 0.1.8. That decision is
  grounded in archival convention (not a gate lock), as stated in SPEC §Spec
  artifacts delta.

---

### T-SPEC-01 — constitution.md: remove phantom researcher from §7

- **Status:** [x]
- **Owner:** product-engineer
- **Findings:** LOW constitution §7 phantom researcher agent
- **Acceptance:** AC-MEM-08 — `specs/constitution.md §7` agent roster does not list
  `researcher`. No other §7 content altered. `dadaia specs doctor` exits 0.
- **Write set:** `specs/constitution.md`
- **Preconditions:** SPEC Aprovado; explicit operator acknowledgement for
  constitution edits (PE constitution write rule).

---

### T-SPEC-02 — quality-assurance.md: remove stale deletion sentence

- **Status:** [x]
- **Owner:** product-engineer
- **Findings:** LOW `quality-assurance.md:43-45` stale deletion sentence
- **Acceptance:** AC-MEM-09 — Lines 43-45 (stale deletion sentence) removed.
  Surrounding content coherent. `dadaia specs doctor` exits 0.
- **Write set:** `specs/memory/product/quality-assurance.md`
- **Preconditions:** T-MEM-01 done.

---

## Track C — software-engineer (code layering)

### T-CODE-01 — subprocess→infrastructure adapters in features/

- **Status:** [x]
- **Owner:** software-engineer
- **Findings:** MEDIUM `features/import_/service.py:4`,
  `features/ci_preflight/service.py:10`, `features/specs/doctor.py:54`
- **Acceptance:** AC-CODE-01 — None of the three files import subprocess directly.
  Each calls an `infrastructure/` adapter via Protocol. Import-linter config forbids
  `features.* -> subprocess`. `pytest` passes (0 regressions). Import-linter passes.
- **Write set:**
  `dadaia_workspace/features/import_/service.py`,
  `dadaia_workspace/features/ci_preflight/service.py`,
  `dadaia_workspace/features/specs/doctor.py`,
  `dadaia_workspace/infrastructure/<new-or-extended-adapter>.py`,
  `setup.cfg` or import-linter config file.
- **Preconditions:** Read existing `infrastructure/` adapters and import-linter config
  before writing. SPEC + PLAN Aprovado.

---

### T-CODE-02 — container.py: PLATFORM singleton replaces sys.platform

- **Status:** [x]
- **Owner:** software-engineer
- **Findings:** LOW `container.py:134` inline sys.platform vs PLATFORM singleton
- **Acceptance:** AC-CODE-02 — `container.py` line 134 (or equivalent) uses
  `PLATFORM` singleton. No direct `sys.platform` string comparison at that callsite.
  `pytest` passes.
- **Write set:** `dadaia_workspace/core/container.py`
- **Preconditions:** T-CODE-01 done (same branch, avoid conflict on pytest run).
- **Parallel note:** Independent of T-CODE-01 at file level; may execute in parallel
  if on the same branch; coordinate pytest run.

---

## Track D — ai-engineer (AI-surface, public/ source)

All T-AI-* tasks require `dadaia public stage && dadaia public install --target all`
after changes. Run the full propagation once after all T-AI-* are complete, then
verify with `dadaia public doctor` (exit 0).

### T-AI-01 — dev-server-registry skill: wire to agent

- **Status:** [x]
- **Owner:** ai-engineer
- **Findings:** MEDIUM `dadaia_workspace/public/skills/dev-server-registry/SKILL.md`
  referenced by zero agents/rules
- **Acceptance:** AC-AI-01 — skill referenced in `software-engineer.md` agent source
  (or an equivalent owning agent). Manifest reflects the wiring. `dadaia public
  doctor` exits 0.
- **Write set:**
  `dadaia_workspace/public/agents/software-engineer.md`,
  `dadaia_workspace/public/data/manifest.json` (or equivalent manifest source).

---

### T-AI-02 — [SCOPE ERROR] block: add to 5 personas

- **Status:** [x]
- **Owner:** ai-engineer
- **Findings:** MEDIUM I3 partial — 5 personas missing block: code-reviewer,
  product-engineer, project-auditor, project-manager, security-reviewer
- **Acceptance:** AC-AI-02 — All 9 persona source files in
  `dadaia_workspace/public/agents/` carry the `[SCOPE ERROR]` redirect block.
  `dadaia public doctor` exits 0.
- **Write set:**
  `dadaia_workspace/public/agents/code-reviewer.md`,
  `dadaia_workspace/public/agents/product-engineer.md`,
  `dadaia_workspace/public/agents/project-auditor.md`,
  `dadaia_workspace/public/agents/project-manager.md`,
  `dadaia_workspace/public/agents/security-reviewer.md`.

---

### T-AI-03 — ai-context-engineering SKILL.md: I1 schema refresh

- **Status:** [x]
- **Owner:** ai-engineer
- **Findings:** MEDIUM `dadaia_workspace/public/skills/ai-context-engineering/SKILL.md:188`
  I1 reference stale
- **Acceptance:** AC-AI-03 — I1 section lists current persona frontmatter schema keys
  (verify against an existing persona's YAML frontmatter). `dadaia public doctor`
  exits 0.
- **Write set:**
  `dadaia_workspace/public/skills/ai-context-engineering/SKILL.md`.

---

### T-AI-04 — Report-emission block: remove from all 9 persona bodies

- **Status:** [x]
- **Owner:** ai-engineer
- **Findings:** LOW Report-emission block duplicated across 9 personas (~72 lines
  each, already canonical in workspace-protocol §4)
- **Acceptance:** AC-AI-04 — No persona body in `dadaia_workspace/public/agents/`
  contains the verbatim "Report emission" inline block. workspace-protocol rule is
  confirmed present in projection before removal. `dadaia public doctor` exits 0.
- **Write set:** All 9 files under `dadaia_workspace/public/agents/*.md`.
- **Preconditions:** Verify `.claude/rules/workspace-protocol.md` is projected and
  current before removing from personas.
- **Parallel note:** May run after T-AI-02 in the same session (same files touched
  — coordinate edits).

---

### T-AI-05 — opencode_model: remove vestigial key from 2 personas

- **Status:** [x]
- **Owner:** ai-engineer
- **Findings:** LOW vestigial `opencode_model` key in 2 of 9 persona source files
- **Acceptance:** AC-AI-05 — No persona source file under
  `dadaia_workspace/public/agents/` carries `opencode_model` in its frontmatter.
  `dadaia public doctor` exits 0.
- **Write set:** The 2 persona source files that currently carry `opencode_model`
  (ai-engineer discovers which 2 by grepping public/agents/).

---

## Final gate (all tracks)

Before CLOSURE:
1. `dadaia specs doctor` exits 0.
2. `pytest` full suite — 0 failures.
3. `dadaia public doctor` exits 0.
4. Grep confirms: no `LEASE-1` in `workspace-doctor.md`; no `sdd-spec-gate.sh` in
   memory; no `researcher` in constitution §7; no direct `subprocess` import in
   `features/` modules.
