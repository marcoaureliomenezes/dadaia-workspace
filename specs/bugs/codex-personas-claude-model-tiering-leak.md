---
name: codex-personas-claude-model-tiering-leak
status: Open
severity: MEDIUM
reported: 2026-06-11
surface: runtime_transforms/codex.transform_for_codex + model_mapping.MODEL_MAP (persona-body model guidance)
session_id: null
---

**Symptom:** Codex agent persona bodies carry a Claude-centric model strategy that
string-substitution cannot fix — operator-flagged ("makes no sense claude models on
codex agents"). Two concrete defects on the live instance:

1. `.codex/agents/ai-engineer.toml` (Step 4, "Recommend tier moves") instructs:
   "recommend **Opus / Sonnet / Haiku** based on the workload-character table" —
   Anthropic tier names as the operative instruction in a Codex persona. The
   replacement table maps model *ids*, not tier *names*.
2. The registry tier table in the same persona is mapped id-by-id and becomes
   incoherent: `deep` → `gpt-5.5` and `dispatch` → `gpt-5.5` (two tiers collapse to
   one id, erasing the distinction the table exists to teach), while the native Codex
   tiering axis (`model` × `model_reasoning_effort`) is never mentioned.

**Repro:** `dadaia public install --target codex`; inspect
`.codex/agents/ai-engineer.toml` — "Opus / Sonnet / Haiku" survives and the tier
table rows for `deep` and `dispatch` show the same model id. `dadaia public doctor`
D-CX-4 reports `[ok]` (it only catches `claude-*` id literals).

**Expected:** Codex personas express model guidance in Codex-native terms: tier names
that exist for the provider, a registry/tier table that is per-runtime (not a
string-mapped shadow of the Anthropic registry), and `model_reasoning_effort` as a
first-class tiering axis. Mapping that collapses tiers should fail loudly or render a
runtime-specific table.

**Notes:** Sibling of `codex-agent-description-claude-ism-leak` (field bypass) but a
distinct root cause: MODEL_MAP id-substitution is the wrong abstraction for persona
*prose* about model strategy. Source table lives in `public/agents/ai-engineer.md`
("Registry tier" table, derived from `core/model_registry.py`, which is
Anthropic-only). Fidelity audit:
`specs/audits/2026-06-12T001813Z/codex-runtime-fidelity-review.md`.
