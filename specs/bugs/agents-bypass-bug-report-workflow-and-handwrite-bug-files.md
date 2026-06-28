---
name: agents-bypass-bug-report-workflow-and-handwrite-bug-files
status: Closed
severity: HIGH
reported: 2026-06-28
surface: agent instructions / lifecycle bug_report workflow / bug registry format
session_id: sess_43ddcbfb
---

**Symptom:** Layer-1 agents operating inside a dadaia-workspace still report bugs by
hand-writing Markdown files under `specs/bugs/` instead of naturally invoking the
canonical `bug_report` dadaia-workflow and its structured bug-record data plane. The
same pattern appears for release definition: when the operator asks for release/backlog
work, the agent must be oriented to `dadaia lifecycle ...` workflows first, but the
instruction surface still lets agents fall back to direct file edits and ad-hoc bug
records.

**Observed:** During a PI Layer-1 test of a release-definition workflow, the agent
encountered multiple dadaia-workspace workflow/runtime bugs and registered them by direct
file writes to `repos/dadaia-workspace/specs/bugs/*.md`. This followed the current
root-level bug-registration guardrail, but it bypassed the intended workflow-owned bug
intake/dedupe/write process. The operator then corrected the process expectation: bug
reporting should use the `bug_report` dadaia-workflow and the proper structured bug
organization, not ad-hoc Markdown authoring by the entry harness.

**Repro:**

1. Ask a Layer-1 agent to define a release or otherwise operate dadaia-workspace tooling.
2. The agent hits one or more bugs in workflow/runtime behavior.
3. The current always-on guardrail instructs the agent to write a Markdown bug file
   directly under `repos/dadaia-workspace/specs/bugs/`.
4. The available lifecycle CLI exposes governed workflow policy for `bug_report`:

   ```bash
   dadaia lifecycle workflow policy show bug_report --context dadaia-workspace --json
   ```

   but `dadaia lifecycle --help` exposes no runnable `bug_report` command, and the agent
   instructions do not make `bug_report` the mandatory/default path.
5. The agent therefore hand-writes bug Markdown instead of using the workflow, and the
   workflow-step bug data plane is bypassed.

**Expected:**

- Bug registration is workflow-first: agents use a runnable `bug_report` dadaia-workflow
  for intake → dedupe → bug write → terminal gate.
- Layer-1 harnesses (Claude Code, Codex, PI) are instructed that, inside a
  dadaia-workspace, lifecycle work is oriented through `dadaia-workflows`: release
  definition, backlog definition, implementation, closure, bug reporting, audit, and
  research should start from the corresponding `dadaia lifecycle ...` workflow whenever
  that workflow exists.
- Direct hand-written bug files are an emergency fallback only when the bug-report
  workflow itself is unavailable, and that fallback is explicitly logged as a workflow
  failure.
- Bug records use the canonical structured organization for the current product truth
  (including any jsonl/workflow-step data plane required by the bug-report workflow), not
  an agent-invented Markdown shape.

**Impact:** Bugs are recorded without workflow dedupe, without typed step evidence, and
without a terminal Python gate proving the bug record was produced by the canonical
process. Agents also learn the wrong operational habit: direct filesystem mutation for
SDD/lifecycle work instead of invoking dadaia-workflows as the primary control plane.

**Notes:** This is a product/process bug in dadaia-workspace, not a one-off agent typo.
It spans public instructions, CLI discoverability, and workflow availability. The
existing `bug_report` workflow body and policy are present in source/memory, but the
Layer-1 operational surface does not make it the natural or mandatory reporting path.

## Resolution

Fixed in `v0.1.35`.

Root cause: the `bug_report` workflow body and governed catalog entry existed, but the
CLI exposed no runnable `dadaia lifecycle bug report` command and the public root rules
still instructed agents to write Markdown bug files directly as the primary path.

Fix:

- Added `dadaia lifecycle bug report`.
- Added explicit symptom inputs: `--summary`, `--details`, `--repro`, `--expected`,
  `--actual`, and `--severity`.
- Threaded the input into the `bug_intake` prompt as authoritative reported-bug context.
- Added a container builder for the bug-report workflow.
- Updated public AGENTS/rule text so bug registration is workflow-first and direct
  Markdown is only an emergency fallback when the workflow itself is unavailable.

Evidence:

- `tests/integration/cli/test_lifecycle_bug_report_workflow.py::test_bug_report_workflow_is_runnable_from_lifecycle_cli`
- `python -m pytest -q -p no:cacheprovider tests/integration/cli/test_lifecycle_bug_report_workflow.py`
