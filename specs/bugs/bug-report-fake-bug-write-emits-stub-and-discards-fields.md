---
name: bug-report-fake-bug-write-emits-stub-and-discards-fields
status: Closed
severity: MEDIUM
reported: 2026-06-28
resolved: 2026-06-29
release: v0.1.37
surface: dadaia lifecycle bug report (bug_report workflow, fake runtime bug_write step)
session_id: sess_8cdf6cce
---

# `dadaia lifecycle bug report --harness fake` writes a meaningless stub and discards every operator-provided field, while reporting `status: OK`

**Symptom:** Running the `bug_report` workflow on its **default** `--harness fake`
completes successfully (`status: OK`, all steps `accepted`) but the bug file it writes is a
canned placeholder that ignores all the provided `--summary / --details / --repro /
--expected / --actual / --severity` content.

**Repro:**

```bash
.dadaia/.venv/bin/dadaia lifecycle bug report \
  --context dadaia-workspace --release-id v0.1.36 \
  --run-id bug-spec-create-pi-no-artifact \
  --severity HIGH \
  --summary "<detailed multi-line symptom>" \
  --repro "<exact command + JSON output>" \
  --expected "<...>" --actual "<...>" --details "<root-cause analysis>" \
  --json
```

Workflow result:

```json
{"status":"OK","completed":true,"final_phase":"backlog_definition",
 "steps":[{"label":"bug_intake","runtime":"fake","accepted":true},
          {"label":"dedupe","runtime":"fake","accepted":true,"is_gate":true},
          {"label":"bug_write","runtime":"fake","accepted":true},
          {"label":"bug_record_gate","accepted":true,"is_gate":true}]}
```

But the written file (`specs/bugs/bug-spec-create-pi-no-artifact-bug_write.md`) was:

```markdown
---
name: bug-spec-create-pi-no-artifact-bug_write
status: Open
severity: LOW
surface: fake bug-report workflow
---

**Symptom:** Fake bug-report workflow record.
```

Note: `severity: LOW` despite `--severity HIGH`; `surface: fake bug-report workflow`
despite a provided surface; symptom/repro/expected/actual all dropped.

**Expected:** Either (a) the fake `bug_write` runtime should fold the operator-provided
fields (`summary`, `severity`, `repro`, `expected`, `actual`, `details`) into the bug
record so the workflow-first registration path produces a usable bug; or (b) if the fake
runtime is intentionally a no-op stub, the CLI should NOT present `--harness fake` as a
viable default for real bug registration — it should require a real Layer-2 harness for
`bug_write`, or at minimum warn that the fake path produces a non-substantive record.

**Impact:** The documented **workflow-first** bug-registration path
(`bug-registration-guardrail` rule) silently produces useless stubs on its default
harness. An operator who trusts `status: OK` would believe a detailed bug was filed when
only a placeholder exists. This forces the direct-Markdown fallback for every real bug
(as was done for `bug-spec-create-pi-no-artifact-bug_write`,
`pi-default-review-profiles-gpt-5-5-unreachable-provider`, and this record).

**Relation to prior work:** sibling in spirit to the Closed
`release-definition-fake-runtime-does-not-produce-canonical-artifacts` (fake runtime not
producing canonical artifacts) — but for the `bug_report` workflow's `bug_write` step,
which additionally *drops the structured CLI inputs* rather than just omitting a file.

**Severity rationale:** MEDIUM — does not corrupt state, but defeats the sanctioned
workflow-first registration path and can give false confidence.

**Notes:** Discovered while registering the PI release-definition blocking bugs under the
operator's "report any workflow/PI issue as a detailed bug" guardrail. No secrets included.

## Resolution

Closed in `v0.1.37/alpha-1`.

Root cause: the composed fake bug-report runtime wrote a canned markdown record from
`request.task_id` and never received or read the structured `BugReportInput` built by the
CLI. The workflow could therefore report `status: OK` while dropping the operator's
summary, repro, expected, actual, details, and severity fields.

Fix: the bug-report runtime factory now receives the `BugReportInput` and the fake writer
materializes a real additive bug markdown record from those operator-provided fields.

Validation:

- `pytest -p no:cacheprovider tests/integration/cli/test_lifecycle_bug_report_workflow.py -q` -> `1 passed`.
- Included in focused v0.1.37 deterministic suite -> `41 passed`.
