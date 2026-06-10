# SPEC: v0.1.9 alpha-1 — Spec/Memory Fidelity Remediation

**Status:** Aprovado
**Release ID:** v0.1.9
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-09

---

## Objective

Resolve all 34 confirmed findings from the 2026-06-09 project-auditor drift audit
(`2026-06-09T231511Z-spec-memory-drift-audit.html`, overall score 7.0 CONDITIONAL).
No new features are introduced. Every change is fidelity restoration: memory atoms,
spec artifacts, AI-surface source files, and code layering aligned to actual
implementation.

---

## Scope — Product deltas

None. This release introduces no new user-facing behaviour, CLI commands, or data
contracts. It is a documentation/definition + code-hygiene release.

---

## Architecture deltas

- `features/import_/service.py`, `features/ci_preflight/service.py`,
  `features/specs/doctor.py`: remove direct `subprocess` imports; delegate to
  `infrastructure/` adapters via Protocol, consistent with the layering law.
- `dadaia_workspace/core/container.py:134`: replace inline `sys.platform` check with
  the `PLATFORM` singleton already used elsewhere.
- Import-linter contracts updated to forbid `features → subprocess` direct imports.

---

## AI-surface deltas (public/ source, reprojected)

- `dev-server-registry` skill: add references from the owning agent(s) or retire from
  manifest. Decision: wire to `software-engineer` agent as the natural home for local
  server lifecycle tooling.
- `[SCOPE ERROR]` block added to 5 personas currently missing it: `code-reviewer`,
  `product-engineer`, `project-auditor`, `project-manager`, `security-reviewer`.
- `ai-context-engineering/SKILL.md:188` I1 schema reference refreshed against current
  persona frontmatter schema.
- Report-emission block removed from all 9 persona bodies; it is already the canonical
  `workspace-protocol §4` rule — duplication is slop.
- Vestigial `opencode_model` key removed from 2 personas that carry it.

---

## Memory deltas (product-engineer, DEFINITION/CLOSURE phases, §13)

### workspace-doctor.md (HIGH)
Replace LEASE-1..4 descriptions with the actual emitted codes: `LOCK-NEW`, `INV-4`,
`INV-5`, `SENTINEL-GC`.

### sdd-gate-v3.md (MEDIUM)
Replace all bash-era references (`sdd-spec-gate.sh`, `sdd-post-gate.sh`,
`/tmp/sdd-gate.log`) with Python hook path
(`dadaia_workspace/hooks/sdd_gate.py`). Correct `release_origin` from v0.2.0.

### cross-platform-portability.md (MEDIUM)
Update Phase 2/3 CI section: remove `continue-on-error`/GRADUATION-GATE prose;
reflect that the 3-OS matrix is hard-gated since rc-2.

### architecture.md (MEDIUM + LOW)
- Expand CLI bullet from 10 to 21 subcommands (add: clean, lock, ci, reports, server,
  migrate, panel, memory, release, backlog, bug).
- Expand `core/protocols/` from "4 ports" to the 20 that exist.
- Add omitted `features/` modules: reports_next, reports_retention, spec_artifacts,
  ci_preflight, migrate.
- Remove transitional-debt category conflation.
- Replace `:362` reference to `sdd-spec-gate.sh` with Python hook.

### specs-doctor.md (MEDIUM)
Correct SPEC-DOC ID enumeration to actual emitted codes: 001-009, 012, 016.
Correct TREE IDs: replace TREE-1..8 with actual set including TREE-5M; remove TREE-8.

### tech-stack.md (MEDIUM)
Correct project-manager model from `claude-sonnet-4-6` to `claude-opus-4-8`.
Add missing CLI commands in CLI tooling section.

### Stale release_origin fields (LOW)
Update `release_origin` in: `sdd-gate-v3.md` (v0.2.0→v0.1.8), `context-management.md`
(v0.2.0→current), `panel.md` (v0.1.5→current), `workspace-init.md`
(memory-markdown-source-v1→current).

### constitution.md §7 (LOW)
Remove phantom `researcher` agent from the agent roster.

### quality-assurance.md (LOW)
Remove stale deletion sentence at :43-45.

### Skill count (LOW)
Update all 3 locations that state "17 skills" to the correct count of 18 (reflects
`multi-platform-parity.md` skill added in 0.1.8). Update `catalog.json` and `index.md`
accordingly.

---

## Spec artifacts delta

### 0.1.6 CLOSURE (archived — backfill authorized, T-SPEC-03)
`specs/_archive/releases/0.1.6/CLOSURE.md` is missing the canonical sections
`## Summary`, `## Validations`, `## Drifts`, and `## Memory updates`. `dadaia specs
doctor` emits SPEC-DOC-006 ERROR on this file, which blocks the release's final gate
(`dadaia specs doctor` must exit 0 before CLOSURE). **This release authorizes the
T-SPEC-03 backfill.** By archival convention, edits to `_archive/` require approval;
that approval is granted here. The SDD gate does not write-lock directories — the
archival convention is an agent-discipline rule, not a machine block. Task T-SPEC-03
(owner: product-engineer) adds the missing sections reconstructed from the 0.1.6
release narrative.

### L17 note — 0.1.6 and 0.1.8 archive moves already completed
The physical move of `specs/releases/0.1.6/` and `specs/releases/0.1.8/` into
`specs/_archive/releases/` was completed by the release coordinator prior to this
release. No action required in TASKS for the directory moves themselves.

### 0.1.8 CLOSURE description drift (archived — accepted-historical)
`specs/_archive/releases/0.1.8/CLOSURE.md` carries minor overcounting rows
(hooks 51 vs 45; file_permission_windows 8 vs 9/10; GRADUATION-GATE row vs rc-2
addendum). These are descriptive overcounts, not missing required sections — 0.1.8
CLOSURE passes `dadaia specs doctor` structurally. The release shipped correctly.
Decision: **accepted-historical**. By archival convention, edits to `_archive/`
require approval; no such edit is needed here since there is no structural doctor
error. Recorded for auditability.

### candidates.md (LOW)
Stale Priority Index at :112-127 and dead tracking entries at :128-160 to be curated.
**Owner: project-manager** (backlog-ownership rule). This SPEC records the finding;
the task is routed to PM outside the SDD gate (backlog is ADDITIVE).

---

## Security/operations deltas

None. No security surface changes.

---

## Memory files affected at closure

- `specs/memory/product/platform/workspace-doctor.md`
- `specs/memory/product/sdd/sdd-gate-v3.md`
- `specs/memory/product/platform/cross-platform-portability.md`
- `specs/memory/architecture.md`
- `specs/memory/product/sdd/specs-doctor.md`
- `specs/memory/tech-stack.md`
- `specs/memory/product/platform/context-management.md`
- `specs/memory/product/panel.md` (or equivalent path)
- `specs/memory/product/workspace-init.md` (or equivalent path)
- `specs/constitution.md`
- `specs/memory/product/quality-assurance.md`
- `specs/memory/product/index.md` (skill count)

---

## Acceptance criteria

Acceptance is mapped to each finding cluster. All criteria must be met before CLOSURE.

### AC-MEM-01 — workspace-doctor.md LEASE codes (HIGH)
`specs/memory/product/platform/workspace-doctor.md` no longer contains LEASE-1..4.
Actual codes LOCK-NEW, INV-4, INV-5, SENTINEL-GC are documented with correct
file:line references to `features/spec_context/doctor.py`.

### AC-MEM-02 — sdd-gate-v3.md bash references (MEDIUM)
`sdd-gate-v3.md` contains no references to `sdd-spec-gate.sh`, `sdd-post-gate.sh`,
or `/tmp/sdd-gate.log`. Python hook path is present. `release_origin` updated.

### AC-MEM-03 — cross-platform-portability.md Phase 2/3 (MEDIUM)
Phase 2/3 CI section describes the hard-gated 3-OS matrix, with no
`continue-on-error`/GRADUATION-GATE prose remaining.

### AC-MEM-04 — architecture.md CLI + protocol coverage (MEDIUM + LOW)
`architecture.md` lists all 21 CLI subcommands. `core/protocols/` reflects 20 ports.
Five previously-omitted `features/` modules are present. `sdd-spec-gate.sh` reference
replaced with Python hook. Transitional-debt category is correctly scoped.

### AC-MEM-05 — specs-doctor.md check IDs (MEDIUM)
SPEC-DOC IDs match actual emissions (001-009, 012, 016). TREE IDs match actual set
(including TREE-5M; no TREE-8).

### AC-MEM-06 — tech-stack.md PM model (MEDIUM)
`tech-stack.md` records project-manager model as `claude-opus-4-8`. CLI commands
section is complete.

### AC-MEM-07 — stale release_origin fields (LOW)
`release_origin` corrected in all 4 atoms: sdd-gate-v3.md, context-management.md,
panel.md, workspace-init.md.

### AC-MEM-08 — constitution §7 researcher (LOW)
`specs/constitution.md §7` roster does not list `researcher`.

### AC-MEM-09 — quality-assurance.md stale sentence (LOW)
`quality-assurance.md:43-45` stale deletion sentence removed.

### AC-MEM-10 — skill count (LOW)
All occurrences of "17 skills" corrected to 18. `catalog.json` and `index.md`
reflect the correct count.

### AC-SPEC-03 — 0.1.6 CLOSURE doctor-clean (MEDIUM)
`dadaia specs doctor` no longer emits SPEC-DOC-006 on
`specs/_archive/releases/0.1.6/CLOSURE.md`. All required sections (`## Summary`,
`## Validations`, `## Drifts`, `## Memory updates`) are present. `dadaia specs doctor`
exits 0 overall.

### AC-CODE-01 — subprocess layering (MEDIUM)
`features/import_/service.py`, `features/ci_preflight/service.py`,
`features/specs/doctor.py` do not import `subprocess` directly. Each delegates
to an infrastructure adapter. Import-linter contracts forbid `features → subprocess`.
`pytest` passes with no regressions.

### AC-CODE-02 — container.py PLATFORM singleton (LOW)
`container.py:134` uses `PLATFORM` singleton, not inline `sys.platform`. `pytest`
passes.

### AC-AI-01 — dev-server-registry skill wired (MEDIUM)
`dev-server-registry` skill is referenced by at least one agent in
`dadaia_workspace/public/agents/`. Manifest is updated. `dadaia public doctor`
exits 0.

### AC-AI-02 — [SCOPE ERROR] parity (MEDIUM)
All 9 core personas carry the `[SCOPE ERROR]` redirect block (5 newly added:
code-reviewer, product-engineer, project-auditor, project-manager,
security-reviewer). `dadaia public doctor` exits 0.

### AC-AI-03 — ai-context-engineering I1 schema (MEDIUM)
`ai-context-engineering/SKILL.md:188` I1 reference list matches current persona
frontmatter schema keys.

### AC-AI-04 — Report-emission dedup (LOW)
"Report emission" verbatim block is not present in any of the 9 persona bodies.
The canonical source remains `workspace-protocol §4`. `dadaia public doctor`
exits 0.

### AC-AI-05 — opencode_model removal (LOW)
No persona in `dadaia_workspace/public/agents/` carries a vestigial `opencode_model`
key. `dadaia public doctor` exits 0.

---

## Out of scope

- New CLI commands or features.
- Whole-tree dead-code sweep beyond CLI wiring (noted as residual coverage gap in
  audit; deferred to a dedicated future release).
- Backfill of `_archive/releases/0.1.8/` CLOSURE (accepted-historical — structural
  doctor check passes; only descriptive overcount rows, no required-section gaps).
- `candidates.md` curation (PM-owned backlog, ADDITIVE path, routed to PM).

---

## Dependencies and risks

- **Risk:** import-linter contract changes for AC-CODE-01 may require coordinating with
  existing contracts in `setup.cfg` or equivalent. software-engineer to verify before
  adding new forbidden-import rules.
- **Risk:** Removing the Report-emission block (AC-AI-04) from personas requires
  verifying that `workspace-protocol §4` is correctly projected to all runtimes
  (`.claude/rules/workspace-protocol.md` must be present and up-to-date) before removal.
- **Dependency:** AC-AI-01..AC-AI-05 require `dadaia public stage && dadaia public install
  --target all` after changes to `dadaia_workspace/public/` source. devops-engineer or
  operator must run the propagation commands.
- **No release blockers from 0.1.8.** All 34 findings are fidelity/hygiene debt;
  none affect correctness, security, or data integrity.
