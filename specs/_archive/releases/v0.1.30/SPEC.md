# SPEC — Release: v0.1.30 — super release: PI/Codex Layer-2 + workflow system maturation

**Status:** Aprovado
**Release ID:** v0.1.30
**Owner:** product-engineer
**Opened:** 2026-06-27

**Consumes:** shared-headless-adapter-base, codex-runtime-fidelity, workflow-model-governance-operator-profiles-and-context-overlays, workflow-step-handoff-data-plane-cleanup, lifecycle-prompt-fragments-ai-surface-dehydration

> The `**Consumes:**` line declares the backlog slugs **fully** consumed by this release
> (every open intent ships). `pi-agent-fourth-harness` is deliberately **absent** — WS-PI-5
> is deferred (GRILL D-2), so the item is not fully consumed (see §4 and the per-item
> Consumes assessment in §3.3). The release-definition consumes hook (v0.1.27) will bind
> these slugs and write the consumed_backlog ledger; `pi-agent-fourth-harness` stays in the
> live backlog rewritten to its WS-PI-5 residual at CLOSURE.

---

## 1. Problem and context

The two-layer architecture (Layer-1 entry harnesses; Layer-2 bounded workers behind
`AgentRuntimePort`) and the procedural dadaia-workflow engine have shipped incrementally
across v0.1.16–v0.1.29. Six correlated residuals now leave the Layer-2 worker stack and
the workflow system **inconsistent and incomplete**:

1. The three real headless adapters (`pi_runtime`, `codex_runtime`, `claude_sdk_runtime`)
   copy-paste **security-relevant** invariants (`_redact`/`_SECRET_NAME_PARTS`,
   `_GitDiffPort`/`_with_changed_paths`, `_env`/allowlist, the `Runner` seam, the prompt
   envelope). A divergence between copies is a latent security bug, not style debt.
2. Codex (a Layer-1 entry harness) cannot natively reach the by-name rule-law corpus, and
   its interactive-vs-headless trust boundary is not surfaced to operators or doctor.
3. PI shipped as the fourth harness (v0.1.18–v0.1.21) but does not appear in the telemetry
   panel — there is no PI entry in the runtime adapter registry / reader set.
4. Workflow model-governance ships **built-in recommended profiles only** and collapses all
   per-context overlays to the `default` context — an operator cannot register a PI profile
   or use per-context `extends` inheritance; three v0.1.29 code-reviewer LOW nits remain.
5. **(CRITICAL)** Workflow steps communicate by stale prose / "latest handoff by agent"
   directory scans rather than a run-scoped producer→consumer ledger — a drift-and-slop
   source as workflows grow branches, loops, and gates.
6. **(CRITICAL)** The `audit` / `research` / `bug_report` workflow bodies are still
   fail-loud `_deferred.py` stubs, and the projected AI surface still carries lifecycle
   behavior that the fragment engine was built to replace (ctx-inject over-injection).

This release makes Layer-2 workers (PI + Codex) and the workflow system first-class and
consistent: unify the headless-adapter base, finish the PI/Codex worker residuals, and
complete the workflow model-governance + handoff data-plane + prompt-fragment stack.

The mandatory `dadaia-grill-me` gate was run interactively with the operator before this
SPEC (record: `specs/releases/v0.1.30/GRILL.md`, `status: Aprovado`). Its decisions
(D-1..D-5) and laws are binding and are reflected below.

---

## 2. Objective

Make the two-layer architecture's Layer-2 workers (PI + Codex) and the dadaia-workflow
system first-class and consistent — one shared headless-adapter base, the PI/Codex worker
residuals closed, and the workflow model-governance + handoff data-plane + prompt-fragment
stack completed — **by extending existing seams, never by building a parallel subsystem**.

---

## 3. Scope

This release is **foundation-first** (D-3): the shared adapter base lands before the
per-harness fidelity work, which lands before the workflow waves. The six picked items map
to five execution waves (A→E); see PLAN.md for the wave spine.

### 3.0 Anti-slop framing (binding for every item)

Every item **EXTENDS an existing seam**; none introduces a parallel system:

- Item 1 hoists shared logic **into one base over the three existing adapters** — it does
  not rewrite the adapters.
- Item 5 adds a workflow-handoff layer **beside** the existing generic `handoff-v1.1`
  contract, on the **existing** `LifecycleRun` (additive field) + `runtime_files`
  run-artifact zone + `RetentionSweep` — generic `handoff-v1.1` is untouched.
- Item 6 replaces stubs with real workflow bodies **on the v0.1.24 fragment+gate engine**,
  mirroring the shipped `release_definition` body — it does not re-author the engine.
- Item 4 extends the **existing** profile registry + overlay store + resolver.
- Item 3 adds a PI entry to the **existing** telemetry reader/registry set.

### 3.1 Item 1 — shared-headless-adapter-base (FOUNDATION)

**Scope:** hoist the duplicated invariants out of `pi_runtime.py`, `codex_runtime.py`, and
`claude_sdk_runtime.py` into one shared headless-adapter base, factored so the
non-CLI Claude SDK adapter reuses the common parts (redaction + git seam) without
inheriting the subprocess machinery.

**Ships:**
- A shared home (e.g. `dadaia_workspace/infrastructure/headless_adapter_base.py`) carrying:
  `_redact` + `_SECRET_NAME_PARTS`; the `_GitDiffPort` Protocol + `_with_changed_paths`
  override; `_env` env-allowlist filtering; the `Runner` subprocess seam type; and the
  shared `_prompt` JSON-envelope builder (`role`, `prompt`, `context`, `release_id`,
  `task_id`, `allowed_paths`, `forbidden_paths`, `expected_schema`, `required_evidence`).
- `pi_runtime` and `codex_runtime` import the subprocess-capable parts; `claude_sdk_runtime`
  reuses redaction (and the git seam for `changed_paths` parity) **without** the subprocess
  bits. Per-adapter modules keep only the genuinely CLI-specific `_command` builder and
  result/stream extraction (`_result_from_output`, `_last_message_end`, the
  `--output-last-message` read, the JSONL parse).
- A test that fails if redaction or the `changed_paths` override **diverges** between
  adapters (single-source proof).

**Explicitly out:** any behavior change to redaction, the env allowlist, or the
`changed_paths` git-diff override. This is a pure de-duplication: behavior is byte-for-byte
preserved; the existing per-adapter unit suites must stay green unchanged.

**Acceptance:**
- A1. Zero verbatim copies of `_redact`/`_SECRET_NAME_PARTS`,
  `_GitDiffPort`/`_with_changed_paths`, and `_env`/allowlist across the three real adapters
  (grep-verifiable: each invariant defined once, imported elsewhere).
- A2. Per-adapter modules retain only `_command` + result/stream extraction as adapter-local
  logic.
- A3. A new divergence test fails if any adapter's redaction or `changed_paths` behavior
  differs from the shared base.
- A4. The existing `test_pi_runtime.py`, `test_codex_runtime.py`, and the Claude SDK adapter
  tests pass **unchanged** (behavior preservation).
- A5. `mypy --strict` + import-linter green (the base lives in `infrastructure`; no new
  layer violation).

**Consumes assessment:** the item's three intents (hoist out of each of the three adapters)
all ship → **fully consumed → declared**.

### 3.2 Item 2 — codex-runtime-fidelity (residual WS-CDX-PROTOCOL + WS-CDX-HYGIENE)

**Scope:** the residual only. v0.1.13 already shipped WS-CDX-VERIFY / WS-CDX-BUGFIX /
WS-CDX-MODEL.

**Ships:**
- **WS-CDX-PROTOCOL** — make the by-name rule-law corpus (`workspace-protocol`,
  `release-governance`, …) demonstrably reachable from a Codex session. Per the GRILL,
  resolve via `transform_for_codex` (on-disk path transform + read instruction) and/or a
  Codex-visible surface in `public/data/AGENTS.md`: every by-name citation in a
  Codex-projected artifact either resolves to a path Codex can read, or is rewritten to a
  reachable surface. No Codex-projected artifact cites a law surface Codex cannot reach.
- **WS-CDX-HYGIENE** — surface the Codex interactive-vs-headless trust boundary honestly:
  an onboarding note + a `dadaia` doctor INFO line stating "Codex interactive hooks fire and
  block; `codex exec` headless does not". Resolve the `.codex/workflows/` keep-or-drop
  decision (it has no physical projection today — record the decision and remove any inert
  projection reference in `public_assets.py`/`codex_doctor.py`). Drop any remaining inert
  config keys from the `.codex/` projection.

**Explicitly out:** a full per-persona fleet rewrite beyond what reachability requires; any
new Codex headless hook capability (the trust boundary is stated honestly, not changed).

**Acceptance:**
- A6. A test (or doctor check) proves the load-bearing rule corpus is reachable from a Codex
   session, OR that every by-name citation in a Codex-projected artifact points at a
   reachable surface.
- A7. `dadaia doctor` (or `codex_doctor`) emits an INFO line stating the Codex
   interactive-vs-headless trust boundary; onboarding documents it.
- A8. The `.codex/workflows/` keep-or-drop decision is recorded and any inert reference is
   removed; no inert config key remains in the `.codex/` projection (doctor green).
- A9. `dadaia public doctor` stays `[ok]` after re-projection.

**Consumes assessment:** WS-CDX-PROTOCOL + WS-CDX-HYGIENE are the item's only two open
intents (VERIFY/BUGFIX/MODEL already shipped v0.1.13); both ship → **fully consumed →
declared**.

### 3.3 Item 3 — pi-agent-fourth-harness (WS-PI-6 ONLY)

**Scope:** WS-PI-6 only. WS-PI-1..4 shipped v0.1.18–v0.1.21. **WS-PI-5 is DEFERRED**
(GRILL D-2) and is OUT of this release.

**WS-PI-6 determination — IMPLEMENT (a real local session source exists).** The telemetry
panel reads each runtime's **local session store**: Claude reads
`~/.claude/sessions/<id>.json`; Codex reads `~/.codex/state_5.sqlite` + `~/.codex/history.jsonl`
(see `features/telemetry/reader/codex.py` + `aggregator/runtimes.py#ADAPTER_REGISTRY`). The
academy doc `08_pi_agent/02_operacao_cli_sessoes_e_contexto.md` (official PI consult
2026-05-09) documents that **PI persists sessions per directory at
`~/.pi/agent/sessions/`**. A real consumable local session source therefore EXISTS — so the
honest outcome is **implement WS-PI-6**, not close it as not-applicable. The anti-slop guard
(no telemetry adapter without a source) is satisfied.

**Ships:**
- A `PiRuntimeAdapter` in `features/telemetry/aggregator/runtimes.py` (enrichment +
  liveness), plus a `"pi"` entry in `ADAPTER_REGISTRY`. Liveness reads only metadata
  (session-file mtime under `~/.pi/agent/sessions/`), mirroring the Claude/Codex liveness
  posture; cost is unknown for PI (no per-event pricing) → `cumulative_cost_usd=None`,
  `cost_known=False` (the Codex posture), never faked.
- A `reader/pi.py` incremental reader that ingests PI session metadata into the telemetry
  store, mirroring `reader/codex.py` (privacy invariant T1: metadata only — no message
  bodies, no content).
- An academy module documenting PI as the fourth harness (enter-pi flow, trust boundary,
  per-step `--harness pi`).

**Explicitly out (WS-PI-5, DEFERRED — D-2):** the destructive DEAD-mark of the standalone
`dadaia-pi-workspace` context, and its deprecation `README.md`. `dead()` auto-commits +
pushes (leak risk) and is operator-gated. This release does **not** touch the
`dadaia-pi-workspace` repo/context. Because WS-PI-5 remains open, `pi-agent-fourth-harness`
is **NOT** fully consumed and is **NOT** `**Consumes:**`-declared; at CLOSURE it stays in
the live backlog rewritten to the WS-PI-5 residual only.

**Live-shape caveat:** the exact `~/.pi/agent/sessions/` artifact shape (jsonl vs sqlite per
directory) must be live-verified against the pinned `pi` build before the reader is
finalized; the unit suite is fully faked with a canned session fixture, and the reader
degrades gracefully (idle) on any parse/IO failure, exactly as the Codex reader does. If
live verification proves PI does **not** persist a machine-consumable artifact after all,
the fallback is to close WS-PI-6 as not-applicable with that evidence recorded — but the
documented source means the planned path is implement.

**Acceptance:**
- A10. `ADAPTER_REGISTRY` carries a `"pi"` adapter; `get_adapter("pi")` returns it; the
   adapter classifies liveness from `~/.pi/agent/sessions/` mtime (active/idle/ended) and
   degrades to `idle` on any IO/parse failure.
- A11. `reader/pi.py` ingests faked PI session metadata into the store (unit-tested with a
   canned fixture); privacy invariant T1 holds (no content read).
- A12. PI sessions appear in the panel Agents/Sessions tab when a real local source exists.
- A13. The academy module documents PI as the fourth harness.

### 3.4 Item 4 — workflow-model-governance-operator-profiles-and-context-overlays

**Scope:** operator-added PI profiles + per-context overlay `extends` inheritance + the 3
v0.1.29 code-reviewer LOW nits.

**Ships:**
- **WS-PROFILES** — load + validate operator profiles from a new local store
  `.dadaia/states/workflow_model_profiles.local.json`, merged with the built-in recommended
  profiles surfaced by `model_profiles.list_profiles()` / `profiles_for(harness)`. A new
  infrastructure adapter + a `core/protocols` port wired through `container.py`. Invariants:
  validate `harness: pi` on every operator-added profile; **never store API keys** in the
  local store; **never project** the local store into `public/`; preserve
  `UnknownProfileError` fail-closed.
- **WS-OVERLAYS** — honor non-`default` context keys in `workflow_model_policy.json` with an
  `extends` chain (`context → extends… → default`) in
  `WorkflowModelPolicyOverlay.overlay_for` / `workflow_default_harness` / `step_harness` and
  the `policy_resolver` per-step resolution, replacing the D-2 collapse where a non-default
  key is inert. Guardrails: cycle detection on `extends`; a missing `extends` parent is a
  hard validation error (never a silent fallthrough); `default` stays the inheritance root.
  Extend `_ALLOWED_TOP_LEVEL` / schema for `extends` additively.
- **WS-NITS** — (i) de-duplicate `_DEFAULT_PROFILE_BY_HARNESS_PURPOSE` (verbatim twin in
  `policy_resolver.py` and `features/workflows/dadaia_catalog.py`) into one shared home,
  guarded by the existing `_assert_catalog_defaults_resolve`; (ii) correct the
  `policy_resolver.py` module docstring to name `governed_workflow_catalog()` as the
  production resolver source; (iii) make panel `_semantic_check`
  (`features/panel/views/workflow_policy.py`) mirror the doctor's explicit 3-map union
  (`contexts | default_harness_overlay | step_harness_overlay`) instead of relying on the
  empty-steps parse side effect.

**Explicitly out:** the v0.1.28 code-reviewer MEDIUM (snapshot `runtime_kind` vs governed
harness) — already resolved by D-2 (do NOT re-file); non-PI operator profiles (PI-scoped
this release).

**Acceptance:**
- A14. An operator can register a PI profile in
   `.dadaia/states/workflow_model_profiles.local.json` and have it selectable by a governed
   step; the local store carries no API key; `dadaia public doctor` stays `[ok]
   public-privacy` (the store is never projected).
- A15. A non-`default` context key with `extends` resolves a step's profile through the
   inheritance chain; an unresolvable ref or a broken `extends` parent fails closed with an
   actionable error; an `extends` cycle is rejected.
- A16. A v0.1.28/v0.1.29 overlay with no `extends` parses and resolves exactly as before
   (back-compat: overlay schema additive).
- A17. `WMP-*` governance doctor + panel `_semantic_check` agree on the resolved overlay map
   (no parse-side-effect-only coverage); `_DEFAULT_PROFILE_BY_HARNESS_PURPOSE` has one home;
   the `policy_resolver` docstring is corrected; `mypy --strict` + import-linter + suite
   green.

**Consumes assessment:** WS-PROFILES + WS-OVERLAYS + the 3 WS-NITS are the item's full open
intent set; all ship → **fully consumed → declared**.

### 3.5 Item 5 — workflow-step-handoff-data-plane-cleanup (CRITICAL)

**Scope:** the run-scoped workflow handoff ledger. Sliced A→B (core + cleanup) this release;
panel visibility (Slice C) and broad workflow adoption (Slice D) are bounded below.

**Grill-resolved design parameters (the GRILL §16 questions, binding):**
- Storage boundary: `LifecycleRun` control plane + immutable
  `.dadaia/runs/lifecycle/<run_id>/steps/*.step-payload.json` data plane; `.dadaia/handoff`
  stays reserved for durable external evidence (security/report/closure). **Confirmed.**
- Payload schemas: real JSON Schema files for the **envelope**
  (`workflow-step-payload-v1`) + the `lifecycle-run-workflow-steps-v1` shape in this
  release; per-`output_schema` payload schemas (`release-scope-handoff-v1`, …) added as
  Python validators now, schema files following incrementally (Slice D).
- Default retention for internal consumed payloads: **delete-after-consumed** with a
  consumed TTL (default 24h) — survives a short post-run debugging window, then reclaimed.
- Promote-to-evidence by default for: review verdict payloads + the consumed_backlog ledger
  (these feed CLOSURE/report/panel); transient prompt-to-prompt payloads stay
  delete-after-consumed.
- Failed/blocked runs keep all step payload artifacts until a longer failure TTL (for
  investigation), never reclaimed while the run is live.
- Implementation/review loop max automatic retry: a bounded retry count (default 2) before
  the workflow BLOCKS for operator intervention.

**Ships:**
- `core/models/workflow_handoff.py` (NEW) — `WorkflowStepRecord` /
  `WorkflowStepConsumerRecord` / attempt ledger; added to `LifecycleRun` as a
  **backward-compatible** `workflow_steps` field (old run records with no `workflow_steps`
  key still load — additive, mirroring how `workflow_policy` was added).
- `public/schemas/workflow-step-payload-v1.schema.json` +
  `public/schemas/lifecycle-run-workflow-steps-v1.schema.json` (NEW).
- `features/lifecycle/workflow_handoffs.py` (NEW) — the resolver/service: allocate the
  run-scoped step-artifact dir; write immutable step payloads atomically; validate envelope
  + named payload schema; resolve a step's declared upstream refs from
  `LifecycleRun.workflow_steps`; render compact digests (not raw JSON) into the next prompt;
  record consumption atomically through the existing run store; compute cleanup eligibility.
- `infrastructure/runtime_files.py` — `write_run_artifact` persists step payloads under
  `.dadaia/runs/lifecycle/<run_id>/steps/` (extend the existing run-artifact write; the
  `runs/lifecycle` canonical-zone confinement already exists).
- `features/lifecycle/workflows/release_definition.py` — declare per-`ReleaseStep`
  `produces`/`consumes` edges; write+validate the step payload after each model result;
  inject upstream digests through the workflow resolver (not `ContextSelector._handoffs()`);
  the terminal `definition_commit_gate` validates graph completeness.
- `features/lifecycle/context_selector.py` — route required prompt-to-prompt handoff
  selection through the workflow resolver; keep `previous-handoff-only` for legacy/manual
  contexts only; render handoff digests (verdict/summary/findings/refs), not raw JSON.
- `features/lifecycle/antislop/retention.py` — protect live-run step artifacts (via the
  existing `live_claims` injection extended with step payload refs) and reclaim `consumed_all`
  eligible payload artifacts past their consumed TTL; prune empty run dirs (the
  `_prune_empty_parents` machinery already exists).
- `features/lifecycle/hygiene.py` — count workflow-step payloads separately from generic
  handoffs (produced/consumed/orphan/malformed states).
- A `dadaia lifecycle handoffs doctor` check (or fold into `hygiene status`) per GRILL.
- Fix the `public/lifecycle_fragments/shared/output-handoff.md` field mismatch
  (`detail_md` vs `detail`) so the bug is not copied into the workflow-step schema.

**Explicitly out:** mutating the generic `handoff-v1.1` schema (forbidden — additive
separate schema only); SQLite / a queue server (queue semantics live in the Python
resolver — GRILL-confirmed); the full panel Workflows-tab data-plane view beyond a minimal
API exposure of the run ledger (the rich graph is sequenced with the panel control-plane
follow-up); applying the ledger to **all** other workflow bodies (Slice D) — this release
wires release-definition + the implementation/review loop (attempt tracking) only.

**Acceptance (GRILL §15 distilled, falsifiable):**
- A18. A release-definition fake run records `LifecycleRun.workflow_steps` and writes one
   immutable step payload artifact per producing model step under
   `.dadaia/runs/lifecycle/<run_id>/steps/`.
- A19. `spec_create` consumes the exact `release_scope` payload by run id + producer step +
   attempt — NOT "latest handoff by agent filename".
- A20. A missing or malformed required upstream payload BLOCKS the workflow before the next
   prompt runs.
- A21. Every step payload validates envelope + named payload schema.
- A22. Consumption transitions `produced → consumed_partial → consumed_all` are recorded per
   downstream step; a payload is cleanup-eligible only after every declared consumer consumed
   it.
- A23. Retention dry-run reports eligible consumed payloads; apply deletes only eligible ones
   and prunes empty run dirs; promoted/current-release evidence survives; live-run artifacts
   are never reclaimed.
- A24. The implementation/review loop proves `implement#2` consumes the `qa#1` rejection, not
   `qa#0` / an unrelated run; the bounded retry count (default 2) BLOCKS for operator
   intervention when exceeded.
- A25. No workflow code uses "latest handoff by agent filename" for required
   prompt-to-prompt communication.
- A26. `dadaia lifecycle handoffs doctor` (or equivalent) fails on orphan, malformed, stale,
   undeclared, and unconsumed-required payloads.
- A27. Old `LifecycleRun` records (no `workflow_steps` key) still load (back-compat).

**Consumes assessment:** the item's five intents (LifecycleRun ledger; runtime_files step
payloads; context_selector run-manifest lookups; release_definition produces/consumes +
terminal gate; retention protect/reclaim) all ship this release → **fully consumed →
declared**. (Slice C panel-rich-graph and Slice D broad adoption are explicitly bounded
follow-ups, not open intents on this item's frontmatter.)

### 3.6 Item 6 — lifecycle-prompt-fragments-ai-surface-dehydration (CRITICAL)

**Scope:** WS-A (real `audit`/`research`/`bug_report` workflow bodies) + WS-C (ctx-inject
dehydration). WS-B (deep AGENTS.md dehydration + AI-surface doctor) and WS-D (independent
fragment versioning, OQ-6) are bounded below.

**Grill-resolved open decisions (the epic §6 questions, binding):**
- OQ-3 (backlog-author role): `project-manager` curates backlog; `product-engineer` reads it
   to author SPEC/PLAN/TASKS — the docs must stop contradicting. (`backlog_definition` is
   owned by FEAT-BACKLOG-DEFINITION-WORKFLOW-01, NOT this epic — already shipped v0.1.26/27.)
- OQ-4 (old mandatory-lifecycle skills): retain as banner-marked human/manual-entry docs;
   the procedural lifecycle content moves into fragments+gates (WS-B doctor enforces no
   reintroduction — see bounded scope).
- OQ-6 (fragment versioning): **resolved by explicit deferral with rationale** — the
   fragment engine is single-version this release; independent per-fragment versioning is
   deferred behind a concrete archived-replay need (recorded in CLOSURE). WS-D is NOT
   implemented this release; the decision (defer) IS recorded, satisfying the epic's "OQ-6
   resolved" acceptance.
- OQ-7 (max prompt budget per step per harness): adopt the existing `max_context_policy`
   bounds as the budget mechanism; no new per-harness numeric cap this release.

**Ships:**
- **WS-A** — replace the fail-loud `_deferred.py` stubs for `audit`, `research`, and
  `bug_report` with real fragment+gate workflow bodies, mirroring the shipped
  `release_definition` body: per-step role, fragment bundle, dynamic-context selector inputs,
  output schema, Python transition gates, and `record_injected_context` auditability. Bugs
  stay additive-safe (`specs/bugs/` ADDITIVE class — no lease, never blocked); audits produce
  disposition-ready output. These bodies use the Item-5 workflow-handoff ledger for their
  step communication (cross-wave dependency — see PLAN E-after-D ordering).
- **WS-C** — reduce broad `ctx_inject` session-memory injection so lifecycle prompts get
  context from the Python dynamic selector (`ContextSelector`), not session-bootstrap side
  effects. Keep `ctx_inject` for bind/session safety + the lean generic preflight; keep
  `pre_gate`/chokepoints as safety rails (unchanged).

**Explicitly out:**
- WS-B deep AGENTS.md/skill dehydration + the AI-surface doctor check — **bounded follow-up**
   this release: WS-A + WS-C are the CRITICAL completion; WS-B's fleet-wide doctor + deep
   surface shrink is a larger surface tracked as the item's residual. (If WS-A/WS-C close
   the CRITICAL path and WS-B remains, the item is NOT fully consumed — see Consumes note.)
- Re-doing the v0.1.24-delivered fragment engine / loader / selector / release-definition
   body / panel catalog / observability.
- Removing Layer-1 safety hooks; changing the SDD specs folder format; adding new harnesses.

**Acceptance:**
- A28. `audit`, `research`, and `bug_report` run as real fragment+gate workflow bodies (no
   fail-loud stub); each records injected fragments + dynamic context for auditability; a
   test asserts they no longer raise `NotImplementedError` and that each advances/blocks via
   its Python gate. `_deferred.py` no longer lists them in `DEFERRED_WORKFLOWS`.
- A29. The `bug_report` body writes only ADDITIVE paths (`specs/bugs/`); the `audit` body
   produces disposition-ready output.
- A30. No lifecycle prompt requires broad session-memory injection to work; `ctx_inject` is
   reduced to bind/session safety + lean generic preflight (a test proves a lifecycle step
   prompt is fully composed from the dynamic selector without ctx-inject side effects).
- A31. OQ-6 is resolved (deferred) with a recorded rationale; OQ-3/OQ-4/OQ-7 decisions are
   reflected in the affected docs/fragments.
- A32. `dadaia specs doctor` + `dadaia public doctor` pass after projection.

**Consumes assessment:** WS-A + WS-C ship and are the CRITICAL completion path; **WS-B**
(deep AGENTS.md dehydration + AI-surface doctor) and **WS-D** (fragment versioning, beyond
the OQ-6 decision) are bounded as residual. Because WS-B's deep-dehydration intent does not
fully ship, the honest call is: this item is **partially consumed → declared anyway IFF the
operator confirms WS-A+WS-C+the OQ resolutions satisfy the item's open frontmatter intents**
(the three frontmatter intents are exactly WS-A audit, WS-A research, WS-C — all ship). The
frontmatter carries only those three intents → **declared**; WS-B/WS-D are epic-body breadth
beyond the declared intents and stay tracked in the epic body. (Resolved scope ambiguity —
see Return note.)

---

## 4. Out of scope

- **WS-PI-5 (DEFERRED — D-2):** the destructive DEAD-mark of `dadaia-pi-workspace` and its
  deprecation README. Operator-gated (`dead()` auto-commits + pushes → leak risk). This is
  why `pi-agent-fourth-harness` is NOT `**Consumes:**`-declared; it stays in the live backlog
  rewritten to the WS-PI-5 residual at CLOSURE.
- Excluded backlog (D-1): `model-tier-efficiency`, `telemetry-tier2-chmod`,
  `sdd-governance-v2-agents-lifecycle` — stay candidate.
- Item-5 Slice C rich panel Workflows-tab data-plane graph (beyond minimal API exposure) and
  Slice D broad ledger adoption across all workflow bodies.
- Item-6 WS-B deep AGENTS.md/skill dehydration + AI-surface doctor, and WS-D independent
  fragment versioning implementation (OQ-6 decision is recorded; implementation deferred).
- Any new harness; plugin packs; SQLite / queue-server backend; mutating `handoff-v1.1`.
- Implementation itself: **this release is DEFINE-ONLY (D-4)**. Deliverable now is approved
  SPEC/PLAN/TASKS + a DEFINITION review (architect + qa). STOP before implementation.

---

## 5. Laws (binding — from GRILL "Carried-forward laws" + §3-style invariants)

- **L1 — Layer-2 = codex | pi only.** `claude` is a test/SDK adapter and `opencode` is
  removed; neither is a Layer-2 worker. Every new profile/overlay harness value is validated
  against `{codex, pi}`.
- **L2 — No fake telemetry.** A runtime telemetry adapter ships ONLY with a real local
  session source. WS-PI-6 implements because `~/.pi/agent/sessions/` is a real documented
  source; if live verification disproves it, the item closes not-applicable with evidence —
  never a placeholder adapter.
- **L3 — Default-first.** A workflow is runnable before any operator overlay/profile exists;
  a **missing** overlay/local-profile store falls back to library defaults; only a
  **present-but-invalid** store fails closed.
- **L4 — Auditability snapshot.** Governance is resolved once and frozen per run
  (`WorkflowPolicySnapshot`); each workflow step records its injected fragments + dynamic
  refs (`record_injected_context`); each handoff records its producer/consumer edges.
- **L5 — Resolve-once-before-step-1.** Policy/harness/model resolution happens before the
  first worker step; an in-flight run reads the frozen snapshot, never the live overlay.
- **L6 — Never delete a backlog/bug/audit file.** Disposition via status token only (the
  CLOSURE disposition sweep). `pi-agent-fourth-harness` is rewritten to its WS-PI-5 residual,
  not removed.
- **L7 — Additive back-compat.** `LifecycleRun.workflow_steps`, the overlay `extends` field,
  and the local-profile store are all additive: old run records and old overlays load and
  resolve unchanged.
- **L8 — Privacy.** No secrets/API keys in the local-profile store; the store is never
  projected into `public/`; telemetry readers read metadata only (invariant T1).

---

## 6. Memory files affected at closure

(Updated at CLOSURE, not now — DEFINITION authorship defers memory to CLOSURE per the
constitution §13 / `dadaia-release-closure` skill.)

- `specs/memory/architecture.md` — the headless-adapter base layer; the workflow-handoff
  data-plane (control plane = `LifecycleRun`, data plane = run-scoped step payloads); the
  real audit/research/bug_report workflow bodies.
- `specs/memory/tech-stack.md` — pinned `pi` build for the session-store reader (if WS-PI-6
  implements); no new locked dependency expected.
- `specs/memory/product/index.md` + affected feature atoms — PI telemetry surface; workflow
  model-governance operator profiles + per-context overlays; the workflow handoff data plane.

---

## 7. Dependencies and risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | The shared-base dedup silently changes the security-sensitive secret-scrub or `changed_paths` override | HIGH | A1–A4: pure de-dup, behavior byte-preserved; existing per-adapter suites pass unchanged; a divergence test pins single-source behavior; security-reviewer gate at review |
| R2 | Cross-wave coupling: Item-6 WS-A bodies depend on Item-5 handoff ledger; Item-2/3 depend on Item-1 base | HIGH | Foundation-first wave spine (A→E); each wave has a green checkpoint before the next; PLAN justifies the ordering |
| R3 | Retention/cleanup deletes a live or promoted payload (data-loss) | HIGH | Reuse the existing guarded `RetentionSweep` ladder (escape→live→important→TTL, dry-run default); extend `live_claims` with step refs; promote review-verdict + consumed_backlog payloads; A23 proves live/promoted survive |
| R4 | WS-PI-6 live `~/.pi/agent/sessions/` shape differs from the documented consult | MEDIUM | Unit suite fully faked + graceful idle degradation; live-shape verified against pinned `pi` before finalizing; fallback = close not-applicable with evidence |
| R5 | Overlay `extends` cycle / missing parent causes infinite loop or silent fallthrough | MEDIUM | Cycle detection + hard error on missing parent (A15); `default` is the inheritance root |
| R6 | WS-CDX-PROTOCOL fleet change is larger than the residual budget | MEDIUM | Bound to reachability (path transform / AGENTS.md surface), not a per-persona rewrite; A6 is satisfied by reachability OR rewritten citations |
| R7 | Scope creep — this is a large super release | MEDIUM | Slices/bounded-out sections per item; D-4 DEFINE-ONLY checkpoint lets the operator prune before any wave runs |
| R8 | `handoff-v1.1` accidentally mutated for workflow fields | MEDIUM | Separate `workflow-step-payload-v1` schema; generic schema is explicitly out of scope |

**Upstream/sequencing dependencies:** Wave A (shared base) blocks Waves B (PI/Codex
fidelity). Wave D (handoff ledger) blocks Wave E WS-A (the new workflow bodies consume the
ledger). Wave C (governance) is independent of A/B but precedes D/E for review cadence. See
PLAN.md for the full spine and justification.
