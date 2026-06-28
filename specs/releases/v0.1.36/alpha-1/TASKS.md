# TASKS: v0.1.36 alpha-1 - PI Layer-2 Release-Definition Hardening

**Status:** Aprovado
**Release ID:** v0.1.36
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-28

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

## Tasks

### T1 - Refresh PI model catalog and adapter command

- **Status:** [x] DONE
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/model_registry.py`, `dadaia_workspace/core/harness_models.py`, `dadaia_workspace/features/lifecycle/model_profiles.py`, `dadaia_workspace/infrastructure/pi_runtime.py`, related tests
- **Acceptance:** PI catalog/profile use `gpt-5.3-codex-spark`; PI argv includes `--model openai-codex/<id>` and `--thinking <effort>`.
- **Validation:** `pytest -p no:cacheprovider tests/contract/test_headless_runtime_security.py tests/unit/core/test_harness_models.py`

### T2 - Fix release-definition per-step model routing

- **Status:** [x] DONE
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/cli/commands/lifecycle.py`, `dadaia_workspace/container.py`, `dadaia_workspace/features/lifecycle/workflows/release_definition.py`, related tests
- **Acceptance:** Two `--step-model` selections for the same harness remain distinct by step label and reach each `AgentRunRequest.resolved_model`.
- **Validation:** `pytest -p no:cacheprovider tests/integration/cli/test_release_definition_workflow.py`

### T3 - Require canonical artifacts from release-definition create fragments

- **Status:** [x] DONE
- **Owner:** product-engineer
- **Write set:** `dadaia_workspace/public/lifecycle_fragments/release_definition/*.md`, related tests
- **Acceptance:** `spec_create`, `plan_create`, and `tasks_create` tell workers to write canonical release artifacts and return artifact refs plus SHA-256 hashes.
- **Validation:** `pytest -p no:cacheprovider tests/integration/cli/test_release_definition_workflow.py`

### T4 - Update PI bug records and live validation evidence

- **Status:** [x] DONE
- **Owner:** product-engineer
- **Write set:** `specs/bugs/*.md`, release validation notes
- **Acceptance:** Bug records reflect fixed code paths, and any remaining PI live-run issue is either solved or registered as an open bug.
- **Validation:** Targeted pytest, direct PI command smoke, and `dadaia lifecycle release define --harness pi` validation.

### T5 - Persist active-worker state for live release-definition steps

- **Status:** [x] DONE
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/models/lifecycle.py`, `dadaia_workspace/features/lifecycle/workflows/release_definition.py`, related tests
- **Acceptance:** Before `runtime.run()` blocks on a PI/Codex worker, the persisted lifecycle run records `active_worker` with step/runtime/timestamps; after the worker returns, the marker is cleared.
- **Validation:** `pytest -p no:cacheprovider tests/unit/core/test_lifecycle_models.py tests/integration/cli/test_release_definition_workflow.py::test_release_definition_persists_injected_context_before_worker_returns`; bounded real-PI scratch run `v0136-pi-active-worker-smoke` showed `active_worker.runtime_kind=pi_headless` while PI was running.

### T6 - Make canonical artifact hashes Python-authoritative

- **Status:** [x] DONE
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/workflows/release_definition.py`, `tests/integration/cli/test_release_definition_workflow.py`, `specs/bugs/release-definition-pi-create-step-blocks-on-model-reported-hash.md`
- **Acceptance:** `spec_create`/`plan_create`/`tasks_create` still block when the canonical file or artifact ref is missing, but a wrong model-reported hash no longer blocks once Python can read the artifact and compute the authoritative SHA-256.
- **Validation:** `pytest -p no:cacheprovider tests/integration/cli/test_release_definition_workflow.py`; real PI review-path e2e rerun.
