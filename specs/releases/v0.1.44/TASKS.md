# TASKS — Release: v0.1.44

**Status:** Aprovado
**Release ID:** v0.1.44
**Owner:** product-engineer
**Opened:** 2026-06-30

> Markers: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. At most one `[-]` per owner
> unless disjoint write sets are declared. Owners: `ai-engineer` (persona/fragment text +
> public docs), `software-engineer` (Python wiring/tests/doctor), `product-engineer`
> (memory atoms + constitution, DEFINITION/CLOSURE only).

---

## AC-1 — Persona library + PersonaLoader

### [x] T-44-1 — Shared FrontmatterDocLoader base (loader DRY)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/_frontmatter_doc.py` (new base:
  `_split_frontmatter` + str/list key-validation loop + `_FORBIDDEN_TOKENS` /
  `forbidden_token_in` harness-token lint),
  `dadaia_workspace/features/lifecycle/fragments/loader.py` (refactor onto the base),
  `tests/.../` (loader tests stay green)
- **Precondition:** none
- **Done:** frontmatter split + key validation + harness-token lint live in ONE base both
  loaders parameterize (architect MEDIUM — preferred over recording duplication);
  `FragmentLoader` is refactored onto it with existing fragment-loader tests green and no
  behavior change.

### [x] T-44-2 — Author the 8 persona atoms
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/personas/{ai-engineer,code-reviewer,product-engineer,project-auditor,qa-engineer,security-reviewer,software-architect,software-engineer}.md`
- **Precondition:** T-44-1 (token list finalized)
- **Done:** 8 atoms, each with frontmatter `{id, role, summary, source_agent,
  harness_universal}` semantically aligned to `public/agents/<role>.md`, zero forbidden
  harness tokens, no `project-manager` atom. Cross-reference `source_agent` set.

### [x] T-44-3 — PersonaLoader + validation + lint + dangling-ref guard
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/personas/loader.py`,
  `dadaia_workspace/features/lifecycle/personas/__init__.py`,
  `tests/.../test_persona_loader.py`
- **Precondition:** T-44-1, T-44-2
- **Done:** `PersonaLoader` parameterizes the FrontmatterDocLoader base
  (load/validate/lint/list/default); `validate_all()` loads all 8 AND asserts each
  persona's `source_agent` resolves to an existing `public/agents/<role>.md`
  (**dangling-reference guard**); tests: forbidden-token body raises; persona id set ==
  the 8 non-PM roles and excludes `project-manager`; **negative — a dangling
  `source_agent` raises**; **negative — a missing required key raises** (real coverage).

## AC-2 — Persona injection seam

### [x] T-44-4 — Add `persona` field to PromptScope + AgentRunRequest
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/prompt_builder.py`,
  `dadaia_workspace/core/models/lifecycle.py`, `tests/.../test_prompt_builder.py`
- **Precondition:** none (additive)
- **Done:** `PromptScope.persona: str | None = None` and
  `AgentRunRequest.persona: str | None = None`; `LifecyclePromptBuilder.build()` threads
  `scope.persona` into the request; a **direct** test asserts `build()` copies
  `scope.persona → request.persona` (QA advisory — not only transitive); mypy --strict
  green.

### [x] T-44-5 — Emit persona as operative directive in build_prompt_envelope (byte-stable)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/headless_adapter_base.py`,
  `tests/.../test_prompt_envelope.py`
- **Precondition:** T-44-4
- **Done:** when persona is present, the envelope carries it as an **operative directive**
  that explicitly tells the worker to **act per** the persona mandate (not an inert
  sibling key); the key is included **only when present**; persona-less payload is
  byte-identical to the prior output (regression test asserts byte-equality); a test
  asserts the **directive** text (not just the mandate body) is present.

### [x] T-44-6 — Resolve role→persona in pipeline._scope (single + multi-role + shared)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/pipeline.py`,
  `tests/.../test_pipeline_persona.py`
- **Precondition:** T-44-3, T-44-4
- **Done:** `_scope()` resolves `step.role` (comma-split) to persona body(ies); `shared`
  / no-atom → `persona=None`; multi-role joins each mandate; tests: `spec-create`
  (product-engineer) envelope carries the persona **operative directive**, `role: shared`
  step has no persona block, multi-role (`plan-review`) carries both mandates directed.

## AC-3 — Fragment role reassignment (D-1)

### [x] T-44-7 — Reassign the 7 PM-role fragments
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/lifecycle_fragments/release_definition/release-scope.md`,
  `.../backlog_definition/intake_grill.md`, `.../backlog_definition/conflict_resolution_grill.md`,
  `.../research/research-scope.md`, `.../research/synthesis.md`,
  `.../audit/triage.md`, `.../bug_report/bug-intake.md`
- **Precondition:** none
- **Done:** scope/grill/synthesis → `product-engineer`; `audit/triage` + `bug-intake` →
  `project-auditor`; no non-`shared` fragment retains `role: project-manager`.

### [x] T-44-8 — Update worker-step catalog/pipeline role bindings
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/lifecycle/` (workflow catalog/pipeline
  construction naming a `project-manager` worker step), `tests/.../`
- **Precondition:** T-44-7
- **Done:** no worker step binds `role=project-manager`; v0.1.43 no-orphan/no-generic
  fragment guardrail suite green; a test asserts no non-shared fragment role is
  `project-manager`.

## AC-4 — Fragment/persona optimization audit + anti-regression guardrail

### [x] T-44-9 — Anti-regression: every RESOLVED pipeline-step role → non-PM persona
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/specs_doctor/` (or the doctor rule home) +
  `tests/.../test_persona_resolution_guardrail.py`
- **Precondition:** T-44-3, T-44-6, T-44-7, T-44-8
- **Done:** a doctor rule (+ unit test) enumerates the **actual resolved role of every
  model-driven pipeline step using the SAME resolution path as `pipeline._scope()`** (NOT
  a fragment rglob) and FAILS if any resolves to no persona atom or to `project-manager`;
  passes on the current tree; **TWO** negative fixtures make it FAIL — (a) a
  **fragment-layer** role with no persona atom, (b) a **catalog-layer** worker step bound
  to `project-manager`/an unmapped role — proving both surfaces are covered. Negative
  fixtures live under **tmp/fixture roots** (`tmp_path` / `.dadaia/tmp/`), NOT under
  `public/lifecycle_fragments/`, so pass-on-current-tree + `public doctor` stay clean.

### [x] T-44-10 — Fragment/persona optimization pass
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/lifecycle_fragments/**` (only fragments the
  audit flags)
- **Precondition:** T-44-2, T-44-7, T-44-9
- **Done:** fragment bodies that duplicate persona mandate are trimmed/aligned; audit
  findings recorded for CLOSURE — **including a note that the `ai-engineer` persona is
  INTENTIONALLY unreferenced (roster symmetry), not dead code (R4)**; guardrail (T-44-9) +
  fragment guardrail suites green.

## AC-5 — pi model openness

### [x] T-44-11 — Layer-2-native model allowlist (REGISTRY untouched)
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/harness_models.py`, `tests/.../test_harness_models.py`
- **Precondition:** none
- **Done:** add `LAYER2_EXTRA_MODEL_IDS: frozenset[str]` (or a small `Layer2Model` record
  with explicit price/effort) in `harness_models.py` carrying the curated OpenRouter ids
  (`kimi-2.7` + confirmed curated set); **`model_registry.py:REGISTRY` is NOT modified** —
  the synthetic-alias approach is rejected (would break `codex_tier_views()` on the codex
  runtime hot path). Pricing stays honest (explicit Layer-2 price OR `compute_cost` →
  `None`; **no fabricated registry pricing row**). Tests: `REGISTRY` is unchanged and
  `codex_tier_views()` resolves without `ValueError`; exact id set recorded for CLOSURE.

### [x] T-44-12 — Extend pi catalog + relax invariant to allowlist union
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/harness_models.py`, `tests/.../test_harness_models.py`
- **Precondition:** T-44-11
- **Done:** `_CATALOG[PI_HARNESS]` includes the OpenRouter option(s); codex catalog
  unchanged; `_assert_ids_known()` validates against `_known_codex_ids() |
  LAYER2_EXTRA_MODEL_IDS`, keeps the `claude-*` rejection, drops "GPT-only" framing; tests:
  OpenRouter ids accepted via the union, a `claude-*` id still raises, an id outside the
  union raises.

### [x] T-44-13 — Allowlist-validated operator-overlay pi registration
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/json_local_model_profile_store.py`,
  `tests/.../test_local_model_profile_store.py`
- **Precondition:** T-44-11
- **Done:** an operator pi profile whose `model_id` is outside `_known_codex_ids() |
  LAYER2_EXTRA_MODEL_IDS` is rejected; a union-present pi id is accepted; existing
  `harness == pi` constraint preserved; tests cover both paths.

### [x] T-44-14 — Verify pi_runtime passthrough
- **Owner:** software-engineer
- **Write set:** `tests/.../test_pi_runtime.py` (expected no source edit)
- **Precondition:** T-44-12
- **Done:** a test asserts a selected OpenRouter id flows through
  `pi --mode json --model <id>` unchanged; if an edit to `pi_runtime.py` is needed, it is
  minimal and recorded.

## AC-6 — Anti-regression guardrails + docs

### [x] T-44-15 — Doc edits (live source + public): GPT-only → allowlist; persona entity; scoped doc-lint
- **Owner:** ai-engineer (+ software-engineer for the doc-lint test)
- **Write set:** `dadaia_workspace/core/harness_models.py` (module docstring),
  `dadaia_workspace/features/lifecycle/policy_doctor.py` (line ~269 docstring),
  `dadaia_workspace/features/lifecycle/model_profiles.py` (lines ~13,127,196 — docstring +
  two reject messages), relevant `dadaia_workspace/public/rules/*.md` /
  `public/data/AGENTS.md` / agentic doc surface asserting "GPT-only" or omitting the
  persona entity, `tests/.../test_no_gpt_only_claim.py`
- **Precondition:** T-44-12
- **Done:** every **live-source + public-doc** "GPT-only" assertion (incl. `policy_doctor`
  + `model_profiles` reject messages, which would otherwise contradict the relaxed
  invariant) updated to "allowlist-validated (no `claude-*`)"; persona entity documented
  alongside fragments; the doc-lint guardrail is **scoped to live source + public docs,
  EXCLUDING `specs/_archive/` and the v0.1.44 spec text** (so it is satisfiable) and is
  green. MEMORY atoms are out of this task's scope (see T-44-18).

### [x] T-44-16 — Constitution / ADR-B amendment (operator-confirmed)
- **Owner:** product-engineer
- **Write set:** `specs/constitution.md` (and/or the ADR-B reference)
- **Precondition:** explicit operator confirmation (R1)
- **Done:** the GPT-only → allowlist-validated (no `claude-*`) amendment is written only
  after operator confirmation; the no-claude safety bound is explicitly retained.

### [ ] T-44-18 — Update MEMORY atoms asserting GPT-only (DEFINITION/CLOSURE)
- **Owner:** product-engineer
- **Write set:** `specs/memory/architecture.md` (line ~893),
  `specs/memory/product/sdd/lifecycle-foundation.md` (lines ~95,127)
- **Precondition:** T-44-12; ACTIVE.md phase is DEFINITION or CLOSURE (gate-restricted)
- **Done:** the GPT-only assertions in these memory atoms are updated to the
  allowlist-validated (no `claude-*`) reality; memory stays atomic (no changelog); written
  by product-engineer only (NOT ai-engineer); `dadaia specs doctor` clean.

### [x] T-44-17 — Propagate lib-originated assets + full validation
- **Owner:** software-engineer
- **Write set:** (no source files — runs `dadaia public stage && install --target all &&
  public doctor`; surfaced to operator/PM since PE has no Bash)
- **Precondition:** all prior tasks `[x]`
- **Done:** `dadaia public doctor` clean incl. `[ok] public-privacy`; `dadaia specs
  doctor` clean; `pytest` + `mypy --strict` + `ruff` green; persona atoms + edited
  fragments projected to all runtimes with no drift.
