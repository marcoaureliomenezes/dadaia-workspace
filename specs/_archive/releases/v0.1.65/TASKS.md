# TASKS — Release v0.1.65 — L1 Agent Model Governance & Panel Sub-agents Tab

> **Status:** Aprovado
> **Release ID:** v0.1.65
> **Owner:** product-engineer
> **Branch:** `feature/v0.1.65`

Markers: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. Max one `[-]` per owner unless the
tasks declare disjoint write sets (W1 vs W2 are declared parallel-safe). Every code task
is **RED-first**: write/extend the failing test before the production change, and name the
RED test in the completion commit. Implementation-complete is not DONE — QA/code/security
review gates per release-governance cadence.

All paths are repo-relative (`repos/dadaia-workspace/`).

---

## Wave 1 — Foundation (core + store) — owner: software-engineer

- [x] **T-65-01 — `claude-sonnet-5` registry entry (FR6, D-2)**
  Completion note: RED `test_sonnet_5_entry_present_with_expected_mapping_tier_and_pricing`
  (+ mapping/pricing derived-view REDs) captured failing before the registry edit; all
  registry-consuming suites green after.
  Write set: `dadaia_workspace/core/model_registry.py`,
  `tests/unit/core/test_model_registry.py`,
  `tests/unit/infrastructure/runtime_transforms/test_model_mapping.py`,
  `tests/unit/features/telemetry/test_pricing.py`.
  Precondition: none.
  RED: registry test asserting `claude-sonnet-5` → (`gpt-5.3-codex`, tier `plugin`,
  pricing 3.00/15.00/3.75/0.30 effective 2026-07-01).
  Done when: entry added; `registry_by_claude_id`/`codex_tier_views` invariants pass;
  derived MODEL_MAP/PRICING_TABLE tests updated. Parallel: safe with W2.

- [x] **T-65-02 — Core policy model + template registry + resolver (FR2, FR4, D-3, D-4)**
  Completion note: RED captured as collection failure (ModuleNotFoundError) of
  `tests/unit/core/test_agent_model_templates.py` before the core modules existed;
  28 tests green after (template asserts, D-3 clamp table, FR4 precedence matrix incl.
  AC-3 merge + F-6 pack asymmetry). mypy/ruff/lint-imports (9 kept / 0 broken) green.
  Write set: `dadaia_workspace/core/models/agent_model_policy.py` (new),
  `dadaia_workspace/core/agent_model_templates.py` (new),
  `tests/unit/core/test_agent_model_templates.py` (new).
  Precondition: T-65-01.
  RED: template-assert tests (9-agent coverage, never-Fable-on-security, unknown model
  fails at import) + resolver precedence matrix incl. AC-3 (template model + per-field
  override merge) + plugin `pack_default` path (incl. F-6 asymmetry: pack default with
  no override resolves model only — effort unresolved/`None`, never a placeholder) +
  D-3 clamp map table.
  Done when: FR2 table encoded verbatim; `resolve_agent_model` is the only precedence
  implementation; module is pure (no I/O; `core-no-os-primitives` holds).
  Parallel: safe with W2.

- [x] **T-65-03 — Schema + overlay store (FR3, D-7)**
  Completion note: RED captured as collection failure of
  `tests/unit/infrastructure/test_json_agent_model_policy_store.py` before the store
  existed; 21 tests green after (missing→None ≠ invalid→typed error, every FR3
  rejection distinct, D-7 Fable-on-security via the resolver, atomic write +
  `.last-good.json` prior-file snapshot, shared no-I/O `parse()`).
  Write set: `dadaia_workspace/public/schemas/agent-model-policy-v1.schema.json` (new),
  `dadaia_workspace/infrastructure/json_agent_model_policy_store.py` (new),
  `tests/unit/infrastructure/test_json_agent_model_policy_store.py` (new).
  Precondition: T-65-02.
  RED: store tests — missing→`None`; each FR3 rejection (unknown key/agent/model/effort/
  template, Fable-on-security) raises the typed error with a distinct message; atomic
  write + `.last-good.json` snapshot of the prior valid file; `parse()` shared no-I/O path.
  Done when: mirrors `json_workflow_model_policy_store.py` discipline; schema has
  `additionalProperties: false` at every level. Parallel: safe with W2.

## Wave 2 — Bug fixes (parallel with Wave 1 — disjoint write sets)

- [x] **T-65-04 — backlog doctor YAML parse misdiagnosis (FR10)** — owner: software-engineer
  Completion note: RED captured — repro fixture (unquoted `source: text (note: …)` +
  valid `intents[]`) failed 4 tests before the fix
  (`tests/unit/features/backlog/test_frontmatter_yaml_parse_error.py`). After: loader
  captures `frontmatter_error` (YAML problem + mark, file-line corrected +1 for the
  opening `---`); doctor emits `frontmatter YAML parse error: … (line L, column C)` and
  suppresses downstream no-intents/unresolved/status findings for that item; all
  pre-existing backlog integration suites green untouched (16 passed).
  Write set: `dadaia_workspace/features/backlog/preview.py`,
  `dadaia_workspace/features/backlog/doctor.py`,
  `tests/unit/features/backlog/` (loader + doctor tests).
  Precondition: none.
  RED: fixture reproducing the bug (unquoted `source: text (note: more text)` + valid
  `intents[]`) asserting the finding is `frontmatter YAML parse error: ... (line L,
  column C)` and that NO `no intents[] declared` finding is emitted for that item.
  Done when: `BacklogItem.frontmatter_error` captured (YAMLError message + problem-mark
  when available); downstream no-intents/unresolved findings suppressed for that item;
  existing well-formed-file findings byte-identical (regression tests untouched and green).

- [x] **T-65-05 — e2e harness-toggle flake hardening (FR11, D-8)** — owner: qa-engineer
  Write set: `tests/e2e/panel/workflow-policy-harness-toggle.spec.ts`
  (+ `tests/e2e/panel/helpers.ts` only if a shared save-wait helper is extracted).
  Precondition: none.
  Done when: save click is preceded by an armed `waitForResponse` on
  `PUT /api/workflow-model-policy` (200) and the GET runs only after it resolves;
  `restoreEmptyOverlay` asserts 200; assertions tolerate the omitted empty `workflows`
  shape; 20/20 consecutive local runs green (record the loop command + tally in the
  completion note). If a server-side cause is proven instead, STOP and report to
  product-engineer before widening the write set (drift protocol).

## Wave 3 — Sources + projection (sequential) — after W1

> **RED-window discipline (review F-7, never-push-red).** T-65-06 deliberately leaves
> the contract test + goldens RED until T-65-08/T-65-13 restore green. Across the
> T-65-06 → T-65-13 window: **no `git push`, no alpha-N QA review boundary, and no
> security-verdict push-cycle may occur.** QA review runs only after T-65-13. Commits on
> the feature branch are fine (commits are never review-blocked); the push boundary is
> what must stay outside the window.

- [x] **T-65-06 — Generic agent sources (FR1, D-5)** — owner: ai-engineer
  — done 2026-07-08; AC-1 greps clean; suite RED as declared (4 expected failures:
  `test_reader.py::test_all_public_agents_have_model_and_skills`,
  `test_agent_tier_taxonomy.py` ×2, `test_plugin_content.py::test_every_pack_agent_carries_required_frontmatter`)
  — RED window T-65-06→T-65-13 in effect: no push / no QA boundary / no security push-cycle.
  Write set: `dadaia_workspace/public/agents/*.md` (9 core — delete `model:`/`effort:`
  frontmatter lines ONLY), `dadaia_workspace/public/plugins/*/agents/*.md` (3 — model →
  `claude-sonnet-5`).
  Precondition: T-65-01 (sonnet-5 registry-known).
  Done when: AC-1 grep clean on core bodies; no other frontmatter or body text changed;
  plugin bodies keep `dispatch_band: 3`. NOTE: contract test + goldens go RED here and
  stay RED until T-65-08/T-65-13 — expected, declared in the commit message, and governed
  by the Wave-3 RED-window discipline note above (F-7: no push / QA boundary /
  security push-cycle inside the window).

- [x] **T-65-07 — Reader tolerance (FR1)** — owner: software-engineer
  Completion note: RED captured —
  `test_model_and_effort_stay_allowlisted_on_projected_body` failed with
  `unknown frontmatter fields ['effort'] — dropping` before the fix; fix = `effort`
  added to the reader `_ALLOWED_FIELDS` allowlist (model already tolerated absent →
  DTO `model=None`, covered by the new `test_model_less_effort_less_generic_body_reads_clean`).
  `test_all_public_agents_have_model_and_skills` reworked to FR1 truth (staged core
  bodies model-agnostic; skills mandatory). Legacy `tier:` fallback untouched.
  54/54 reader tests green; mypy --strict + ruff clean.
  Write set: `dadaia_workspace/features/agents/reader.py`,
  `tests/unit/features/agents/test_reader.py`.
  Precondition: T-65-06.
  RED: reader test for a model-less + effort-less generic body (no warning, DTO
  `model=None`).
  Done when: `model`/`effort` stay allowlisted; no unknown-field warning regression; the
  legacy `tier:` fallback untouched.

- [x] **T-65-08 — Render-at-install, both harnesses (FR5, D-3, D-6)** — owner: software-engineer
  Completion note: RED captured — `tests/unit/infrastructure/test_render_at_install.py`
  collection ImportError (seam absent) + 3 integration REDs (balanced lockstep,
  overlay lockstep + byte-stable [skip], invalid-overlay loud fail-before-write).
  Implemented: `render_claude_agent` D-6 seam (model: then effort: as last
  frontmatter lines; strips authored model/effort; effort OMITTED when unresolved —
  F-6); `install_claude_agents` renders core agents via `write_generated` (F-5:
  --force re-renders — asserted); codex projection consumes the SAME resolved config
  via `resolve_codex_agent_model` (D-3 clamp; F-3 fail-closed `PublicAssetError` for
  a core agent with neither staged nor resolved model — RED unit tests on both
  `install_codex_agents` and `_codex_toml_from_md`); overlay loaded ONCE per install
  run; pack agents render override>pack-default across install/plugin-install/
  uninstall; `test_plugin_content` restored to sonnet-5. Known interim RED handed to
  T-65-09: doctor still raw-compares `claude:agents/*` (2 integration doctor-surface
  failures + doctor goldens) — closed by the T-65-09 render-compare. mypy --strict +
  ruff + lint-imports (9 kept / 0 broken) green.
  Write set: `dadaia_workspace/infrastructure/install_helpers.py`,
  `dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py`,
  `dadaia_workspace/infrastructure/public_assets.py`, `dadaia_workspace/container.py`,
  `tests/unit/infrastructure/` (install helpers, codex assets, public assets),
  `tests/integration/test_public_assets.py`.
  Precondition: T-65-03, T-65-06, T-65-07.
  RED: integration test — no overlay ⇒ both projections render the exact `balanced`
  roster (AC-2); overlay change moves `.claude` md AND `.codex` toml in lockstep (this
  lockstep test is the codex-correctness assurance — F-1: there is no codex doctor
  byte-compare); repeated install is byte-stable (`[skip]`). PLUS (F-3) a RED unit test
  asserting `install_codex_agents` / `_codex_toml_from_md` RAISE a loud typed error for
  a core agent when neither a staged `model:` nor a resolved policy model is supplied
  (the silent `claude-sonnet-4-6` default is removed for core agents; kept only for
  plugin bodies that author `model:`).
  Done when: `render_claude_agent` seam is the single injection point (deterministic
  `model:` then `effort:` as last frontmatter lines; `effort:` OMITTED entirely when
  unresolved — plugin agent without an override — never empty/placeholder, F-6); codex
  `model_reasoning_effort` uses the D-3 clamp of resolved effort; core-agent codex
  render fails closed per the F-3 RED test; `--force` re-RENDERS (clobbers a diverged
  projection back to render output, never to raw staged bytes — F-5, asserted in a unit
  test); plugin-pack agent projection resolves override > pack default; overlay loaded
  once per run; invalid overlay fails loud before any write.

- [x] **T-65-09 — Policy-aware doctor + model-resolution rework (FR7, D-6)** — owner: software-engineer
  Completion note: RED captured — new AC-5 integration tests
  (`test_doctor_ok_after_policy_rerender_drift_on_hand_edit_nonagent_untouched`,
  `test_doctor_errors_on_invalid_overlay_ok_on_missing`) + 3 model-resolution unit REDs
  (resolved-roster registry/vocab validation, valid-overlay clean, plugin staged-model
  scan), plus the T-65-08-declared doctor-gap failures (pi CLI doctor, plugin uninstall
  golden, doctor goldens ×3). Implemented: interception pinned EXACTLY at the
  `runtime_expectations` loop — non-plugin `claude:agents/*.md` labels route to
  `_compare_content(render(staged generic + resolved policy))`; `stage:agents/*` and
  all non-agent labels stay raw `_compare` (asserted); overlay loaded once per doctor
  run — invalid ⇒ `[drift] agent-model-policy ERROR` line, missing ⇒ silent balanced;
  installed-pack claude doctor lines render-compared (override>pack-default); NO
  `codex_doctor.py` change (F-1). `check_model_resolution(public_dir, overlay)`
  validates the RESOLVED core roster + plugin staged frontmatter models; key-set check
  unchanged; loader injected into `PublicAssetService` via `container.build_public_service`
  (D-4, no features→infrastructure edge). Goldens regenerated for genuinely changed
  truth ONLY: the new `stage:schemas/agent-model-policy-v1.schema.json` [ok] line
  (asset added by T-65-03) in doctor_all_four_v0158 + plugin goldens a/b;
  `test_plugin_projection` expectations updated to the rendered pack-body truth.
  Full suite: 4816 passed; remaining failures = ONLY the 2 tier-taxonomy contract
  tests (T-65-13). mypy --strict, ruff format/check, lint-imports (9 kept/0 broken) green.
  Write set: `dadaia_workspace/infrastructure/public_assets.py` (doctor compare paths),
  `dadaia_workspace/features/public/model_resolution.py`,
  `dadaia_workspace/features/public/service.py`,
  `tests/unit/features/public/test_model_registry_doctor.py`,
  `tests/unit/infrastructure/test_public_assets.py`,
  `tests/integration/test_public_assets.py`.
  Precondition: T-65-08.
  RED: AC-5 all three directions — doctor `[ok]` immediately after a policy re-render;
  `[drift]` on a hand-edited projected `.claude/agents/*.md`; **non-agent stage/runtime
  compare lines stay `[ok]`, untouched by the render seam (F-2)**; doctor ERROR on an
  invalid overlay, `[ok]` on a missing one.
  Done when: **the interception is pinned (F-2)** — intercept ONLY the
  `claude:agents/*.md` branch of the `runtime_expectations` loop in
  `public_assets.py::doctor` (~l.686-718), for non-plugin stems (reuse the existing
  plugin-stem exclusion at l.706-712), routing it to a content compare against
  `render(staged generic + resolved policy)`; `stage:agents/*.md` (generic↔generic) and
  ALL non-agent labels stay on the raw `_compare` path — never patch `_compare`
  globally. **Codex TOML is NOT doctor-byte-compared (F-1):** no `codex_doctor.py`
  change; codex correctness is the T-65-08 install-time lockstep test.
  `check_model_resolution` validates the RESOLVED roster + plugin staged models; staging
  manifest untouched (staged-bytes hashing).

## Wave 4 — Panel Sub-agents tab — after T-65-08

- [x] **T-65-10 — Feature service + wiring (FR8)** — owner: software-engineer
  Completion note: RED captured as collection failure (ModuleNotFoundError) of
  `tests/unit/features/agents/test_model_policy.py` before the module existed; 7 tests
  green after. `AgentModelPolicyService` (get_policy/{exists,policy,resolved},
  resolved_roster source-tagged override|template|default|pack via the FR4 resolver,
  templates_payload, validate=store.parse, apply = validate → save → injected
  re-render → summary + G-2 per-harness instructions; invalid apply never saves nor
  re-renders). Store port declared in the feature module (Protocol);
  `container.build_agent_model_policy_service` wires the concrete store (plugin agent
  names from the installed-pack ledger), pack-defaults provider, and the agents-only
  `install(target="all", only="agents")` re-render. mypy --strict, ruff,
  lint-imports (9 kept / 0 broken) green in-wave.
  Write set: `dadaia_workspace/features/agents/model_policy.py` (new),
  `dadaia_workspace/container.py`, `tests/unit/features/agents/test_model_policy.py` (new).
  Precondition: T-65-03, T-65-08.
  RED: service tests — `apply()` validates, saves, invokes the injected re-render
  callable, returns its summary; `resolved_roster()` sources tagged
  override|template|default|pack.
  Done when: store + re-render injected (no features→infrastructure import;
  `lint-imports` green in-wave).

- [x] **T-65-11 — API endpoints (FR8)** — owner: software-engineer
  Completion note: RED captured as collection failure (ModuleNotFoundError) of
  `tests/unit/features/panel/test_api_agent_policy.py` before the view module
  existed; 16 tests green after. `views/agent_policy.py` mirrors the workflow-policy
  pipeline exactly (415 → 413 → 400 invalid-JSON → 400 non-object root → 400
  shape/semantic via the shared store parse — AC-4 messages verbatim incl. D-7);
  GET `{exists, policy, resolved}` (invalid overlay ⇒ 409, missing ≠ invalid);
  templates payload (3 rosters + registry models + effort vocab); PUT = validate →
  atomic save → re-render BOTH projections (G-2), response carries `rerendered` +
  per-harness `instructions`. Routes registered in `_ROUTE_TABLE` (GET ×2, BEARER),
  `_PUT_ROUTE_TABLE`, `_POST_BODY_ROUTE_TABLE`; foreign Host → 403 asserted at the
  handler layer. Full panel unit suite 592→608 green; mypy --strict, ruff,
  lint-imports (9 kept / 0 broken) green.
  Write set: `dadaia_workspace/features/panel/views/agent_policy.py` (new),
  `dadaia_workspace/features/panel/handler.py` (routes only),
  `tests/unit/features/panel/test_api_agent_policy.py` (new).
  Precondition: T-65-10.
  RED: endpoint tests mirroring the workflow-policy suite — GET shape
  `{exists, policy, resolved}`; templates payload (3 templates + model ids + effort
  vocab); validate dry-run 400s with FR3 messages; PUT 415/413/400 pipeline; PUT
  persists + triggers re-render; foreign Host → 403.
  Done when: AC-4 messages surface verbatim through the API.

- [x] **T-65-12 — UI tab + post-apply pop-up (FR8, G-2)** — owner: software-engineer
  Completion note: RED captured — `test_index_dom_contract.py` `_SECTIONS` extended
  with `subagents` (2 failures: missing tab id + section panel) before the UI landed;
  `test_views_index.py` tablist/tabpanel contracts updated to the 7-tab truth (genuine
  behavior change, not re-baselining). Implemented: nav tab "Sub-agents"
  (`data-section="subagents"`) beside Workflows; `section-subagents` scaffold in
  `index.py` (template selector + explicit Apply toolbar, banner, roster mount, hidden
  post-apply dialog); `assets/js/agent_policy.js` (lazy tab-click load; roster table
  with per-agent model + effort pickers `low|medium|high|xhigh|max`; template selector;
  Apply = validate-before-save POST→PUT; post-apply pop-up rendering the server's G-2
  per-harness instructions verbatim + the re-rendered file list; all DOM values
  escHtml'd); scoped token-anchored `assets/css/agent_policy.py` (.ap-*, one control
  language); both registered in `static.py`. NO inline script changed —
  `_CSP_SCRIPT_HASH_*` unchanged by construction, CSP coverage test green.
  Independence fix: views type the service via a structural
  `AgentModelPolicyServicePort` Protocol (no features→features import; lint-imports
  stays 9 kept / 0 broken). Panel + agents suites 656 green; mypy --strict + ruff green.
  Write set: `dadaia_workspace/features/panel/views/index.py`,
  `dadaia_workspace/features/panel/views/assets/js/agent_policy.js` (new),
  `dadaia_workspace/features/panel/views/assets/css/` (scoped, new),
  `dadaia_workspace/features/panel/views/static.py`,
  `dadaia_workspace/features/panel/handler.py` (CSP hashes iff inline script changes).
  Precondition: T-65-11.
  Done when: nav tab "Sub-agents" (`data-section="subagents"`) beside Workflows; roster
  table with model + effort pickers (`low|medium|high|xhigh|max`), template selector,
  Apply (validate-before-save), post-apply pop-up carrying the G-2 per-harness text
  verbatim; `_CSP_SCRIPT_HASH_*` recomputed if any inline script changed; existing tabs
  visually unaffected.

- [x] **T-65-13 — Contract-test rework (FR9, AC-7)** — owner: software-engineer
  Completion note: RED = the 2 declared RED-window failures
  (`test_core_agents_carry_numeric_tier_and_pinned_model_effort`,
  `test_plugin_agents_carry_tier3_sonnet_plugin_model`) captured failing on the old
  per-file pins before the rework. Reworked to FR9 pins (a)–(g): 3-template FR2
  table verbatim (`_EXPECTED_TEMPLATES`), balanced single default,
  never-Fable-on-security across all templates, registry tiers
  (fable-5→deep, opus-4-8→dispatch, sonnet-5→plugin), staged core bodies
  model-/effort-less with numeric mandatory `dispatch_band`, plugin bodies
  `dispatch_band: 3` + `claude-sonnet-5`, 9/3 roster counts. Backlog-anchored test
  NAMES preserved (both v0.1.60/64 names kept; no backlog anchor pins a function
  name — grep verified). AC-7 mutation-sanity verified once and reverted:
  (1) resolver precedence flip (override branch disabled) → 5 unit failures incl.
  the AC-3 merge test; (2) one-entry `balanced` mutation (qa-engineer high→medium)
  → `test_builtin_templates_pin_the_fr2_table_verbatim` FAILS. 8/8 green after;
  mypy --strict + ruff clean.
  Write set: `tests/contract/test_agent_tier_taxonomy.py`.
  Precondition: T-65-02, T-65-06.
  Done when: pins (a)–(g) of FR9 (template contents verbatim, balanced default,
  never-Fable-on-security, registry tiers, model-less staged core bodies, sonnet-5
  plugin bodies, 9/3 roster counts); AC-7 mutation-sanity verified once (resolver
  precedence flip fails units; one-entry balanced mutation fails this contract) and
  recorded in the completion note.

- [x] **T-65-14 — Panel e2e: Sub-agents tab (AC-6)** — owner: qa-engineer
  Completion note: `agent-policy.spec.ts` — 4 journeys: (1) roster renders the 9 core
  agents with model + effort pickers (D-3 5-value vocab asserted) + 3-template
  selector with `balanced` selected; (2) template apply (subscription-saver) —
  `clickAndAwaitPut` (T-65-05 helper reused, no PUT/GET race) → G-2 pop-up
  (claude+codex instructions + rerendered list) → GET reflects template
  (product-engineer = sonnet-5/xhigh/template, never-Fable-on-security asserted);
  (3) per-agent override — SE model→opus-4-8 on subscription-saver, AC-3 per-field
  merge asserted verbatim (model from override, effort xhigh from template,
  source=override) + UI reload reflects it; (4) Fable-on-security rejection — armed
  `waitForResponse` on the 400 validate POST, readable error banner naming
  security-reviewer, NO pop-up, NO write (GET still clean baseline). Clean-overlay
  (`balanced`, no overrides) restored before/after every test with asserted 200s.
  RED (mutation-sanity): sabotaged the Apply PUT endpoint in `agent_policy.js`
  (`/api/agent-model-policy` → `-borked`) — both Apply journeys FAILED (PUT wait
  timeout), roster + rejection stayed green as expected; reverted. Stability:
  `--repeat-each=5` → 20/20 passed. Full panel e2e suite: 57 specs (53 baseline
  + 4 new) — 56 passed / 1 failed: `E2E-TAB-01` exact-tab-list pin, a rendered-truth
  golden genuinely changed by the T-65-12 Sub-agents tab; updated under T-65-15's
  golden write set. Run on an isolated panel instance (port 5065; operator's 4999
  untouched).
  Write set: `tests/e2e/panel/agent-policy.spec.ts` (new),
  `tests/e2e/panel/helpers.ts` (additive only — no change needed; `clickAndAwaitPut`
  reused as-is).
  Precondition: T-65-12, T-65-05 (reuse the deterministic-wait pattern).
  RED-first by nature (spec written against the running panel).
  Done when: tab activates and renders the 9-agent roster; template select + Apply
  round-trips PUT/GET (armed `waitForResponse` before the Apply click); post-apply
  pop-up asserted; per-agent override round-trips; clean-overlay restore before/after
  with asserted 200s; suite green locally.

  > **Amendment note (2026-07-08, qa-engineer, T-65-14 CI-fix):** the GHA
  > `E2E panel (Playwright)` job (PR #124) failed all 4 `agent-policy.spec.ts` journeys
  > with HTTP 500 on their seed/Apply PUT. Root cause: the panel resolves
  > `workspace_root` by walking up from its own process cwd at startup
  > (`core/workspace_resolver.resolve_workspace_root`). The e2e harness launched the
  > panel with `webServer.cwd: REPO_ROOT` (`playwright.config.ts`) paired with
  > `.github/scripts/bootstrap-panel-ws.sh`, which wrote
  > `.dadaia/states/spec_contexts.json` directly at that same checkout root — making
  > `workspace_root == the source repo root`. Any PUT that re-renders L1 projections
  > (the agent-model-policy Apply path, `public install(..., only="agents")`) was then
  > correctly refused by the `_is_source_repo_root` production guard
  > (`infrastructure/public_assets.py`) — production behavior was CORRECT; the harness
  > was not hermetic. Dual symptom: locally the same walk-up instead escaped the
  > (unpolluted) checkout and found the developer's own enclosing real
  > dadaia-workspace instance, silently re-rendering its live `.claude/agents/*.md`.
  >
  > RED reproduction (before the fix, honest capture — not from CI logs): built a
  > directory satisfying the exact `_is_source_repo_root` predicate (a `pyproject.toml`
  > naming `dadaia-workspace` + a `dadaia_workspace/public` dir), initialized it as a
  > workspace, started the panel with cwd there, and PUT a valid overlay to
  > `/api/agent-model-policy` → `HTTP 500` with
  > `PanelHandler: mutation route error: Refusing to project public runtime assets
  > into the dadaia-workspace source repository root...` in the server log — the exact
  > CI symptom, reproduced honestly outside CI.
  >
  > Fix (hermetic, root cause — no production Python touched, and
  > `DADAIA_ALLOW_SOURCE_ROOT_PUBLIC_INSTALL=1` was considered and rejected as the
  > primary fix per the assignment: it would keep polluting the source checkout and
  > hide the local instance-mutation problem): new
  > `tests/e2e/panel/run-panel-e2e-server.sh` builds a disposable temp workspace
  > (never the repo root, never an enclosing real operator workspace), inits it,
  > symlinks `repos/dadaia-workspace` to THIS checkout (`_is_self_repo` skips writing
  > back into it — read-only consumption of real specs/memory for the Projects tab),
  > stages + installs a real projection INTO the temp workspace, and execs the panel
  > there. `playwright.config.ts`'s default `webServer.command` now runs this script
  > (env-overridable: `PANEL_E2E_PYTHON`, `PANEL_E2E_WS`); default port moved
  > 4999 → 5065 (`helpers.ts` + `playwright.config.ts`, kept in lockstep) — 4999 is the
  > conventional operator-local live panel port. `ci.yml` / `release.yml` e2e-panel
  > legs: dropped the "Bootstrap panel workspace" step + the hardcoded
  > `--port 4999` `PANEL_WEB_SERVER_COMMAND` override (both retired); added
  > `PANEL_E2E_PYTHON: poetry run python` and a pinned `PANEL_E2E_WS`/
  > `PANEL_TEST_REGISTRY` pair (`${{ runner.temp }}/dadaia-panel-e2e-ws`) so
  > `spec-context-operation-journey.spec.ts` (AC-4) keeps running for real in CI
  > instead of silently regressing to its local-dev skip branch (its `PANEL_TEST_REGISTRY`
  > default is the checkout root, which never carries a registry — the skip guard is
  > unchanged, only now driven by an explicit env pin rather than an accidental
  > cwd coincidence). Deleted the now-dead `.github/scripts/bootstrap-panel-ws.sh`
  > (both workflows were its only callers) and updated its contract test
  > (`tests/contract/test_ci_workflow_hygiene.py`, CI-2 v0.1.61 FR6) to the new
  > anti-duplication invariant: neither workflow may override
  > `PANEL_WEB_SERVER_COMMAND` (the single `playwright.config.ts` default is now the
  > only place naming the bootstrap script, so an override is the only way the two
  > legs could diverge again); the discriminator/executable-bit checks now point at
  > `tests/e2e/panel/run-panel-e2e-server.sh`.
  >
  > Verification (this session, `feature/v0.1.65`): RED reproduced honestly (above,
  > outside CI) before the fix; GET/PUT verified 500→200 against the new hermetic
  > harness directly; full local `poetry run pytest` green (unit+contract+integration);
  > `ruff format --check` / `ruff check --no-cache` / `mypy --strict` clean on the
  > touched Python contract test. Full panel e2e suite (58 tests, `chromium`) —
  > **58/58 passed**, including `spec-context-operation-journey.spec.ts` running for
  > real (not skipped) under a pinned `PANEL_E2E_WS`/`PANEL_TEST_REGISTRY`.
  > `agent-policy.spec.ts --repeat-each=5` — **20/20 passed**. Confirmed the operator's
  > live workspace was never touched: `git status --short` on the checkout shows only
  > the intended source edits; `find .claude/agents .codex/agents .dadaia/agentic
  > -newermt <session-start>` returned zero results across the entire session (RED
  > repro + GREEN repro + full suite + repeat-each runs).
  > Write set (amendment): `tests/e2e/panel/run-panel-e2e-server.sh` (new),
  > `tests/e2e/panel/playwright.config.ts`, `tests/e2e/panel/helpers.ts`,
  > `tests/e2e/panel/response-guard.spec.ts` (comment only),
  > `tests/e2e/panel/spec-context-operation-journey.spec.ts` (header comment only —
  > behavior unchanged, safety mechanism re-described),
  > `.github/workflows/ci.yml`, `.github/workflows/release.yml`,
  > `tests/contract/test_ci_workflow_hygiene.py`; deleted
  > `.github/scripts/bootstrap-panel-ws.sh`.

## Wave 5 — Verification tail — after all above

- [x] **T-65-15 — Golden + AC re-verification sweep (AC-1..AC-10)** — owner: qa-engineer
  Completion note (merge-base `d2b94585`):
  **Golden triage.** Diffed every golden touched on the branch vs merge-base:
  `doctor_all_four_v0158.json` + `plugin_doctor_report_golden_{a,b}_v0160.json` each
  carry exactly one added line (`[ok] stage:schemas/agent-model-policy-v1.schema.json`)
  — genuine truth from T-65-09 (the new FR3 schema asset now stages). No other golden
  under `tests/**/_golden/` changed on the branch; `api_golden_v0155.json`,
  `panel_runtime_validation_v0158.json`, and the install-target goldens are
  byte-identical to merge-base (zero-diff, confirmed) despite referencing
  `claude-fable-5`/`claude-opus-4-8` strings — no silent re-baselining. The
  `grep -rl "claude-fable-5\|claude-opus-4-8\|claude-sonnet-4-6" tests/` set has grown
  to 39 files since spec time (new template/policy/e2e test files); every hit is a
  genuine test-content reference to a registry model id, not an unexplained golden
  churn. Frozen v0.1.50 no-steal suite: zero-diff vs merge-base (no lease/steal test
  file touched). Fixed 1 rendered-truth regression found only by the full e2e-panel run
  below: `tab-navigation.spec.ts` E2E-TAB-01/03/04 pinned the pre-FR8 6-tab list;
  updated to the 7-tab truth (`Sub-agents` beside `Workflows`) + `helpers.ts`
  `activateTab` union extended with `'subagents'` (additive) — genuine truth change
  from T-65-12, not a re-baseline of a behavior bug.
  **AC-by-AC evidence** (all commands run fresh this session):
  AC-1 — `grep -rn "^model:\|^effort:" dadaia_workspace/public/agents/` → 0 hits (core
  bodies model-agnostic).
  AC-2 — `test_install_with_no_overlay_renders_balanced_roster_in_lockstep` (PASS).
  AC-3 — `test_overlay_change_moves_claude_md_and_codex_toml_in_lockstep` +
  `test_agent_model_templates.py::…AC-3…` + e2e "Per-agent override round-trips…
  AC-3 per-field merge" (PASS ×3).
  AC-4 — `test_api_agent_policy.py::…AC-4: unknown agent/model/effort/template +
  Fable-on-security…` + `test_json_agent_model_policy_store.py` store-parse rejections
  (PASS).
  AC-5 — `test_doctor_ok_after_policy_rerender_drift_on_hand_edit_nonagent_untouched`
  (PASS, all 3 directions + F-2 pin).
  AC-6 — `agent-policy.spec.ts` (T-65-14) — 4/4 e2e journeys PASS, 20/20 stability,
  mutation-sanity RED captured.
  AC-7 — recorded once at T-65-13 (resolver precedence flip → 5 unit fails incl. AC-3
  merge test; one-entry `balanced` mutation → contract test fails); re-confirmed live
  this session via T-65-14's own mutation-sanity (Apply-PUT sabotage → 2 e2e fails).
  AC-8 — `test_frontmatter_yaml_parse_error.py` (PASS, 4 tests).
  AC-9 — re-ran `workflow-policy-harness-toggle.spec.ts --repeat-each=10` fresh (20
  executions) → 20/20 PASS.
  AC-10 — full gate battery below, all green.
  AC-11 — out of scope for this task (T-65-16).
  **Full gate battery** (fresh, this session, `.dadaia/.venv`-equivalent repo venv):
  `ruff format --check .` → 842 files already formatted (0 diff). `ruff check
  --no-cache .` → all checks passed. `mypy --strict dadaia_workspace/` (CI-canonical
  scope) → Success, no issues found in 319 source files. `lint-imports --config
  setup.cfg --no-cache` → 9 kept / 0 broken. `pytest -p no:cacheprovider -q` (full
  suite, unit+contract+integration+e2e-python) → **4941 passed, 0 failed, 18 skipped**
  (526s wall once, 410s on a clean-tree rerun after removing a stray
  `.import_linter_cache/` this session's own earlier bare `lint-imports` run had left —
  not a product bug, repo-hygiene self-correction). Full Playwright e2e-panel suite
  (isolated port 5066, operator's 4999 untouched) → **57 specs, 56 passed / 1 skipped**
  (the pre-existing LAN-IPv4-conditional skip), 0 failed.
  Write set: `tests/e2e/panel/tab-navigation.spec.ts`,
  `tests/e2e/panel/helpers.ts` (the only rendered-truth golden regen this task
  required).
  Precondition: T-65-01..T-65-14 all `[x]`-eligible (implementation complete).
  Done when: each golden diff is triaged at merge-base (never re-baselined to silence a
  behavior bug); AC-1..AC-10 each verified with command + evidence recorded in the task
  completion note; full gates green locally: `ruff format --check`, `ruff check`,
  `mypy --strict`, `pytest` (unit+contract+integration; pytest with
  `-p no:cacheprovider`), `lint-imports`, e2e panel suite.

## Wave 6 — Instance propagation + manual verification — after W5

- [x] **T-65-16 — Propagate to THIS instance + live panel check (AC-11, D-1)** — owner: software-engineer — DONE: stage+install --target all+doctor exit 0 incl. [ok] public-privacy + [ok] model-resolution, no agent [drift] post-render; instance .claude/agents + .codex/agents carry the balanced roster (D-1 LIVE RETIER: this instance re-tiered — fable-5 now only on PM+architect); panel restarted, Sub-agents tab live, /api/agent-model-templates + /api/agent-model-policy verified (applied_template=balanced, resolved sources=template); panel registered on 4999 per dev-server guardrail.
  Write set: none in-repo (workspace projections via CLI only).
  Precondition: T-65-15.
  Done when: from the workspace venv — `dadaia public stage`,
  `dadaia public install --target all`, `dadaia public doctor` all exit 0 (incl.
  `[ok] public-privacy` and no agent `[drift]` post-render); `.claude/agents/*.md` and
  `.codex/agents/*.toml` on this instance carry the `balanced` roster; `dadaia panel`
  Sub-agents tab manually verified live (roster, Apply, pop-up) with the panel server
  registered per the dev-server guardrail; completion note calls out the D-1 live retier.

---

## Golden/AC re-verification reminder (applies to every task)

A task that changes rendered agent output MUST run the contract test + affected goldens
before flipping `[x]`. Goldens document truth; a golden updated without a matching FR is
a review-blocker.

## Revision log

- 2026-07-07 — Tasks authored; `**Status:** Aprovado`.
- 2026-07-07 — Architect review REVISE folded (report:
  `.dadaia/reports/dadaia-workspace/software-architect/2026-07-07T200000Z-review-v0165-definition.md`):
  F-1/F-2 folded into T-65-09 (pinned `runtime_expectations` interception; claude-md-only
  doctor scope; no `codex_doctor.py` work) and T-65-08 RED (lockstep = codex assurance);
  F-3 fail-closed core codex render RED test in T-65-08; F-5 `--force` re-render
  assertion in T-65-08; F-6 effort-omission asymmetry in T-65-02 RED + T-65-08 Done;
  F-7 Wave-3 RED-window push-discipline note. Status remains Aprovado — fold of an
  approved review, no scope change.
