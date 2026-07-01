# SPEC — Release: v0.1.44

**Status:** Aprovado
**Release ID:** v0.1.44
**Owner:** product-engineer
**Opened:** 2026-06-30

---

## 1. Problem and context

The dadaia-workflows assemble each Layer-2 worker step prompt from a **fragment**
(`public/lifecycle_fragments/<workflow>/<step>.md`) plus a stable, cacheable
`PromptPrefix`. The fragment carries a `role:` string that threads
`Fragment → PromptScope.role → AgentRunRequest.role → build_prompt_envelope()` and is
emitted on the wire as **a bare role string only** — the worker is told *which role it
is* but is never handed *the behavioral mandate of that role*. At Layer-1 (Claude) the
sub-agent files under `public/agents/<name>.md` carry that mandate; at Layer-2 (codex/pi)
there is no equivalent entity, so a real PI/Codex worker runs a step with no persona
behind the role token. This is the missing half of the agentic surface.

Two further defects compound it:

1. **PM is mis-modeled as a Layer-2 persona.** Seven step fragments carry
   `role: project-manager`. `project-manager` is the **Layer-1 orchestrator**, not a
   Layer-2 worker persona — dispatching one as a worker is a category error and would
   create a "PM persona" that should not exist (D-1).
2. **pi's model set is closed to GPT-only by construction.** `core/harness_models.py`
   hard-asserts that every Layer-2 catalog id is a non-`claude-*` id present in the
   registry, and the module is documented as "GPT-only by construction" (ADR-B). The
   operator wants pi opened to a curated OpenRouter catalog (e.g. `kimi-2.7`) and to be
   able to register additional validated pi model ids via the operator-overlay store
   **without a code change**.

This release introduces the **persona** entity (the Layer-2 equivalent of a Claude
sub-agent), wires it into every dadaia-workflow step prompt alongside the fragment,
performs a full fragment+persona optimization/audit pass, and opens pi's model set to an
allowlist-validated curated catalog (registry codex ids + a Layer-2-native allowlist).

## 2. Objective

Introduce the harness-universal **persona** entity, inject it alongside the fragment into
every Layer-2 dadaia-workflow step prompt, reassign the seven PM-role fragments to real
Layer-2 personas, and open pi's model set from GPT-only to allowlist-validated (curated
OpenRouter catalog via a Layer-2-native allowlist + operator-overlay registration).

---

## 3. Scope

### AC-1 — Persona library (harness-universal source of truth)

A new persona library at `dadaia_workspace/public/personas/<role>.md`, one atom per
**non-PM core persona** (8): `ai-engineer`, `code-reviewer`, `product-engineer`,
`project-auditor`, `qa-engineer`, `security-reviewer`, `software-architect`,
`software-engineer`. Each persona is **semantically aligned** to its Claude sub-agent
(`public/agents/<name>.md`) but carries **no Claude-isms** — no "Read tool", no sub-agent
dispatch, no `.claude/` / `.codex/` paths — and passes the same harness-universal token
lint the fragments obey. Each persona frontmatter carries a `source_agent` **navigational
pointer** to its source sub-agent, backed by a **dangling-reference guard** (the loader
asserts the pointed-at `public/agents/<role>.md` exists). This pointer + existence guard
does **not** detect content divergence between the two hand-authored mandates — keeping
them aligned is hand-authored discipline, recorded as a known risk (R2), not a solved
problem. A `PersonaLoader` (mirroring `FragmentLoader`) loads, validates frontmatter, and
lints each persona body. `project-manager` deliberately has **no** persona atom (D-1).

- **Frontmatter schema (minimal):** `id`, `role`, `summary`, `mandate`,
  `harness_universal`, `source_agent` (navigational pointer to `agents/<role>.md`).
- **How to verify:** `PersonaLoader.validate_all()` loads all 8 personas with no error
  and asserts each persona's `source_agent` resolves to an existing
  `public/agents/<role>.md`; the persona token-lint rejects a persona body containing any
  forbidden harness token; a test asserts the persona id set equals the 8 non-PM core
  roles and excludes `project-manager`. Negative tests: a **dangling** `source_agent`
  raises, and a **missing required key** raises (keeps loader coverage real).

### AC-2 — Persona injection into the Layer-2 prompt envelope

A persona **body** is resolved from the step's `role:` and threaded into the worker
prompt envelope alongside the fragment.

- Role→persona resolution happens in `pipeline._scope()`
  (`features/lifecycle/pipeline.py:377-393`); a `persona` field is added to `PromptScope`
  (`prompt_builder.py:146`) and to `AgentRunRequest`
  (`core/models/lifecycle.py:367`); `build_prompt_envelope()`
  (`infrastructure/headless_adapter_base.py:236-258`) emits the persona body.
- A step whose role resolves to a persona gets that persona's mandate injected as an
  **operative instruction** — the envelope must explicitly **direct the worker to act
  per** that mandate, not merely carry the body as a present-but-inert sibling key. A
  `role: shared` fragment (the 5 shared fragments) and a step with no resolvable persona
  get **no** persona block (additive-optional, never a placeholder).
- Multi-role fragments (e.g. `plan-review` → `qa-engineer, software-architect`) resolve
  to the **set** of named personas; the envelope carries each named persona's mandate.
- **How to verify:** a unit test builds a scope for `spec-create` (role
  `product-engineer`) and asserts the envelope contains an **operative directive** that
  instructs the worker to act per the persona mandate (not just the mandate text present);
  a test for a `role: shared` fragment asserts **no** persona block; a multi-role test
  asserts both mandates present and directed; byte-stability of `build_prompt_envelope` is
  preserved for persona-less steps.

### AC-3 — Fragment role reassignment (D-1)

Rewrite the `role:` of the seven `role: project-manager` fragments to real Layer-2
personas, per D-1 (scope/grill/synthesis → `product-engineer`; audit/triage →
`project-auditor`):

| Fragment | Old role | New role |
|---|---|---|
| `release_definition/release-scope.md` | project-manager | product-engineer |
| `backlog_definition/intake_grill.md` | project-manager | product-engineer |
| `backlog_definition/conflict_resolution_grill.md` | project-manager | product-engineer |
| `research/research-scope.md` | project-manager | product-engineer |
| `research/synthesis.md` | project-manager | product-engineer |
| `audit/triage.md` | project-manager | project-auditor |
| `bug_report/bug-intake.md` | project-manager | project-auditor |

Any pipeline/workflow-catalog step `role=` binding that names `project-manager` for a
worker step is updated to match. After reassignment **no model-driven step fragment
carries `role: project-manager`**. The v0.1.43 no-orphan / no-generic fragment guardrail
must still pass.

- **How to verify:** a test asserts no `*.md` fragment under `public/lifecycle_fragments/`
  (excluding `role: shared`) has `role: project-manager`; the existing fragment/role
  guardrail suite is green; `dadaia public doctor` is clean after stage+install.

### AC-4 — Fragment/persona optimization audit + anti-regression guardrail

A one-pass audit over every model-driven step confirming each has both a fragment **and**
a resolvable persona (single or multi-role). Trim/align fragments where the audit finds
redundancy or drift against the persona mandate. Add an anti-regression check (doctor rule
and/or test) that **FAILS** if any model-driven step resolves to **no persona** or to
**`project-manager`**.

The guardrail must enumerate the **actual resolved role of every model-driven pipeline
step using the SAME resolution path as `pipeline._scope()`** — NOT a static `rglob` over
fragment files. A fragment-file-only scan passes vacuously for a role that is set in the
workflow **catalog/pipeline** binding independently of any fragment file (the surface
T-44-8 edits); the guardrail must cover that catalog-layer surface too.

- **How to verify:** the anti-regression check passes on the post-reassignment tree;
  TWO deliberately-broken negative fixtures make it FAIL — (a) a **fragment-layer** role
  with no persona atom, and (b) a **catalog-layer** worker step bound to
  `project-manager` (or an unmapped role) — proving both surfaces are covered. Negative
  fixtures live under **tmp/fixture roots**, NOT under `public/lifecycle_fragments/`, so
  the pass-on-current-tree assertion and `dadaia public doctor` stay clean. The audit
  findings are recorded in the release (PLAN/CLOSURE), with any fragment trims captured as
  task acceptance.

### AC-5 — pi model openness (curated OpenRouter catalog + overlay registration)

Open pi's Layer-2 model set from GPT-only to **allowlist-validated** (registry codex ids
**plus** a Layer-2-native worker-model allowlist):

- **Do NOT extend `REGISTRY`.** `core/model_registry.py:REGISTRY` is keyed
  `claude_id → codex_id` and has **THREE** derived views, not two: `MODEL_MAP`,
  `PRICING_TABLE`, **and** `codex_tier_views()` / `_codex_id_for_tier()`
  (`core/model_registry.py:201-252`). Inserting an OpenRouter id (e.g. `kimi-2.7`) as a
  `codex_id` under a synthetic `claude_id` would land in some `Tier` whose
  `_codex_id_for_tier()` then collects `{gpt-5.5, kimi-2.7}` → `len>1` → **raises
  `ValueError` on the codex runtime hot path** (`codex_runtime.py:193-199`, via
  `codex_tier_views()`) and breaks codex-assets TOML projection. It would also fabricate a
  pricing row (telemetry would lie). The synthetic-alias approach is therefore rejected.
- Instead, add a **Layer-2-native worker-model allowlist** in `core/harness_models.py`:
  `LAYER2_EXTRA_MODEL_IDS: frozenset[str]` (or a small `Layer2Model` record carrying an
  explicit price/effort when needed). Add the curated OpenRouter ids (`kimi-2.7` + a small
  curated set — exact extra ids a bounded PLAN decision) here, and add the option(s) to
  the **pi** catalog (`core/harness_models.py:62-71`). The **codex** catalog is unchanged.
- Relax the invariant in `_assert_ids_known()` (`core/harness_models.py:79-102`): a
  Layer-2 catalog id must be present in `_known_codex_ids() | LAYER2_EXTRA_MODEL_IDS` and
  must **never** be a `claude-*` id (claude is never a Layer-2 worker) — the implicit
  "GPT-only" framing is dropped; the allowlist-membership + no-`claude-*` guarantees
  remain.
- **Pricing stays honest:** either give the OpenRouter ids an explicit price in the
  Layer-2 set, or let `compute_cost` return `None` ("unknown" — honest). **No fabricated
  registry pricing row.**
- The operator-overlay store
  (`infrastructure/json_local_model_profile_store.py:192-231`) may register additional
  **pi** model ids without a code change, **validated against the SAME union**
  (`_known_codex_ids() | LAYER2_EXTRA_MODEL_IDS`) — an overlay profile naming an id
  outside that union is rejected.
- pi command build (`infrastructure/pi_runtime.py:148-183`) passes the selected id
  through unchanged (`pi --mode json --model <id>`).
- **How to verify:** a test asserts the pi catalog contains the new OpenRouter ids and
  that `_assert_ids_known()` accepts them via the allowlist union; a test asserts a
  `claude-*` catalog id still raises and an id outside the union still raises; a test
  asserts `REGISTRY` is **unchanged** and `codex_tier_views()` still resolves with no
  `ValueError`; a test asserts an overlay profile naming an id outside the union is
  rejected and a union-present pi id is accepted; resolver precedence
  (`policy_resolver.py:358-384`) still selects the overlay/CLI id correctly.

### AC-6 — Anti-regression guardrails + docs

- Add/extend doctor checks and tests covering AC-2..AC-5 invariants (persona resolves for
  every model-driven step; no PM worker persona; allowlist-validated catalog).
- Update **all** live "GPT-only" law assertions, which exist beyond the docstring:
  - `core/harness_models.py` module docstring;
  - **live Python NOT previously in scope:** `features/lifecycle/policy_doctor.py:269`
    (docstring) and `features/lifecycle/model_profiles.py:13,127,196` (a docstring + two
    reject messages) — these will otherwise contradict the relaxed invariant and are
    added to the doc-edit write set;
  - rule / `AGENTS.md` references that state Layer-2 is "GPT-only";
  - add the persona entity to the relevant agentic documentation.
  - **MEMORY atoms** (`specs/memory/architecture.md:893`,
    `specs/memory/product/sdd/lifecycle-foundation.md:95,127`) are product-engineer-only
    and writable only in DEFINITION/CLOSURE — handled by a separate product-engineer task
    (see T-44-18), NOT by ai-engineer.
- The constitution/ADR-B amendment (GPT-only → allowlist-validated) is an explicit law
  change requiring operator confirmation.
- The doc-lint grep guardrail is scoped to **live source + public docs**, EXCLUDING
  `specs/_archive/` (FROZEN; e.g. v0.1.24 false-matches) and the v0.1.44 spec text itself,
  so it is satisfiable.
- All lib-originated edits are made at source under `public/` then propagated via
  `dadaia public stage && dadaia public install --target all && dadaia public doctor`.
- **How to verify:** `dadaia public doctor` clean (incl. `[ok] public-privacy`);
  `dadaia specs doctor` clean; full `pytest`/`mypy --strict`/`ruff` green; the scoped
  doc-lint test (or grep guardrail) asserts no remaining "GPT-only" claim contradicts the
  new law.

---

## 4. Out of scope

- **Panel redesign** (Workflows diagram cards, Agentic-tab rework, styling) — that is the
  fast-follow **v0.1.45**, which **depends on** the persona entity defined here.
- **claude as a Layer-2 worker** — claude is never a Layer-2 persona; the no-`claude-*`
  catalog guarantee is preserved.
- A **closure fragment suite** (the `closure/` workflow dir remains a stub this release).
- Any **open-passthrough model mode** — pi model openness is registry-validated only;
  there is no unvalidated free-text model passthrough.
- Authoring a `project-manager` persona — PM is the Layer-1 orchestrator, not a Layer-2
  persona (D-1).

---

## 5. Dependencies and risks

### Dependencies

- **v0.1.45 (panel redesign) depends on this release** — the panel will render the
  persona entity defined here; v0.1.45 must not start before v0.1.44 ships.
- Persona library (AC-1) is a prerequisite for the injection seam (AC-2) and the
  anti-regression audit (AC-4).
- Fragment role reassignment (AC-3) must land before the AC-4 anti-regression check is
  switched on (otherwise the seven PM fragments fail it).

### Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | **Constitution/ADR-B amendment.** Relaxing the GPT-only law touches `constitution.md`/ADR-B — a law change. | Make the amendment explicit; require operator confirmation before writing the constitution edit; keep the no-`claude-*` guarantee intact so the law only *widens*, never removes a safety bound. |
| R2 | **Persona content drift vs sub-agent (KNOWN, not solved).** Two hand-authored mandates (`personas/<role>.md` and `agents/<role>.md`) can diverge in content over time. The `source_agent` pointer + dangling-reference guard catch a **missing/renamed** sub-agent file, but do **NOT** detect content divergence. | Accept content alignment as hand-authored discipline; the loader's dangling-ref guard catches only the structural case; CLOSURE records this as an accepted residual risk. Not claimed as "cannot silently drift". |
| R3 | **Multi-role fragments** (`plan-review`, future). | The injection seam resolves a comma-separated role string to the persona **set**; covered by an explicit multi-role test (AC-2). |
| R4 | **`ai-engineer` persona unreferenced by current fragments.** No fragment currently names `role: ai-engineer`. | Author it anyway for roster completeness; the AC-4 audit checks *every model-driven step resolves to a persona*, it does **not** require every persona to be used. CLOSURE must record the `ai-engineer` persona as **INTENTIONALLY unreferenced** (roster symmetry) so it is not later read as dead code. |
| R5 | **Envelope byte-stability.** Adding a `persona` field could break the deterministic `build_prompt_envelope` ordering for persona-less steps. | Keep `persona` additive-optional and omit the key entirely when absent, preserving the existing byte-stable payload for the no-persona path (covered by a regression test). |
| R6 | **Registry redesign (CRITICAL — corrected).** The registry is keyed `claude_id → codex_id` and feeds THREE derived views including `codex_tier_views()`/`_codex_id_for_tier()` on the codex runtime hot path; a synthetic-alias OpenRouter entry would raise `ValueError` there and fabricate telemetry pricing. | Do NOT extend `REGISTRY`. Use a Layer-2-native `LAYER2_EXTRA_MODEL_IDS` allowlist in `core/harness_models.py`, validate the catalog + overlay against `_known_codex_ids() | LAYER2_EXTRA_MODEL_IDS`, keep the no-`claude-*` rejection, and keep pricing honest (explicit Layer-2 price or `compute_cost` → `None`). A test asserts `REGISTRY` is unchanged and `codex_tier_views()` does not raise. |
| R7 | **Lib-originated propagation.** Persona files + edited fragments are lib-originated; forgetting stage/install leaves the instance drifted. | Every AC closes with `dadaia public stage && install --target all && doctor`; CLOSURE records `[ok] public-privacy`. |
