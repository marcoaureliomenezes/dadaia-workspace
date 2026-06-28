---
name: release-definition-pi-create-step-blocks-on-model-reported-hash
status: Closed
severity: HIGH
reported: 2026-06-28
surface: lifecycle release_definition canonical artifact gate / PI Layer-2 worker
session_id: sess_8cdf6cce
---

# `release define` with real PI can block at `spec_create` when the model reports the wrong content hash

**Symptom:** The opt-in real PI Layer-2 review-path e2e reached `spec_create` but never
reached `spec_arch_review`. `spec_create` wrote and referenced the canonical SPEC
artifact, but the canonical artifact gate blocked because the model-reported
`content_hash` did not match the bytes Python read from disk.

**Repro:**

```bash
DADAIA_E2E_REAL_WORKER=1 PI_BIN="$(command -v pi)" \
  timeout 900 .dadaia/.venv/bin/python -m pytest -p no:cacheprovider -q -s \
  repos/dadaia-workspace/tests/integration/pi_live/test_pi_command_smoke.py \
  repos/dadaia-workspace/tests/integration/pi_live/test_real_layer2_worker_workflow_e2e.py
```

Observed result:

```text
2 passed, 1 failed in 662.56s
spec_arch_review never ran — the run did not reach the review step
reached: ['release_scope', 'spec_create']
```

The `spec_create` block detail showed distinct `expected_hash` and `reported_hash` values.

**Expected:** Python should require the canonical file to exist and the worker to report
the canonical artifact path, but Python should compute the authoritative SHA-256 from the
written file. The model is not a reliable authority for hashing disk bytes.

**Impact:** A real PI worker can perform the important side effect correctly (write the
canonical release artifact) and still fail before review because it miscomputed or
misreported a hash. That blocks the "real PI reaches review gate" validation and makes
release-definition brittle under live workers.

## Resolution — v0.1.36 alpha-1

`ReleaseDefinitionWorkflow` now treats canonical artifact existence and canonical
`artifact_refs` as the blocking evidence. Once those pass, Python computes the SHA-256 from
the file and enriches the step result with `content_hash` plus the artifact-specific hash
field (`spec_hash`, `plan_hash`, or `tasks_hash`) before downstream payload production.

Regression:

```bash
.dadaia/.venv/bin/python -m pytest -p no:cacheprovider \
  repos/dadaia-workspace/tests/integration/cli/test_release_definition_workflow.py::test_release_definition_uses_python_hash_when_worker_reports_wrong_hash
```

Evidence: the full release-definition integration file passed with `11 passed` after the
fix. The real PI review-path e2e is rerun as the live validation for T6.
