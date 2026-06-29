# PLAN: v0.1.40 alpha-1 - SDD Governance v2 completion

**Status:** Aprovado
**Release ID:** v0.1.40
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-29

## Strategy

Implement from the lifecycle foundation outward:

1. Repair release-definition create-artifact behavior so workflow definition can be
   trusted again.
2. Add the JSONL bug-event model and CLI without breaking existing Markdown bug reports.
3. Add audit-disposition validation and archive law.
4. Make workflow-first lifecycle default explicit across public rules, skills, and memory.
5. Align backlog terminal status parsing and consume-aware implementation behavior so the
   backlog item can be fully consumed without doctor conflict.

## Work Packages

### WP1 - Release-definition artifact reliability

- Add deterministic fake create-artifact behavior for `SPEC.md`, `PLAN.md`, and
  `TASKS.md` when a release-definition create step allows those paths.
- Keep the existing canonical artifact gate: handoff-only success must still block.
- Add coverage proving production `--harness fake` completes through
  `definition_commit_gate`.
- Strengthen create-step artifact evidence handling for Codex/PI by keeping exact
  allowed path and hash requirements in the prompt/gate.

### WP2 - Bug JSONL telemetry

- Add a feature module for bug events: event dataclasses or typed dictionaries,
  append/read/validate/status/stats helpers, hourly file selection, and rotation.
- Add CLI group `dadaia bugs` with `append`, `status`, `stats`, and a migration command
  or specs-upgrade hook for Markdown records.
- Ship the event schema under public schemas and project it through public assets.
- Add tests for event validation, coherence, rotation, status aggregation, stats, and
  Markdown migration.

### WP3 - Audit disposition law

- Add audit-disposition parsing/validation for audit workflow outputs and on-disk audit
  records.
- Add doctor checks that block/flag archive attempts when findings are not fully
  dispositioned.
- Update audit workflow fragments/rules so triage means disposition-complete, not
  solve-all.
- Add tests for complete, incomplete, and invalid dispositions.

### WP4 - Workflow-first governance

- Update public `release-governance`, `workspace-protocol`, and bug-registration rules.
- Update release-definition/task-manager/closure/spec-navigator skills where they describe
  manual protocols, making workflows the default and manual fallback exceptional.
- Update `sdd-bug-backlog-governance` and `lifecycle-foundation` memory during closure.
- Add public doctor or contract coverage if any public surface can regress.

### WP5 - Backlog terminal status and consume-aware doctor

- Align `backlog doctor` status parsing with ADR-11 terminal statuses plus version suffix.
- Align `specs doctor` SPEC-DOC-031 with the same parser.
- During an active release implementation, exempt anchors for backlog items declared in
  `**Consumes:**` from blocking BL-SCHEMA solely because the implementation is moving the
  referenced anchor.
- Add tests for suffixed terminal status, consumed active release exemptions, and retained
  errors for non-consumed stale anchors.

## Validation

- Focused unit/integration tests for each work package.
- `dadaia lifecycle release define --harness fake` smoke after WP1.
- `dadaia specs doctor --specs-dir repos/dadaia-workspace/specs`.
- `dadaia backlog doctor --specs-dir repos/dadaia-workspace/specs`.
- `dadaia public stage`, `dadaia public doctor`.
- `ruff format --check`, `ruff check --no-cache`, `mypy --strict`, and focused pytest.
- Lifecycle QA/security review before closure; security handoff must match final pushed
  commit SHA.

## Risks

- Full JSONL migration can be disruptive. Keep Markdown compatibility in alpha-1 and
  make migration explicit rather than destructive by default.
- Audit records in history are heterogeneous. Make archive law forward-looking unless an
  existing audit already carries parseable findings.
- Release-definition PI/Codex live behavior may remain provider-sensitive; deterministic
  fake completion is required for CI, while live PI/Codex failures must remain visible.
