---
name: release-definition-spec-create-accepts-handoff-only-without-spec-file
status: Open
severity: HIGH
reported: 2026-06-27
surface: lifecycle release_definition workflow / spec_create gate / context selector
session_id: sess_43ddcbfb
---

**Symptom:** A PI Layer-2 `release define` run accepted `spec_create`, then immediately
blocked at `spec_arch_review` because the reviewer did not receive a SPEC draft.

**Observed command:**

```bash
.dadaia/.venv/bin/dadaia lifecycle release define \
  --context dd-chain-capture \
  --release-id v0.1.2 \
  --run-id pi-dd-chain-capture-v0.1.2-define-default-model \
  --harness pi \
  --json
```

**Observed result:**

```json
{
  "status": "BLOCKED",
  "blocked": {
    "blocked_at_step": "spec_arch_review",
    "reason": "agent result missing APPROVED verdict"
  },
  "steps": [
    {"label": "release_scope", "accepted": true},
    {"label": "spec_create", "accepted": true},
    {"label": "spec_arch_review", "accepted": false}
  ]
}
```

**Inspection:**

- `spec_create` emitted `.dadaia/handoff/dd-chain-capture/2026-06-27T235230Z-product-engineer-v0.1.2-spec-create-define-default-model.handoff.json`.
- The handoff's `artifact.type` is `spec`, but it contains no `artifact.path` and no
  `content_hash` for a written `specs/releases/v0.1.2/SPEC.md`.
- `find repos/dd-chain-capture/specs/releases/v0.1.2` reported that the release
  directory does not exist.
- The SPEC draft text exists only inside a handoff finding's `detail_md` field.
- `spec_arch_review` then emitted a REJECTED handoff saying: “SPEC draft is missing from
  the review input.”

**Expected:** A create step that is supposed to produce a SPEC must not be accepted
unless it writes the SPEC artifact at the canonical path and returns artifact evidence
that the Python gate validates. Downstream reviewers should receive the exact written
SPEC draft via `spec_draft`, not a handoff-only prose payload.

**Impact:** The workflow can advance past SPEC creation without creating the release
artifact it is meant to create. The next gate then fails for a secondary reason, leaving
no release directory and no actionable SPEC file to review or repair.

**Acceptance:** Strengthen the `spec_create` gate for release-definition so acceptance
requires a real `specs/releases/<release-id>/SPEC.md` (or explicitly documented draft
path) plus artifact path/hash evidence; add a regression test that a handoff-only SPEC
payload is rejected at `spec_create`.
