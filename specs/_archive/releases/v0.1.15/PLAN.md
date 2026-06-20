# PLAN: v0.1.15 - Codex Lifecycle Foundation + Slop Control

**Status:** Aprovado
**Release ID:** v0.1.15
**Owner:** product-engineer
**Created:** 2026-06-18

---

## Strategy

Build the deterministic spine first. The release starts with models, ports,
state machine, runtime-file APIs, and hygiene policy, then exposes a thin CLI,
then attaches Codex as a bounded worker behind an exec-backed adapter. LLM output never
advances lifecycle state without Python validation.

Implementation is intentionally narrower than the full target architecture:
foundation commands, semantic gates, hygiene snapshots/cleanup, blocked/resume,
and Codex adapter contract. Full autonomous backlog/release/implementation
workflows come later.

## Layers affected

| Layer | Scope |
|---|---|
| `core/models` | lifecycle, run-state, gate, agent request/result, hygiene models |
| `core/protocols` | agent runtime and runtime-file ports |
| `features/lifecycle` | state machine, service, gates, hygiene, report workflow, prompts, run store |
| `features/workspace_clean`, `features/reports_retention` | TTL reconciliation or adapter into one hygiene policy |
| `infrastructure` | Codex SDK/exec adapter and filesystem runtime-file adapters |
| `cli/commands` | `dadaia lifecycle` command group |
| `tests` | unit, contract, integration, CLI, and slow/performance hygiene tests |
| `public/*` | only minimal command-discovery updates if they replace advisory text |

## Execution order

```text
PRE  T-015-00 release approval and implementation branch

W1 Models and contracts
  T-015-01 lifecycle core models
  T-015-02 hygiene models and SlopPolicy
  T-015-03 runtime file and agent runtime protocols

W2 Runtime files and hygiene
  T-015-04 filesystem runtime-file adapters
  T-015-05 shared hygiene service and TTL reconciliation
  T-015-06 boundary-safe cleanup and preservation rules
  T-015-07 hygiene snapshot and high-volume scan test

W3 State machine and gates
  T-015-08 lifecycle state machine
  T-015-09 semantic handoff gate validators
  T-015-10 preflight service and blocked/resume state
  T-015-11 lifecycle run-state store

W4 CLI and report workflow
  T-015-12 lifecycle command group
  T-015-13 status/preflight/hygiene CLI behavior
  T-015-14 report workflow proof
  T-015-15 guarded skeleton commands

W5 Codex worker integration
  T-015-16 fake AgentRuntimePort tests
  T-015-17 Codex SDK/exec adapter decision and implementation
  T-015-18 scoped prompt builder and write allowlist contract

W6 Bug proof and end-to-end validation
  T-015-19 blocked push/resume regression
  T-015-20 review gate integration
  T-015-21 temp workspace lifecycle smoke

W7 Final gates and closure
  T-015-22 final validation
  T-015-23 CLOSURE, memory, and backlog/bug disposition
```

## Technical approach

### W1 - Models and contracts

Define pure types first:

- lifecycle phases, blocked state, run state, idempotency key;
- gate requirements and structured evidence;
- `AgentRunRequest` / `AgentRunResult`;
- `SlopPolicy` and `HygieneCounters`;
- ports for agent runtime and runtime-file writes.

No filesystem, subprocess, SDK, or git imports belong in core.

### W2 - Runtime files and hygiene

Create concrete file APIs before lifecycle workflows use them:

- reports, handoffs, tmp files, run artifacts, and hygiene snapshots have one
  canonical writer each;
- writers reject unknown top-level `.dadaia/` folders;
- cleanup only considers declared safe zones;
- cleanup apply is explicit and dry-run is default;
- preservation rules protect important reports, current-release evidence,
  active run records, durable state, locks/sessions, and valid handoff-linked
  artifacts.

Existing cleanup services may be wrapped, but their TTL defaults must be
reconciled to one `SlopPolicy`.

### W3 - State machine and gates

The state machine owns legal transitions and consumes structured evidence. It
has no LLM dependency. Semantic gate validators reject report text that merely
contains required substrings and instead verify handoff schema, context, release,
agent, verdict, severity threshold, artifact hash, commit SHA, and task group.

Blocked states are first-class. A blocked result records the exact reason, next
operator command when available, and a resume token.

### W4 - CLI and report workflow

Expose deterministic commands:

- `status --json` is read-only.
- `preflight --json` is deterministic and does not call Codex.
- `hygiene status --json` measures.
- `hygiene clean --dry-run/--apply` uses the same policy as workflow postflight.
- `report` proves canonical report+handoff creation and hygiene status.
- skeleton workflow commands return next state or blocked state; no silent no-op.

### W5 - Codex worker integration

Codex integration is infrastructure:

- fake adapter is binding for CI;
- real Codex adapter is `CodexExecAdapter` behind `AgentRuntimePort`;
- no SDK/package dependency is added in v0.1.15;
- exec surface is documented in the task output;
- cwd, environment allowlist, credential redaction, and model/profile selection
  are explicit;
- no project-local provider/auth/telemetry/profile config or whole-environment
  pass-through is allowed;
- sandbox/profile widening requires explicit operator-controlled input;
- lifecycle state advances only after Python validates structured result and diff.

### W6 - Proofs

The release proves two operator-critical paths:

1. Hygiene and report workflow: creates canonical report+handoff, emits snapshots,
   and applies cleanup only under explicit apply policy while preserving evidence.
2. Blocked push: Codex cannot push in no-approval mode, so preflight records
   BLOCKED with exact operator command and resume token.

## Validation plan

1. Unit tests for lifecycle models and pure transition table.
2. Unit tests for `SlopPolicy` boundary values and counter aggregation.
3. Contract tests for runtime-file writer ports and concrete filesystem adapters.
4. Integration tests for cleanup preservation and safe deletion.
5. Slow/integration high-volume hygiene scan test at or above measured baseline
   class, with documented time, memory, and content-read constraints.
6. Unit/integration tests for semantic gate validators.
7. CLI tests for lifecycle status, preflight, hygiene, report, resume, and
   guarded skeleton commands.
8. Fake Codex adapter tests proving Python authority over state advancement.
9. Opt-in live Codex smoke only when environment supports it; not required in CI.
10. `ruff format --check`, `ruff check --no-cache`, `mypy --strict`.
11. `.dadaia/.venv/bin/python -m pytest -p no:cacheprovider`.
12. `.dadaia/.venv/bin/dadaia specs doctor --specs-dir repos/dadaia-workspace/specs`.
13. `.dadaia/.venv/bin/dadaia public doctor`.

## Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---:|---|
| Cleanup deletes valuable evidence | Medium | Dry-run default, explicit apply, preservation rules, current-release exclusions, tests. |
| Scope expands into full automation | High | Foundation release boundary and guarded skeletons only. |
| Codex SDK/API changes | Medium | Adapter port, fake adapter in CI, live smoke opt-in. |
| High-volume slop scan is too slow | High | Streaming scan, no content reads, slow performance test. |
| Advisory text keeps growing | Medium | NF requires no net new lifecycle prose unless replacing or pointing to commands. |
| Review gates remain theatrical | Medium | Semantic handoff validators and commit/release identity checks. |
