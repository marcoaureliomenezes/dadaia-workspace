---
name: model-catalog-modelmap-pricing-drift-no-registry
status: Closed
severity: MEDIUM
reported: 2026-06-09
resolved: 2026-06-10
resolved_in: v0.1.10
surface: infrastructure/runtime_transforms/model_mapping.py (MODEL_MAP) + features/telemetry/pricing.py (PRICING_TABLE)
session_id: null
---

> **Resolution (2026-06-10, release v0.1.10).** Closed by the two-task R8
> fix:
> - **T-010-23 (R8a)** introduced `core/model_registry.py` as the single
>   source of truth (`REGISTRY` of `ModelEntry{claude_id, codex_id, pricing
>   (dated append-only), tier}`); `MODEL_MAP` and `PRICING_TABLE` became
>   *derived views* over it, so both share an identical key-set by
>   construction. The haiku drift was reconciled to the canonical
>   `claude-haiku-4-5-20251001`, and the `claude-fable-5` row
>   (10.00/50.00/12.50/1.00, effective 2026-06-01) was added.
> - **T-010-24 (R8b)** added the standing `dadaia public doctor`
>   model-resolution check (`features/public/model_resolution.py`,
>   `check_model_resolution`): every `model:` frontmatter value across the
>   canonical `public/agents/*.md` must resolve in `REGISTRY`, and the
>   MODEL_MAP / PRICING_TABLE / REGISTRY key-sets must be identical — any
>   unknown id or desync emits a `[drift]` ERROR line and exits the doctor
>   nonzero. The clean fleet emits `[ok] model-resolution`.
>
> **Regression tests** (`tests/unit/features/public/test_model_registry_doctor.py`):
> `test_unknown_model_in_agent_frontmatter_errors`,
> `test_keyset_desync_modelmap_vs_pricing_errors`,
> `test_keyset_desync_pricing_vs_registry_errors`,
> `test_current_tree_resolves_clean` (plus the T-010-23 cross-table
> key-equality contract test).

> **Provenance note (corrected 2026-06-10).** This bug was originally filed by
> a concurrent operator session as `model-catalog-missing-claude-fable-5`. The
> v0.1.9 session rewrote it, declaring `claude-fable-5` "a non-existent model /
> hallucination" — that correction was itself wrong: it was made by a model
> whose knowledge predates Fable 5. **`claude-fable-5` is a real, current
> Claude model id** (Anthropic's flagship alongside the 4.x family); the
> operator set it as the session default via `/model` on 2026-06-09 and
> explicitly ordered retiering 5 agent personas to it. The original symptom is
> restored below alongside the (also real) haiku drift this file documented.

**Symptom 1 (verified live, 2026-06-09):** `claude-fable-5` is absent from
both catalogs, so the operator-ordered retier cannot land:

```bash
python -c "from dadaia_workspace.infrastructure.runtime_transforms.model_mapping import map_model; map_model('claude-fable-5')"
# ValueError: No Codex mapping for model: 'claude-fable-5'   (model_mapping.py:33)
```

Setting `model: claude-fable-5` in any `public/agents/*.md` therefore crashes
`dadaia public install --target codex` (raised from `install_helpers.py:395`),
and telemetry events for the model cost out as `cost_micro_usd = NULL`.

**Symptom 2 (verified):** The two hardcoded model catalogs have drifted from each
other:

- `MODEL_MAP` (`infrastructure/runtime_transforms/model_mapping.py:12-15`):
  `claude-opus-4-7`, `claude-opus-4-8`, `claude-sonnet-4-6`,
  **`claude-haiku-4-5-20251001`**.
- `PRICING_TABLE` (`features/telemetry/pricing.py:41-50`): `claude-opus-4-7`,
  `claude-opus-4-8`, `claude-sonnet-4-6`, **`claude-haiku-3-5`**.

The haiku ids disagree (`haiku-4-5-20251001` vs `haiku-3-5`). Any telemetry
event costed against the real `claude-haiku-4-5-20251001` model resolves to a
missing `PRICING_TABLE` key → `cost_micro_usd = NULL`, while `MODEL_MAP`
projects that same id fine. The two tables have no shared source of truth.

**Repro:**

```bash
python -c "from dadaia_workspace.infrastructure.runtime_transforms.model_mapping import MODEL_MAP; print('haiku key:', [k for k in MODEL_MAP if 'haiku' in k])"
# ['claude-haiku-4-5-20251001']
python -c "from dadaia_workspace.features.telemetry.pricing import PRICING_TABLE; print('haiku key:', [k for k in PRICING_TABLE if 'haiku' in k])"
# ['claude-haiku-3-5']
```

**Expected:** A single model id is priced and mapped consistently across both
tables. A model id present in `MODEL_MAP` should have a `PRICING_TABLE` row (and
vice-versa), enforced by a check rather than manual discipline.

**Root cause:** Two independently hand-maintained hardcoded tables with no
single registry and no doctor check. Every new/changed Claude model id requires
editing both by hand (the recurring "MODEL_MAP gotcha" already in operator
memory); nothing detects when they desync — which is how the haiku drift landed.

**Fix direction (for a future release — out of v0.1.9 scope):**
- Single model-registry module (claude id → codex id + pricing row + tier)
  consumed by both `model_mapping` and `telemetry.pricing`.
- A `public doctor` / `specs doctor` check that every model id referenced in
  `public/agents/*.md` frontmatter resolves in the registry, and that
  MODEL_MAP and PRICING_TABLE key-sets are identical.
- Immediate: reconcile the haiku row in `PRICING_TABLE` to
  `claude-haiku-4-5-20251001` (or whatever the priced haiku tier actually is).
- Immediate (operator-directed workaround, pre-release): add `claude-fable-5`
  entries to `MODEL_MAP` (top tier, alongside opus) and `PRICING_TABLE` so the
  ordered agent retier can project to all runtimes; the systemic registry fix
  still owns the real close of this bug.

**Notes:** Related to the recurring MODEL_MAP maintenance trap. The
`map_model` fail-loud behavior on unknown ids is by design (ADR-5) and is NOT
the defect — the defect is the absent registry + the silent table desync.
