---
name: bug-spec-create-pi-no-artifact-bug_write
status: Closed
severity: HIGH
reported: 2026-06-28
surface: features/lifecycle/workflows/release_definition.py (spec_create step) + public/lifecycle_fragments/release_definition/spec-create.md + features/lifecycle/agent_runner.py (_blocked_result)
session_id: sess_8cdf6cce
---

# release_definition `spec_create` blocks on PI: real create worker SUCCEEDS but emits no `artifact_refs` / writes no SPEC file

**Symptom:** `dadaia lifecycle release define --harness pi` advances `release_scope`
(APPROVED) but then BLOCKS at `spec_create` with
`reason: "agent result missing artifact evidence"` and an empty `detail: {}`. The
entire release-definition workflow is therefore unrunnable on the **default PI
auto-profile** past step 2 — no SPEC is ever authored.

**Repro (deterministic, reproduced under two run-ids):**

```bash
.dadaia/.venv/bin/dadaia lifecycle release define \
  --context dadaia-workspace \
  --release-id v0.1.36 \
  --run-id v0136-repro-json \
  --backlog centralize-release-semver-canon \
  --intent "Centralize the release SemVer canon ..." \
  --harness pi \
  --json
```

Result:

```json
{"status":"BLOCKED",
 "blocked":{"blocked_at_step":"spec_create",
            "reason":"agent result missing artifact evidence","detail":{}},
 "steps":[{"label":"release_scope","runtime":"pi_headless","accepted":true},
          {"label":"spec_create","runtime":"pi_headless","accepted":false}]}
```

**Expected:** `spec_create` should materialize `specs/releases/v0.1.36/SPEC.md` and
populate `result.artifact_refs` (or structured-output evidence) so the create-step gate
at `features/lifecycle/agent_runner.py:215-218` passes and the workflow advances to
`spec_arch_review`.

**Actual / diagnosis:**
- `release_scope` is APPROVED by the real PI worker (stale `gpt-5.3-codex:medium` at
  report time; current catalog uses `gpt-5.3-codex-spark:medium` via the
  `openai-codex` provider) — auth and step 1 work; the produced handoff is correct
  (it even caught the persona-prose extension surface).
- `spec_create` worker returns `AgentRunStatus.SUCCEEDED` — **not** the error branch at
  `agent_runner.py:194-195` (which would surface a PI error). It hits the **line-218**
  branch: `if not result.artifact_refs and not (data.structured_output_evidence and
  result.structured_output): block("agent result missing artifact evidence")`. So the
  worker ran fine but returned **no `artifact_refs`** and no qualifying structured-output
  evidence.
- No `specs/releases/v0.1.36/` dir is created; `ACTIVE.md` is untouched (no corruption).

**Root cause (analysis):**
`public/lifecycle_fragments/release_definition/spec-create.md` never instructs the worker
to **WRITE** the SPEC to a concrete path and return that path in `artifact_refs`. Its
`## Output` section only says *"A SPEC draft plus its traceability table, emitted per the
output contract."* The `PiHeadlessAdapter` **does** enable write tools
(`infrastructure/pi_runtime.py`: `tools=("read","write","edit","bash")`), so the worker is
*capable* of writing the file — it is simply never told to. The create-step gate
(`agent_runner.py:215`) nonetheless requires `artifact_refs` (or
`structured_output_evidence` + `structured_output`, which `spec_create` does not satisfy
here). Net: the prompt contract and the gate disagree — the gate demands a materialized
artifact the prompt never asks the worker to produce.

**Why this is distinct from existing (Closed/Open) bugs:**
- `pi-headless-masks-nonzero-auth-failure-as-missing-artifact` (Closed) — that masked an
  auth **FAILURE** as missing-artifact; here `status` is genuinely `SUCCEEDED`.
- `release-definition-spec-create-accepts-handoff-only-without-spec-file` (Closed) — the
  **opposite** defect (accepting `spec_create` with no file); this is a hard BLOCK.
- `backlog-definition-pi-intake-grill-artifact-evidence-gate` (Open) — that argues a
  **structured-data** step (`intake_grill`) is wrongly gated on artifacts. `spec_create`
  legitimately MUST produce a SPEC file, so the fix is the opposite: make the worker
  produce the artifact, not relax the gate.

**Severity rationale:** HIGH — blocks the operator's stated goal of running
release-definition end-to-end on the PI harness; the default PI auto-profile has no
working create step.

**Secondary defect (diagnosability):** on a create-step block the gate persists
`blocked.detail = {}` — the worker's raw stdout / `structured_output` / `summary` is
discarded, so the failure cannot be diagnosed from the run state
(`.dadaia/states/lifecycle/<run>.json`) or the handoff ledger. The gate should persist the
worker's (redacted) raw output/summary into `blocked.detail` for create-step blocks.

**Suggested fix:** Either (a) extend `spec-create.md` (+ the shared output contract) to
instruct the worker to write the SPEC to the canonical release path and return it in
`artifact_refs`, and verify a real PI worker honors it; and/or (b) make `spec_create` a
`structured_output_evidence` step so a schema-valid `release-spec-draft-v1` payload (SPEC
body inline) satisfies the gate and the workflow itself writes the file. Add a real-PI
integration test asserting `spec_create` advances with the current PI model catalog.

**Notes / environment:** Registered via the direct-Markdown fallback because the
`dadaia lifecycle bug report` workflow on its default `--harness fake` produced a
meaningless stub that discarded every operator-provided field (see sibling bug
`bug-report-fake-bug-write-emits-stub-and-discards-fields`). Reproduced from the workspace
root with `.dadaia/.venv/bin/dadaia`. No secrets included.

## Resolution — v0.1.36 alpha-1

The release-definition create fragments now explicitly tell workers to write the canonical
release artifact path from the allowed write scope:

- `spec_create` writes `SPEC.md`
- `plan_create` writes `PLAN.md`
- `tasks_create` writes `TASKS.md`

Each fragment also requires one `agent-run-result-v1` payload whose `artifact_refs`
includes the canonical path and whose `structured_output.content_hash` is the SHA-256 of
the written file bytes. This aligns the worker prompt contract with
`ReleaseDefinitionWorkflow._canonical_artifact_block()`.

Regression:

```bash
.dadaia/.venv/bin/python -m pytest -p no:cacheprovider \
  repos/dadaia-workspace/tests/integration/cli/test_release_definition_workflow.py::test_cli_fake_runtime_writes_canonical_create_artifacts
```

Residual risk: the next live PI release-definition run must confirm PI follows the
tightened create-fragment instruction. If it still omits `artifact_refs`, keep this bug
reopened with the live worker output attached to the run record.
