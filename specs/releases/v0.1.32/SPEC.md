# SPEC — Release: v0.1.32 — harden real-worker workflows (coherent worker-output contract + live review path)

**Status:** Aprovado
**Release ID:** v0.1.32
**Owner:** product-engineer
**Opened:** 2026-06-27

> No `**Consumes:**` line. This is a **bug-driven** release: it solves the bug
> `lifecycle-prompt-names-two-schemas-confusing-real-workers` (the prompt-side root cause that
> v0.1.31's extractor hardening only *tolerated*). `specs/backlog/` carries no item that maps
> 1:1 to a coherent-worker-output-contract intent, so per the GRILL the SPEC declares no
> consumed backlog (do not invent one).

---

## 1. Problem and context

v0.1.31 proved the dadaia-workflows can run on a **real** Layer-2 worker (`pi`/`codex`) past
step 1 — but it proved only the **create** path, and only because the PI extractor was
*hardened to tolerate* a non-compliant worker. The worker-output contract is internally
inconsistent: the prompt tells the worker one thing, the extractor checks another, and the
shared fragment documents a third field name. Real GPT/Codex workers reconcile the
contradiction differently across runs, so a strict extractor would silently drop a correct
result. Two further gaps remain: the **review/verdict path has never been proven live** on a
real worker, and the second Layer-2 worker (`codex`) was never confirmed to tolerate the same
real-worker output shapes.

The contract has **three drifts** a worker cannot reconcile (diagnosed in
`specs/releases/v0.1.32/GRILL.md`):

1. **`build_fragment_suffix` tells every step to self-verdict.** The "## Required output"
   section (`prompt_builder.py:69-74`) instructs **every** step to *"Emit a handoff whose
   structured_output.verdict is APPROVED or REJECTED"*. This is stale against v0.1.31's
   **review-only** gate — a *create* step must NOT be told to self-verdict (it cheapens the
   review gate and confuses the worker). `build_fragment_suffix` has no `is_review` signal
   today, so it cannot tailor the instruction to the step kind.
2. **Two competing schema ids.** The same text says *"conforms to the output schema
   `{bundle.output_schema}`"* — the fragment's **domain** schema (e.g.
   `release-scope-handoff-v1`) — while the extractor (`pi_runtime._verdict_payload`) checks
   `payload["schema"] == expected_schema` where `expected_schema` defaults to the **transport**
   id `agent-run-result-v1` (`prompt_builder.py:111`). The worker sees two "schema" ids and
   labels the `schema` field inconsistently (observed live: run 1 `agent-run-result-v1`;
   run 2 the field omitted, with `output_schema: release-scope-handoff-v1` nested instead).
3. **Field-name drift.** `shared/output-handoff.md` documents the result field as
   `schema_version`, but the extractor reads `schema`. The worker is told the wrong field name.

Because the contract is incoherent, v0.1.31's strict `schema == expected_schema` accept was
demoted to a documented fallback and **structural acceptance** (non-empty `artifact_refs` +
`status`/`summary`/`structured_output`) became the load-bearing path. That tolerance is a
liability: it accepts payloads on shape alone, so the schema label is effectively unchecked.

This release makes the contract **coherent by design** — the worker is told exactly ONE field
name (`schema`) with exactly ONE value (the transport id `agent-run-result-v1`), and the
instruction is **step-kind-aware** (review steps self-verdict; create steps emit an
artifact and do NOT). With the contract coherent, the strict `schema == expected_schema`
accept is **restored as primary** and structural acceptance is demoted to documented
defence-in-depth. Then the **review/verdict path is proven live**: a real `pi` worker emits a
real APPROVED verdict on a review/gate step and the review gate PASSES live (and a REJECTED
verdict BLOCKS). Codex parity is applied as needed.

The mandatory `dadaia-grill-me` gate was run before this SPEC (record:
`specs/releases/v0.1.32/GRILL.md`, `status: Aprovado`). Its decisions (D-1..D-7) and open
questions (OQ-1..3) are binding and are reflected below.

---

## 2. Objective

Make the Layer-2 worker-output contract **coherent by design** — one transport schema in one
field (`schema: agent-run-result-v1`), step-kind-aware emission instructions, the canonical
field name reconciled across prompt/fragment/extractor — so a real `pi`/`codex` worker
reliably produces a parseable result on **every** step kind; restore strict schema acceptance
as primary (structural as defence-in-depth); and **prove the review/verdict path live** on a
real worker — **by extending the existing prompt/extractor/e2e seams only, never building a
new fragment family, schema, or per-step `expected_schema` wiring** (D-7).

---

## 3. Scope

This release is **small and surgical** (D-7, anti-slop). The work maps to **four execution
waves** (A→D); see PLAN.md for the wave spine and sequencing. Acceptance criteria are numbered
`A1..An`, grouped by cluster.

### 3.0 Anti-slop framing (binding — D-7)

Every change EXTENDS an existing seam; none introduces a parallel system:

- The coherent-contract fix **extends `build_fragment_suffix`** (threads `is_review`, emits
  one `schema` field with one value) and edits the **single existing** `shared/output-handoff.md`
  — it does NOT fork a new fragment family (D-1/D-2/D-3).
- The schema discipline reuses the **already-present** `PromptScope.expected_schema` default
  (`agent-run-result-v1`); **no per-step `expected_schema` wiring is added** (D-1/D-7). The
  fragment's `output_schema` stays descriptive (it tells the worker *what artifact* it is
  producing and Python tags the produced payload with it) — it is **not** the `schema` value.
- The strict-accept restoration **extends the existing `pi_runtime._verdict_payload` /
  `_is_result_payload`** by reordering the existing two accept paths (strict primary,
  structural fallback) — no new extractor, no new schema validation (D-4).
- The codex parity change **extends `codex_runtime._result_from_output`** only as far as
  reading codex confirms is needed (D-5 / OQ-3) — no new adapter.
- The live review-path proof **extends the existing env-gated real-worker e2e**
  (`tests/integration/pi_live/test_real_layer2_worker_workflow_e2e.py`) — no new harness, no
  new test family (D-6).

### 3.1 Cluster 1 — Coherent worker-output contract (Wave A; D-1, D-2, D-3)

**Scope:** make the prompt-side contract say exactly one thing — one field name, one value,
step-kind-aware — so a real worker is never told two competing schema ids or to self-verdict
on a create step.

**Ships:**
- **D-2 — `build_fragment_suffix` becomes `is_review`-aware.** Add a **keyword-only,
  no-default** `is_review: bool` parameter to `build_fragment_suffix` (signature
  `def build_fragment_suffix(bundle, *, selected_context, is_review)` — DEFINITION-review C2):
  every caller is forced to choose, so a forgotten flag is a type/call error, never a review
  step silently fed create-step text. The "## Required output" section branches:
  - **Review step** (`is_review=True`): instruct the worker to emit
    `structured_output.verdict` = APPROVED/REJECTED + evidence (`findings`/`verdict_reason`),
    in the `schema: agent-run-result-v1` envelope, with `artifact_refs`.
  - **Create step** (`is_review=False`): instruct the worker to emit the produced artifact +
    `artifact_refs` in the `schema: agent-run-result-v1` envelope, and **NOT** to self-verdict
    (no `verdict` field is required for create steps).
- **D-1 — one transport schema id, in the `schema` field.** The "## Required output" text
  names exactly ONE schema target: the literal field `schema` set to `agent-run-result-v1`
  (the transport envelope). It stops surfacing `{bundle.output_schema}` (the fragment's domain
  schema) as a competing "schema to emit" — the domain schema remains internal/descriptive
  (Python tags the produced payload with it from the run ledger's `produces`). **No per-step
  `expected_schema` wiring is added** — the default is already `agent-run-result-v1`.
- **D-3 — canonical field name `schema`.** Reconcile `shared/output-handoff.md` (currently the
  field is documented as `schema_version`) and any fragment text to say `schema` (the literal
  transport id `agent-run-result-v1`), matching what the extractor reads. **The extractor's
  field name is NOT changed** — the docs/prompt are aligned to it (OQ-1 default).
- **Thread `is_review` to the suffix builder** through `LifecyclePromptBuilder` / the workflow
  call sites that invoke `build_fragment_suffix` (enumerated in PLAN §3). Each call site already
  has the step's review signal in scope (`step.is_review` for the four release-style workflows
  + pipeline; `False` for `backlog_definition`'s create step). `phase_workflow` does **not**
  call `build_fragment_suffix` (it builds its prompt from `scope.prompt`) and already threads
  `is_review` into `AgentRunnerInput` (v0.1.31) — it needs no suffix-builder change.
- **Second stale surface — `pipeline._generic_prompt` (DEFINITION-review C6).**
  `pipeline._generic_prompt` (~lines 395-400) is NOT a `build_fragment_suffix` caller — it
  hard-codes the universal self-verdict text for every step ("Emit a handoff whose
  structured_output.verdict is APPROVED or REJECTED …"). It is a separate stale surface and must
  ALSO be made step-kind-aware: review → verdict instruction; create → emit artifact + refs, no
  self-verdict. Left untouched it remains an untested stale-text path that re-introduces Drift 1
  on the pipeline's generic (no-fragment) steps.

**Explicitly out:** any new fragment family or `create_handoff` fragment (D-2); a new schema id
(D-1); per-step `expected_schema` wiring (D-1/D-7); changing the extractor's field name (D-3);
changing `shared.output_handoff`'s `output_schema` frontmatter id (`handoff-v1.1` stays).

**Acceptance:**
- A1. `build_fragment_suffix` accepts an `is_review: bool` parameter; a **review** step's
  assembled "## Required output" instructs `structured_output.verdict` = APPROVED/REJECTED +
  evidence; a **create** step's does NOT instruct a verdict (asserted on the assembled text).
- A2. The "## Required output" text names exactly ONE schema target — the literal field
  `schema` = `agent-run-result-v1` — and does **not** surface `{bundle.output_schema}` as a
  competing schema-to-emit (asserted: the transport id appears as the `schema` value; the
  fragment domain schema does not appear as a second "emit this schema" instruction).
- A3. The fragment-guard test asserts BOTH halves of Drift 2/3 die in the
  `shared/output-handoff.md` **body** (DEFINITION-review C1): (a) the body contains **NO**
  `schema_version` field and instructs exactly `schema` = the transport id `agent-run-result-v1`
  as the field to emit (Drift 3); AND (b) the body carries **NO** residual "conform to the
  `output_schema`" emit-framing — no instruction to emit/conform-to the fragment's domain schema
  as the worker-emitted field (Drift 2). The frontmatter `output_schema: handoff-v1.1` stays
  **UNCHANGED** (a distinct concept — the fragment's own id, not the worker-emitted field). Both
  assertions are explicit; no fragment text under `public/lifecycle_fragments/` instructs
  `schema_version` (grep-verifiable).
- A4. `is_review` is threaded from each `build_fragment_suffix` call site: the four
  release-style workflows (`release_definition`, `audit`, `bug_report`, `research`) and
  `pipeline` pass `step.is_review`; `backlog_definition` passes `False` for its `backlog_author`
  create step. No per-step `expected_schema` is wired (the default `agent-run-result-v1`
  stands — grep-verifiable: no new `expected_schema=` at the call sites). **The threading test
  ENUMERATES the suffix callers and FAILS when a new caller omits the flag** (back-compat guard
  for the keyword-only param — DEFINITION-review C2).
- A4b. `pipeline._generic_prompt` is **step-kind-aware** (DEFINITION-review C6): a test asserts
  it produces a verdict instruction for a review step and **no** self-verdict instruction for a
  create step — the second stale surface is no longer an untested universal-verdict path.
- A5. No new fragment family / `create_handoff` fragment exists; `shared.output_handoff` is the
  single output contract (grep-verifiable). `PromptScope.expected_schema` keeps its
  `agent-run-result-v1` default (unchanged).

### 3.2 Cluster 2 — Strict accept primary + structural defence-in-depth (Wave B; D-4)

**Scope:** with the contract coherent, restore strict schema acceptance as the PRIMARY accept
path in `pi_runtime._verdict_payload` and demote the v0.1.31 structural acceptance to an
explicit, documented fallback (no longer load-bearing).

**Ships:**
- Reorder `_is_result_payload` so `payload["schema"] == expected_schema` is the **primary**
  accept and the structural path (non-empty `artifact_refs` + `status`/`summary`/
  `structured_output`) is the **documented fallback**. (The current implementation already
  tries strict first then structural; this wave makes that ordering and intent **explicit and
  documented as primary/fallback**, and pins it with tests so a future edit cannot silently
  re-promote structural to load-bearing.)
- Keep accepting both **fenced** and **bare** JSON candidates (`_json_candidates` unchanged) —
  real workers emit either.
- Update the `_verdict_payload` / `_is_result_payload` docstrings to state: strict
  `schema == expected_schema` is the primary contract (now that the prompt is coherent),
  structural acceptance is defence-in-depth for an imperfectly-labelled real worker, and a
  no-op worker (no payload) still yields `None` → empty `artifact_refs` → BLOCK.

**Explicitly out:** field-level schema validation (D-7 anti-slop); removing structural
acceptance (it stays as fallback — a real worker may still mis-label); changing the fenced/bare
candidate ordering.

**Acceptance:**
- A6. `pi_runtime._verdict_payload` accepts a payload whose `schema == expected_schema` as the
  **primary** path (a test asserts a correctly-labelled fenced AND a correctly-labelled bare
  payload are accepted via the strict path).
- A7. A payload that is structurally valid (non-empty `artifact_refs` + `status`/`summary`/
  `structured_output`) but mis-labelled / unlabelled `schema` is **still** accepted via the
  documented fallback (the v0.1.31 tolerance is retained, not removed — a test pins it).
- A8. A no-op worker (no result payload at all) yields `None` → empty `artifact_refs` (the
  create-step gate still BLOCKs — the gate is not made permissive; a test pins it).
- A9. Strict primacy is pinned by **behaviour, not docstring** (DEFINITION-review C5): a test
  feeds a payload that is BOTH structurally-valid (non-empty `artifact_refs` +
  `status`/`summary`/`structured_output`) AND `schema`-matched, and asserts the strict path
  carries it; a second test feeds a payload that is structurally-valid but `schema`-mismatched
  and asserts it is accepted ONLY via the documented fallback — proving structural acceptance is
  a fallback that never shadows/overrides strict semantics. A future reordering that promotes
  structural to primary must FAIL this test. (The docstrings also state strict-primary +
  structural-defence-in-depth, but the test — not the prose — is the gate.)

### 3.3 Cluster 3 — Codex parity (Wave B; D-5, OQ-3)

**Scope:** apply the same coherent contract + extraction tolerance to `codex_runtime` only as
far as reading it confirms is needed.

**D-5/OQ-3 finding (product-engineer read `codex_runtime.py`):** `codex_runtime._result_from_output`
(lines 201-236) reads a **single JSON object** from the `--output-last-message` temp file
(`json.loads(raw)`). It is **less tolerant than the hardened pi extractor** in two ways:
1. **No bare/fenced/sliced candidate fallback.** It calls `json.loads(raw)` on the whole file
   once; if a real codex worker wraps the JSON in a fence or trails prose, the parse fails and
   it degrades to a prose-summary `SUCCEEDED` result with **empty `artifact_refs`** — which
   would BLOCK a create step exactly like the pre-hardening pi path.
2. **No `schema`-field acceptance at all** — it never inspects `schema`/`expected_schema`; it
   unconditionally maps any parsed dict to a result. So it neither enforces the strict contract
   (D-4) nor degrades coherently to it.
   Conclusion: **codex DOES need hardening** for parity — it must gain the same fenced-or-bare
   candidate extraction and the same strict-primary + structural-fallback acceptance the pi
   extractor uses, so the second Layer-2 worker behaves identically. (The coherent prompt
   contract from Cluster 1 is harness-agnostic and already benefits codex.)

**Ships:**
- Extract the shared candidate-extraction + acceptance logic so codex reuses the same
  fenced-or-bare candidate scan and the same strict-primary + structural-fallback acceptance as
  pi (prefer a small shared helper in `headless_adapter_base` over duplicating the logic — the
  two adapters already share that base). `codex_runtime._result_from_output` is rewired to read
  the temp file's text through that shared candidate/acceptance path against
  `request.expected_schema`.
- Codex keeps its `--output-last-message` temp-file read as the source of the assistant text;
  only the *parse + accept* step is upgraded to parity.

**Explicitly out:** changing the codex argv / sandbox / temp-file mechanism; a new codex
adapter; any codex behavior beyond parse-and-accept parity.

**Acceptance:**
- A10. `codex_runtime` extracts the result object from **fenced OR bare** JSON in the
  last-message text (a test asserts a fenced and a bare codex payload both parse).
- A11. `codex_runtime` accepts a payload via the **strict** `schema == expected_schema` path as
  primary and the **structural** path as fallback — identical to pi (tests pin both); a no-op
  codex worker (no payload) yields empty `artifact_refs`. **Codex reject-guard parity
  (DEFINITION-review C4):** a test asserts the rewired `codex_runtime` **REJECTS arbitrary JSON
  lacking the result shape** — a parsed dict with no `schema` match and no non-empty
  `artifact_refs` yields empty `artifact_refs` (it no longer maps ANY dict to a result, matching
  pi's `_is_result_payload` returning `False` for such a dict). This pins the regression away
  from today's unconditional `_result_from_output` dict acceptance.
- A12. The shared extraction/acceptance logic is **factored once** and **positively proven**
  (DEFINITION-review C3 — not a grep): a test **patches the shared extraction helper** (in
  `headless_adapter_base`) and asserts **both** `pi_runtime` **and** `codex_runtime` call it for
  result extraction — proving one implementation so copy-paste divergence cannot silently
  reappear. (A grep for a single impl is a supporting check, not the gate.)

### 3.4 Cluster 4 — Prove the REVIEW path live (Wave C; D-6 — the core deliverable)

**Scope:** extend the env-gated real-worker e2e so a real `pi` worker emits a real APPROVED
verdict on a **review/gate step** and the review gate PASSES live; a REJECTED verdict BLOCKS.

**Ships:**
- Extend `tests/integration/pi_live/test_real_layer2_worker_workflow_e2e.py` (the v0.1.31
  module) with a real **create→review** proof. **PLAN selects (OQ-2)** between the full
  `release_definition` sequence to the terminal commit gate and a minimal create→review pair;
  the SPEC requires at minimum that the chain includes **≥1 real review/gate step** whose
  verdict is read by the Python gate on **real worker output**.
- **APPROVED-passes assertion (live, real worker):** with the env flag set, the review/gate
  step yields a parsed `SUCCEEDED` result carrying `verdict == APPROVED` from the real worker,
  and the run is **not blocked** at that gate (the verdict gate fired on real worker output and
  PASSED).
- **REJECTED-blocks proof:** prove the negative — a REJECTED (or missing) verdict on a review
  step BLOCKs the run. OQ-2 / PLAN selects the cheapest faithful mechanism (e.g. a
  deterministic fake/stub review step in a fast unit/integration test that exercises the same
  gate, OR a second live run prompted to reject if cheap) — the live half MUST prove APPROVED
  passes on a real worker; the REJECTED-blocks half MAY use the existing faked gate path so CI
  stays green and credit is not burned twice.
- Env-gated (`DADAIA_E2E_REAL_WORKER=1` + the existing `pi` live preconditions), **skip-by-default**
  so default `pytest` / CI stay fully faked + green. The codex live variant is **OPTIONAL**
  (OQ-2). Document the run command in the module docstring + PLAN.

**Worker-compliance note (D-6):** now that the contract is coherent (Cluster 1) and strict
accept is primary (Cluster 2), the live run should pass via the **strict** path. The e2e must
assert the verdict gate fired on real worker output; if a real worker still mis-labels and only
the structural fallback accepts it, that is a recorded CLOSURE residual (the fallback is
retained for exactly this — Cluster 2).

**Explicitly out:** running the e2e in default CI; a non-opt-in real-worker test; making the
REJECTED-blocks half a mandatory second live (credit-burning) run; a full all-steps real run
*unless* PLAN selects the full `release_definition` sequence as the chosen target.

**Acceptance:**
- A13. The real-worker e2e drives a chain that includes **≥1 review/gate step** whose verdict is
  read by the Python gate on **real `pi` worker output**; env-gated, **SKIPPED by default** (a
  default `pytest` / CI run collects it and skips — fully faked + green).
- A14. With the env flag set, the review/gate step yields a parsed `SUCCEEDED` result carrying
  `verdict == APPROVED` from the real worker, and the run is **not blocked** at that gate — the
  e2e asserts the **verdict gate fired on real worker output and PASSED** (concrete state, not
  "no exception").
- A15. The **REJECTED-blocks** negative is proven: a REJECTED/missing verdict on a review step
  BLOCKs the run (asserted concretely; the mechanism per OQ-2 — live or faked-gate path — keeps
  default CI green and does not burn credit twice).
- A16. The run command is documented (test docstring + PLAN); a default `pytest` run shows the
  live review-path test SKIPPED (not failed, not errored).

### 3.5 Cluster 5 — Bug disposition (Wave D — CLOSURE only; recorded now)

**Scope:** record the disposition plan now; flip status at CLOSURE (do NOT close the bug in
this DEFINITION cycle).

**Plan (release-governance: bugs are always solved):**
- `lifecycle-prompt-names-two-schemas-confusing-real-workers` → solved by Clusters 1+2 (D-1/
  D-2/D-3 make the contract coherent; D-4 restores strict accept so worker compliance no longer
  *depends* on tolerance); status flips to `Closed` at CLOSURE with the live-review-e2e
  evidence (A14) + the coherent-contract tests (A1-A3).

**Acceptance:**
- A17. At CLOSURE, the bug carries `status: Closed` with an evidence pointer (CLOSURE section /
  commit SHA) in the disposition sweep; it is not deleted (never-delete law).

---

## 4. Out of scope

- **Implementation itself: this release is DEFINE-ONLY (D-7).** Deliverable now is approved
  SPEC/PLAN/TASKS + a DEFINITION review (architect + qa). Every TASKS marker stays `[ ]`.
  Implementation begins only after the operator approves at the DEFINITION checkpoint and
  `ACTIVE.md` advances to IMPLEMENTATION. **No push** (standing operator constraint — D-7).
- **A new fragment family / `create_handoff` fragment** — forbidden by D-1/D-2; extend the
  single `shared.output_handoff`.
- **A new schema id** — the transport id `agent-run-result-v1` is the single target (D-1).
- **Per-step `expected_schema` wiring** — the default already is `agent-run-result-v1`; threading
  a per-step schema is explicitly rejected (D-1/D-7).
- **Renaming the extractor's `schema` field** — the docs/prompt align to the extractor, not the
  reverse (D-3 / OQ-1).
- **Field-level schema validation of payloads** — the `schema`-field equality is the mechanism;
  no full schema validator is added (D-7).
- **Removing the structural-acceptance fallback** — it is retained as documented
  defence-in-depth (D-4); only its primacy is removed.
- **Running the real-worker e2e in default CI / on every push** — env-gated, opt-in only (D-6);
  default CI/pytest stay fully faked + green.
- **A mandatory second credit-burning live run for the REJECTED-blocks proof** — the negative may
  use the faked gate path (OQ-2).
- **Any new harness, plugin pack, or new fragment family** (D-7).
- **`pyproject` version bump** — version stays `0.1.7` (no PyPI — D-7).

---

## 5. Laws (binding — from GRILL D-1..D-7)

- **L1 — One transport schema, in `schema` (D-1).** The worker always emits the transport
  envelope id `agent-run-result-v1` in a field named `schema`. The fragment `output_schema`
  stays descriptive — it is never what the worker puts in the `schema` field. No per-step
  `expected_schema` wiring.
- **L2 — Step-kind-aware emission, both surfaces, no silent default (D-2 / C2 / C6).**
  `build_fragment_suffix` is `is_review`-aware via a **keyword-only, no-default** param: review
  steps are told to self-verdict (APPROVED/REJECTED + evidence); create steps are told to emit
  an artifact + `artifact_refs` and are NOT told to self-verdict. The prompt matches the
  v0.1.31 review-only gate. The **second stale surface** `pipeline._generic_prompt` is made
  step-kind-aware too — no universal-verdict text survives on any prompt path.
- **L3 — Canonical field name `schema` (D-3).** The contract names exactly one field (`schema`,
  the literal transport id), reconciled across prompt, `shared/output-handoff.md`, and the
  extractor. The extractor's field name is the canon; docs align to it.
- **L4 — Strict primary, structural defence-in-depth, pinned by behaviour (D-4 / C5).** With the
  contract coherent, `schema == expected_schema` is the PRIMARY accept; structural acceptance is
  an explicit, documented fallback (not load-bearing). A no-op worker still BLOCKs. No
  field-level schema validation is added. Primacy is pinned by a **behaviour test** (a both-valid
  payload takes the strict path; a structural-only payload takes only the fallback) so a future
  reordering fails the test — not by docstring text alone.
- **L5 — Codex parity, single helper proven (D-5 / C3 / C4).** The second Layer-2 worker
  (`codex`) gets the same coherent contract and the same fenced-or-bare + strict-primary/
  structural-fallback extraction, AND rejects arbitrary JSON lacking the result shape (no more
  unconditional dict acceptance). The extraction/acceptance logic is factored once and
  **positively proven** by a test that patches the shared helper and asserts both pi and codex
  call it — pi and codex cannot diverge.
- **L6 — Prove the review path live (D-6).** At least one env-gated real-worker e2e proves a
  real `pi` worker emits a real APPROVED verdict on a review/gate step and the review gate
  PASSES live; the REJECTED-blocks negative is proven. Skip-by-default; CI stays faked + green.
- **L7 — Never delete a bug file.** `lifecycle-prompt-names-two-schemas-confusing-real-workers`
  is dispositioned `Closed` with evidence at CLOSURE, never removed (release-governance
  never-delete law).
- **L8 — Extend existing seams only (D-7).** No parallel fragment family, no new schema, no new
  harness, no per-step `expected_schema` wiring; software-architect enforces the root-cause +
  fidelity gates on this SPEC. No push; version stays v0.1.32 (`pyproject` 0.1.7).

---

## 6. Memory files affected at closure

(Updated at CLOSURE, not now — DEFINITION authorship defers memory to CLOSURE per the
constitution §13 / `dadaia-release-closure` skill.)

- `specs/memory/architecture.md` — the worker-output contract is now **coherent by design**:
  the worker emits one transport schema (`agent-run-result-v1`) in the `schema` field; the
  emission instruction is step-kind-aware (review steps self-verdict; create steps emit an
  artifact); the extractor accepts strict-primary + structural-defence-in-depth; both pi and
  codex share one extraction path. Replaces the v0.1.31 "structural acceptance is load-bearing"
  note.
- `specs/memory/product/sdd/lifecycle-foundation.md` — the review/verdict path is now proven
  live on a real Layer-2 worker (env-gated anti-fake e2e); the worker-output contract is
  coherent (one field, one value, step-kind-aware); codex shares pi's extraction tolerance.
  Remove the stale "real workers depend on extractor tolerance" framing.
- `specs/memory/tech-stack.md` — record the live-verified pinned `pi` build used for the
  live review-path proof, if it changed since v0.1.31. No new locked dependency expected.
- `specs/memory/product/index.md` + `catalog.json` — no change expected (no feature added/
  removed/reordered); state the reason at CLOSURE if confirmed.

---

## 7. Dependencies and risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | Restoring strict accept as primary regresses the live chain if a real worker still mis-labels `schema` | HIGH | A6/A7/L4: structural acceptance is RETAINED as documented fallback; the live e2e (A14) proves the coherent contract makes strict accept the path; if it only passes structurally, that residual is recorded at CLOSURE |
| R2 | A `build_fragment_suffix` call site is missed when threading `is_review`, so a create step is still told to self-verdict (or a review step is not) | HIGH | A1/A4/C2: keyword-only **no-default** `is_review` forces every caller to choose (a forgotten flag is a call error); the threading test ENUMERATES the callers and FAILS on a new omitter; all SIX call sites threaded; a test asserts review-vs-create prompt text per call path |
| R2b (C6) | The **second stale surface** `pipeline._generic_prompt` keeps the universal-verdict text and re-introduces Drift 1 on generic pipeline steps | HIGH | A4b: `_generic_prompt` is made step-kind-aware; a test asserts review→verdict, create→no-self-verdict |
| R3 | The codex extractor is left less tolerant than pi (OQ-3 finding), so a real codex worker BLOCKs on a create step, OR pi/codex silently diverge | HIGH | A10/A11/A12/L5/C3/C4: codex hardened to pi parity incl. reject-guard (rejects shapeless JSON); the helper is factored once and **positively proven** by a patch-the-helper test asserting both adapters call it |
| R3b (C5) | A future edit silently re-promotes structural acceptance to primary, eroding the schema contract | MEDIUM | A9/L4: a behaviour test feeds a both-valid payload (strict wins) and a structural-only payload (fallback only) — a reorder that makes structural shadow strict FAILS the test |
| R4 | The live review-path proof burns operator credit on every run / leaks into CI | MEDIUM | A13/A16 / D-6: env-gated (`DADAIA_E2E_REAL_WORKER=1` + live preconditions), auto-SKIP by default; the REJECTED-blocks negative may use the faked gate path (no second live run) |
| R5 | A real worker does not reliably emit a real APPROVED verdict even with the coherent contract, so the live review proof cannot pass strict | MEDIUM | A14 + Cluster-2 fallback: structural acceptance still parses the verdict-carrying payload; the live proof asserts the gate fired on real output; a strict-vs-fallback outcome is a recorded CLOSURE residual |
| R6 | Removing `{bundle.output_schema}` from the "## Required output" text loses information the worker needs to know which artifact to produce | MEDIUM | A2/L1: the fragment body + the `produces` ledger already tell the worker the artifact; only the *competing schema-to-emit* framing is removed, not the artifact description |
| R7 | Editing `shared/output-handoff.md` (a `public/` fragment) drifts the projection | LOW | re-stage + `dadaia public install --target all` + `dadaia public doctor` `[ok]` after the fragment edit (PLAN §4) |
| R8 | Scope creep on a bug-driven release | LOW | D-7 anti-slop framing; D-7 DEFINE-ONLY checkpoint lets the operator prune before any wave runs; architect fidelity gate |

**Upstream/sequencing:** Wave A (the coherent prompt contract) is the keystone — it is what
makes strict accept correct. Wave B (strict-primary extractor + codex parity) depends on Wave A
(the contract must be coherent before strict accept is restored). Wave C (the live review-path
proof) depends on Wave A **and** Wave B — it cannot prove the review gate fires strictly on real
output until both land. Wave D (disposition) is CLOSURE-only. See PLAN.md for the full spine.

**Open questions — RESOLVED at the DEFINITION review (architect + qa, APPROVE-WITH-CONDITIONS):**
- OQ-1 (RESOLVED): D-3 canonical field is **`schema`** (align docs to the extractor), not
  teaching the extractor to also read `schema_version`. Encoded as A3/L3; the fragment-guard test
  now kills both halves of Drift 2/3 in the fragment body (C1).
- OQ-2 (RESOLVED): the live review proof targets **the minimal `release_scope → spec_create →
  spec_arch_review` create→review pair** (PLAN §3, Wave C); the REJECTED-blocks negative uses the
  **faked gate path** (no second live run); the **codex live variant is OMITTED** (pi required;
  codex parity is unit-proven). Encoded as A13-A16.
- OQ-3 (RESOLVED): **codex DOES need hardening** — its `_result_from_output` does a single
  `json.loads` with no fenced/bare/sliced fallback and no `schema` acceptance, so a real codex
  worker that fences or trails prose would BLOCK a create step. Encoded as Cluster 3 /
  A10-A12 / L5; the shared-helper factoring is confirmed and positively proven (C3).

**DEFINITION-review conditions folded (architect + qa, APPROVE-WITH-CONDITIONS):** C1 (fragment
guard kills both halves of Drift 2/3 — A3); C2 (no-default keyword-only `is_review` + enumerating
caller test — A1/A4/L2); C3 (positively prove single shared helper — A12); C4 (codex reject-guard
parity — A11); C5 (pin strict primacy by behaviour — A9); C6 (the `pipeline._generic_prompt`
second stale surface made step-kind-aware — A4b).
