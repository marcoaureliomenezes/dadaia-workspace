---
name: lifecycle-review-commands-miss-active-segment-artifacts
status: Closed
severity: HIGH
reported: 2026-06-29
surface: lifecycle review commands segmented releases
session_id: codex-2026-06-29-v0139
release: v0.1.39
resolved: 2026-06-29
---

# Lifecycle review commands miss active segment artifacts

**Symptom:** `dadaia lifecycle review qa --release-id v0.1.39` ran against a segmented
release whose artifacts live under `specs/releases/v0.1.39/alpha-1/`, but the QA worker
looked for flat artifacts under `specs/releases/v0.1.39/{SPEC,PLAN,TASKS}.md` and rejected
the review.

**Repro:**

```bash
.dadaia/.venv/bin/dadaia lifecycle review qa \
  --context dadaia-workspace \
  --release-id v0.1.39 \
  --run-id v0139-qa-pi-86be0303 \
  --harness pi \
  --model gpt-5.3-codex-spark:medium \
  --json
```

**Expected:** Review prompts identify the active segmented release artifact directory when
`ACTIVE.md` contains `segment: alpha-1`, so workers review
`specs/releases/v0.1.39/alpha-1/{SPEC,PLAN,TASKS}.md`.

**Actual:** The generated QA handoff rejected with:

```text
Unable to locate release v0.1.39 definition artifacts for QA review
```

It specifically cited the flat path `specs/releases/v0.1.39/{SPEC,PLAN,TASKS}.md`.

**Acceptance:** Single-step lifecycle review/closure prompts include the active release
artifact directory when the active release id matches the requested release and declares a
segment. Add regression coverage for `_phase_step_prompt`.

## Resolution - v0.1.39 alpha-1

Single-step lifecycle prompts now include a concrete release artifact directory. When the
active release id matches `ACTIVE.md` and that file declares a segment, the prompt names
`specs/releases/<release>/<segment>`.

Regression:

```bash
.dadaia/.venv/bin/python -m pytest -p no:cacheprovider \
  repos/dadaia-workspace/tests/integration/cli/test_lifecycle_command_skeletons.py::test_phase_step_prompt_is_step_kind_aware \
  repos/dadaia-workspace/tests/integration/cli/test_lifecycle_command_skeletons.py::test_release_artifact_dir_hint_uses_active_segment -q
```

Workflow validation: the first QA rerun after this fix no longer failed due missing flat
release artifacts. It reached the correct segmented TASKS.md and rejected only because T3
was still marked IN PROGRESS with pending validation, which is expected gate behavior.
