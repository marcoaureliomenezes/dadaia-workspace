# SPEC — Release: v0.1.28 — Workflow Model Governance + Panel Control Plane

**Status:** Aprovado
**Release ID:** v0.1.28
**Owner:** product-engineer
**Opened:** 2026-06-26
**Consumes:** workflow-model-governance-panel-control-plane

> Grill of record: `GRILL.md` (decisions D-1..D-5, binding). This SPEC honors those
> decisions exactly; where the backlog reads broader than the grill, the grill wins.

---

## 1. Problem and context

dadaia-workspace now runs two agentic layers (constitution §0/§4/§8): Layer-1 interactive
orchestrators (`claude`/`codex`/`pi`) that drive workflow CLI verbs, and Layer-2 workflow
workers that run bounded prompts on `codex` or `pi`. The model-governance half of that
design is not yet built. Today:

- The Layer-2 model is a **discrete `<id>:<effort>` string** selected ad hoc on the CLI
  (`core/harness_models.py` + `cli/commands/lifecycle.py --model/--step-model`). There is
  **no named profile registry**, so an operator must memorize raw model ids and there is no
  stable, inspectable governance unit.
- There is **no operator-editable policy overlay** — per-workflow / per-step model choices
  cannot be saved; every run re-specifies flags.
- There is **no resolved-policy snapshot** persisted on a run, so a completed run cannot
  prove which model each step actually used (the `LifecycleRun` has prompt-observability
  fields but no governed policy object).
- The panel describes the dadaia-workflows (`features/workflows/dadaia_catalog.py`,
  `/api/dadaia-workflows`) but is **read-only**: no policy editor, no mutation API, and
  Workflows lives **subordinate to the Ops subtab** rather than as a first-class surface.
- There is **no doctor coverage** for policy/profile/harness consistency, so this governance
  layer would rot silently.

Without a governance layer, dadaia-workflows are powerful but opaque: the operator cannot
see, change, audit, or reproduce which model runs each prompt.

## 2. Objective

Ship a **workflow control plane** — a named model-profile registry, a validated
workspace-wide policy overlay, a single shared `WorkflowExecutionPolicyResolver`, a
persisted per-run policy snapshot, a first-class panel Workflows area with a guarded
policy editor + fragment inspector, and doctor coverage — built by **extending the
existing seams** (backlog §4.1 readiness verdict), not by inventing a parallel subsystem.

## 3. Approach — governance layer over existing seams (anti-slop)

This is the load-bearing framing. The repo already has the right seams (backlog §4.1):
`PipelineStep.model_profile`, `AgentRunRequest.model_profile`, the discrete
`harness_models` catalog, `CodexExecAdapter._model_and_effort()`,
`PiHeadlessConfig.model` + `pi --model`, atomic `JsonLifecycleRunStore`, the
`dadaia_catalog` panel surface, `render_dag_svg()`/`render_step_mermaid()`, and the
fragment `FragmentLoader`. This release **connects** those seams for governance:

- Profiles become **named ids** layered over the existing `harness_models` discrete
  catalog (a profile resolves to a `HarnessModelOption`), not a second drifting model table.
- The resolver feeds the **existing** `model_profile`/`model=...` adapter path — no new
  adapter transport. `pi --model` and `codex -m … -c model_reasoning_effort=…` are already
  wired through `container.build_agent_runtime(..., model=...)`.
- The panel policy surface extends the **existing** `dadaia_catalog` + `/api/dadaia-workflows`
  read path with read/validate/write routes; the diagram path reuses
  `render_dag_svg`/`render_step_mermaid`.
- The run snapshot extends the **existing** `LifecycleRun` dataclass + atomic store.

No prompt step ever reads policy JSON directly; the runner resolves+snapshots once before
the first step and threads resolved model data into each step (backlog §5.0).

## 4. Non-negotiable product laws (carried from GRILL.md / backlog §3)

1. **Layer-2 harness law.** Workflow workers are **only `codex` and `pi`**; `fake` is
   test-only; `claude` / `opencode` are rejected with actionable messages (already enforced
   by `_resolve_harness`; extended to contract tests + doctor on the policy/profile set).
2. **CLI selection law.** Every workflow run resolves a workflow execution policy:
   selected worker harness, per-step harness override where allowed, and per-step model
   **profile**.
3. **Registry law.** Allowed model choices are governed by a registry: harness, profile id,
   model id, reasoning level, purpose, availability, deprecation state. Workers never receive
   ungoverned free-text model strings (D-3).
4. **Default-first law.** Every step ships a library default; a workflow is runnable before
   any panel config exists. **Missing overlay = defaults** (≠ invalid overlay).
5. **Panel governance law.** Panel writes a **validated JSON overlay**, never Python source
   or projected agentic assets; security posture is the existing loopback bind + Host-header
   allowlist (no bearer auth), atomic temp+rename writes, last-good backup, and **invalid
   policy blocks execution**.
6. **Auditability law.** Each run records the resolved policy snapshot: harness, profile id,
   concrete model, reasoning, fragment ids, prefix hash, overlay id, policy source.
7. **Mid-run safety.** Policy is resolved + snapshotted once before the first step; an
   in-flight run ignores later panel edits.

## 5. Scope — whole epic A→D, sliced as four waves (D-1)

The epic ships in one release but is structured as four independently-testable waves, each
with its own acceptance and green checkpoint (see PLAN.md and TASKS.md). High-level scope:

### Slice A — model-policy foundation
- Named **model-profile registry** (built-in profiles only — D-2): Codex profiles +
  recommended PI aliases, each a `WorkflowModelProfile` resolving to a `harness_models`
  option. New `features/lifecycle/model_profiles.py`.
- **Policy overlay store** (`infrastructure/json_workflow_model_policy_store.py`) over
  `.dadaia/states/workflow_model_policy.json`, using the `JsonLifecycleRunStore`
  atomic temp+rename pattern, with a `.last-good.json` backup; **missing ≠ invalid**.
- **`WorkflowExecutionPolicyResolver`** (`features/lifecycle/policy_resolver.py`) with the
  precedence rule **CLI > context overlay > default overlay > library default**, honoring
  only the `default` context overlay this release (D-2).
- `ResolvedModelConfig` + `WorkflowPolicySnapshot` core models; `AgentRunRequest` carries a
  resolved model config; `LifecycleRun` persists a `workflow_policy` snapshot.
- CLI `--step-model` accepts **profile ids only** (D-3); `--show-policy` / `--json` print the
  resolved policy. Read-only `workflow policy show` / `workflow profiles list` inspection.
- The **implementation pipeline** is the first full end-to-end demo path (D-4): resolver +
  run snapshot are asserted against `dadaia lifecycle pipeline`.

### Slice B — Python workflow catalog (consolidate as the policy source)
- The dadaia-workflow catalog (`dadaia_catalog.py`) becomes the **governed** source for
  workflow id, step ids, roles, default harness, default profile per supported harness,
  fragment refs, and gates — extended from the existing introspection so the resolver and
  panel read one source.
- Diagrams remain generated from Python metadata (`render_dag_svg`/`render_step_mermaid`).
- Old `*.workflow.md` (`WorkflowsService.get_detail`) is **demoted to reference/doc-only**;
  it is no longer the authority for executable workflow behavior.

### Slice C — panel model-governance UX
- **First-class Workflows panel area** (D-5): promote Workflows to a top-level nav area;
  keep Agents/Kanban available during transition (do not delete the Ops subtab abruptly).
- Workflow detail: diagram + step matrix (Step | Role | Harness | Effective profile |
  Concrete model | Fragments | Gate), default-vs-effective distinction, run-snapshot
  evidence view.
- **Policy editor**: per-step profile dropdown filtered by harness, reset-to-default,
  validate-before-save, save through a guarded mutation API.
- **Panel mutation routes** (the handler currently has no PUT and a near-empty POST):
  `GET/PUT /api/workflow-model-policy`, `POST /api/workflow-model-policy/validate`,
  `GET /api/workflow-model-profiles`, `GET /api/workflow-catalog[/<id>]`,
  `GET /api/lifecycle-runs?workflow=&context=`. Mutation guardrails: JSON schema validation
  before write, atomic write, reject non-JSON content type, reject oversized payload,
  structured field-path errors, never expose secrets.

### Slice D — fragment inspector integration
- Each step links to its prompt-fragment bundle metadata (ids + resolved body via
  `FragmentLoader`); add a **read-only** fragment inspector (editing fragments stays
  source-controlled release work).
- Surface dynamic-context selectors + output schema per step.
- Doctor checks: every model step resolves its fragments and output schema; every policy
  override references an existing workflow/step/profile; profile harness matches the step
  harness; no `claude`/`opencode` in any product policy or profile.

## 6. Acceptance criteria (backlog §9, scoped by the grill)

- AC-1 The product CLI rejects Layer-2 `claude`/`opencode`; `codex`/`pi` are the only
  user-selectable Layer-2 worker harnesses (LAW 1).
- AC-2 Every workflow step has a default model **profile** for each supported harness, or an
  explicit "not supported on this harness" declaration.
- AC-3 `--step-model` accepts a **profile id** only (D-3); a raw `<id>:<effort>` string or an
  unknown/harness-mismatched/deprecated profile is rejected with an actionable message.
- AC-4 The resolver applies precedence CLI > context overlay > default overlay > library
  default; only the `default` context overlay is honored (D-2).
- AC-5 A panel policy edit persists to `.dadaia/states/workflow_model_policy.json` via atomic
  write, keeps a `.last-good.json` backup, and is validated before write.
- AC-6 The workflow runner reads the policy, resolves+snapshots it once before the first step,
  uses the selected profile's model for the selected step, and an in-flight run ignores later
  panel edits (LAW 7).
- AC-7 A run records the resolved `workflow_policy` snapshot (harness, profile id, concrete
  model, reasoning, fragment ids, prefix hash, overlay id, source) and exposes it via
  `GET /api/lifecycle-runs`. Historical run detail shows the model actually used, even after
  current policy changes.
- AC-8 The implementation pipeline (D-4) demonstrates AC-6/AC-7 end-to-end with `--harness
  fake` and asserted snapshot fields.
- AC-9 The panel workflow detail shows diagram, steps, roles, harnesses, effective profiles,
  concrete models, fragments, dynamic inputs, output schemas, and gates — including a
  default-vs-effective view — without reading Python source in the browser.
- AC-10 Doctor fails on: invalid policy JSON, unknown profile, harness/profile mismatch,
  stale workflow/step id in an override, and any `claude`/`opencode` Layer-2 policy residue.
- AC-11 Tests prove default policy, context (`default`) override, CLI override, invalid
  override (blocks execution, last-good intact), and reset-to-default behavior.
- AC-12 `PiHeadlessAdapter` receives the per-step resolved PI model and passes
  `pi --mode json --model <id>`; `CodexExecAdapter` receives the per-step resolved
  model/reasoning and passes `-m <id> -c model_reasoning_effort=<effort>`.
- AC-13 The first-class Workflows panel area is reachable; Agents and Kanban remain available
  during transition (D-5).
- AC-14 Read-only fragment inspector shows each model step's fragment ids/body, dynamic
  inputs, and output schema (Slice D).
- AC-15 The old `*.workflow.md` catalog is no longer the authority for executable workflow
  behavior (Slice B).
- AC-16 `pytest`, `ruff format --check`, `ruff check`, `mypy --strict` green; panel E2E green
  for the C/D waves.

## 7. Out of scope (explicit — D-2 deferrals + reserved seams)

- **Operator-added PI profiles** (`.dadaia/states/workflow_model_profiles.local.json`):
  NOT implemented. Built-in recommended profiles only. The store/schema MAY document the
  seam but MUST NOT load or validate operator `.local.json` profiles this release.
- **Per-context overlays + `extends` inheritance** (backlog §5.3): NOT implemented. The
  overlay schema MAY reserve the `contexts{}` shape, but only the `default` context is
  honored/validated; a non-`default` context key is ignored (or a clear "not yet honored"
  note) — never silently treated as active.
- **Raw one-shot concrete model id on `--step-model`** (D-3): rejected, not supported.
- **Live PI availability checks**: never mandatory for offline tests; out of scope as a gate.
- **Browser-side Mermaid as an execution dependency**: diagrams come from Python metadata;
  the existing mistune mermaid render path is reused, no new browser execution dependency.
- **Editing fragments from the panel**: fragment inspector is read-only.
- **Removing the `CLAUDE_SDK` enum/adapter** (Layer-1): untouched.
- **Renaming/relocating `dadaia lifecycle` to `dadaia workflow`**: the backlog leaves the
  command surface open; this release keeps the existing `dadaia lifecycle` verbs and adds the
  policy inspection subcommands under that group (final top-level rename is out of scope).

> These deferrals do **not** correspond to declared backlog `intents[]`. The four
> frontmatter intents (pipeline resolver, run-store policy snapshot, PI per-request model,
> panel policy routes) all map into Slices A and C above, so the backlog item is **fully
> consumed by its declared intents** — hence the `**Consumes:**` line. The deferrals are
> design breadth from §5.2-5.3/§11, recorded here as scope boundaries. At CLOSURE, if the
> operator wants the deferred breadth tracked, file a follow-up backlog item
> (`workflow-model-governance-operator-profiles-and-context-overlays`).

## 8. Memory files affected at closure

- `specs/memory/architecture.md` — the workflow control-plane layer (profile registry →
  policy store → resolver → run snapshot → panel routes) and the resolver as the single
  policy seam shared by CLI and panel.
- `specs/memory/product/index.md` — catalog touch if a "Workflow control plane" feature atom
  is added.
- `specs/memory/product/<workflow-control-plane>.md` — new/updated feature atom (decided at
  closure).
- `specs/memory/tech-stack.md` — likely no change (no new dependency); confirm at closure.

## 9. Dependencies and risks

Builds directly on v0.1.24 (two-layer redesign, `harness_models`, `dadaia_catalog`) and the
fragment library / dadaia-workflows. No upstream blocker; branch `feature/v0.1.28` descends
from v0.1.27 @ 44b3109.

| Risk | Mitigation |
|---|---|
| Profile registry becomes a second drifting model table | A profile resolves to a `harness_models` option; an import-time assert ties every profile model id to the registry (mirror `_assert_ids_known`). |
| Free-text model strings create broken runs | Profile ids only (D-3); CLI + panel + doctor reject non-profile / mismatched / deprecated. |
| Panel writes corrupt policy state | JSON schema validation before write, atomic temp+rename, `.last-good.json` backup, doctor checks; invalid blocks execution (missing ≠ invalid). |
| Mid-run policy mutation changes behavior | Resolve+snapshot once before the first step; in-flight run ignores later edits (LAW 7). |
| Old run evidence misleading after edits | Panel reads the persisted run snapshot for history; current policy only for future runs. |
| CLI and panel resolve policy differently | One shared `WorkflowExecutionPolicyResolver` consumed by both. |
| Scope creep into deferred breadth | §7 hard boundaries; `default`-only overlay; built-in profiles only. |
| Panel handler has no PUT and a near-empty POST | Slice C adds body-reading mutation dispatch with content-type/size guards and structured errors; covered by route-registration + validation tests. |
