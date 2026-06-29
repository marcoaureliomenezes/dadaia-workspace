# TASKS: v0.1.37 alpha-1 - PI Workflow Hardening

**Status:** Aprovado
**Release ID:** v0.1.37
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-29

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

## Tasks

### T1 - Guard Layer-2 workers against recursive lifecycle commands

- **Status:** [ ] OPEN
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/**`, `dadaia_workspace/public/lifecycle_fragments/**`, `dadaia_workspace/infrastructure/pi_runtime.py`, related tests
- **Acceptance:** PI/headless workflow workers cannot validly satisfy a lifecycle step by invoking `dadaia lifecycle ...`; regression coverage proves a recursive attempt is rejected or prevented.

### T2 - Add headless prompt budgeting for release definition

- **Status:** [ ] OPEN
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/workflows/release_definition.py`, `dadaia_workspace/features/lifecycle/**`, related tests
- **Acceptance:** Oversized bug/backlog catalogs do not produce raw Codex/PI input-limit errors during `spec_create`; the workflow either summarizes context or blocks early with an actionable lifecycle error.

### T3 - Fix lifecycle status no-arg behavior

- **Status:** [ ] OPEN
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/cli/commands/lifecycle.py`, lifecycle status helpers, related tests
- **Acceptance:** `dadaia lifecycle status` with no args exits promptly with bounded status or a clear usage error and no CPU spin.

### T4 - Fix bug-report workflow default writer fidelity

- **Status:** [ ] OPEN
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/workflows/bug_report.py`, `dadaia_workspace/cli/commands/lifecycle.py`, related tests
- **Acceptance:** `dadaia lifecycle bug report` preserves summary, repro, expected, and actual fields in the emitted bug markdown when using the default/fake path.

### T5 - Validate PI workflow hardening and update dispositions

- **Status:** [ ] OPEN
- **Owner:** product-engineer
- **Write set:** `specs/bugs/*.md`, `specs/releases/v0.1.37/alpha-1/CLOSURE.md`, `specs/releases/ACTIVE.md`
- **Acceptance:** Focused deterministic tests pass, PI-relevant workflow evidence is recorded, selected bug records carry resolution notes, and remaining PI residuals are explicitly left open.
