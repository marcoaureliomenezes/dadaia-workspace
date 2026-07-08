---
name: l1-agent-model-governance-panel
status: candidate
opened: 2026-07-07
owner: project-manager (curates)
source: "operator demand 2026-07-07 (major new capability) — mirror the proven Layer-2 workflow model-governance architecture for Layer-1 sub-agents so operators can retier agents without a library deploy"
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/agents/reader.py#read_canonical_agents" }
    change: "make the generic-agent-source change legible in the canonical reader: the 12 `public/agents/*.md` bodies drop their hardcoded `model:`/`effort:` frontmatter and become model-agnostic templates (name, description, dispatch_band, tools, skills, write_allowlist stay). `read_canonical_agents` (and the DTO path it drives) must therefore stop treating `model:` as an authoritative source-of-truth frontmatter key — a resolved (model, effort) pair is now composed into the PROJECTED `.claude/agents/*.md` at install time from policy, not read from the staged generic body. `effort` becomes a first-class rendered field: `effort: low|medium|high|xhigh|max` is officially-supported Claude Code agent frontmatter that overrides session effort. The reader/DTO/allowlist must tolerate a generic body that carries neither `model:` nor `effort:`. (NOTE: does not touch the `_raw_to_dto` legacy `tier:` fallback owned by `dispatch-band-legacy-fallback-removal` — that strip is a separate, sequenced concern.)"
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/model_profiles.py#_BUILT_IN" }
    change: "build the Layer-1 built-in template registry as the direct analog of this Layer-2 `_BUILT_IN` profile tuple: a library-shipped set of 3 named agent-model templates, each a full 9-core-agent map of (model, effort). `balanced` (DEFAULT): project-manager=claude-fable-5/high, software-architect=claude-fable-5/high, product-engineer=claude-opus-4-8/high, project-auditor=claude-opus-4-8/xhigh, security-reviewer=claude-opus-4-8/xhigh, code-reviewer=claude-opus-4-8/high, ai-engineer=claude-sonnet-5/high, software-engineer=claude-sonnet-5/xhigh, qa-engineer=claude-sonnet-5/high. `subscription-saver` (zero Fable): project-manager=opus-4-8/high, software-architect=opus-4-8/high, security-reviewer=opus-4-8/high, all others claude-sonnet-5 (software-engineer/product-engineer/project-auditor/code-reviewer xhigh, rest high). `max-quality`: fable-5/high on project-manager+software-architect+product-engineer+project-auditor, opus-4-8/xhigh on security-reviewer+code-reviewer, opus-4-8/medium ai-engineer, opus-4-8/high qa-engineer, sonnet-5/xhigh software-engineer. HARD CONSTRAINT baked into all templates: claude-fable-5 is NEVER assigned to security-reviewer (its cyber-safety classifiers can refuse security-review-shaped work). Plugin agents (frontend-engineer, design-specialist, devops-engineer) are NOT in the core templates; when a pack is installed its agents get a pack-provided default (claude-sonnet-5) plus the same per-agent override capability."
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/json_workflow_model_policy_store.py#JsonWorkflowModelPolicyStore" }
    change: "build the operator overlay store `.dadaia/states/agent_model_policy.json` as the direct analog of this Layer-2 workflow-policy store: new schema `agent-model-policy-v1` (a JSON Schema authored under `public/schemas/`) holding {applied_template, per-agent overrides {model, effort}}. Mirror the atomic-write + `.last-good.json` backup discipline this store already implements. Pair it with a single resolver whose precedence is: per-agent overlay override > applied template > library default template (`balanced`)."
  - subject: { kind: code, ref: "dadaia_workspace/features/public/service.py#PublicAssetService" }
    change: "make `install` render, not copy: it must compose the staged generic agent body + the resolver's resolved (model, effort) into `.claude/agents/<name>.md` AND feed the SAME resolved config to the Codex projection — one policy, both Layer-1 harnesses. Make `doctor` policy-aware: it must compare each projected agent file against render(staged generic body + resolved policy), NOT against raw staged bytes — otherwise every operator policy change reads as drift. The manifest hash contract for agent assets must account for the policy input so a policy-driven render is not a false `[drift]`."
  - subject: { kind: code, ref: "dadaia_workspace/features/public/model_resolution.py#check_model_resolution" }
    change: "the public-doctor model-resolution check must validate the RESOLVED model/effort composed from policy (per the resolver precedence overlay > template > balanced), not the model as literally written in a staged generic body that no longer carries one. It resolves against the registry — which requires the registry gap below to be closed first."
  - subject: { kind: code, ref: "dadaia_workspace/core/model_registry.py#REGISTRY" }
    change: "close the model-registry gap: add `claude-sonnet-5` to REGISTRY (API pricing $3/$15 per MTok; the codex-id mapping and registry Tier to be decided at spec time). The templates above assign claude-sonnet-5 to several core roles, so it must be a registry-known claude_id or `check_model_resolution` fails. Facts to record for spec judgment: Sonnet 5 draws ~5x less subscription limit than Opus and beats Opus 4.8 on Terminal-Bench (80.4 vs 74.6); Opus 4.8 is stronger on deep-review/security/audit judgment; claude-fable-5 is expensive ($10/$50) and reserved for strategic-judgment roles."
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py#_codex_reasoning_effort_for_model" }
    change: "the Codex projection must consume the SAME resolved policy as the Claude projection: `.codex/agents/*.toml` gets its codex model id via `core/model_registry.py` mapping and its `model_reasoning_effort` DERIVED FROM THE RESOLVED EFFORT (low|medium|high|xhigh|max) rather than tier-only. Today this helper derives effort from the model/tier alone; it must instead honor the per-agent resolved effort from the overlay/template so a policy change moves both L1 harnesses in lockstep."
  - subject: { kind: code, ref: "dadaia_workspace/features/panel/views/workflow_policy.py#render_api_workflow_model_profiles" }
    change: "add a new panel `Sub-agents` tab (alongside Workflows) whose endpoints mirror these Layer-2 workflow-policy views: GET/PUT `/api/agent-model-policy`, GET `/api/agent-model-templates`, POST `/api/agent-model-policy/validate`. The tab is a roster table with per-agent model + effort pickers and a template selector, plus an explicit Apply button — PUT validates + saves the overlay + triggers a re-render of BOTH L1 projections, then shows a post-apply pop-up with per-harness instructions: Claude Code sessions pick up the changed `.claude/agents/*.md` automatically within seconds (next delegation uses the new definition — officially documented at code.claude.com/docs/en/sub-agents; the only exception is a brand-new agents dir created mid-session, which needs a restart), whereas Codex sessions must be restarted."
---

# BACKLOG — Layer-1 agent model governance + panel Sub-agents tab

**Priority:** HIGH (major new capability). Layer-1 sub-agent `model:` and `effort:` are
today **hardcoded** in `dadaia_workspace/public/agents/*.md` frontmatter and copied verbatim
by stage/install. An operator cannot change a sub-agent's model or effort without a library
deploy. Layer 2 (dadaia-workflows) already has full panel-managed model governance — profile
registry, operator overlay store, single policy resolver, per-run snapshot; **Layer 1 has
none.** This item mirrors the proven Layer-2 architecture for the Layer-1 agent roster so the
operator retiers agents live from the panel.

## The mirrored architecture (Layer-2 → Layer-1)

1. **Generic agent sources.** `public/agents/*.md` drop hardcoded `model:`/`effort:`; the
   bodies become model-agnostic templates (name, description, dispatch_band, tools, skills,
   write_allowlist stay). The (model, effort) pair is composed at install, not authored in the
   body. Anchor: `features/agents/reader.py#read_canonical_agents`.
2. **Built-in template registry** — the library analog of `model_profiles.py#_BUILT_IN`: 3
   named templates (`balanced` DEFAULT, `subscription-saver`, `max-quality`), each a full
   9-core-agent map of (model, effort). Exact maps live in the intents above. Plugin agents
   are out of the core templates; an installed pack supplies a `claude-sonnet-5` default plus
   the same override capability.
3. **Operator overlay JSON** — `.dadaia/states/agent_model_policy.json`, new schema
   `agent-model-policy-v1` under `public/schemas/`, `{applied_template, per-agent overrides
   {model, effort}}`, atomic write + `.last-good.json` backup, mirroring
   `json_workflow_model_policy_store.py#JsonWorkflowModelPolicyStore`.
4. **Single resolver** — precedence: per-agent overlay override > applied template > library
   default template (`balanced`).
5. **Render at install** — `PublicAssetService.install` composes staged generic body +
   resolved (model, effort) → `.claude/agents/<name>.md`, and feeds the SAME resolved config
   to the Codex projection. One policy, both L1 harnesses.
6. **Model registry gap** — `claude-sonnet-5` must be added to
   `core/model_registry.py#REGISTRY` ($3/$15 per MTok; codex mapping + Tier decided at spec
   time). The templates reference it, so `check_model_resolution` fails until it is registered.
7. **Panel `Sub-agents` tab** — roster table with per-agent model+effort pickers + template
   selector + explicit **Apply** → PUT validates + saves overlay + re-renders both projections
   → post-apply pop-up with per-harness restart guidance. Endpoints mirror the L2
   workflow-policy views (GET/PUT `/api/agent-model-policy`, GET `/api/agent-model-templates`,
   POST `/api/agent-model-policy/validate`).
8. **Policy-aware doctor** — `public doctor` compares projected agent files against
   render(staged generic + resolved policy), not raw staged bytes, else every policy change
   reads as `[drift]`; the manifest hash contract for agent assets must account for the policy
   input. Anchors: `features/public/service.py#PublicAssetService`,
   `features/public/model_resolution.py#check_model_resolution`.
9. **Effort vocabulary** — `effort: low|medium|high|xhigh|max` is officially-supported Claude
   Code agent frontmatter (overrides session effort) and is now a rendered field.

## Hard constraints / facts to preserve at spec time

- **Fable 5 must NEVER be assigned to `security-reviewer`** — its cyber-safety classifiers can
  refuse security-review-shaped work. Every template must honor this.
- **Fable 5 is expensive ($10/$50)** and reserved for strategic-judgment roles.
- **Sonnet 5** draws ~5x less subscription limit than Opus and beats Opus 4.8 on Terminal-Bench
  (80.4 vs 74.6); **Opus 4.8** is stronger on deep-review / security / audit judgment.
- **Contract-test rework (not anchored — a consequence).** The pinned contract test
  `tests/contract/test_agent_tier_taxonomy.py` currently hardcodes today's (model, effort)
  roster and must be reworked to pin **template contents** instead (the per-agent maps of the
  3 built-in templates), since the roster is no longer fixed in the frontmatter. This lands in
  the release's TASKS as a required test-plan item; it is not a backlog anchor because the
  `code` anchor kind resolves against the `dadaia_workspace/` source root only.

**Anchors:** `features/agents/reader.py#read_canonical_agents`,
`features/lifecycle/model_profiles.py#_BUILT_IN` (pattern mirrored),
`infrastructure/json_workflow_model_policy_store.py#JsonWorkflowModelPolicyStore` (pattern
mirrored), `features/public/service.py#PublicAssetService`,
`features/public/model_resolution.py#check_model_resolution`,
`core/model_registry.py#REGISTRY`,
`infrastructure/runtime_transforms/codex_assets.py#_codex_reasoning_effort_for_model`,
`features/panel/views/workflow_policy.py#render_api_workflow_model_profiles` (pattern mirrored).
</content>
