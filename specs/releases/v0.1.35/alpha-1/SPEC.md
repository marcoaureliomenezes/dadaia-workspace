# SPEC: v0.1.35 alpha-1 - dadaia-workflows operational hardening

**Status:** Aprovado
**Release ID:** v0.1.35
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-28

---

## Objective

Make `dadaia lifecycle release define` reliable enough to dogfood for
dadaia-workspace release creation with Codex/PI Layer-2 workers.

This alpha targets the workflow machinery, not a product feature outside
dadaia-workspace. The release fixes the known failure modes that made workflow-created
releases unsafe:

- no explicit operator intent / selected scope input for release definition;
- create steps accepted handoff-only prose without canonical SPEC/PLAN/TASKS artifacts;
- workflow bug-report discipline was bypassed by manual bug-file creation;
- Codex Layer-2 worker startup used stale/insufficient `codex exec` invocation defaults;
- PI Layer-2 runtime failures could be misreported as generic artifact-evidence blocks;
- transcript/prompt noise around bound context injection remains a named follow-up risk.

## Picked Bugs

- `release-definition-lacks-operator-intent-channel-and-infers-scope-from-run-id`
- `release-definition-spec-create-accepts-handoff-only-without-spec-file`
- `agents-bypass-bug-report-workflow-and-handwrite-bug-files`
- `lifecycle-codex-exec-ask-for-approval-invalid`
- `codex-lifecycle-read-only-sandbox-blocks-layer2-worker-init`
- `codex-lifecycle-workspace-root-requires-skip-git-repo-check`
- `pi-headless-masks-nonzero-auth-failure-as-missing-artifact`
- `codex-bind-context-injection-visible-transcript-noise`

## Requirements

1. `dadaia lifecycle release define` must accept explicit operator scope inputs:
   selected backlog slugs, selected bug slugs, selected audit refs, and free-form
   operator intent.
2. The `release_scope` prompt must receive those inputs as first-class structured
   context and must treat `run_id` / `task_id` as opaque operational identifiers.
3. Release-definition create steps must not pass the Python gate unless the expected
   canonical artifact exists:
   - `spec_create` -> `specs/releases/<release-id>/SPEC.md`
   - `plan_create` -> `specs/releases/<release-id>/PLAN.md`
   - `tasks_create` -> `specs/releases/<release-id>/TASKS.md`
4. Canonical artifact evidence must include an in-workspace path and content hash. A
   handoff-only draft is blocked at the producing step, not deferred to the next review.
5. The workflow-owned bug-report path must be documented and tested enough that future
   agents can dogfood it instead of hand-writing bug files by default.
6. The Codex Layer-2 runtime adapter must invoke `codex exec` using currently supported
   startup flags, writable workflow sandbox defaults, and the workspace-root trust bypass
   needed by dadaia's non-git workspace root.
7. The PI Layer-2 runtime adapter must surface non-zero CLI failures without a
   `message_end` as runtime failures, even when PI emits partial session JSON on stdout.
8. Transcript-noise behavior must be inspected and either fixed or converted into a
   precise residual bug with root cause and acceptance.

## Non-Goals

- Do not redesign the full release-definition authoring UX.
- Do not remove PI/Codex as Layer-2 workers.
- Do not close stale Codex startup bug files without verification.
