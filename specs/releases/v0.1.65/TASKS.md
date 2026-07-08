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

- [-] **T-65-13 — Contract-test rework (FR9, AC-7)** — owner: software-engineer
  Write set: `tests/contract/test_agent_tier_taxonomy.py`.
  Precondition: T-65-02, T-65-06.
  Done when: pins (a)–(g) of FR9 (template contents verbatim, balanced default,
  never-Fable-on-security, registry tiers, model-less staged core bodies, sonnet-5
  plugin bodies, 9/3 roster counts); AC-7 mutation-sanity verified once (resolver
  precedence flip fails units; one-entry balanced mutation fails this contract) and
  recorded in the completion note.

- [ ] **T-65-14 — Panel e2e: Sub-agents tab (AC-6)** — owner: qa-engineer
  Write set: `tests/e2e/panel/agent-policy.spec.ts` (new),
  `tests/e2e/panel/helpers.ts` (additive only).
  Precondition: T-65-12, T-65-05 (reuse the deterministic-wait pattern).
  RED-first by nature (spec written against the running panel).
  Done when: tab activates and renders the 9-agent roster; template select + Apply
  round-trips PUT/GET (armed `waitForResponse` before the Apply click); post-apply
  pop-up asserted; per-agent override round-trips; clean-overlay restore before/after
  with asserted 200s; suite green locally.

## Wave 5 — Verification tail — after all above

- [ ] **T-65-15 — Golden + AC re-verification sweep (AC-1..AC-10)** — owner: qa-engineer
  Write set: `tests/**` golden files ONLY where rendered truth genuinely changed
  (api/panel/install goldens; the 16 files matching
  `grep -rl "claude-fable-5\|claude-opus-4-8\|claude-sonnet-4-6" tests/` at spec time).
  Precondition: T-65-01..T-65-14 all `[x]`-eligible (implementation complete).
  Done when: each golden diff is triaged at merge-base (never re-baselined to silence a
  behavior bug); AC-1..AC-10 each verified with command + evidence recorded in the task
  completion note; full gates green locally: `ruff format --check`, `ruff check`,
  `mypy --strict`, `pytest` (unit+contract+integration; pytest with
  `-p no:cacheprovider`), `lint-imports`, e2e panel suite.

## Wave 6 — Instance propagation + manual verification — after W5

- [ ] **T-65-16 — Propagate to THIS instance + live panel check (AC-11, D-1)** — owner: software-engineer
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
