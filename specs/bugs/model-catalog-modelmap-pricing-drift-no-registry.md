---
name: model-catalog-modelmap-pricing-drift-no-registry
status: Open
severity: MEDIUM
reported: 2026-06-09
surface: infrastructure/runtime_transforms/model_mapping.py (MODEL_MAP) + features/telemetry/pricing.py (PRICING_TABLE)
session_id: null
---

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
