# TASKS: v0.1.5 - bug-backlog-release-governance

**Status:** Draft
**Release ID:** v0.1.5
**Owner:** product-engineer
**Created:** 2026-06-04

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.
Execution mode: Direct. Owners below denote the canonical domain; the driver
applies the lib-origination + gate workflow per task.

---

## Tasks

### T-ADR-01 — Author ADR-1..4 (alpha/rc model, hotfix unification, cadence, bug/backlog)
- **Status:** [ ]
- **Owner:** software-architect + product-engineer
- **Write set:** `specs/releases/v0.1.5/adr/ADR-1..4.md`
- **Acceptance:** four ADRs `Aprovado`; ADR-1 sketches `ACTIVE.md` schema-v2
  (`segment:`); ADR-2 supersedes `sdd-hotfix-track`; ADR-3 fixes the cadence +
  `feature/{version}` branch; ADR-4 records the bug/backlog rules.

### T-GOV-01 — New skill `dadaia-release-definition`
- **Status:** [ ]
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/skills/dadaia-release-definition/SKILL.md`
- **Acceptance:** encodes pick / bug-always-solved / `superseded_by` subsumption /
  sanitize / mandatory-grill; projects to runtimes; appears in `EXPECTED_SKILLS`.

### T-GOV-02 — Persona edits: product-engineer + project-manager
- **Status:** [ ]
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/agents/{product-engineer,project-manager}.md`
- **Acceptance:** product-engineer gains release-definition responsibility
  (discovers *within* bugs+backlog); project-manager gains the release-definition
  dispatch flow + mandatory-grill gate; `.claude/` + `.codex/` projections verified.

### T-GOV-03 — Rewrite `project-orchestration` review contract + playbook
- **Status:** [ ]
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/skills/project-orchestration/SKILL.md`;
  affected contract/e2e tests
- **Acceptance:** contract reflects segment/release cadence + branch model
  (alpha=qa+commit; rc=ship-trio-or-iterate); `bug-fix-fastlane`/
  `release-definition` playbook defined; review-gate contract tests updated + green.

### T-GOV-04 — `dadaia-grill-me` mandatory-at-release-definition trigger
- **Status:** [ ]
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md`
- **Acceptance:** release-definition listed as a mandatory grill trigger.

### T-GOV-05 — Always-on rule `release-governance`
- **Status:** [ ]
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/rules/release-governance.md`
- **Acceptance:** concise always-on rule; projects to `.claude/rules/` + `.codex/rules/`.

### T-GATE-01 — Mandatory pre-push CI gate
- **Status:** [ ]
- **Owner:** software-engineer-python + devops-engineer
- **Write set:** `dadaia_workspace/public/scripts/pre-push-ci-gate.sh`; install
  wiring (`infrastructure/public_assets.py`); tests
- **Acceptance:** runs `ruff format --check` + `ruff check` + `mypy --strict` +
  `pytest`; blocks `git push` on any failure; caches off-repo; unit/integration
  tests cover pass + fail paths; demonstrated blocking a deliberate failure.

### T-SANI-01 — Sanitize stale bugs/backlog + v0.1.3 draft
- **Status:** [ ]
- **Owner:** product-engineer
- **Write set:** `specs/releases/v0.1.3/*` (disposition), `specs/backlog/*`,
  `specs/bugs/*`
- **Acceptance:** v0.1.3 stale Draft triaged (archive or `deferred` with reason);
  open bugs/backlog reviewed for staleness per the new sanitize protocol.

### T-MEM-01 — CLOSURE memory atoms
- **Status:** [ ]
- **Owner:** product-engineer (CLOSURE phase only)
- **Write set:** `specs/memory/product/{sdd-bug-backlog-governance,sdd-hotfix-track}.md`,
  release-lifecycle atom
- **Acceptance:** new governance atom; `sdd-hotfix-track` annotated superseded;
  `dadaia specs doctor` memory lint OK.

### T-PROP-01 — Propagate + verify projections + full suite green
- **Status:** [ ]
- **Owner:** devops-engineer
- **Write set:** projections (generated)
- **Acceptance:** `public stage` + `install --force` + `doctor` exit 0; manual
  persona-projection check; full CI-equivalent suite green locally.
