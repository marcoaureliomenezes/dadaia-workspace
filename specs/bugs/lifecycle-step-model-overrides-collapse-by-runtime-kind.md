---
name: lifecycle-step-model-overrides-collapse-by-runtime-kind
status: Open
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
  --step-model release_scope=gpt-5.3-codex:medium \
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
