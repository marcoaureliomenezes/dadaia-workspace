---
name: release-definition-fake-runtime-does-not-produce-canonical-artifacts
status: Closed
severity: HIGH
reported: 2026-06-28
surface: lifecycle release define / fake runtime / canonical artifact gate
session_id: sess_6a2bcfe7
---

**Symptom:** After adding canonical SPEC/PLAN/TASKS artifact gates to
`release_definition`, the production `--harness fake` path can no longer complete the
release-definition workflow. The fake runtime still returns only a handoff artifact ref,
so `spec_create` is blocked by the new canonical artifact gate.

**Repro:** Run `dadaia lifecycle release define --release-id <id> --harness fake --json`
in a temp workspace with initialized specs and an open release.

**Expected:** The fake runtime remains a deterministic workflow driver for tests/smokes.
For create steps it must produce the canonical artifact expected by the Python gate and
report the artifact path/hash.

**Root cause:** `_release_definition_runtime_factory()` returned a static
`FakeAgentRuntime` result for every step. That was sufficient when create-step acceptance
only required some artifact ref, but it is incompatible with the stricter
release-definition gate introduced in `v0.1.35`.

**Notes:** Found while preparing a Codex release-definition smoke that runs the
`release_scope` step on Codex and the remaining steps on fake inside a temp workspace.

## Resolution

Fixed in `v0.1.35`.

Fix: `_release_definition_runtime_factory()` now uses a request-aware fake runtime. For
create steps whose scoped allowed paths include `SPEC.md`, `PLAN.md`, or `TASKS.md`, the
fake runtime writes that canonical artifact and returns both the handoff ref and the
artifact ref with `structured_output.content_hash`. Non-create steps keep returning the
deterministic approved handoff.

Evidence:

- `tests/integration/cli/test_release_definition_workflow.py::test_cli_fake_runtime_writes_canonical_create_artifacts`
