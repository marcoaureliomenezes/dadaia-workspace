# Backlog candidates

Curated index of surviving backlog items. Rebuilt 2026-06-26 after an aggressive cleanup.
This index lists **only** the surviving open candidates. `ideas.md` is a separate informal
scratchpad and is not indexed here.

Architecture baseline: post-v0.1.24 two-layer model. Layer-1 entry harnesses =
`{claude, codex, pi}` (OpenCode removed entirely). Layer-2 = `dadaia lifecycle` Python
workflow bodies driving pi/codex/fake workers.

---

## NEXT RELEASE (operator-elected)

### `workflow-model-governance-panel-control-plane` — Workflow Model Governance + Panel Control Plane
**FEAT-WORKFLOW-MODEL-GOVERNANCE-01 · Status: OPEN — candidate (CRITICAL, operator's next release).**
Governance/control-plane for Python-owned dadaia workflows: per-step default harness/model
profile, panel inspection of diagrams/fragments/gates/effective-models, validated JSON
overlay consumed by the workflow runner. Requires operator pick + mandatory grill before SPEC.

### `backlog-definition-workflow-dedup-conflict-control` — `backlog_definition` workflow: dedup + conflict + staleness control
**FEAT-BACKLOG-DEFINITION-WORKFLOW-01 · Status: OPEN — candidate (CRITICAL, operator-directed 2026-06-26).**
The `backlog_definition` dadaia-workflow must MECHANICALLY keep the backlog a deduplicated,
conflict-free, non-stale SET: mandatory grill + full existing-backlog review + conflict
classifier (UNRELATED/DUPLICATE/OVERLAP/DIVERGENT_CONFLICT/SUPERSEDES/DEPENDS), Python gate
that forbids a NEW file when any non-UNRELATED match exists (update-existing, never a divergent
twin — the `C→D` vs `C→E` failure), and removal-on-release (consumed items are REMOVED from
`specs/backlog/`, not archived) + BL-DUP/BL-CONFLICT/BL-STALE doctor checks. Splits out the
deferred `backlog_definition` body from FEAT-LIFECYCLE-PROMPT-FRAGMENTS-01. Mandatory grill before SPEC.

### `workflow-step-handoff-data-plane-cleanup` — Workflow Step Handoffs + Consumption-Aware Cleanup
**FEAT-WORKFLOW-STEP-HANDOFFS-01 · Status: OPEN — candidate (CRITICAL).**
Defines the run-scoped handoff ledger for prompts inside dadaia-workflows:
`LifecycleRun` as control plane, immutable `.dadaia/runs/lifecycle/<run_id>/steps/`
payload artifacts as data plane, typed producer->consumer edges, exact upstream payload
injection, attempt-aware implementation/review loops, consumption tracking, cleanup
eligibility, retention integration, panel visibility, and doctor checks. This closes the
gap between static prompt fragments and dynamic prompt-to-prompt state while preventing
consumed workflow payloads from becoming slop.

---

## OPEN CANDIDATES

### `panel-ux-overhaul` — Panel UX overhaul
**FEAT-PANEL-UX-200 · Status: OPEN — candidate (MEDIUM).** Tab consolidation (Agents /
Workflows / Kanban / workflow-catalog into one denser tab; Sessions untouched) + theme-switcher
UX redesign. Re-baselined against the current post-v0.1.24 panel. Library source edit, no plugin
(operator-authorized `plugin-scope` deviation). Intake only; mandatory grill before SPEC.

### `model-tier-efficiency-and-fast-tier-utilization` — Layer-1 model-tier efficiency
**FEAT-MODEL-TIER-EFFICIENCY-01 · Status: OPEN — candidate (P2).** The Layer-1 `fast` tier has
zero agent assignments (all 9 core personas = claude-opus-4-8) and there is no recurring
efficiency-audit trigger. Distinct from the v0.1.24 Layer-2 GPT model catalog.

### `plugin-packs-and-install-command` — Plugin packs distribution + `dadaia plugin install`
**Status: OPEN — candidate (MEDIUM).** Distribute the frontend-design + devops plugin packs and
ship a real `dadaia plugin install` command. Blocks the plugin agents (`frontend-engineer`,
`design-specialist`, `devops-engineer`) and the panel-UX `plugin-scope` deviation.

### `centralize-release-semver-canon` — Centralize the release SemVer canon
**Status: idea/candidate (LOW).** One shared SemVer-canon constant across `scaffolder.py`,
`doctor.py`, `new_artifacts.py` instead of the duplicated regex/canon.

### `features-import-infrastructure-direct-debt` — features → infrastructure layering debt
**Status: CANDIDATE — not picked (MEDIUM).** Remove the transitional direct
`features → infrastructure` imports (7 import-linter `ignore_imports`) behind Protocol/DI.

### `pid-probe-seam-consolidation` — Consolidate `_build_pid_probe`
**Status: OPEN — candidate (LOW).** Single public composition-root builder for the PID probe
instead of the duplicated seam wiring.

### `telemetry-tier2-chmod-unguarded-on-windows` — telemetry Tier-2 `os.chmod` on Windows
**Status: CANDIDATE — not picked (LOW).** Tier-2 telemetry `os.chmod` is a silent no-op on
Windows; route it through the platform permission seam.

### `review-rejection-rework-path` — Wire/document the review-rejection rework path
**Status: idea/candidate (LOW).** Wire (or formally document) the
`LifecycleAgentRunner._blocked_result` → `implementation_ladder` rework loop on a REJECTED
review verdict.

### `sdd-governance-v2-agents-lifecycle` — SDD governance v2 residual
**FEAT-GOV-V2-01 · Status: OPEN — PARTIALLY CONSUMED.** v0.1.15 shipped the Codex
lifecycle-foundation slice; later releases shipped adjacent backlog-consumption and audit
workflow pieces. Remaining scope = specs taxonomy decision + archive gate classes,
event-sourced JSONL bug telemetry, and audit-disposition law. All OpenCode-enforcement
scope stripped (dead).
