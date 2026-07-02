---
name: workflow-model-governance-panel-control-plane
status: delivered
delivered_in: v0.1.28
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/pipeline.py#PipelineStep" }
    change: "Slice A: build steps from a resolved workflow-model policy instead of hard-coded model_profile strings; add a WorkflowExecutionPolicyResolver"
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/json_lifecycle_run_store.py#JsonLifecycleRunStore" }
    change: "persist the resolved workflow policy snapshot (harness, model profile, concrete model, reasoning, fragments) into LifecycleRun"
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/pi_runtime.py#PiHeadlessAdapter" }
    change: "consume the per-request resolved PI model and pass `--model <id>` per step (not only at adapter construction)"
  - subject: { kind: api, ref: "panel:/api/workflow-model-policy" }
    change: "Slice C: add the workflow control-plane GET/PUT/POST policy + catalog + profiles routes that validate and atomically write the operator overlay JSON"
---

# EPIC - Workflow Model Governance + Panel Control Plane

**ID:** FEAT-WORKFLOW-MODEL-GOVERNANCE-01
**Reported:** 2026-06-26 (operator architecture review after the two-agentic-layer
workflow shift).
**Owner:** project-manager (curates) -> product-engineer (release definition after a
MANDATORY grill).
**Status:** DELIVERED - v0.1.28 (see frontmatter `status: delivered` + `delivered_in`).
Shipped the whole epic A→D: model-profile registry + atomic overlay store + shared
`WorkflowExecutionPolicyResolver` + per-run policy snapshot (Wave A), governed Python
`dadaia_catalog` with `*.workflow.md` demoted to reference-only (Wave B), first-class
panel Workflows control plane + guarded policy editor + GET/PUT/validate mutation routes
(Wave C), and a read-only fragment inspector + `WMP-*` governance doctor (Wave D). rc-ship
trio APPROVED (qa + code + security) at commit `28379a71`. CLOSURE:
`specs/_archive/releases/v0.1.28/CLOSURE.md` (after archive).

**Follow-ups carried into a future release** (NOT delivered in v0.1.28 — filed as the
candidate `workflow-model-governance-operator-profiles-and-context-overlays`):
- **D-2 deferral** — operator-added PI profiles
  (`.dadaia/states/workflow_model_profiles.local.json`); v0.1.28 ships built-in recommended
  profiles only.
- **D-2 deferral** — per-context overlays + `extends` inheritance; v0.1.28 honors only the
  `default` context (a non-`default` context key is inert).
- **code-reviewer MEDIUM** — under a `--harness` override the persisted run snapshot records
  the *governed* harness, not the adapter that actually ran (e.g. `--harness pi` runs the PI
  adapter with the codex-governed model id); reconcile snapshot `runtime_kind` vs governed
  harness for run-history fidelity.
**Priority:** CRITICAL - workflows are becoming a core product surface, beside Spec
Context Projects and the panel itself.
**Depends on / coordinates with:**
`lifecycle-prompt-fragments-ai-surface-dehydration.md` and the OpenCode removal /
Layer-2 contraction release.

---

## 1. Problem

dadaia-workspace now has two distinct agentic layers:

1. **Layer 1 - interactive orchestrator.** The operator launches `claude`, `codex`, or
   `pi`, binds a Spec Context Project, and the Layer-1 agent invokes dadaia workflow CLI
   commands.
2. **Layer 2 - workflow workers.** Python workflow bodies call bounded worker prompts in
   a procedural routine: sequence, loop, if/else, gates, and future parallel batches.

The Layer-2 product contract is changing to exactly two worker harnesses:

- `codex`
- `pi`

Claude Code remains Layer 1 only. OpenCode is removed/deferred and must not appear as a
supported workflow worker.

The current implementation is not ready for the model-governance part of this design:

- `dadaia lifecycle` has `--harness` and `--step-harness`, but no governed
  `--model-profile` / `--step-model` policy.
- `PipelineStep.model_profile` exists, but defaults are hard-coded in Python
  (`sonnet` / `opus`) and are not user-governed.
- Codex maps `model_profile` through `core/model_registry.py`; PI accepts only a raw
  optional model string in `PiHeadlessConfig`.
- The panel Workflows tab still reads projected/reference `*.workflow.md` files through
  `WorkflowsService` / `MarkdownWorkflowStore`; it does not describe the Python lifecycle
  workflow bodies, prompt fragments, harness/model choices, or editable policy overlays.
- `/api/workflows` is read-only workflow documentation, not a control plane.

This creates a governance risk: once workflows contain many prompts, each prompt may need
a different model depending on role, cost, depth, latency, and provider availability. If
this is controlled by ad hoc CLI flags or hard-coded Python defaults, users will not be
able to understand or manage the workflow they are running.

## 2. Target thesis

Create a **workflow control plane**:

- Python workflow definitions are the source of truth for workflow identity, steps,
  prompt fragments, gates, default harnesses, and default model profiles.
- A validated JSON overlay stores operator-selected per-workflow/per-step model choices.
- The panel is the primary UX for inspecting and changing those choices.
- The CLI remains the execution path: Layer-1 agents invoke workflows with a selected
  Layer-2 harness profile (`codex` or `pi`) and optional named configuration overlay.
- Workers never receive arbitrary ungoverned model strings from free text. They receive
  resolved model profiles from a registry/policy service.

This is not a cosmetic panel change. It is the missing governance layer for the new
workflow-centered architecture. Without it, dadaia-workflows become powerful but opaque:
the user cannot see which model is used for each prompt, cannot safely change cost/depth
tradeoffs, and cannot audit whether a run used the intended worker harness. With it,
workflows become inspectable, configurable, and reproducible.

## 3. Non-negotiable product laws

1. **Layer-2 harness law:** workflow workers support only `codex` and `pi`. `fake` may
   exist for tests only. `claude` and `opencode` are not product CLI choices for Layer 2.
2. **CLI selection law:** every workflow run must resolve a workflow execution policy:
   selected worker harness, per-step harness override if allowed, and per-step model
   profile.
3. **Panel visibility law:** every workflow must be inspectable in the panel: flow diagram,
   step list, role, harness, model profile, prompt fragments, dynamic inputs, output
   schema, and gates.
4. **Panel governance law:** user changes from the panel write a validated JSON overlay,
   never Python source or projected agentic assets.
5. **Registry law:** allowed model choices are governed by a registry with harness,
   profile id, model id, reasoning level, cost metadata when available, availability, and
   deprecation state.
6. **Default-first law:** every step ships with a library default. The operator may
   override it, but a workflow is runnable before any panel configuration exists.
7. **Auditability law:** each workflow run records the resolved policy: harness, model
   profile, concrete model id, reasoning setting, fragment ids, prefix hash, overlay id,
   and policy source.

## 4. Current architecture findings

Representative current-state files:

- `dadaia_workspace/core/models/lifecycle.py` defines `AgentRuntimeKind` and still includes
  `CLAUDE_SDK`; the desired Layer-2 product surface should contract to Codex/PI plus
  test-only fake.
- `dadaia_workspace/cli/commands/lifecycle.py` maps CLI `--harness` values and implements
  `--step-harness`, but has no `--step-model` or profile overlay command.
- `dadaia_workspace/features/lifecycle/pipeline.py` has `PipelineStep.model_profile`, but the
  implementation ladder hard-codes profile names.
- `dadaia_workspace/features/lifecycle/prompt_builder.py` passes `model_profile` into
  `AgentRunRequest`, but does not resolve a governed policy.
- `dadaia_workspace/infrastructure/codex_runtime.py` can resolve Codex tier profiles through
  `codex_tier_views()`.
- `dadaia_workspace/infrastructure/pi_runtime.py` accepts `PiHeadlessConfig.model`, but does not resolve
  request-level model profiles.
- `dadaia_workspace/features/workflows/service.py` and
  `dadaia_workspace/infrastructure/markdown_workflow_store.py` read reference
  `*.workflow.md` files; this is not the Python lifecycle workflow catalog.
- `dadaia_workspace/features/panel/views/workflows.py` shows a runtime switcher for Claude/Codex, which is
  stale for the new Layer-2 model.
- `dadaia_workspace/features/panel/views/assets/js/workflows.js` renders cards,
  server-side SVG DAGs, and stage tables; it has no model-policy editor or fragment
  inspector.
- `dadaia_workspace/features/panel/handler.py` currently exposes panel routes without
  bearer authentication by operator decision; its hard guard is loopback bind plus
  Host-header allowlist. New write endpoints must match that real security posture, not
  assume a bearer-token model that no longer exists.
- `dadaia_workspace/infrastructure/json_lifecycle_run_store.py` persists lifecycle runs
  atomically under `.dadaia/states/lifecycle/`, but `LifecycleRun` currently has no
  resolved policy snapshot.
- `dadaia_workspace/container.py` is the composition root for `build_agent_runtime`,
  `build_lifecycle_pipeline`, `build_lifecycle_phase_workflow`, `build_panel_service`,
  and `build_panel_views`; new services must be wired there, not constructed ad hoc in
  view modules.

### 4.1 Architecture readiness verdict

The repo has the right seams, but they are not yet connected for governance:

| Existing seam | Why it helps | Missing piece |
|---|---|---|
| `PipelineStep.model_profile` | A step can already carry model intent | Profiles are hard-coded and not resolved from policy |
| `AgentRunRequest.model_profile` | Runtime request can carry model selection | It carries only one string, not a resolved harness-specific profile snapshot |
| `CodexExecAdapter._model_and_effort()` | Codex can map profile to model + reasoning | It is tied to current tier names, not workflow profile ids |
| `PiHeadlessConfig.model` | PI can receive `--model` | Request-level profile resolution is absent |
| `JsonLifecycleRunStore` | Atomic run state already exists | Run records do not include policy/fragments/model evidence |
| Panel `/api/workflows` | UI already has a workflow detail route | Source is reference Markdown, not Python workflow definitions |
| `render_dag_svg()` | Diagram rendering exists | Diagram must be generated from executable workflow metadata |

Conclusion: this feature should be built by extending existing seams, not by inventing a
parallel panel/workflow subsystem.

## 5. Proposed architecture

### 5.0 End-to-end flow

The intended runtime flow must be explicit:

```text
Panel edit
  -> validates workflow id + step id + harness + model profile
  -> atomically writes .dadaia/states/workflow_model_policy.json

Layer-1 agent runs CLI
  -> dadaia workflow run <workflow-id> --context <ctx> --harness codex|pi
  -> CLI loads Python workflow definition
  -> CLI loads model registry + operator policy overlay
  -> WorkflowExecutionPolicyResolver resolves each step
  -> workflow persists policy snapshot into LifecycleRun
  -> each prompt step builds PromptScope/AgentRunRequest from resolved policy
  -> adapter receives concrete model config
  -> run evidence exposes policy/fragments/gates back to panel
```

No prompt step should read `.dadaia/states/workflow_model_policy.json` directly. The
workflow runner reads it once through a service, validates it, snapshots it, and passes
resolved model data into each step. This prevents mid-run panel edits from mutating an
in-flight run.

### 5.1 Workflow definition registry

Add a library-owned workflow registry in Python, not projected Markdown:

```text
dadaia_workspace/features/lifecycle/catalog.py
dadaia_workspace/features/lifecycle/workflow_defs/
  release_definition.py
  implementation.py
  closure.py
  backlog_definition.py
  audit.py
  research.py
  bug_report.py
```

Each workflow definition exposes:

```yaml
id: release_definition
display_name: Release Definition
description: Turns selected backlog/bugs/audit findings into SPEC/PLAN/TASKS.
steps:
  - id: scope_grill
    role: project-manager
    default_harness: codex
    default_model_profile:
      codex: codex-review-deep
      pi: pi-reasoning-high
    fragments:
      - shared.context-contract
      - release_definition.scope-grill
    dynamic_inputs:
      - backlog_candidates
      - open_bugs
      - active_memory_catalog
    output_schema: release-scope-handoff-v1
    gate: operator-questions-resolved
```

The registry must be importable by CLI, workflow runners, panel APIs, doctor checks, and
tests. Reference Markdown workflow docs become generated/documentation-only, not the
source of execution truth.

Required DTOs/models, likely under `dadaia_workspace/core/models/workflow_execution.py`
or `dadaia_workspace/core/models/lifecycle.py`:

```text
WorkflowDefinition
WorkflowStepDefinition
WorkflowFragmentRef
WorkflowModelDefault
WorkflowGateDefinition
WorkflowDynamicInput
```

The existing `dadaia_workspace/core/models/workflow.py` models represent old Markdown
workflow files. The release must decide whether to extend them or add new
lifecycle-specific models. The safer path is new lifecycle workflow models, then adapt
the panel API to return a stable JSON DTO.

### 5.2 Model profile registry

Add a workflow-facing model registry separate from historical Claude-agent tiering. It
must support multiple model families for PI and Codex without leaking one harness's names
into the other.

Conceptual shape:

```json
{
  "schema_version": "workflow-model-registry-v1",
  "profiles": [
    {
      "id": "codex-implementation-standard",
      "harness": "codex",
      "model": "gpt-5.3-codex",
      "reasoning": "medium",
      "purpose": "implementation",
      "availability": "default",
      "deprecated": false
    },
    {
      "id": "codex-review-deep",
      "harness": "codex",
      "model": "gpt-5.5",
      "reasoning": "high",
      "purpose": "review",
      "availability": "default",
      "deprecated": false
    },
    {
      "id": "pi-reasoning-high",
      "harness": "pi",
      "model": "<operator/provider-model-id>",
      "reasoning": "high",
      "purpose": "review",
      "availability": "operator-configured",
      "deprecated": false
    }
  ]
}
```

Codex profiles can initially derive from `core/model_registry.codex_tier_views()`, but
workflow model governance should become its own policy layer because Codex workflow
profiles and projected agent persona tiers are not the same product concept.

PI profiles must allow more breadth than the current registry. PI can expose many
operator/provider models, so the product needs:

- built-in recommended aliases;
- operator-added profiles;
- validation that a selected profile has `harness: "pi"`;
- optional live availability checks, never mandatory for offline tests.

The model profile registry needs two layers:

1. **Built-in library profiles** shipped in source/package data. These give every workflow
   safe defaults.
2. **Operator profiles** stored in workspace state, for PI and future provider-specific
   choices.

Candidate files:

```text
dadaia_workspace/features/lifecycle/model_profiles.py
dadaia_workspace/infrastructure/json_workflow_model_policy_store.py
.dadaia/states/workflow_model_policy.json
.dadaia/states/workflow_model_profiles.local.json
```

The `.local.json` profile file, if added, must be treated as operator runtime state and
must not be projected into public assets. It must never store API keys.

Profile fields should be explicit enough to render a useful panel:

```json
{
  "id": "codex-review-deep",
  "harness": "codex",
  "label": "Codex review deep",
  "model": "gpt-5.5",
  "reasoning": "high",
  "purpose": "review",
  "latency_class": "slow",
  "cost_class": "high",
  "availability": "default",
  "source": "built-in",
  "deprecated": false,
  "replacement": null
}
```

The panel should show label, model, reasoning, source, and warning state. It should not
force users to memorize raw model ids.

### 5.3 Operator overlay JSON

Store operator-selected overrides under workspace state, not source:

```text
.dadaia/states/workflow_model_policy.json
```

Candidate schema:

```json
{
  "schema_version": "workflow-model-policy-v1",
  "updated_at": "2026-06-26T00:00:00Z",
  "profiles_version": "workflow-model-registry-v1",
  "contexts": {
    "default": {
      "workflows": {
        "release_definition": {
          "default_harness": "codex",
          "steps": {
            "scope_grill": {
              "harness": "codex",
              "model_profile": "codex-review-deep"
            },
            "spec_create": {
              "harness": "pi",
              "model_profile": "pi-reasoning-high"
            }
          }
        }
      }
    },
    "dadaia-workspace": {
      "extends": "default",
      "workflows": {}
    }
  }
}
```

Rules:

- Missing overlay means "use library defaults".
- A context-specific overlay may inherit from `default`.
- Every override must validate against workflow step ids and allowed harness/profile ids.
- Unknown workflow id, unknown step id, unknown profile, harness/profile mismatch, and
  deprecated profile should be hard validation failures in the panel API and doctor.
- The workflow runner records the resolved policy snapshot into the lifecycle run record
  before executing the first prompt.

State management rules:

- The store must use the same atomic-write pattern as `JsonLifecycleRunStore`: write temp
  file in the target directory, then `os.replace`.
- The store must preserve unknown future-compatible top-level fields only if the schema
  explicitly allows them; otherwise fail fast. Silent dropping is dangerous because it
  loses operator configuration.
- Invalid JSON must never be partially repaired by the panel. The panel should show a
  clear invalid-state message and offer reset/backup actions.
- A last-good backup should be kept, for example:
  `.dadaia/states/workflow_model_policy.last-good.json`.
- The workflow runner should fail before starting a model call when policy is invalid.
  It must not silently fall back to defaults if a user has a malformed explicit policy;
  silent fallback would hide governance failure.
- Missing policy file is different from invalid policy file: missing means defaults;
  invalid means blocked.

### 5.4 CLI contract

Add policy-aware workflow commands. Final names can be refined during SPEC, but the
contract should support:

```bash
dadaia workflow run release-definition \
  --context dadaia-workspace \
  --harness codex \
  --policy default

dadaia workflow run implementation \
  --context dadaia-workspace \
  --harness pi \
  --step-harness review_security=codex \
  --step-model implement=pi-implementation-standard \
  --step-model review_security=codex-review-deep
```

Acceptance rules:

- Product harness choices are exactly `codex|pi`.
- `fake` is allowed only through tests or an explicit hidden/internal flag.
- `--harness claude` and `--harness opencode` fail with actionable messages.
- `--step-model` must reference a profile valid for that step's resolved harness.
- If CLI overrides and panel JSON overlays both exist, precedence is explicit:
  CLI run override > context overlay > default overlay > workflow library default.
- The resolved policy is printed in `--json` output and persisted in run state.

The current CLI lives under `dadaia lifecycle`. The SPEC should decide whether the
operator-facing command becomes `dadaia workflow run` or remains under
`dadaia lifecycle`. Regardless of naming, the contract needs:

```text
--harness codex|pi
--policy <name-or-default>
--step-harness <step-id>=codex|pi
--step-model <step-id>=<model-profile-id>
--show-policy
--json
```

The command must reject ambiguous inputs:

- `--step-model review=codex-review-deep` when `review` is running on `pi`;
- `--step-harness unknown=codex`;
- `--step-model unknown=...`;
- `--harness claude`;
- `--harness opencode`;
- profile id exists but is deprecated with no explicit override flag;
- workflow step is declared non-overridable.

The CLI should also expose read-only inspection commands:

```bash
dadaia workflow policy show release-definition --context dadaia-workspace --json
dadaia workflow profiles list --harness codex --json
```

These commands make the panel behavior scriptable and testable.

### 5.5 Runtime resolution

Add a `WorkflowExecutionPolicyResolver` used by both CLI and Python workflow bodies:

```text
workflow_id + context + CLI flags + overlay JSON + workflow defaults
  -> ResolvedWorkflowPolicy
```

It returns, for every prompt step:

- step id;
- role;
- harness (`codex` or `pi`);
- model profile id;
- concrete model id;
- reasoning setting if the harness supports it;
- fragment bundle ids;
- output schema id;
- dynamic context selector id.

The runtime adapters should not parse overlay JSON. They receive a resolved
`AgentRunRequest` with concrete model information.

`AgentRunRequest` likely needs to evolve from:

```python
model_profile: str | None
```

to a nested resolved model config:

```python
ResolvedModelConfig(
    profile_id="codex-review-deep",
    harness="codex",
    model="gpt-5.5",
    reasoning="high",
    source="context-overlay",
)
```

Adapter behavior:

- `CodexExecAdapter` should prefer the resolved concrete model config on the request,
  then fall back to registry defaults only for legacy compatibility.
- `PiHeadlessAdapter` should use the resolved PI model to add `--model <id>` per request,
  not only from adapter construction time. This likely requires changing `_command()` to
  receive the request or resolved model.
- `FakeAgentRuntime` should record/echo the model config in tests so policy resolution can
  be asserted without invoking real providers.

Run snapshot:

`LifecycleRun` should persist a policy snapshot. Suggested field:

```json
"workflow_policy": {
  "workflow_id": "implementation",
  "policy_id": "default",
  "resolved_at": "2026-06-26T00:00:00Z",
  "source_precedence": ["cli", "context-overlay", "default-overlay", "library-default"],
  "steps": {
    "implement": {
      "harness": "pi",
      "model_profile": "pi-implementation-standard",
      "model": "glm-5.2",
      "reasoning": "medium",
      "fragments": ["implementation.implement-tdd"],
      "output_schema": "implementation-handoff-v1"
    }
  }
}
```

The panel should read this snapshot for completed/in-flight runs. It should not reconstruct
past runs from current policy because current policy may have changed.

### 5.6 Panel control plane

Replace the current "Ops subtab reference workflows" UX with a first-class Workflows
area. Minimum viable panel shape:

- Workflow list grouped by lifecycle phase.
- Detail page per workflow with:
  - generated diagram from Python workflow definition;
  - step timeline/table;
  - role per step;
  - default harness and effective harness;
  - default model profile and effective model profile;
  - concrete model id and reasoning level;
  - fragment ids with an inspector;
  - dynamic inputs;
  - output schema;
  - gates and failure transitions.
- Model policy editor:
  - segmented control for `codex` / `pi`;
  - per-step model dropdown filtered by harness;
  - reset-to-default action;
  - diff view: default vs effective;
  - validation banner before save;
  - save writes JSON overlay through a guarded panel mutation API.
- Read-only run evidence view:
  - latest runs;
  - resolved policy snapshot;
  - fragment ids;
  - prefix hash;
  - selected dynamic files;
  - gate result.

Diagram rendering can use the existing server-side SVG DAG machinery initially. Mermaid
source may be generated for inspection/export, but the first implementation should avoid
making browser Mermaid the execution dependency. The important contract is that diagrams
come from Python workflow metadata, not hand-maintained Markdown.

The new Workflows tab should replace the old subordinate "workflow cards under Ops" model
with a first-class navigation area. Agents and Kanban can remain available during
transition, but Workflows becomes the primary operational surface.

Recommended UI layout:

```text
Workflows
  Left: workflow list grouped by lifecycle phase
  Main: diagram + selected workflow summary
  Step matrix:
    Step | Role | Harness | Model profile | Concrete model | Fragments | Gate
  Right/detail drawer:
    selected step details
    fragment inspector
    dynamic context selector
    output schema
    failure/backtrack behavior
  Policy editor:
    context selector
    default vs effective diff
    per-step controls
    save / reset / validate
```

Controls:

- Harness choice: segmented control with only Codex and PI.
- Model choice: dropdown filtered by selected harness and step purpose.
- Deprecated profile: selectable only with explicit warning and ideally blocked unless a
  replacement is unavailable.
- Reset: per-step reset and whole-workflow reset.
- Validation: always run before save; save disabled while invalid.

The panel must make the default/effective distinction obvious:

| State | Meaning |
|---|---|
| Default | library workflow default applies |
| Context override | `.dadaia/states/workflow_model_policy.json` overrides the default |
| CLI override | current run used a one-shot CLI override |
| Invalid | saved policy references missing workflow/step/profile |
| Deprecated | selected profile is still resolvable but should be replaced |

### 5.7 Panel APIs

Add panel APIs:

```text
GET  /api/workflow-catalog
GET  /api/workflow-catalog/<workflow-id>
GET  /api/workflow-model-profiles
GET  /api/workflow-model-policy?context=<ctx>
PUT  /api/workflow-model-policy?context=<ctx>
POST /api/workflow-model-policy/validate
GET  /api/lifecycle-runs?workflow=<id>&context=<ctx>
```

Security/robustness:

- Current panel architecture has no bearer-token auth by operator decision. Writes must
  therefore rely on the existing loopback-only bind plus Host-header allowlist, and add
  mutation-specific guardrails.
- JSON schema validation before any write.
- Atomic write via temp + rename under `.dadaia/states/`.
- Backup last-good policy or keep a small rollback history.
- Never expose secrets or provider credentials in profiles or run snapshots.
- Reject non-JSON content types for mutation routes.
- Reject oversized payloads.
- Return structured validation errors with field paths.

Files likely touched:

```text
dadaia_workspace/features/panel/handler.py
dadaia_workspace/features/panel/service.py
dadaia_workspace/features/panel/views/index.py
dadaia_workspace/features/panel/views/workflows.py
dadaia_workspace/features/panel/views/assets/js/workflows.js
dadaia_workspace/features/panel/views/assets/css/*.css
dadaia_workspace/container.py
```

Route table changes in `handler.py` must include the new GET/PUT/POST routes explicitly;
there is no route fallback.

### 5.8 Doctor and drift checks

Add doctor coverage so this governance layer does not rot:

- `dadaia workflow doctor` or `dadaia lifecycle doctor` validates workflow definitions,
  model defaults, profile ids, and policy overlays.
- `dadaia public doctor` should assert removed/deferred Layer-2 harnesses do not leak into
  public workflow policy docs.
- `dadaia specs doctor` may remain focused on specs, but release closure should update
  memory atoms so current product truth says workflows are Codex/PI only.

Required checks:

- every workflow id is unique;
- every step id is stable and unique inside workflow;
- every step has a default profile for each supported harness or a clear unsupported
  declaration;
- every fragment id resolves;
- every output schema id resolves;
- every policy override references existing workflow/step/profile;
- profile harness matches resolved step harness;
- no product policy exposes `claude` or `opencode` as Layer-2 worker choices;
- invalid state files fail with actionable messages and do not crash the panel.

### 5.9 Feature integration map

| Feature/module | Change |
|---|---|
| `core/models/lifecycle.py` | Add resolved model config and workflow policy snapshot to core dataclasses |
| `features/lifecycle/pipeline.py` | Build steps from resolved workflow policy instead of hard-coded model profile strings |
| `features/lifecycle/phase_workflow.py` | Use resolved policy for single-step workflow runs |
| `features/lifecycle/prompt_builder.py` | Include resolved model metadata and fragment ids in built requests/output payload |
| `features/lifecycle/*catalog*` | New Python workflow definition registry |
| `features/lifecycle/*policy*` | New resolver for defaults + overlay + CLI overrides |
| `infrastructure/codex_runtime.py` | Consume concrete request model/reasoning config |
| `infrastructure/pi_runtime.py` | Consume per-request model config and pass `--model` |
| `infrastructure/json_lifecycle_run_store.py` | Persist evolved `LifecycleRun` schema with policy snapshot |
| `infrastructure/json_workflow_model_policy_store.py` | New atomic store for policy overlays |
| `features/panel/service.py` | Expose catalog, profiles, policy read/validate/write, run snapshots |
| `features/panel/views/assets/js/workflows.js` | Replace card-only docs with workflow control-plane UI |
| `features/workflows/service.py` | Deprecate or adapt old Markdown workflow catalog |
| `container.py` | Wire new stores/services/resolvers through composition root |
| `tests/unit/features/lifecycle/` | Policy resolver, workflow catalog, prompt/request construction |
| `tests/unit/infrastructure/` | JSON store resilience, Codex/PI model config behavior |
| `tests/unit/features/panel/` | API validation, route registration, service behavior |
| `tests/integration/cli/` | CLI policy precedence and JSON output |
| `tests/e2e/features/` | Panel workflow editor behavior once frontend exists |

## 6. UX principles

- Workflows are not "docs cards"; they are a control surface.
- The user must understand what each prompt will run before executing the workflow.
- Model selection should be explicit but not noisy: defaults make the simple path easy,
  per-step overrides make expert control possible.
- The panel must make drift obvious: default, overridden, deprecated, missing, and
  invalid states should have distinct visual treatment.
- Fragment inspection is read-only. Editing fragments remains source-controlled release
  work, not panel state.

The Workflows tab should answer these operator questions without opening code:

- What workflows exist?
- Which lifecycle phase does each workflow serve?
- What exact prompt steps will run?
- Which worker harness will each step use?
- Which model and reasoning level will each step use?
- Which fragments and dynamic files are injected?
- Which schema/gate decides whether the workflow advances?
- What did the last run actually use?
- What changed from the default policy?

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Free-form model strings create broken runs | Profiles only; optional advanced operator-added profiles validated before save |
| Codex and PI model semantics diverge | Separate harness-specific profile schema; common fields only at policy level |
| Panel writes corrupt workflow state | JSON schema validation, atomic writes, rollback history, doctor checks |
| Workflow definitions and panel docs drift | Panel reads Python workflow registry directly; no hand-maintained workflow Markdown as source |
| CLI flags fight panel configuration | Explicit precedence: CLI > context overlay > default overlay > library default |
| Future parallel steps need model policy | Step ids remain stable; policy resolver handles parallel groups as normal steps |
| Deprecated model remains selected | Doctor warns or fails depending severity; panel shows replacement path |
| Secrets leak through model config | Profiles store model ids/aliases only, never API keys or provider secrets |
| OpenCode/Claude sneak back into Layer 2 | Contract tests and doctor check allowed harness set for workflow policy and CLI help |
| Mid-run policy mutation changes behavior | Resolve and snapshot policy before first step; in-flight run ignores later panel edits |
| Old run evidence becomes misleading after policy edits | Panel reads persisted run snapshot for history, current policy only for future runs |
| Invalid local PI model id breaks important workflow | Validate profile shape offline; optional live-check command; fail before model call with clear error |
| Model profile ids become unstable | Treat profile id as stable API; deprecate with replacement instead of renaming in place |
| Parallel execution later creates race on policy state | Snapshot policy once before parallel fan-out; workers receive immutable per-step config |
| Panel and CLI resolve policy differently | One shared `WorkflowExecutionPolicyResolver`; CLI and panel service both call it |
| Store schema evolves | Versioned schema + migration/doctor path; no silent best-effort coercion |

## 8. Suggested release slicing

This is large. Do not ship it as one opaque release.

### Slice A - model policy foundation

- Add workflow model profile registry.
- Add overlay JSON store and schema.
- Add policy resolver with precedence rules.
- Wire lifecycle pipeline to resolved policy.
- Add CLI `--step-model` and policy `--json` output.
- Contract tests: Codex/PI only, profile validation, overlay precedence.
- Update `AgentRunRequest` and runtime adapters so PI and Codex can consume concrete
  resolved model config.
- Persist policy snapshot in `LifecycleRun`.

### Slice B - Python workflow catalog

- Add Python workflow definition registry.
- Move panel workflow data source from `MarkdownWorkflowStore` to the Python registry.
- Generate diagrams from registry metadata.
- Keep old Markdown workflow files as reference-only or generated docs.
- Add doctor checks for workflow/fragment/schema/profile consistency.

### Slice C - panel model governance UX

- Add workflow detail view with effective policy.
- Add per-step model editor.
- Add validation/save/reset.
- Add run snapshot evidence view.
- Add panel API routes and service methods for catalog/profile/policy operations.
- Add frontend tests for invalid policy, save, reset, and default/effective diff.

### Slice D - fragment inspector integration

- Link each step to prompt fragment bundle metadata.
- Add read-only fragment inspector.
- Show dynamic context selectors and output schema.
- Add doctor checks for every step having fragments and schemas.

## 9. Acceptance criteria

- `dadaia workflow/lifecycle` product CLI rejects Layer-2 `claude` and `opencode`.
- `codex` and `pi` are the only user-selectable Layer-2 worker harnesses.
- Every workflow step has a default model profile for each supported harness, or an
  explicit "not supported on this harness" declaration.
- A user can change a workflow step's model profile in the panel and the change is
  persisted to `.dadaia/states/workflow_model_policy.json`.
- The workflow runner reads the policy and uses the selected model for the selected
  prompt step.
- A workflow run records the resolved policy snapshot and exposes it through panel APIs.
- The panel workflow detail shows diagram, steps, roles, harnesses, model profiles,
  fragments, dynamic inputs, output schemas, and gates.
- Doctor fails on invalid workflow policy JSON, unknown profiles, harness/profile
  mismatch, stale workflow step ids, and any Layer-2 OpenCode/Claude policy residue.
- Tests prove default policy, context override, CLI override, invalid override, and
  reset-to-default behavior.
- `PiHeadlessAdapter` receives the selected per-step PI model from the resolved request
  and passes it to `pi --mode json --model`.
- `CodexExecAdapter` receives the selected per-step Codex model/reasoning from the
  resolved request and passes it to `codex exec -m ... -c model_reasoning_effort=...`.
- A panel-saved policy change affects the next run but not an already-started run.
- The panel can show "default vs effective" for every step without reading Python source
  in the browser.
- Historical run detail shows the model policy actually used at run time, even after the
  current policy changes.
- Corrupt `.dadaia/states/workflow_model_policy.json` blocks workflow execution with an
  actionable error and leaves the last-good file intact.
- The old Markdown workflow catalog is no longer the authority for executable workflow
  behavior.

## 10. Implementation checklist for SPEC authors

Before SPEC is written, convert this backlog into tasks that cover these concrete
deliverables:

- Data models:
  - workflow definition models;
  - model profile models;
  - policy overlay models;
  - resolved policy models;
  - lifecycle run policy snapshot model.
- Services:
  - workflow catalog service;
  - model profile registry service;
  - workflow model policy store;
  - workflow execution policy resolver;
  - panel workflow governance service methods.
- CLI:
  - policy inspection commands;
  - run commands with `--harness`, `--step-harness`, `--step-model`, `--show-policy`;
  - clear rejection of `claude`/`opencode` for Layer 2.
- Runtime:
  - Codex per-request model/reasoning;
  - PI per-request model;
  - fake runtime capture for tests.
- Panel:
  - top-level Workflows tab or promoted Workflows area;
  - workflow diagram from Python registry;
  - step model matrix;
  - fragment inspector;
  - policy editor;
  - run snapshot viewer.
- Doctor/tests:
  - schema validation;
  - corrupt JSON behavior;
  - policy precedence;
  - stale step/profile detection;
  - adapter command construction;
  - panel API route registration;
  - frontend save/reset validation.

## 11. Mandatory grill questions before SPEC

These do not block this backlog record, but they must be resolved before SPEC:

1. Should workflow model policy be workspace-wide only at first, or support per-context
   overrides in the first release?
2. Should the first implementation expose operator-added PI profiles, or only built-in
   recommended PI aliases until live PI model behavior is verified?
3. Should CLI `--step-model` accept only profile ids, or also an advanced one-shot
   concrete model id with a loud "not persisted" marker?
4. Should the panel replace the Ops subtab immediately, or first add a new top-level
   Workflows tab while keeping old Agents/Kanban read-only for transition?
5. Which workflow should be the first full demo path: release definition or
   implementation pipeline?
