# PLAN: v0.1.35 alpha-1 - dadaia-workflows operational hardening

**Status:** Aprovado
**Release ID:** v0.1.35
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-28

---

## Approach

1. Extend the release-definition CLI and workflow constructor with explicit scope inputs:
   `--intent`, repeatable `--backlog`, repeatable `--bug`, and repeatable `--audit`.
2. Carry those inputs as a typed value into `ReleaseDefinitionWorkflow` and inject them
   into the `release_scope` selected context.
3. Add create-step artifact requirements to the release-definition gate. The gate should
   validate the expected canonical path and hash before accepting `spec_create`,
   `plan_create`, or `tasks_create`.
4. Update release-definition tests to cover:
   - misleading `run_id` cannot define scope when explicit intent is present;
   - handoff-only `spec_create` blocks at `spec_create`;
   - canonical artifact evidence passes the create gate;
   - existing mixed Codex/PI seam remains intact.
5. Inspect the workflow-owned bug-report CLI and transcript-noise bug. Fix narrow defects
   if root cause is clear; otherwise update the bug records with precise residual scope.
6. Align the Codex Layer-2 adapter command with the installed Codex CLI: remove stale
   approval flags, use a writable workflow sandbox default, and pass the non-interactive
   workspace-root trust bypass.
7. Make PI Layer-2 runtime failures actionable by treating non-zero exits without a
   terminal `message_end` as adapter failures, not as successful worker prose that later
   fails an artifact gate.
8. Dogfood with at least one `dadaia lifecycle release define` Codex run after the
   changes, using explicit intent/scope, and record any new bug discovered.

## Validation

- Focused release-definition workflow tests.
- Focused headless/Codex runtime tests for command construction and workflow startup
  behavior if touched.
- Focused PI runtime test for non-zero exit + partial session stdout + stderr.
- `dadaia specs doctor --specs-dir repos/dadaia-workspace/specs`.
- Pre-push suite before publishing.
