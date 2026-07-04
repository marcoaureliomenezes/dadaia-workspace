# Closure: Release — v0.1.56 — Lifecycle Verb Governance

> **Status:** Aprovado
> **Release ID:** v0.1.56
> **Owner:** product-engineer
> **Closed:** 2026-07-04
> **Branch:** `feature/v0.1.56` · **Base:** `53a14e57` (v0.1.55 closure) · **Merged:** `3a02f758` (PR #101, squash of `feature/v0.1.56`) · **Closure branch:** `closure/v0.1.56`
> **Ship gates:** qa-engineer **APPROVE** (zero blockers, 5/5 AC coverage re-verified) · security-reviewer **APPROVED** (zero findings, keyed to `5e2483b8`) · CI 35 checks, 0 failures.

## Summary

v0.1.56 is R8 of the operator's R6→R8 continuation mandate — the **final** release of that
mandate — and it settles the runtime/policy seam before prompt assembly is rebuilt in R9. Before
this release the v0.1.28/29 governance control plane (the shared `WorkflowExecutionPolicyResolver`,
the per-run `WorkflowPolicySnapshot` frozen before step 1, and the single author of `runtime_kind`)
governed **exactly one verb** — `dadaia lifecycle pipeline`; every other run-a-worker verb ran a
legacy raw `<id>:<effort>` second path and authored `runtime_kind` itself. This release makes
governance uniform: **every** run verb now resolves its policy through the one shared resolver,
freezes the resolved snapshot onto the run before step 1, and lets a single FAKE-preserving
per-step author (`apply_entry_to_step`, mapped by `apply_resolved_policy` over a **structural**
`PolicyApplicableStep` Protocol) be the sole author of each step's `runtime_kind`. The raw id:effort
path is retired; `--step-model` is profile-ids-only on every verb; `--model` degrades to a non-fatal
stderr deprecation warning that proceeds under the resolved policy.

Three catalog-AVAILABLE workflows with real fragment+gate bodies but no way to be run —
`audit`/`research`/`bug_report` — become **invocable** CLI verbs, each backed by a container builder
and **born resolver-governed** on the same seam (no second raw path). The `bug_report` driving fake
is step-aware so its ADDITIVE `bug_write` step stays in-scope and the run COMPLETES. The defective,
unreachable `run_implement_review_loop` is fixed at the root: it now injects the resolved
`review#N-1` rejection digest into the `implement#N` prompt, routes both loop workers through the
`LifecycleAgentRunner` **evidence-only structural gate** (never verdict-gating the review worker,
which would kill the retry model on round 0), and gains its **first production caller**, the
`dadaia lifecycle implement-review` verb. Finally the `TRANSITIONS` table is made honest: the three
provably-dead `QA_REVIEW`/`SECURITY_REVIEW`/`CODE_REVIEW` → `IMPLEMENTATION` backtrack edges are
removed while every forward edge and the full `BLOCKED → {…}` resume fan-out are retained. After
this release the roster is **7 defined / 7 invocable workflows**, surfaced by ≈12 CLI verbs.

This CLOSURE records the invocability and control-plane truth into memory (`dadaia-workflows`,
`lifecycle-foundation`), confirms no change is needed in `architecture`/`quality-assurance`/
`tech-stack`, dispositions the single consumed backlog entry (bug ledger stays 0 open), and returns
one follow-through item (`hard-remove-model-flag-across-run-verbs`) tracking the eventual hard
removal of the deprecated `--model` flag once callers migrate.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-56-01 | W0 definition (SPEC/PLAN/TASKS from the 2026-07-03 verb-by-verb code read; mandatory release-definition grill on the picked set; dual definition review software-architect REJECT + qa-engineer REJECT → R-1..R-6 + A1..A9 folded + `--model` deprecation ruling → Decisions A=WIRE / B=REMOVE ratified → `Aprovado`) | `cffae53f` (definition) · phase-flip `3f163c2a` (squash `3a02f758`) |
| T-56-10 | W1 FR1 — route all 7 run verbs through the shared resolver; extract `apply_entry_to_step` + structural `PolicyApplicableStep` Protocol; `ReleaseStep`/`BacklogStep` `resolved_model`+`model_profile` + `policy_snapshot` on both workflow `__init__`s; FAKE-preservation seed; retire the raw `<id>:<effort>` path; `--model` non-fatal deprecation warning | `78bb92a9` (squash `3a02f758`) |
| T-56-20 | W2 FR2 — wire `audit`/`research`/`bug_report` as invocable, born-governed CLI verbs + three container builders (bug_report step-aware fake keeps ADDITIVE `bug_write` in-scope); three-part FR1 seam on each body; NO `pipeline.py` edit (structural decoupling) | `c86283f5` (squash `3a02f758`) |
| T-56-30 | W3 FR3 — fix `run_implement_review_loop`: digest injection + evidence-only structural runner gate (`is_review=False`) + `dadaia lifecycle implement-review` CLI caller; 4-test fate ledger resolved | `65e1600a` (squash `3a02f758`) |
| T-56-40 | W4 FR4 — remove the three review→IMPLEMENTATION backtrack edges from `TRANSITIONS`; frozenset-equality pins; invert the two synthetic-ladder integration tests that asserted the removed edges; A9 public-asset grep → no `public/` edit | `4e6ed9cd` (squash `3a02f758`) |
| T-56-50 | W5 gates + ship — full local gates (AC-6); frozen no-steal suite zero-diff; QA ship gate APPROVE; security push gate keyed to pushed sha; push; CI watch; PR #101; merge | `5e2483b8` · merge `3a02f758` |
| T-56-60 | W6 closure — this CLOSURE.md + memory truth updates + disposition sweep + backlog return + candidates R8 row shipped | (this closure) |

## Validations

Each row is a triple: description, command, evidence (SHA / stdout snippet / handoff path). Gate
evidence captured at the W5 tree (`4e6ed9cd`), re-verified on PR #101 (`3a02f758`).

| Description | Command | Evidence |
|-------------|---------|----------|
| AC-6 full suite green (unpiped, real exit) | `pytest tests/` (no pipe) | `4406 passed, 17 skipped, exit 0` (722s) — QA ship-gate handoff `2026-07-04T024052Z-qa-engineer-v0156-ship-gate` |
| AC-6 format + lint clean | `ruff format --check` · `ruff check --no-cache` | both exit 0 (772 files ruff format) — W5 |
| AC-6 types clean | `mypy --strict dadaia_workspace` | exit 0, 302 files — W5 |
| AC-6 import contracts + ignore-cap unchanged | `lint-imports --no-cache` · `pytest …/test_import_linter_ignore_cap.py` | `8 kept, 0 broken` (zero "No matches for ignored import"); ignore-cap `== 26` + per-family `9/4/13` **UNCHANGED** (new builders/verbs import only already-imported lifecycle internals) — W5 |
| AC-6 SDD + backlog + projection doctors | `dadaia specs doctor` · `dadaia backlog doctor` · `dadaia public doctor` | specs doctor exit 0; backlog doctor exit 0; `[ok] public-privacy`, exit 0 (zero `public/` change, per the W4 A9 pre-justification) — W5 |
| Frozen v0.1.50 no-steal suite untouched | `git diff <base> -- <frozen lease/gate files>` + QA adjudication | **zero-diff** — the two "release"-substring grep hits are `model_by_kind` factory-arg repoints, not lease/gate files (release lives entirely in `features/lifecycle/**`, `core/models/lifecycle.py`, `cli/commands/lifecycle.py`, `container.py`) — W5 |
| AC-1 resolver-governance per verb (all 7+3+1) | `pytest …/test_lifecycle_verb_governance.py` + `…/test_lifecycle_fr2_wire_verbs.py` | each run verb under `--harness fake` persists a resolver-derived `LifecycleRun.workflow_policy` in the run-store record (`None` pre-fix, snapshot post-fix); RED-first per exact verb id — W1/W2/W3 |
| AC-4 FR3 loop fixes (digest + structural gate + CLI caller) | `pytest …/test_implement_review_loop.py` | `implement#N` prompt contains the `review#N-1` digest; empty-`artifact_refs` worker BLOCKs via the structural gate; `implement-review` verb drives APPROVED→COMPLETED and exhausted-retries→BLOCK — W3 |
| AC-5 FR4 TRANSITIONS frozenset pins | `pytest …/test_lifecycle_models.py` | `TRANSITIONS[QA_REVIEW] == frozenset({SECURITY_REVIEW, BLOCKED})` (and SECURITY/CODE analogues) by exact equality; `test_blocked_phase_can_resume_*` retained green — W4 |
| AC-7 mutation-sanity (sabotage → FAIL → revert) | one-line plant per new test | (a) `policy_snapshot=None` in `release_define` ⇒ AC-1 FAILED; (b) revert digest line ⇒ AC-4(a) FAILED; (c) revert structural-gate wiring ⇒ AC-4(b) FAILED; (d) re-add one removed edge ⇒ AC-5 frozenset-equality FAILED; (e) accept raw `--step-model` ⇒ AC-2(iii) rejection FAILED — all reverted, zero residue — W1..W4 |
| QA ship gate | `dadaia reports validate <handoff>` | **APPROVE**, zero blockers (5/5 AC coverage re-verified in a fresh 77-test targeted run; all three wave adjudications ruled sound; no slop) — handoff `2026-07-04T024052Z-qa-engineer-v0156-ship-gate` |
| Security push gate (per push-cycle) | pre-push security-verdict chokepoint | **APPROVED**, zero findings — keyed to `5e2483b8` (the pushed ref sha) |
| CI (PR #101) | GitHub Actions | 35 checks, 0 failures — merge gate `3a02f758` |

## Drifts

### spec-ac2iv-assumed-click-mix-stderr-kwarg

**Description:** SPEC AC-2(iv) and the TASKS W1 test note both prescribed asserting the `--model`
deprecation warning with `CliRunner(mix_stderr=False)` — the Click ≤ 8.2 idiom for splitting stderr
from stdout. The pinned Click (8.3.3) **removed** `mix_stderr` and now **separates stderr by
default**, so `CliRunner(mix_stderr=False)` raises a `TypeError` at construction.

**Resolution:** The AC-2(iv) tests use the default `CliRunner()` and assert `result.stderr`
directly (the deprecation warning text is in `result.stderr`; on the `--model X --json` path the
warning is absent from `result.stdout` so `json.loads(result.stdout)` stays parseable). The two
guarantees AC-2(iv) demanded — warning-on-stderr and parseable-json-on-stdout — are **intact**; only
the runner-construction idiom changed to match the installed Click. No behavior change.

**Memory updates:** none — a test-harness idiom detail, not a product-state change.

### bug-report-fake-step-aware-not-uniform-handoff-ref

**Description:** The TASKS W2 checklist prescribed a **uniform** `.dadaia/handoff/<ctx>/**`
artifact_ref for the `bug_report` driving fake (mirroring the release/backlog fakes). Empirically
this is **incompatible with the frozen `bug_write` scope**: the `bug_write` step's `allowed_paths`
law is `specs/bugs/**`-only, so a uniform handoff-ref out-of-scope-BLOCKs `bug_write` and the run
never reaches COMPLETED — failing AC-3.

**Resolution:** The `bug_report` fake was implemented **step-aware** — it returns a `specs/bugs/`
ref for the `bug_write` step and an in-scope handoff ref elsewhere. This is the only implementation
that satisfies both AC-3 (COMPLETED under `--harness fake`) and the frozen `bug_write` scope test.
The verb's real ADDITIVE `bug_write` target remains the `specs/bugs/` class (a structural property,
asserted structurally, not via a fake-run lease observation). Adjudicated sound at the QA ship gate.

**Memory updates:** none — a test-fixture shape, not a product-state change. (The `bug_report`
ADDITIVE `specs/bugs/**` write scope was already recorded in `lifecycle-foundation.md`.)

### spec-9b-imprecise-two-synthetic-ladder-integration-tests-inverted

**Description:** SPEC §9 Decision B stated "no positive test asserts them" of the three removed
review→IMPLEMENTATION backtrack edges. The AC-8 sweep (tests/ + docstrings) found this imprecise:
**two synthetic-ladder integration tests** asserted the removed edges as legal end-to-end —
`tests/integration/cli/test_lifecycle_pipeline_full.py::test_pipeline_qa_review_backtracks_to_implementation_on_fake`
and `::test_pipeline_security_and_code_review_backtrack_to_implementation_on_fake` (both former
T-23-03). The "no PRODUCTION consumer" half of the ruling still held (the ladder is forward-only;
the loop never touches the state machine), but these two tests inverted the claim.

**Resolution:** Both tests were **inverted** to
`test_pipeline_qa_review_cannot_backtrack_to_implementation_on_fake` /
`test_pipeline_security_and_code_review_cannot_backtrack_to_implementation_on_fake`: each asserts
`not is_legal_transition(<review>, IMPLEMENTATION)` and that the pipeline run does NOT reach
IMPLEMENTATION (the state machine rejects the illegal transition; the run stays at its review
phase). The module docstring's T-23-03 note was updated. Decision B (REMOVE) is unchanged and
strengthened — the table is now honest and the inverted tests guard the removal.

**Memory updates:** none — the TRANSITIONS-removal truth is recorded in `lifecycle-foundation.md`;
this drift is a test-fate correction, not an additional product-state change.

### latent-pipeline-accepts-illegal-transition-out-of-scope-recorded-for-future-pick

**Description:** While inverting the two synthetic-ladder tests (drift above), the implementer
noted a **latent quirk out of this release's scope**: `LifecyclePipeline` marks a step
`accepted=True` even when the state machine **rejects** an illegal transition. Because the
production ladder is forward-only and never attempts an illegal transition, this is
**synthetic-only reachability** — it cannot occur in real operation and did not affect any AC. It
surfaced only under the deliberately-illegal synthetic ladder the inverted tests construct.

**Resolution:** Recorded here for a **future pick** — no fix in v0.1.56 (out of the FR1–FR4 scope;
zero production reachability). The inverted tests already assert the run does not reach
IMPLEMENTATION, so the observable behavior is guarded; the `accepted=True`-on-rejected-transition
imprecision is a defensive-coding tidy-up for a later release. Surfaced to PM in the closure handoff
so it can be registered as a bug or slotted into a future backlog pick if the operator judges it
worth a code change.

**Memory updates:** none — synthetic-only, no product-state change.

## Memory updates

Memory describes the product **as it is now**; the change history lives here and in `_archive/`.
Written this CLOSURE (phase = CLOSURE, MEMORY gate open):

- `specs/memory/product/sdd/dadaia-workflows.md` — **`tldr` + `summary` change** (invocability):
  the 7 governed workflows are now **all operator-invocable** (v0.1.56), surfaced by these CLI
  verbs — `release define`, `backlog define`, `pipeline`, `implement`, `review qa|security|code`,
  `close`, `audit`, `research`, `bug_report`, `implement-review` (≈12 verbs on 7 workflows;
  `implement-review` is a **verb on the `implementation` workflow**, not a new workflow). The
  invocability table's three "no verb — pending" rows flip to their CLI verbs; the honest-invocability
  paragraph and the `lifecycle-verb-governance-uniformity`-pending note are replaced. `release_origin`
  → v0.1.56. **Because `tldr`/`summary` changed, `catalog.json` + `index.md` are regenerated by the
  CLI** (see below — PE does not hand-edit them).
- `specs/memory/product/sdd/lifecycle-foundation.md` — the control-plane statement is generalized to
  **every run-a-worker verb** (policy resolved through the one shared resolver, applied, and the
  snapshot frozen onto the run-store record before step 1 on all run verbs — the legacy raw
  `<id>:<effort>` second path retired); the CLI-surface line gains `audit`/`research`/`bug_report`/
  `implement-review` and the `--model` non-fatal-deprecation note; the D-2 `runtime_kind`-author note
  is generalized to `apply_entry_to_step` over the structural `PolicyApplicableStep` Protocol (with
  the FAKE-preservation seed); the `run_implement_review_loop` description gains the loop-fix note
  (digest injection + evidence-only structural gate + first production caller `implement-review`); the
  `state_machine`/`TRANSITIONS` note gains the three-review-edge removal (BLOCKED resume fan-out
  retained). `tldr`/`summary`/`area` **unchanged** (already generic) — **no catalog regen from this
  atom**. `release_origin` → v0.1.56.
- `specs/memory/architecture.md` — **no change**: the atom does **not** enumerate the `dadaia
  lifecycle` verb roster (it describes the control plane generically in §"Workflow control plane
  subsystem" and defers full mechanics to [[lifecycle-foundation]], which this CLOSURE corrects); the
  feature count is unchanged (23). Per SPEC §8 (update the verb roster only if enumerated), no edit
  and no `release_origin` bump.
- `specs/memory/quality-assurance.md` — **no change**: this release's ACs are structural assertions
  on the persisted snapshot artifact + captured prompts via the fake runtime, **not** byte-goldens,
  so the golden-authoring law is not triggered; no new CI job, no change to the five-layer taxonomy,
  the no-slop policy, the frozen no-steal suite, or the module-size ratchet. Confirmed at CLOSURE.
- `specs/memory/tech-stack.md` — **no change**: no dependency added; no harness/model roster change;
  no `AgentRuntimeKind` change. Confirmed at CLOSURE.
- `specs/memory/product/catalog.json` + `index.md` — **no hand-edit** (PE has no shell tool). The
  `dadaia-workflows.md` `tldr`/`summary` change is a catalog-regen trigger; authoritative regeneration
  (`dadaia memory catalog generate`) + `lint-memory-atoms` exit-0 confirmation is a pending
  orchestrator shell step. No other atom's `tldr`/`summary`/`area` changed.

## Dispositions

Disposition-sweep ledger. **Archival is at CLOSURE (normal), not at SHIP** — both consumed anchors
(`pipeline.py#LifecyclePipeline`, `lifecycle.py#TRANSITIONS`) **survive** this release (governance
change, not deletion), so no anchor-killing wave exists and `dadaia backlog doctor` never saw a live
entry referencing a dead anchor mid-branch (the R4/R5 dead-anchor archival-at-SHIP law does not
apply). No implementation-wave commit (W1–W4) staged any `specs/backlog/**` (verified). The consumed
entry is dispositioned + archived by the orchestrator's `git mv` at CLOSURE with `consumed_backlog.json`.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/_archive/v0.1.56/consumed-backlog/lifecycle-verb-governance-uniformity.md` | backlog | `DELIVERED — v0.1.56` | this CLOSURE (FR1→resolver-on-every-verb, FR2→invocability wire, FR3→loop fixes, FR4→TRANSITIONS reconciliation); orchestrator `git mv` + `consumed_backlog.json` at CLOSURE |

Bug ledger: **0 open** — no bug was consumed (open-bug debt at pick was 0), and none was introduced.

## Backlog returns

Filed one follow-through item (routed through PM curation), per the v0.1.56 `--model` deprecation
ruling:

- `backlog/candidates.md` (MEDIUM) ← **`hard-remove-model-flag-across-run-verbs`** — v0.1.56 made
  `--model` a non-fatal stderr deprecation warning on every run verb (anchored at
  `cli/commands/lifecycle.py#_warn_model_deprecated`); this entry tracks the **hard REMOVAL** of the
  flag across all run verbs once callers migrate to `--step-model <profile-id>` (no-legacy-code path).

The R9–R12 conversion sequence continues unchanged in `specs/backlog/candidates.md` (R8 row now
marked **SHIPPED — v0.1.56**; the consumed `lifecycle-verb-governance-uniformity` entry removed from
the surviving-candidates listing). R8 is the **final** release of the operator's R6→R8 mandate.

## Archive decision

**MOVE** — `specs/releases/v0.1.56/` will be moved to `specs/_archive/releases/v0.1.56/` via `git
mv` (by the orchestrator / devops-engineer; PE issues no git mutations), together with the consumed
backlog entry → `specs/_archive/v0.1.56/consumed-backlog/` + `consumed_backlog.json`.
`specs/releases/ACTIVE.md` is then advanced to the next release (the operator's R6→R8 mandate is
complete at R8; the R9 "Injection canon" release is the next planned entry) or `release: none` if the
operator pauses.
