# Closure: Release — v0.1.32 — harden real-worker workflows (coherent worker-output contract + live review path)

> **Status:** Aprovado
> **Release ID:** v0.1.32
> **Owner:** product-engineer
> **Closed:** 2026-06-27

## Summary

v0.1.32 turns the v0.1.31 extractor *tolerance* into a worker-output contract that is **coherent
by design**, and proves the previously-unproven half of the workflow — the **review/verdict
path** — live on a real Layer-2 worker. v0.1.31 made the dadaia-workflows run on a real `pi`
worker past step 1, but only the *create* path, and only because the PI extractor was hardened to
*tolerate* a non-compliant worker: the prompt told the worker one thing (self-verdict, conform to
the fragment's domain schema), the extractor checked another (`schema == agent-run-result-v1`),
and the shared fragment documented a third field name (`schema_version`). A real GPT/Codex worker
reconciled that contradiction differently across runs, so a strict extractor would silently drop a
correct result, leaving structural acceptance load-bearing.

This release makes the contract say exactly one thing. The worker is now told ONE field name
(`schema`) with ONE value (the transport id `agent-run-result-v1`), and the "## Required output"
instruction is **step-kind-aware** — review steps self-verdict (APPROVED/REJECTED + evidence);
create steps emit an artifact + `artifact_refs` and are NOT told to self-verdict. The instruction
was made coherent across **all three** prompt surfaces: `build_fragment_suffix` (now `is_review`-
aware via a keyword-only, no-default parameter so a forgotten flag is a call error), the pipeline's
`_generic_prompt` (the second stale surface the SPEC named), and — discovered during
implementation — a **third** stale surface in the CLI's `_run_phase_step`, all reconciled through a
single shared `is_review_phase` helper. With the contract coherent, result extraction is single-
sourced in `headless_adapter_base` (strict-primary `schema == expected_schema`, structural fallback
as documented defence-in-depth, `normalize_artifact_refs` accepting string OR object-form refs) and
shared by both the `pi` and `codex` adapters, so the second Layer-2 worker behaves identically and
the two cannot diverge.

The core proof is live: with `DADAIA_E2E_REAL_WORKER=1` a real `pi` worker (gpt-5.5,
software-architect) reviewed a substantive SPEC, emitted `verdict: APPROVED`, and the Python
verdict gate PASSED on real worker output. The acceptance was via the **STRICT** path — the worker
emitted `schema: agent-run-result-v1` matching the expected transport id, so the structural
fallback was never needed (R5): the coherent contract made the worker comply by design, exactly as
intended. The REJECTED-blocks negative is proven via the faked gate path so default CI stays green
and operator credit is not burned twice. This CLOSURE was authored CLOSURE-ONLY per the operator's
decision — no push, no PR, no `git mv` to `_archive` (the coordinator performs the archive/repoint
mechanics after this document, the memory atoms, and the disposition sweep are written).

## Tasks completed

All Wave A/B/C implementation tasks are `[x]`. T-32-Z-01 is this CLOSURE task. Commit SHAs are on
`feature/v0.1.32` (range `3ee88fa7..HEAD`).

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-32-A-01 | Failing suffix-contract tests (review vs create; one schema; `_generic_prompt` step-kind-aware) | `b266217d` |
| T-32-A-02 | `build_fragment_suffix` `is_review`-aware + one-schema/canonical text | `b266217d` |
| T-32-A-03 | Failing enumerating threading test (FAILS when a caller omits the flag) | `b266217d` |
| T-32-A-04 | Thread `is_review` at the six `build_fragment_suffix` call sites + `_generic_prompt` step-kind-aware | `b266217d` |
| T-32-A-05 | Canonical field `schema` in `shared/output-handoff.md` (re-stage + install + public doctor) | `b266217d` |
| T-32-A-06 | Fragment-guard test — both halves of Drift 2/3 die in the body | `b266217d` |
| T-32-B-01 | Failing extractor strict/structural tests (pi + codex; C5 behaviour; C4 codex reject-guard) | `103014f9` |
| T-32-B-02 | Factor the shared extraction/acceptance helper once (`headless_adapter_base`); rewire pi | `103014f9` |
| T-32-B-03 | Codex parity: rewire `_result_from_output` to the shared helper + patch-the-helper proof | `103014f9` |
| T-32-C-01 | Extend the real-worker e2e chain to include a real review step (+ `normalize_artifact_refs`, substantive SPEC fixture) | `737c511` / `0e1a7750` |
| T-32-C-02 | Live: real `pi` review step emits APPROVED and the gate PASSES | `737c511` |
| T-32-C-03 | REJECTED-blocks negative (faked gate path, default-CI green) | `737c511` |
| T-32-Z-01 | Release closure + memory atoms + disposition sweep | this commit |

Supporting on-branch commits: `ef85f0b4` (DEFINITION: SPEC/PLAN/TASKS/GRILL), `a780a545`
(advance-to-IMPLEMENTATION), `a14a5388` (review remediation — the third stale prompt surface
`cli/commands/lifecycle.py _run_phase_step` made step-kind-aware via the shared `is_review_phase`
helper + a guard test).

## Validations

Each validation is a triple: description, command, evidence.

| Description | Command | Evidence |
|-------------|---------|----------|
| Full faked suite green (the 3 real-worker live tests skip by default) | `pytest -p no:cacheprovider` | `4105 passed, 17 skipped` |
| Strict type-check clean | `mypy --strict dadaia_workspace` | `Success` — 288 files |
| Format clean | `ruff format --check .` | clean |
| Lint clean | `ruff check --no-cache .` | clean |
| **LIVE review-path proof** — real `pi` (gpt-5.5, software-architect) reviews a substantive SPEC, emits `verdict: APPROVED`, the Python verdict gate PASSES on real worker output via the **STRICT** path (worker emitted `schema: agent-run-result-v1`; structural fallback NOT needed) | `DADAIA_E2E_REAL_WORKER=1 PI_BIN=$(command -v pi) pytest tests/integration/pi_live/test_real_layer2_worker_workflow_e2e.py::test_real_pi_worker_review_step_emits_approved_and_gate_passes` | **PASSED** — `spec_arch_review` ran, yielded a parsed `SUCCEEDED` result carrying `verdict == APPROVED`, run NOT blocked at the review gate; **STRICT acceptance** (R5) |
| Code review | code-reviewer | APPROVE-WITH-COMMENTS — its lone MEDIUM (the third stale surface) FIXED in `a14a5388` |
| Security review (0 boundary regressions, 0 secrets) | security-reviewer | APPROVE |
| Acceptance review (A1–A18 + 6 DEFINITION-review conditions pinned) | qa-engineer | APPROVE |

## Drifts

### third-stale-prompt-surface-cli-run-phase-step

**Description:** The SPEC named exactly two stale "## Required output" surfaces carrying the
universal self-verdict text: `build_fragment_suffix` (Wave A keystone) and `pipeline._generic_prompt`
(the C6 second stale surface). During code review a **third** stale surface was found:
`cli/commands/lifecycle.py _run_phase_step` independently assembled a step prompt that hard-coded
the universal-verdict instruction for every step, re-introducing Drift 1 on the CLI single-step
verb path (`dadaia lifecycle implement`/`review`/`close`). Left untouched it would have been an
untested stale-text path on a real surface operators invoke.

**Resolution:** Factored the review-vs-create decision into a single shared `is_review_phase`
helper and made `_run_phase_step` step-kind-aware through it (review → verdict instruction;
create → emit artifact + refs, no self-verdict), with a guard test. Fixed in `a14a5388` as code-
review remediation. The shared helper means a future fourth surface inherits the correct branch
rather than copy-pasting a fork — closing the divergence class, not just this instance.

**Memory updates:** `specs/memory/architecture.md` and `specs/memory/product/sdd/lifecycle-foundation.md`
(the "## Required output" instruction is now step-kind-aware across **all three** prompt surfaces
via the shared helper).

### live-review-acceptance-was-strict-not-structural

**Description:** R5 (SPEC §7) anticipated that a real worker might still mis-label `schema` even
with the coherent contract, so the live review proof might pass only via the structural fallback
(a recorded CLOSURE residual). The live run resolved the open question in the strong direction:
the real `pi` worker emitted `schema: agent-run-result-v1` matching `expected_schema`, so the
verdict-carrying payload was accepted via the **STRICT** primary path — the structural fallback
was never exercised.

**Resolution:** No residual. The coherent contract (Wave A) plus strict-primary acceptance (Wave B)
work as designed: the worker complied by design. Structural acceptance remains in place as
documented defence-in-depth for an imperfectly-labelling worker (pinned by the Wave-B behaviour
test C5/A9), but it is no longer load-bearing — the v0.1.31 "structural acceptance is load-bearing"
posture is retired. This is the intended R5 outcome, recorded as the positive result.

**Memory updates:** `specs/memory/architecture.md` and `specs/memory/product/sdd/lifecycle-foundation.md`
(the review/verdict path is proven live and the live acceptance was strict; structural acceptance
demoted to defence-in-depth).

## Memory updates

Memory describes the product as it is **after** v0.1.32 (atomic snapshot, not a changelog). Files
written during this CLOSURE phase:

- `specs/memory/architecture.md` — the worker-output contract is now **coherent by design**: the
  worker emits one transport schema (`agent-run-result-v1`) in a single field named `schema`; the
  "## Required output" instruction is step-kind-aware (review → verdict; create → artifact only)
  across **all three** prompt surfaces (`build_fragment_suffix` via a keyword-only no-default
  `is_review`, `pipeline._generic_prompt`, and CLI `_run_phase_step` via the shared `is_review_phase`
  helper); result extraction is single-sourced in `headless_adapter_base` (strict-primary
  `schema == expected_schema`, structural fallback as defence-in-depth, `normalize_artifact_refs`
  accepts string OR object refs) and shared by both pi and codex; the review/verdict path is proven
  live (real pi APPROVED via the STRICT path). Replaces the v0.1.31 "structural acceptance is load-
  bearing / extractor tolerance" framing.
- `specs/memory/product/sdd/lifecycle-foundation.md` — the review/verdict path is now proven live on
  a real Layer-2 worker (env-gated anti-fake e2e); the worker-output contract is coherent (one
  field, one value, step-kind-aware, three surfaces reconciled); codex shares pi's single extraction
  helper (strict-primary + structural-defence-in-depth, string-or-object refs); removed the stale
  "real workers depend on extractor tolerance" framing and the corresponding deferred item from
  `## Current limits`.
- `specs/memory/tech-stack.md` — no change: the live review-path proof ran on the same pinned `pi`
  build already recorded in v0.1.31 (0.79.3, provider openai-codex, model gpt-5.5); no new locked
  dependency and no version change this cycle.
- `specs/memory/product/index.md` + `specs/memory/product/catalog.json` — no change: no catalog
  reorder, no feature added/removed (the touched feature `lifecycle-foundation` is already cataloged).

## Dispositions

Disposition-sweep ledger. The picked bug is solved by this release and flipped to `status: Closed`
with an evidence pointer; it is not deleted (never-delete law, L7). Follow-up items that stay Open
are recorded under "Backlog returns".

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/bugs/lifecycle-prompt-names-two-schemas-confusing-real-workers.md` | bug | `Closed` | coherent-contract Wave A (`b266217d`: `is_review`-aware suffix + one `schema` field + canonical field name, A1–A3) + strict-primary extractor Wave B (`103014f9`, A6/A9) + **live STRICT-path review proof** `test_real_pi_worker_review_step_emits_approved_and_gate_passes` PASSED (A14, R5); CLOSURE Validations |

## Backlog returns

Out-of-scope follow-ups discovered or carried during this release. They stay `Open` (never-delete
law); per the dispatch they are noted here without creating new files where none exist.

- `specs/bugs/subagent-handoff-resolves-dadaia-inside-repo-cwd.md` (**Open**, MEDIUM) — recurred
  every wave this session: subagents writing handoffs into the repo-cwd `.dadaia/` instead of the
  workspace-root `.dadaia/`. Carried forward; not fixed this release (out of the coherent-contract
  scope).
- **(LOW) `shared/output-handoff.md` body table omits an `artifact_refs` row** — code-review
  follow-up, NOT fixed this release. The fragment body documents `schema`/`verdict`/`verdict_reason`/
  `findings` but the body table does not carry a dedicated `artifact_refs` row even though the
  worker is instructed to emit it. Cosmetic/doc-completeness; the extractor already reads
  `artifact_refs` and `normalize_artifact_refs` accepts both shapes. Noted as a CLOSURE follow-up
  (no new file created per the dispatch).
- **(INFO) `pi_runtime._structured_from_verdict` vs `codex_runtime._structured_from_payload`
  flatten `structured_output` asymmetrically** — code-review follow-up, NOT fixed this release. The
  two adapters now share the candidate-scan + accept helper (A12), but the post-accept flattening of
  `structured_output` into the result still differs in shape between the two runtimes. No behavioural
  divergence at the gate (both surface `verdict`/`artifact_refs`/`changed_paths`); noted as an INFO
  follow-up for a future parity polish (no new file created per the dispatch).

No new backlog candidates or ideas beyond the above.

## Archive decision

**MOVE** — the release directory will be moved to `specs/_archive/releases/v0.1.32/` via `git mv`,
and `ACTIVE.md` repointed to the next release (or `release: none`), **by the coordinator** (the
operator's CLOSURE-ONLY decision defers the archive/repoint mechanics to the coordinator after this
document, the memory atoms, and the disposition sweep are written). Product-engineer does not push,
open a PR, or `git mv` in this turn.
