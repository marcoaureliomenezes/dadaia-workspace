# PLAN — Release: v0.1.44

**Status:** Aprovado
**Release ID:** v0.1.44
**Owner:** product-engineer
**Opened:** 2026-06-30

---

## 1. Strategy

Build the persona entity as a **mirror of the fragment subsystem**: a `public/personas/`
source library + a `PersonaLoader` (semantic twin of `FragmentLoader`) + a token lint,
then thread a resolved persona body through the **existing** role seam
(`PromptScope → AgentRunRequest → build_prompt_envelope`) as one additive-optional field.
Reassign the seven PM fragments, switch on an anti-regression guardrail that scans
**resolved pipeline-step roles** (fragment-layer + catalog-layer), then open the pi
catalog with an **allowlist** relaxation (a Layer-2-native id set in `harness_models.py` —
`REGISTRY` is NOT touched). Order: AC-1 (library) → AC-2 (injection) → AC-3 (reassignment)
→ AC-4 (audit/guardrail) → AC-5 (model openness) → AC-6 (docs/doctor). Persona/fragment
**text** is `ai-engineer`; Python wiring is `software-engineer`; memory atoms +
constitution are `product-engineer` (DEFINITION/CLOSURE).

## 2. Layers affected

- `core/` — `harness_models.py` (catalog + invariant + `LAYER2_EXTRA_MODEL_IDS`
  allowlist), `core/models/lifecycle.py` (`AgentRunRequest.persona`). **`model_registry.py`
  is NOT modified** (see §3.6 — the synthetic-alias approach is rejected).
- `features/lifecycle/` — `prompt_builder.py` (`PromptScope.persona`), `pipeline.py`
  (`_scope` role→persona resolution), a new `personas/loader.py`, a shared frontmatter
  base (`_frontmatter_doc.py`), `policy_doctor.py` + `model_profiles.py` (doc/message
  edits — AC-6).
- `infrastructure/` — `headless_adapter_base.py` (`build_prompt_envelope`),
  `json_local_model_profile_store.py` (allowlist-validated overlay), `pi_runtime.py`
  (passthrough — likely no change, verify only).
- `public/` (lib-originated) — new `personas/<role>.md` × 8, seven edited fragments,
  doc edits; propagated via `public stage`/`install`/`doctor`.
- `specs/memory/` (product-engineer, DEFINITION/CLOSURE) — `architecture.md`,
  `product/sdd/lifecycle-foundation.md` GPT-only assertions (T-44-18).
- Doctor/tests — new persona-resolution (resolved-role) and catalog guardrails.

## 3. Module-by-module design

### 3.1 Persona library — `public/personas/<role>.md` (AC-1, ai-engineer)

Eight atoms: `ai-engineer`, `code-reviewer`, `product-engineer`, `project-auditor`,
`qa-engineer`, `security-reviewer`, `software-architect`, `software-engineer`. **No**
`project-manager.md` (D-1). Frontmatter (minimal, validated by the loader):

```yaml
---
id: <role>                       # equals filename stem; the role string fragments name
role: <role>                     # canonical Layer-2 role token
summary: <one-line mandate>
source_agent: agents/<role>.md   # navigational pointer to the Claude sub-agent
harness_universal: true
---
```

`source_agent` is a **navigational pointer**, not a drift detector: the loader's
dangling-reference guard asserts the pointed-at `public/agents/<role>.md` exists, but
does NOT compare mandate **content** between the two hand-authored files. Content
alignment is hand-authored discipline (R2).

Body = the persona **mandate**: what this role does, its decision posture, its outputs —
**semantically aligned** to `public/agents/<role>.md` but stripped of every Claude-ism.
Body must pass the harness-universal token lint (same forbidden-token list as fragments).

### 3.2 `PersonaLoader` + shared frontmatter base (AC-1, software-engineer)

**Loader DRY decision (architect MEDIUM):** extract a generic `FrontmatterDocLoader`
base (`features/lifecycle/_frontmatter_doc.py`) that both `FragmentLoader` and
`PersonaLoader` parameterize — sharing `_split_frontmatter`, the str/list key-validation
loop, **and** the harness-token lint (`_FORBIDDEN_TOKENS` + `forbidden_token_in`). This
is the **preferred** option over recording the duplication as deliberate; the fragment
loader is refactored onto the base with its existing tests kept green (no behavior
change). `PersonaLoader` (`features/lifecycle/personas/loader.py`) then parameterizes the
base with the persona schema.

- `_default_root()` → `public/personas/`
  (`Path(__file__).resolve().parents[2] / "public" / "personas"`).
- `Persona` frozen dataclass: `id`, `role`, `summary`, `source_agent`,
  `harness_universal`, `body`, `path`.
- Required keys `{id, role, summary, source_agent, harness_universal}`, validated by the
  shared base.
- **Dangling-reference guard:** `validate_all()` (and/or a doctor rule) asserts each
  persona's `source_agent` resolves to an existing `public/agents/<role>.md`; a dangling
  pointer raises. A missing-required-key case also raises (real loader coverage).
- `load_persona(role)`, `list_personas()`, `validate_all()`, and a module-level default
  loader, mirroring the fragment loader API.

### 3.3 Persona injection seam (AC-2, software-engineer)

Thread one additive-optional field end-to-end. Exact anchors:

1. **`PromptScope.persona: str | None = None`** — `prompt_builder.py:146-163`. Additive
   field; no validation change (persona is optional).
2. **`AgentRunRequest.persona: str | None = None`** — `core/models/lifecycle.py:367`.
   Threaded in `LifecyclePromptBuilder.build()` (`prompt_builder.py:189-202`) from
   `scope.persona`. A **direct** unit test asserts `build()` copies `scope.persona →
   request.persona` (QA advisory — today only transitively covered).
3. **Resolution in `pipeline._scope()`** — `pipeline.py:377-393`. Add a
   `PersonaLoader` to the pipeline's deps; resolve `step.role` → persona body:
   - split `step.role` on `,` (multi-role); for each role, `load_persona(role.strip())`;
   - `role == "shared"` or no persona atom → `persona=None` (no block);
   - multiple roles → join their mandate bodies (clearly delimited per role).
   Set `PromptScope(..., persona=<resolved-or-None>)`.
4. **`build_prompt_envelope()`** — `headless_adapter_base.py:236-258`. When persona is
   present, emit it as an **operative directive** — wrap the mandate in instruction text
   that explicitly tells the worker to **act per** this persona (e.g. a `persona`
   key whose value leads with a directive, not a bare body), so the body is operative,
   not an inert sibling key (architect INFO). Emit the key **only when present** (omit
   entirely when `None`) so the persona-less payload stays byte-identical to today (R5).
   Keep `indent=2, sort_keys=True`. The AC-2 test asserts the **directive** text is
   present, not merely the mandate body.

The `build_fragment_suffix`/`PromptPrefix` assembly (`prompt_builder.py:79-143`) is
unchanged — persona is a request/envelope field, not a fragment-suffix section.

### 3.4 Fragment role reassignment (AC-3, ai-engineer + software-engineer)

Edit the `role:` frontmatter of the seven fragments per SPEC AC-3 table. Then audit any
worker-step `role=`/`default` binding in the workflow catalog
(`features/lifecycle/` catalog/pipeline construction) that names `project-manager` for a
worker step and update it to the new persona. The v0.1.43 no-orphan/no-generic guardrail
suite must stay green.

### 3.5 Anti-regression audit + guardrail (AC-4, software-engineer)

- A check (new `dadaia specs doctor`/`public doctor` rule, backed by a unit test) that
  enumerates the **actual resolved role of every model-driven pipeline step using the
  SAME resolution path as `pipeline._scope()`** — NOT a static `rglob` over fragment
  files. The catalog/pipeline construction is the source of truth for which steps run and
  what role each binds; for each model-driven step the check resolves its role(s) the same
  way `_scope()` does and asserts: `PersonaLoader.load_persona(role)` resolves AND
  `role != "project-manager"`. FAIL otherwise. This covers the **catalog-layer** surface
  T-44-8 edits, where a role is set independently of any fragment file (a fragment-only
  scan would pass vacuously there).
- **TWO** negative fixtures prove both surfaces FAIL: (a) a **fragment-layer** role with
  no persona atom; (b) a **catalog-layer** worker step bound to `project-manager` (or an
  unmapped role). Both fixtures live under **tmp/fixture roots**
  (`.dadaia/tmp/<agent>/<date>/` or pytest `tmp_path`), NOT under
  `public/lifecycle_fragments/`, so the pass-on-current-tree assertion and
  `dadaia public doctor` stay clean.
- The optimization pass (manual, ai-engineer) trims/aligns fragment bodies that duplicate
  persona mandate; findings recorded in CLOSURE.

### 3.6 pi model openness (AC-5, software-engineer)

> **R6 registry redesign (architect CRITICAL).** The synthetic-alias approach is
> **rejected.** `core/model_registry.py:REGISTRY` (keyed `claude_id → codex_id`) feeds
> **THREE** derived views, not two: `MODEL_MAP`, `PRICING_TABLE`, **and**
> `codex_tier_views()` / `_codex_id_for_tier()` (`model_registry.py:201-252`). Inserting
> `kimi-2.7` as a `codex_id` under a fake `claude_id` lands in some `Tier` whose
> `_codex_id_for_tier()` then collects `{gpt-5.5, kimi-2.7}` → `len>1` → **raises
> `ValueError` on the codex runtime hot path** (`codex_runtime.py:193-199`, which calls
> `codex_tier_views()` for every Codex run) and breaks codex-assets TOML projection. It
> also fabricates a pricing row (telemetry lies). **`REGISTRY` is therefore NOT touched.**

- **Layer-2-native allowlist (`harness_models.py`).** Add
  `LAYER2_EXTRA_MODEL_IDS: frozenset[str]` (or a small `Layer2Model` record carrying an
  explicit `(model_id, effort, optional price)` when a price is wanted). The curated
  OpenRouter ids live here, NOT in `REGISTRY`.
- **Curated extra ids (PLAN decision).** Recommended minimal set: `kimi-2.7` only this
  release, leaving headroom for overlay-registered ids; exact additional ids confirmed at
  implementation by ai-engineer/operator and recorded in CLOSURE. Keep the set small and
  named — no wildcard.
- **Catalog (`harness_models.py:62-71`).** Add the OpenRouter option(s) to
  `_CATALOG[PI_HARNESS]`. Codex catalog untouched.
- **Invariant (`harness_models.py:79-102`).** Relax `_assert_ids_known()`: validate each
  Layer-2 catalog id against `_known_codex_ids() | LAYER2_EXTRA_MODEL_IDS`; keep the
  `claude-*` rejection (claude is never Layer-2); drop the "GPT-only" framing from the
  message + module docstring. The function still raises on a `claude-*` id and on an id
  outside the union.
- **Pricing — honest, no fabrication.** Either give the OpenRouter ids an explicit price
  in the Layer-2 set, OR let `compute_cost` return `None` ("unknown" — honest) for them.
  **No fabricated `REGISTRY` pricing row.** A test asserts `REGISTRY` is unchanged and
  `codex_tier_views()` resolves without `ValueError`.
- **Overlay store (`json_local_model_profile_store.py:192-231`).** Validate an operator pi
  profile's `model_id` against the **same union** (`_known_codex_ids() |
  LAYER2_EXTRA_MODEL_IDS`): an id outside the union is rejected with a clear message; a
  union-present pi id is accepted. Keep the existing `harness == pi` constraint.
- **pi_runtime (`pi_runtime.py:148-183`).** Verify the selected id flows through
  `pi --mode json --model <id>` unchanged — expected **no edit**, add a test only.

### 3.7 Docs + doctor + propagation (AC-6, ai-engineer + software-engineer + product-engineer)

GPT-only assertions live in more places than the docstring; fix **all live** surfaces:

- **ai-engineer / software-engineer write set:** `harness_models.py` module docstring;
  `features/lifecycle/policy_doctor.py:269` (docstring);
  `features/lifecycle/model_profiles.py:13,127,196` (a docstring + two reject messages
  that would otherwise contradict the relaxed invariant); rule / `AGENTS.md` references
  asserting Layer-2 is "GPT-only" → "allowlist-validated (no `claude-*`)". Add the persona
  entity to the relevant agentic doc surface (the doc that enumerates fragments / workflow
  prompt assembly).
- **product-engineer write set (DEFINITION/CLOSURE, T-44-18):** MEMORY atoms
  `specs/memory/architecture.md:893` and
  `specs/memory/product/sdd/lifecycle-foundation.md:95,127`. These are product-engineer-
  only and gate-restricted to DEFINITION/CLOSURE — **not** ai-engineer.
- **constitution/ADR-B amendment requires operator confirmation** before the edit is
  written (T-44-16).
- **Doc-lint guardrail scope:** the grep/test is scoped to **live source + public docs**,
  EXCLUDING `specs/_archive/` (FROZEN; e.g. v0.1.24 false-matches) and the v0.1.44 spec
  text itself — making the assertion satisfiable. It asserts no surviving "GPT-only" claim
  contradicts the new law.
- Propagate every lib-originated change: `dadaia public stage && dadaia public install
  --target all && dadaia public doctor` (must show `[ok] public-privacy`).

## 4. Execution order

1. AC-1 persona library + `PersonaLoader` + shared lint module.
2. AC-2 persona injection seam (scope → request → envelope), with tests.
3. AC-3 fragment role reassignment + catalog binding updates.
4. AC-4 anti-regression guardrail + optimization pass.
5. AC-5 Layer-2 allowlist + pi catalog + invariant relaxation + overlay validation
   (`REGISTRY` untouched).
6. AC-6 docs/doctor/propagation + memory-atom edits (T-44-18) + constitution amendment
   (operator-confirmed).

## 5. Technical risks

- **Envelope byte-stability** — omit the `persona` key when absent (R5); regression test
  on the persona-less payload.
- **Loader DRY** — extract a `FrontmatterDocLoader` base (frontmatter split + key
  validation + harness-token lint) shared by both loaders; refactor FragmentLoader onto it
  with existing tests green.
- **REGISTRY untouched (R6)** — do NOT add OpenRouter ids to `REGISTRY`; a test asserts
  `REGISTRY` is unchanged and `codex_tier_views()` does not raise. The Layer-2 allowlist
  is the only model-set extension.
- **Resolved-role guardrail** — must enumerate catalog/pipeline-resolved roles, not
  fragment rglob; catalog-layer negative fixture in tmp roots.
- **Doc-lint satisfiability** — scope the grep to live source + public docs, exclude
  `_archive/` and the v0.1.44 spec.
- **Constitution + memory edits** — product-engineer-only; constitution gated on operator
  confirmation; do not write speculatively.

## 6. Validation plan

- `pytest` (persona loader incl. dangling-ref + missing-key negatives; build() persona
  threading; injection-seam operative directive; multi-role; byte-stability; catalog +
  allowlist invariant; `REGISTRY`-unchanged + `codex_tier_views()` no-raise; overlay
  union validation; resolved-role anti-regression with fragment-layer AND catalog-layer
  negatives).
- `mypy --strict`, `ruff format --check`, `ruff check`.
- `dadaia public stage && install --target all && public doctor` → `[ok] public-privacy`.
- `dadaia specs doctor` clean (incl. the resolved-role persona guardrail).
- Manual: confirm an envelope for a real role (e.g. `spec-create`) carries the persona
  **operative directive**, and a `role: shared` step carries none.
