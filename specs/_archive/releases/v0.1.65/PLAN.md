# PLAN — Release v0.1.65 — L1 Agent Model Governance & Panel Sub-agents Tab

> **Status:** Aprovado
> **Release ID:** v0.1.65
> **Owner:** product-engineer
> **Branch:** `feature/v0.1.65`

## Strategy

Mirror the Layer-2 model-governance stack (profiles → overlay store → single resolver →
per-run consumption) onto Layer-1, with one structural adaptation forced by import-linter
(SPEC D-4): **templates + resolver are pure core data/functions** (the install pipeline is
`infrastructure/`, which may only import `core/`), while the panel-facing service stays in
`features/` with the store injected via DI. Build bottom-up: registry → core policy model →
store → render seam → projections → doctor → panel → tests/goldens → instance propagation.
The two LOW bugs are independent, disjoint-write-set fixes that run in parallel with the
core wave.

## New modules

| Module | Layer | Content |
|---|---|---|
| `dadaia_workspace/core/models/agent_model_policy.py` | core (pure) | `ClaudeEffort` literal (`low\|medium\|high\|xhigh\|max`), `AgentModelAssignment(model, effort)`, `AgentModelTemplate(id, label, default, assignments)`, `AgentModelPolicyOverlay(applied_template, overrides)`, `ResolvedAgentModel(model, effort, source)`, typed store error, `_SCHEMA_VERSION = "agent-model-policy-v1"`, D-3 clamp map `codex_effort_for_claude_effort()` |
| `dadaia_workspace/core/agent_model_templates.py` | core (pure) | `_BUILT_IN` 3 templates (SPEC FR2 table verbatim), import-time `_assert_templates_resolve()` (9-agent coverage, registry-known models, effort vocab, never-Fable-on-security, unique ids, balanced default), `list_templates()`, `default_template()`, `resolve_agent_model(agent, overlay, *, pack_default=None)` — the ONLY precedence implementation (FR4) |
| `dadaia_workspace/public/schemas/agent-model-policy-v1.schema.json` | asset | JSON Schema for FR3 shape (enum efforts; `additionalProperties: false` at every level) |
| `dadaia_workspace/infrastructure/json_agent_model_policy_store.py` | infrastructure | `JsonAgentModelPolicyStore` at `.dadaia/states/agent_model_policy.json`; mirrors `json_workflow_model_policy_store.py`: `load()` (missing→`None`; invalid→typed error), `parse()` (shared with validate endpoint), `save()` (atomic temp+rename + `.last-good.json`); parse enforces FR3 hard errors incl. D-7 |
| `dadaia_workspace/features/agents/model_policy.py` | features | Panel-facing service: `get_policy()`, `validate(raw)`, `apply(raw) -> rerender summary`, `templates_payload()`, `resolved_roster()`; store + re-render callable injected (protocol/DI per `features-no-infrastructure`); re-render wired in `container.py` to the agents-only install path |
| `dadaia_workspace/features/panel/views/agent_policy.py` | features | GET/PUT/POST endpoint renderers mirroring `views/workflow_policy.py` (415/413/400 pipeline, Host guard) |
| `dadaia_workspace/features/panel/views/assets/js/agent_policy.js` + scoped CSS | features asset | Sub-agents tab UI (roster table, pickers, template select, Apply, post-apply pop-up) |

## Touched modules

| Module | Change |
|---|---|
| `core/model_registry.py` | FR6: add `claude-sonnet-5` entry (D-2). No other entries touched |
| `public/agents/*.md` (9 core) | FR1: delete `model:` / `effort:` frontmatter lines only — body text untouched |
| `public/plugins/*/agents/*.md` (3) | D-5/G-4: `model: claude-sonnet-4-6` → `claude-sonnet-5` |
| `features/agents/reader.py` | FR1: tolerate model-less/effort-less generic body (keep keys allowlisted; no new warnings for their absence) |
| `infrastructure/install_helpers.py` | FR5: new `render_claude_agent(staged_text, resolved) -> str` seam (deterministic `model:`+`effort:` injection as last frontmatter lines; `effort:` OMITTED when unresolved — plugin asymmetry, F-6); `install_codex_agents` takes resolved policy and **fails closed for core agents** when neither a staged `model:` nor a resolved policy model is supplied (F-3 — the silent `claude-sonnet-4-6` default at l.375, and its twin `public_assets.py::_codex_toml_from_md` l.274, removed for core agents; kept for plugin bodies that legitimately author `model:`); `--force` re-RENDERS, never re-copies staged bytes (F-5 — under render only the `content` argument of `write_generated` changes); core-agent claude install switches `copy_file` → render + `write_generated` |
| `infrastructure/runtime_transforms/codex_assets.py` | FR5/D-3: `model_reasoning_effort` from resolved effort via clamp map (agent TOML path); tier-derivation retained only for surfaces without a resolved policy (persona tier table) |
| `infrastructure/public_assets.py` | FR5/FR7: load overlay once per install/doctor run; thread resolved policy into claude/codex agent install and plugin-pack agent projection; agents-only re-render entry for panel Apply (existing `only == "agents"` path). **Doctor interception pinned (F-2):** the ONLY doctor compare change is inside the `runtime_expectations` loop (~l.686-718) — non-plugin `claude:agents/*.md` labels route to a content compare against `render(staged generic + resolved policy)`, reusing the existing plugin-stem exclusion at l.706-712; `stage:agents/*.md` (generic↔generic) and every non-agent label stay on the raw `_compare` path; never patch `_compare` globally. **No `codex_doctor.py` change (F-1)** — codex TOML correctness is install-time-asserted (T-65-08 lockstep), not doctor-byte-compared |
| `features/public/service.py` + `features/public/model_resolution.py` | FR7: doctor validates resolved policy (registry + vocab; invalid overlay = ERROR, missing = ok) + plugin staged models; key-set coherence unchanged |
| `features/panel/handler.py` | FR8: routes (`GET/PUT /api/agent-model-policy`, `GET /api/agent-model-templates`, `POST /api/agent-model-policy/validate`), static JS registration, **recompute `_CSP_SCRIPT_HASH_*` if any inline script changes** |
| `features/panel/views/index.py` | FR8: nav tab button + `section-subagents` panel section |
| `container.py` | wire store, service, re-render callable |
| `features/backlog/preview.py` + `features/backlog/doctor.py` | FR10: `frontmatter_error` capture (YAML message + mark line/col) + dedicated BL-SCHEMA finding, suppressing downstream no-intents/unresolved findings for that item |
| `tests/e2e/panel/workflow-policy-harness-toggle.spec.ts` | FR11: `waitForResponse` on save PUT; restore PUTs assert 200; tolerate omitted empty `workflows` |
| `tests/contract/test_agent_tier_taxonomy.py` | FR9 rework (template pinning) |

## Execution order

1. **W1 (foundation, core):** registry entry → core models + templates + resolver →
   schema JSON → store. Everything else consumes these.
2. **W2 (bugs, parallel with W1 — disjoint write sets):** FR10, FR11.
3. **W3 (sources + projection):** generic agent sources + reader tolerance → render seam +
   claude render-at-install → codex resolved-effort projection → policy-aware doctor +
   model-resolution rework.
4. **W4 (panel):** feature service + container wiring → endpoints → UI tab (JS/CSS/CSP)
   → panel e2e specs.
5. **W5 (contract + golden tail):** contract-test rework → golden/AC re-verification
   sweep → full local gates.
6. **W6 (instance propagation):** `dadaia public stage/install/doctor` on this workspace +
   live panel manual verification (source-vs-instance law).

## Test plan

- **Unit:** registry entry invariants (`test_model_registry`, mapping/pricing derived
  views); template asserts (coverage, never-Fable-on-security, unknown-model failure);
  resolver precedence matrix (no overlay / template only / per-field override / plugin
  pack default) incl. AC-3 case; store (missing vs invalid, atomic write, last-good,
  every FR3 rejection); render seam (deterministic injection; `effort:` omitted when
  unresolved — plugin pack-default path, F-6; idempotent hash-compare; `--force`
  re-renders rather than re-copying staged bytes, F-5); fail-closed core codex render —
  RED test asserting the loud raise when no resolved model is supplied for a core agent
  (F-3); codex effort clamp map; backlog loader/doctor FR10 (repro fixture with unquoted
  colon — RED first); panel view handlers (status codes, validation pipeline, PUT triggers
  re-render callable).
- **Contract:** reworked `test_agent_tier_taxonomy.py` (FR9 pins a–g) + AC-7
  mutation-sanity one-off verification.
- **Integration:** `tests/integration/test_public_assets.py` — install renders balanced
  by default; overlay changes both projections in lockstep (this lockstep test IS the
  codex-correctness assurance — F-1: no doctor byte-compare exists for codex TOML);
  doctor `[ok]` after Apply, `[drift]` on hand-edited `.claude/agents/*.md`, and
  non-agent stage/runtime lines stay `[ok]` (AC-5, F-2).
- **Goldens (check, update only for genuinely changed truth):**
  `tests/unit/features/panel/_golden/api_golden_v0155.json`,
  `tests/unit/infrastructure/_golden/panel_runtime_validation_v0158.json`,
  `tests/unit/infrastructure/test_install_target_goldens.py`, plus every file found by
  `grep -rl "claude-fable-5\|claude-opus-4-8\|claude-sonnet-4-6" tests/` (16 files known
  at spec time — incl. `test_reader.py`, `test_public_assets.py`, `test_api_agents.py`,
  `test_claude_sdk_runtime.py`).
- **E2E (Playwright, `tests/e2e/panel/`):** new `agent-policy.spec.ts` (tab renders
  roster; template select + Apply round-trips PUT/GET; post-apply pop-up; restore clean
  overlay before/after — apply FR11's deterministic-wait pattern from day one); hardened
  `workflow-policy-harness-toggle.spec.ts` (FR11).
- **Static gates:** `ruff format --check`, `ruff check`, `mypy --strict`, `lint-imports`
  (all contracts, esp. `features-no-infrastructure`, `infrastructure-no-upper-layers`,
  `core-no-os-primitives` — core additions are pure), `pytest` full.

## Risks & mitigations

1. **Doctor/manifest seam (highest).** False `[drift]` after Apply, or doctor blind to
   hand-edits. Mitigation: D-6 single render seam consumed by install-write AND
   doctor-compare; interception site PINNED to the `runtime_expectations` loop branch
   for non-plugin `claude:agents/*.md` labels (F-2 — never a global `_compare` patch);
   AC-5 asserted in both directions plus the non-agent-lines-stay-`[ok]` assertion.
   Manifest keeps hashing staged bytes — no manifest schema change. Doctor render-compare
   scope is claude-md-only by design (F-1).
2. **Import-linter violations.** Resolver in core (D-4); panel service takes the store via
   DI; run `lint-imports` in the wave, not only at the tail.
3. **Golden churn.** Agent frontmatter appears in api/panel/install goldens. Law: goldens
   change only to reflect genuinely changed rendered truth; never re-baseline to silence a
   failure; triage each diff at merge-base.
4. **CSP hash trap.** Any inline-script edit in the panel requires recomputing
   `_CSP_SCRIPT_HASH_1/2`; e2e catches a miss (blank panel).
5. **Live-instance retier at propagation (D-1).** Operator-ratified; called out in the
   propagation task's completion note.
6. **Plugin-pack projection interplay.** Pack agents render through the same resolver
   path (override > pack default); plugin uninstall/restore flows must keep using the
   render seam for stub restore comparison — covered in integration tests.

## Rollback

- Panel/API + store are additive; disabling = removing routes/tab (no data migration —
  the overlay file is ignorable state; deleting `.dadaia/states/agent_model_policy.json`
  returns the fleet to `balanced`).
- FR1 is the only destructive source change; rollback = `git revert` of the release
  branch (staged bodies and render seam revert together — projections regenerate from
  either state via `dadaia public install`).
- Registry entry FR6 is append-only; safe to keep even on rollback.
- Bug fixes FR10/FR11 are independent and never rolled back with the feature.

## Revision log

- 2026-07-07 — Plan authored; `**Status:** Aprovado`.
- 2026-07-07 — Architect review REVISE folded (report:
  `.dadaia/reports/dadaia-workspace/software-architect/2026-07-07T200000Z-review-v0165-definition.md`):
  F-1 codex doctor scope corrected (install-time lockstep assurance; no `codex_doctor.py`
  work); F-2 doctor interception site pinned to the `runtime_expectations` loop branch;
  F-3 fail-closed core codex render + RED test; F-5 `--force` re-renders; F-6 plugin
  `effort:` omission in the render seam + resolver test. Status remains Aprovado — fold
  of an approved review, no scope change.
