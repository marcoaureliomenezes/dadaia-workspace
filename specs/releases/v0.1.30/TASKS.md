# TASKS — Release: v0.1.30 — super release: PI/Codex Layer-2 + workflow system maturation

**Status:** Aprovado
**Release ID:** v0.1.30
**Owner:** product-engineer

> DEFINE-ONLY (GRILL D-4). Tasks are approved but **NOT started** — every marker is `[ ]`.
> Implementation begins only after the operator approves at the DEFINITION checkpoint and
> `ACTIVE.md` phase advances to IMPLEMENTATION. Markers: `[ ]` OPEN → `[-]` IN PROGRESS →
> `[x]` DONE. One `[-]` per owner unless disjoint write sets are declared.

---

## Wave A — shared-headless-adapter-base (FOUNDATION — must land first, D-3)

- [x] **T-30-A-01** — Author the shared headless-adapter base.
  - Goal: create the single home for `_redact`/`_SECRET_NAME_PARTS`, `_GitDiffPort`/
    `_with_changed_paths`, `_env`/allowlist, the `Runner` seam type, and the shared `_prompt`
    JSON-envelope builder; factor subprocess parts separable from redaction+git seam.
  - Write set: `dadaia_workspace/infrastructure/headless_adapter_base.py` (NEW).
  - Acceptance: A1, A5 — invariants defined once; `mypy --strict` + import-linter green.

- [x] **T-30-A-02** — Refactor `pi_runtime` onto the base.
  - Goal: import shared parts; keep only `_command`/result-extraction/`PiHeadlessConfig`.
  - Write set: `dadaia_workspace/infrastructure/pi_runtime.py`.
  - Acceptance: A2, A4 — `test_pi_runtime.py` passes unchanged.

- [x] **T-30-A-03** — Refactor `codex_runtime` onto the base.
  - Goal: import shared parts; keep only `_command`/`_model_and_effort`/result-extraction.
  - Write set: `dadaia_workspace/infrastructure/codex_runtime.py`.
  - Acceptance: A2, A4 — `test_codex_runtime.py` passes unchanged.

- [x] **T-30-A-04** — Refactor `claude_sdk_runtime` onto the base (redaction + git seam only).
  - Goal: reuse `_redact`/`_SECRET_NAME_PARTS` (+ git seam for parity) without subprocess bits.
  - Write set: `dadaia_workspace/infrastructure/claude_sdk_runtime.py`.
  - Acceptance: A2, A4 — Claude SDK adapter tests pass unchanged.

- [x] **T-30-A-05** — Divergence test + base unit coverage.
  - Goal: a test that FAILS if redaction or `changed_paths` override diverges between adapters.
  - Write set: `tests/unit/infrastructure/test_headless_adapter_base.py` (NEW).
  - Acceptance: A3.

> **Wave A green checkpoint:** divergence test green; all three adapter suites green unchanged;
> mypy/lint green. **Foundation locked — no per-harness wave starts before this.**

---

## Wave B — codex-runtime-fidelity (Item 2) + PI WS-PI-6 (Item 3)

- [x] **T-30-B-01** — WS-CDX-PROTOCOL: rule-law corpus reachable from Codex.
  - Goal: on-disk path transform + read instruction in `transform_for_codex` (or rewrite
    by-name citations to a reachable surface).
  - Write set: `dadaia_workspace/infrastructure/runtime_transforms/codex.py`;
    `dadaia_workspace/public/data/AGENTS.md` (if a reachable surface is needed).
  - Acceptance: A6.

- [x] **T-30-B-02** — WS-CDX-HYGIENE: trust-boundary INFO + keep/drop + inert keys.
  - Goal: doctor INFO line on interactive-vs-headless; resolve `.codex/workflows/` keep-or-drop
    (remove inert reference); drop inert config keys; onboarding note.
  - Write set: `dadaia_workspace/infrastructure/codex_doctor.py`;
    `dadaia_workspace/infrastructure/public_assets.py` (inert ref removal);
    `dadaia_workspace/public/skills/ai-harness-codex/SKILL.md`.
  - Acceptance: A7, A8, A9.

- [x] **T-30-B-03** — WS-PI-6: PI telemetry reader.
  - Goal: incremental reader ingesting `~/.pi/agent/sessions/` metadata into the store (mirror
    `reader/codex.py`; metadata-only, T1; graceful idle on IO/parse failure).
  - Write set: `dadaia_workspace/features/telemetry/reader/pi.py` (NEW).
  - Acceptance: A11.

- [x] **T-30-B-04** — WS-PI-6: PI telemetry adapter + registry entry + panel A12 wiring.
  - Goal: `PiRuntimeAdapter` (enrichment + liveness, cost unknown) + `"pi"` in
    `ADAPTER_REGISTRY`; PI session ingestion in service/panel; PI runtime button in panel.
  - Write set: `dadaia_workspace/features/telemetry/aggregator/runtimes.py`;
    `dadaia_workspace/features/telemetry/service.py`;
    `dadaia_workspace/cli/commands/panel.py`;
    `dadaia_workspace/features/panel/views/` (sessions/agents/index/handler).
  - Acceptance: A10, A12.

- [x] **T-30-B-05** — PI fourth-harness academy module.
  - Goal: document enter-pi flow, trust boundary, per-step `--harness pi`.
  - Write set: `dadaia_workspace/features/academy/knowledge_basis/08_pi_agent/<module>.md` (NEW).
  - Acceptance: A13.

> **Wave B green checkpoint:** PI adapter+reader green with faked fixture; Codex reachability
> + doctor INFO green; `dadaia public doctor` `[ok]`.

---

## Wave C — workflow-model-governance: operator profiles + overlays + nits (Item 4)

- [x] **T-30-C-01** — WS-PROFILES: local PI-profile store + port.
  - Goal: `.dadaia/states/workflow_model_profiles.local.json` adapter (atomic; validate
    `harness=pi`; reject API keys; never projected) + port wired via container.
  - Write set: `dadaia_workspace/infrastructure/json_local_model_profile_store.py` (NEW);
    `dadaia_workspace/core/protocols/local_model_profile_store.py` (NEW);
    `dadaia_workspace/container.py`.
  - Acceptance: A14 (store/validation half).

- [x] **T-30-C-02** — WS-PROFILES: merge operator profiles into `model_profiles`.
  - Goal: `list_profiles`/`profiles_for` merge built-in + operator-loaded; preserve
    `UnknownProfileError` fail-closed; default-first when store missing.
  - Write set: `dadaia_workspace/features/lifecycle/model_profiles.py`.
  - Acceptance: A14 (selectability half).

- [x] **T-30-C-03** — WS-OVERLAYS: `extends` inheritance in the overlay store.
  - Goal: add `extends` to `_ALLOWED_TOP_LEVEL`/schema; walk `context → extends… → default`
    in `overlay_for`/`workflow_default_harness`/`step_harness`; cycle detection; hard error on
    missing parent.
  - Write set: `dadaia_workspace/infrastructure/json_workflow_model_policy_store.py`;
    `dadaia_workspace/public/schemas/workflow-model-policy-v1.schema.json`.
  - Acceptance: A15, A16.

- [-] **T-30-C-04** — WS-OVERLAYS: resolver chain resolution.
  - Goal: `policy_resolver` resolves a step's profile through the per-context overlay chain,
    fail-closed on unresolvable refs.
  - Write set: `dadaia_workspace/features/lifecycle/policy_resolver.py`.
  - Acceptance: A15.

- [ ] **T-30-C-05** — WS-NITS: de-dup `_DEFAULT_PROFILE_BY_HARNESS_PURPOSE` + docstring + panel.
  - Goal: one shared home for the map (guarded by `_assert_catalog_defaults_resolve`);
    correct `policy_resolver` docstring to name `governed_workflow_catalog()`; panel
    `_semantic_check` 3-map union.
  - Write set: `dadaia_workspace/features/lifecycle/policy_resolver.py`;
    `dadaia_workspace/features/workflows/dadaia_catalog.py`;
    `dadaia_workspace/features/panel/views/workflow_policy.py`.
  - Acceptance: A17.

> **Wave C green checkpoint:** operator-profile load test; `extends` chain + cycle/missing-parent
> tests; WMP doctor ↔ panel `_semantic_check` agree; nits resolved; `public doctor` `[ok]`.

---

## Wave D — workflow-step handoff data plane (Item 5) — **CRITICAL**

- [ ] **T-30-D-01** — Workflow-handoff models + LifecycleRun field (additive).
  - Goal: `WorkflowStepRecord`/`WorkflowStepConsumerRecord`/attempt ledger; additive
    `workflow_steps` on `LifecycleRun` with round-trip (old records load).
  - Write set: `dadaia_workspace/core/models/workflow_handoff.py` (NEW);
    `dadaia_workspace/core/models/lifecycle.py`.
  - Acceptance: A27 (back-compat round-trip).

- [ ] **T-30-D-02** — Payload + run-steps JSON schemas; output-handoff field fix.
  - Goal: `workflow-step-payload-v1` + `lifecycle-run-workflow-steps-v1` schemas; fix
    `output-handoff.md` `detail` → `detail_md`.
  - Write set: `dadaia_workspace/public/schemas/workflow-step-payload-v1.schema.json` (NEW);
    `dadaia_workspace/public/schemas/lifecycle-run-workflow-steps-v1.schema.json` (NEW);
    `dadaia_workspace/public/lifecycle_fragments/shared/output-handoff.md`.
  - Acceptance: A21 (envelope+payload validation).

- [ ] **T-30-D-03** — Workflow-handoff resolver/service.
  - Goal: enqueue/resolve/ack/reclaim; envelope + named-payload validation; compact digest
    rendering; atomic consumption recording through the run store.
  - Write set: `dadaia_workspace/features/lifecycle/workflow_handoffs.py` (NEW);
    `dadaia_workspace/container.py`.
  - Acceptance: A19, A20, A22, A25.

- [ ] **T-30-D-04** — Persist step payloads + run-store extension.
  - Goal: `write_run_artifact` step-payload path under `runs/lifecycle/<run_id>/steps/`;
    persist `workflow_steps` atomically.
  - Write set: `dadaia_workspace/infrastructure/runtime_files.py`;
    `dadaia_workspace/infrastructure/json_lifecycle_run_store.py`.
  - Acceptance: A18.

- [ ] **T-30-D-05** — Wire release-definition produces/consumes + terminal gate.
  - Goal: per-`ReleaseStep` edges; write+validate payloads; resolver-injected digests;
    terminal gate graph-completeness.
  - Write set: `dadaia_workspace/features/lifecycle/workflows/release_definition.py`;
    `dadaia_workspace/features/lifecycle/context_selector.py`.
  - Acceptance: A18, A19, A20, A25.

- [ ] **T-30-D-06** — Implementation/review loop attempt tracking + bounded retry.
  - Goal: attempts so `implement#2` consumes `qa#1`; bounded retry (default 2) → BLOCK.
  - Write set: `dadaia_workspace/features/lifecycle/pipeline.py`.
  - Acceptance: A24.

- [ ] **T-30-D-07** — Retention + hygiene for step payloads.
  - Goal: protect live step artifacts (extended `live_claims`); reclaim `consumed_all` past
    consumed TTL; prune empty run dirs; hygiene state counters.
  - Write set: `dadaia_workspace/features/lifecycle/antislop/retention.py`;
    `dadaia_workspace/features/lifecycle/hygiene.py`.
  - Acceptance: A22, A23.

- [ ] **T-30-D-08** — `dadaia lifecycle handoffs doctor` + minimal panel API exposure.
  - Goal: doctor fails on orphan/malformed/stale/undeclared/unconsumed-required; expose the
    run ledger via a minimal panel API (rich graph view is OUT — Slice C follow-up).
  - Write set: lifecycle handoffs doctor module (NEW or fold into hygiene status);
    `dadaia_workspace/features/panel/views/` (minimal run-ledger API).
  - Acceptance: A26.

> **Wave D green checkpoint (CRITICAL gate):** A18–A27 all green — fake-run ledger; exact-by-
> attempt consumption; block on missing/malformed; retention live/promoted/eligible; attempt
> loop; handoffs doctor; old-record load. No Wave E task starts before this is green.

---

## Wave E — real audit/research/bug_report bodies + ctx-inject dehydration (Item 6) — **CRITICAL**

- [ ] **T-30-E-01** — Real `audit` workflow body.
  - Goal: fragment+gate body (mirror `release_definition`); consumes the Wave-D ledger;
    disposition-ready output; records injected fragments/context.
  - Write set: `dadaia_workspace/features/lifecycle/workflows/audit.py` (NEW);
    `dadaia_workspace/public/lifecycle_fragments/` (audit fragments).
  - Acceptance: A28, A29 (audit half).

- [ ] **T-30-E-02** — Real `research` workflow body.
  - Goal: fragment+gate body; records injected fragments + dynamic context.
  - Write set: `dadaia_workspace/features/lifecycle/workflows/research.py` (NEW);
    `dadaia_workspace/public/lifecycle_fragments/` (research fragments).
  - Acceptance: A28 (research half).

- [ ] **T-30-E-03** — Real `bug_report` workflow body (ADDITIVE-safe).
  - Goal: fragment+gate body writing only `specs/bugs/` (ADDITIVE class — no lease).
  - Write set: `dadaia_workspace/features/lifecycle/workflows/bug_report.py` (NEW);
    `dadaia_workspace/public/lifecycle_fragments/` (bug_report fragments).
  - Acceptance: A28, A29 (bug_report half).

- [ ] **T-30-E-04** — Remove the three from `DEFERRED_WORKFLOWS`.
  - Goal: drop `audit`/`research`/`bug_report` stub entry points + names; a test asserts they
    no longer raise `NotImplementedError`.
  - Write set: `dadaia_workspace/features/lifecycle/workflows/_deferred.py`.
  - Acceptance: A28.

- [ ] **T-30-E-05** — WS-C ctx-inject dehydration.
  - Goal: reduce broad session-memory injection; lifecycle prompts get context from the
    dynamic selector; keep bind/session safety + lean generic preflight; chokepoints unchanged.
  - Write set: `dadaia_workspace/hooks/ctx_inject.py`.
  - Acceptance: A30.

- [ ] **T-30-E-06** — Record OQ decisions (OQ-3/4/6/7).
  - Goal: reflect OQ-3/OQ-4/OQ-7 in affected docs/fragments; record the OQ-6 deferral rationale.
  - Write set: affected `public/` fragments/docs (per OQ-3/4/7); OQ-6 rationale captured for
    CLOSURE.
  - Acceptance: A31.

> **Wave E green checkpoint (CRITICAL gate):** A28–A32 green — three bodies run as real
> fragment+gate workflows; ctx-inject dehydration proven; OQ decisions recorded;
> `dadaia specs doctor` + `dadaia public doctor` green after projection.

---

## Closure / ship (DEFINE-ONLY — NOT run this release cycle)

- [ ] **T-30-Z-01** — Release closure + memory atoms + disposition sweep.
  - Goal (CLOSURE phase only, after every wave `[x]` and the trio/QA cadence per
    `release-governance`): write `CLOSURE.md` (template `dadaia-release-closure`); update
    `specs/memory/architecture.md`, `tech-stack.md`, and the affected `product/` atoms;
    run the disposition sweep — flip the five `**Consumes:**`-declared backlog items to
    `DELIVERED — v0.1.30`, and rewrite `pi-agent-fourth-harness` to its **WS-PI-5 residual**
    (NOT deleted, NOT marked delivered — D-2); run the release-definition consumes hook /
    confirm the consumed_backlog ledger; `git mv` the release to `_archive/`; point `ACTIVE.md`
    at the next release.
  - Write set: `specs/releases/v0.1.30/CLOSURE.md`; `specs/memory/**`; `specs/backlog/**`
    (disposition status only); `specs/releases/ACTIVE.md`.
  - Acceptance: CLOSURE evidence complete (summary, tasks+SHAs, validations triples, drifts,
    memory updates, dispositions, archive decision); OQ-6 deferral rationale recorded;
    `dadaia specs doctor` green.

---

## Parallelism notes

- Within Wave A, T-30-A-02/03/04 have disjoint write sets (one adapter each) and may run in
  parallel **after** T-30-A-01 lands the base; T-30-A-05 follows.
- Wave B: T-30-B-01/02 (Codex) and T-30-B-03/04/05 (PI) are disjoint and may run in parallel.
- Wave C: T-30-C-01/02 (profiles) and T-30-C-03/04 (overlays) are largely disjoint; T-30-C-05
  (nits) touches `policy_resolver.py` shared with C-04 — sequence C-05 after C-04.
- Wave D is a tight CRITICAL chain (shared `LifecycleRun`/run-store/resolver) — prefer
  sequential execution; D-01 → D-02 → D-03/04 → D-05 → D-06/07 → D-08.
- Wave E: E-01/02/03 are disjoint workflow bodies (parallelizable); E-04 follows them;
  E-05/E-06 are independent.
