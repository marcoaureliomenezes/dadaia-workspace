---
release: v0.1.32
kind: grill-record
date: 2026-06-27
status: Aprovado
---

# Grill record — v0.1.32 (harden real-worker workflows — coherent worker-output contract)

Operator demand 2026-06-27 (AskUserQuestion: "Harden real-worker workflows"): fix
`lifecycle-prompt-names-two-schemas-confusing-real-workers` so workers emit the right schema
**by design**, not just tolerated; then run a FULL real `release define` on pi end-to-end
**including a REVIEW step** emitting a real APPROVED/REJECTED verdict (v0.1.31 only proved the
*create* path live). Continues [[project_v0131_real_layer2_worker]].

## Theme
Make the **worker-output contract coherent end to end** so a real `pi`/Codex Layer-2 worker
reliably produces a parseable result on every step kind, and prove the **review/verdict path**
live — turning the v0.1.31 extractor *tolerance* into a contract that is *correct by design*
(tolerance demoted to defence-in-depth).

## Diagnosis (the contract is internally inconsistent — three drifts the worker can't reconcile)
1. `prompt_builder.build_fragment_suffix` "## Required output" (prompt_builder.py:~71) tells
   **every** step to "Emit a handoff whose `structured_output.verdict` is APPROVED or REJECTED" —
   the stale universal-verdict framing. v0.1.31 made the gate **review-only**: a create step must
   NOT be told to self-verdict (it cheapens the review gate and confuses the worker).
2. The same text says "conforms to the output schema `{bundle.output_schema}`" (the fragment's
   domain schema, e.g. `release-scope-handoff-v1`), but the extractor checks
   `payload["schema"] == expected_schema` where `expected_schema` defaults to the **transport**
   id `agent-run-result-v1` (prompt_builder.py:111). Two competing schema ids → the worker labels
   `schema` inconsistently across runs (observed live: run 1 `agent-run-result-v1`; run 2 omitted).
3. `shared/output-handoff.md` documents the field as `schema_version`, but the extractor reads
   `schema`. Field-name drift.

## Adversarial grill → decisions (binding)

### D-1 — ONE transport schema id, in the `schema` field (Option b, not per-step domain schema)
The worker always emits the **transport** envelope `agent-run-result-v1` in a field named
`schema`. The fragment's `output_schema` (e.g. `release-scope-handoff-v1`) stays **descriptive**
(it tells the worker *what artifact* it is producing and Python tags the produced payload with
it) but is **not** what the worker puts in the `schema` field. Rationale: Python already knows the
step's domain schema from the run ledger (`produces`); the worker only needs one unambiguous
target; this needs no per-step `expected_schema` wiring (the default already is
`agent-run-result-v1`). Per-step domain-schema-as-transport (Option a) is rejected as more wiring
for no gain.

### D-2 — Step-kind-aware "Required output" (align the prompt with the review-only gate)
`build_fragment_suffix` must be **is_review-aware** (thread the step's `is_review`): a **review**
step is told to emit `structured_output.verdict` = APPROVED/REJECTED + evidence; a **create** step
is told to emit the artifact + `artifact_refs` and is NOT told to self-verdict. This removes the
contradiction between the prompt and the v0.1.31 gate.

### D-3 — Canonical field name = `schema`
Reconcile the contract to the field the extractor actually reads: `schema` (literal transport id).
Update `shared/output-handoff.md` (currently `schema_version`) and any fragment text so the
worker is told exactly one field name with one value. (Do NOT change the extractor's field name —
align the docs/prompt to it.)

### D-4 — Restore strict accept as primary; keep structural tolerance as defence-in-depth
With the contract coherent, restore `payload["schema"] == expected_schema` as the PRIMARY accept
path in `pi_runtime._verdict_payload`, and KEEP the v0.1.31 structural acceptance (non-empty
`artifact_refs` + status/summary/structured_output) as an explicit, documented **fallback** — not
the load-bearing path. Both fenced and bare JSON still accepted.

### D-5 — Codex parity
Apply the same extraction tolerance (fenced-or-bare + structural fallback) and the same coherent
contract to `codex_runtime`'s extractor, so the second Layer-2 worker behaves identically. (Codex
currently parses a single JSON object from a temp file — confirm it tolerates the same real-worker
shapes.)

### D-6 — Prove the REVIEW path live (the core deliverable)
Extend the real-worker e2e to run a real `pi` worker through a chain that **includes at least one
review/gate step**, so the worker emits a real APPROVED verdict and the review gate PASSES live
(and a REJECTED verdict BLOCKS live). Target: the full `release_definition` sequence to the
terminal commit gate, OR a minimal create→review pair. Assert the verdict gate fired on real
worker output. Env-gated (`DADAIA_E2E_REAL_WORKER=1`), skip-by-default (CI stays faked+green).
Codex variant OPTIONAL (OQ-2).

### D-7 — Scope / branch / version
Extend existing seams only (`prompt_builder`, `output-handoff.md`, `pi_runtime`/`codex_runtime`
extractors, the e2e). No new fragment family, no new schema, no per-step expected_schema wiring.
`feature/v0.1.32` branches off `feature/v0.1.31` (unmerged). DEFINE-ONLY checkpoint; implement only
after operator approval. **No push.** Version id v0.1.32; `pyproject` stays 0.1.7 (no PyPI).

## Bug dispositions
- `lifecycle-prompt-names-two-schemas-confusing-real-workers` → solved by D-1/D-2/D-3; Closed at
  CLOSURE with the live-review-e2e evidence.

## Open questions for DEFINITION
- OQ-1: D-3 — confirm the canonical field is `schema` (align docs to extractor) vs. teaching the
  extractor to also read `schema_version`. Default: canonical `schema`.
- OQ-2: D-6 — full `release_definition` sequence vs. a minimal create→review pair for the live
  review proof; and whether to include a codex case.
- OQ-3: D-5 — does `codex_runtime` already tolerate bare/structural output, or does it need the
  same hardening as pi? (product-engineer to read codex_runtime and confirm.)
