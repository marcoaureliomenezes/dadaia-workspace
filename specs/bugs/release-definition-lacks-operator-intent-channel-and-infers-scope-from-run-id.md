---
name: release-definition-lacks-operator-intent-channel-and-infers-scope-from-run-id
status: Open
severity: MEDIUM
reported: 2026-06-27
surface: lifecycle release define CLI / release_scope prompt inputs
session_id: sess_43ddcbfb
---

**Symptom:** A release-definition run for `dd-chain-capture` was requested for backlog
item `scraping-capture-lane`, with the operator explicitly stating the real goal was to
test dadaia-workspace capabilities: Layer-1 PI invoking dadaia-workflows, which then use
PI as the Layer-2 worker for purpose-specific lifecycle prompts. The CLI has no option to
pass that operator intent or selected backlog slug into the workflow.

**Observed command:**

```bash
.dadaia/.venv/bin/dadaia lifecycle release define \
  --context dd-chain-capture \
  --release-id v0.1.2 \
  --run-id pi-dd-chain-capture-v0.1.2-define-default-model \
  --harness pi \
  --json
```

**Observed behavior:** The `release_scope` handoff picked `scraping-capture-lane`, but
narrowed it to a “default-model authority” slice. That slice appears to have been
inferred from the operational run id suffix `define-default-model`, not from an explicit
product-scope input. It did not capture the operator's stated test objective for the
release.

**Expected:** `dadaia lifecycle release define` should provide a first-class,
machine-readable operator-intent/scope channel, e.g. `--backlog scraping-capture-lane`
and/or `--intent <text>` / an intake handoff reference. Operational ids such as `run_id`
should never be treated as product scope.

**Impact:** The workflow can define the wrong release slice while still appearing to
follow the backlog. This is especially risky for agentic workflow testing, where run ids
are often operational labels and not product requirements.

**Acceptance:** Add explicit release-definition inputs for selected backlog/bugs/audits
and operator intent; ensure the `release_scope` prompt receives those inputs and does not
mine semantic scope from `run_id`/`task_id` except as an opaque identifier. Add a test
where a run id contains misleading words and the selected scope still follows the
explicit intent.
