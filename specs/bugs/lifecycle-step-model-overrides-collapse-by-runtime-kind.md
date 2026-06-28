---
name: lifecycle-step-model-overrides-collapse-by-runtime-kind
status: Closed
severity: MEDIUM
reported: 2026-06-27
surface: lifecycle CLI model override resolution
session_id: sess_43ddcbfb
---

**Symptom:** The lifecycle CLI advertises per-step model overrides (`--step-model
step=model`), but the implementation stores resolved models in a dictionary keyed only by
`AgentRuntimeKind`. Multiple per-step model choices for the same harness collapse into a
single model for that harness.

**Inspection:** In `dadaia_workspace/cli/commands/lifecycle.py`, `release_define()`
parses `--step-model` values, resolves each model, and writes:

```python
models[_resolve_harness(step_harness_name)] = resolved
```

`container.build_release_definition_workflow(..., models=models)` then passes this
`model_by_kind` map into `_release_definition_runtime_factory()`, where each adapter is
constructed with `model=model_by_kind.get(kind)`. There is no per-step key left by the
time the runtime request is built.

**Expected:** A command like:

```bash
dadaia lifecycle release define --harness pi \
  --step-model release_scope=gpt-5.3-codex-spark:medium \
  --step-model spec_arch_review=gpt-5.5:high
```

should run `release_scope` with the medium model and `spec_arch_review` with the high
model. The current data structure can only retain one PI model, so the last override for
`pi` wins globally.

**Impact:** The CLI cannot actually honor purpose-specific per-step model selection for
workflows that use the same harness across multiple steps. This undermines the advertised
model-governance surface and the operator goal of testing dadaia-workflows with
purpose-oriented PI Layer-2 prompts.

**Acceptance:** Thread model selection per step label (or embed the resolved model into
each `ReleaseStep` / `PromptScope`) instead of per runtime kind; add a regression test
with two steps on the same harness using different models and assert the two subprocess
commands receive different `--model` values.

---

## Confirmation — reproduced 2026-06-28 (session sess_8cdf6cce) via release_definition

Independent reproduction in the `release_definition` workflow, which makes the collapse
visible as a *cross-step auth failure*:

```bash
.dadaia/.venv/bin/dadaia lifecycle release define \
  --context dadaia-workspace --release-id v0.1.36 --run-id v0136-spec55 \
  --backlog centralize-release-semver-canon --intent "..." \
  --harness pi --step-model spec_create=gpt-5.5:high --json
```

Only `spec_create` was overridden to `gpt-5.5:high`, yet the run blocked at **`release_scope`**
(step 1, which was NOT overridden) with `reason: "No API key found for
azure-openai-responses."` — i.e. the single `pi`-keyed model map applied the gpt-5.5
override to `release_scope` too, routing it to the gpt-5.5 provider. (Baseline: with no
`--step-model`, `release_scope` runs on the `pi-implementation-standard` gpt-5.3-codex
profile and is APPROVED.)

This both **confirms the collapse** (per-step override leaks onto a same-harness step that
was not targeted) and shows a sharp failure signature when the two models route to
different providers (stale `gpt-5.3-codex`/current `gpt-5.3-codex-spark` → `openai-codex`;
gpt-5.5 previously routed ambiguously when unqualified — see
`pi-default-review-profiles-gpt-5-5-unreachable-provider`).

## Resolution — v0.1.36 alpha-1

`release_define()` now keeps explicit `--step-model` overrides in a label-keyed
`step_models` map. `ReleaseDefinitionWorkflow` threads each label-specific selection into
the built request as `resolved_model`, which the real adapters prioritize over
construction-time defaults. The runtime-kind keyed map remains only as the default
fallback.

Regression:

```bash
.dadaia/.venv/bin/python -m pytest -p no:cacheprovider \
  repos/dadaia-workspace/tests/integration/cli/test_release_definition_workflow.py::test_release_definition_threads_step_model_by_label_not_runtime_kind
```

The test drives two PI steps on the same harness with different `--step-model` values and
asserts the requests carry distinct `resolved_model` pairs:
`release_scope=gpt-5.5:low`, `spec_create=gpt-5.3-codex-spark:medium`.
