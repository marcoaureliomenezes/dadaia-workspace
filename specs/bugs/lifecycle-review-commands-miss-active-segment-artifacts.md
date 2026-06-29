---
name: lifecycle-review-commands-miss-active-segment-artifacts
status: Open
severity: HIGH
reported: 2026-06-29
surface: lifecycle review commands segmented releases
session_id: codex-2026-06-29-v0139
release: v0.1.39
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
