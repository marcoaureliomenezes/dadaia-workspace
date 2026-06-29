# SPEC: v0.1.37 alpha-1 - PI Workflow Hardening

**Status:** Aprovado
**Release ID:** v0.1.37
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-29

---

## Objective

Make PI safe and reliable as a Layer-2 worker for `dadaia lifecycle` workflows, especially
when a Layer-1 operator starts workflows from Codex, Claude Code, or PI. The release targets
the concrete failures discovered while shipping `v0.1.36 rc-1`: PI recursively invoking
lifecycle commands from inside a worker, workflow bug reporting losing operator details,
`lifecycle status` hanging during investigation, and release-definition context injection
exceeding headless runtime input limits.

## Scope

**Consumes:** none

This release does not consume the `pi-agent-fourth-harness` backlog epic. That item is
already delivered except for the WS-PI-5 operator-gated `dadaia-pi-workspace` dead-marking
residual. This release advances the epic by fixing open bugs that block seamless PI use in
dadaia-workflows.

In scope:

- Prevent PI and other headless workers from using `dadaia lifecycle ...` recursively while
  acting as bounded Layer-2 workflow workers.
- Make release-definition prompt assembly transport-budget aware so growing backlog/bug
  catalogs cannot overrun `codex exec` or PI headless input limits.
- Make `dadaia lifecycle status` inspection bounded and useful for stuck workflow runs.
- Fix the bug-report workflow fake/default path so bug intake preserves operator fields and
  emits a real bug record instead of a stub.
- Add regression coverage for the root causes and run PI-relevant workflow validation.

Out of scope:

- Publishing `v0.1.36` or `v0.1.37`.
- Tagging releases.
- DEAD-marking or deleting the standalone `dadaia-pi-workspace` context.
- Solving unrelated PI backlog that does not affect lifecycle worker reliability.

## Requirements

| ID | Requirement | Verification |
|---|---|---|
| R1 | A Layer-2 worker prompt for lifecycle workflows MUST explicitly forbid recursive `dadaia lifecycle ...` execution and require direct emission of the expected result object. | Fragment/runtime tests assert the generated prompt carries the recursion guard; a fake PI worker attempting recursion is rejected or prevented before acceptance. |
| R2 | PI workflow-review steps MUST not require broad shell capability unless the step scope explicitly needs it. | Adapter/request tests or workflow tests show review requests use a restricted tool profile. |
| R3 | Release-definition worker prompt assembly MUST cap or summarize injected context before invoking headless runtimes. | Oversized backlog/bug regression test no longer reaches a raw transport `input_too_large` failure. |
| R4 | `dadaia lifecycle status` with no args MUST return bounded output or a clear usage/error result, never hang or spin CPU. | CLI regression test covers no-arg status. |
| R5 | `dadaia lifecycle bug report` MUST preserve summary/repro/expected/actual fields and write a usable bug record when using the default/fake path. | CLI/integration test asserts the emitted bug markdown contains the supplied operator fields. |
| R6 | Validation MUST include focused deterministic tests plus at least one PI-relevant workflow check, using real PI when safe and fake PI when a real run would spend unnecessary credits. | Closure evidence records commands and outputs. |

## Traceability

| Scoped item | Requirement(s) | Root cause |
|---|---|---|
| `pi-security-review-worker-recurses-into-lifecycle-command` | R1, R2, R6 | PI received a command-shaped review task and had enough bash/tool surface to invoke `dadaia lifecycle review security` recursively instead of returning `agent-run-result-v1`. |
| `release-definition-spec-create-overinjects-context-exceeds-codex-input-limit` | R3, R6 | `spec_create` inherited a broad release-scope context set and injected whole historical/backlog/bug artifacts without a headless runtime character budget. |
| `lifecycle-status-no-args-hangs-100pct-cpu` | R4 | Status inspection has an unbounded/no-arg code path that can spin instead of returning bounded status or usage. |
| `bug-report-fake-bug-write-emits-stub-and-discards-fields` | R5 | The workflow's default fake writer path discards supplied operator bug fields and materializes a stub, forcing manual Markdown fallback. |
| `pi-agent-fourth-harness` | R1, R2, R6 | Backlog correlation only; core PI support is delivered, WS-PI-5 remains deferred. |

## Manual Definition Note

The normal `dadaia lifecycle release define` path was attempted for this scope and blocked
at `spec_create` by `release-definition-spec-create-overinjects-context-exceeds-codex-input-limit`.
This manual SDD definition is therefore part of the repair path for the workflow itself.
