# Closure: Release — v0.1.57 — Injection Canon

> **Status:** Aprovado
> **Release ID:** v0.1.57
> **Owner:** product-engineer
> **Closed:** 2026-07-04
> **Branch:** `feature/v0.1.57` · **Base:** v0.1.56 closure · **Merged:** `8bab315a` (PR #104, squash of `feature/v0.1.57`) · **Closure branch:** `closure/v0.1.57`
> **Ship gates:** qa-engineer **APPROVE** (AC-1..AC-9 each mapped to named passing tests; all 7 AC-10 evidences specific; slop check clean) · security-reviewer **APPROVED** (zero findings; re-keyed to `1aec51a4` after the CI Rich-box-wrap fix) · CI 35 checks, 0 failures on PR #104.

## Summary

v0.1.57 is R9 of the operator-approved 12-release plan — the **first** release of the R9→R12
continuation mandate — and it makes Layer-2 prompt assembly a single canonical seam and makes
role grounding a guarantee rather than per-fragment luck. Before this release, five near-identical
workflow bodies each carried their own copy of the assembly machinery, so any role-grounding fix
had to land five times (or land by accident); role grounding depended on whichever fragment author
remembered to declare a memory atom; injection was phase-blind on both agentic layers; a reachable
state-machine bug let the pipeline mark an illegal transition as accepted; and a v0.1.56 `--model`
soft-deprecation was now pure debt.

This release extracts one `FragmentGateWorkflow` base (behind the four handoff-ledger bodies —
`release_definition`, `audit`, `research`, `bug_report`) plus a thin `_FragmentAssemblyMixin` shared
with the structural-outlier `backlog_definition`, under golden-first discipline (the built prompts
and produced ledger payloads were byte-locked before the refactor). On that one seam it adds a
**declarative role→memory-atom map** (`role_atoms.py`) — a single resolve-and-inject helper consumed
by all three assembly surfaces (the base, `LifecyclePipeline`, and `LifecyclePhaseWorkflow`, wired
from the production container builders, not only fixtures) so `qa-engineer` always receives
`quality-assurance.md`, `software-architect` always receives `architecture.md`, and
`product-engineer` always receives the product catalog. It threads the active `ACTIVE.md` phase into
`SpecContext` (fail-open), adds per-input `max_context_policy` overrides, and ships a
fragment/selector/role-map coherence doctor (`FRAG-COH-1..4`) that makes Layer-2 role grounding
mechanically checkable. It fixes the illegal-transition bug at root cause with a single-sourced
`TransitionDecision.advanced` dual-signal predicate applied to both the pipeline and its
phase-workflow twin. Finally it hard-removes the `--model` flag and its `_warn_model_deprecated` seam
from all twelve run verbs (deprecation-expiry); `--step-model <profile-id>` is the sole
model-selection surface.

The Layer-1 injection question is settled by ratifying **self-pull** (Ruling A): `ctx_inject.py`
stays byte-identical, preserving the deliberate v0.1.30 dehydration; the deferred mechanical
verifiability of Layer-1 self-pull is filed as a backlog return. This CLOSURE records the assembly
canon into memory (`lifecycle-foundation`, `architecture`), retires the `--model` verb surface in
`dadaia-workflows`, adds the width-independent CLI stderr-assert law to `quality-assurance`,
confirms no change in `context-management`/`sdd-gate-v3`/`tech-stack`, dispositions the consumed
bug + three backlog entries (bug ledger returns to 0 open), and returns one item
(`layer1-selfpull-handoff-audit-line`).

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-57-01 | W0 definition — SPEC/PLAN/TASKS from the 2026-07-04 code read; mandatory release-definition grill on the picked set; three operator-unavailable rulings recorded (A ratify self-pull / B include `--model` removal / C base-for-4 + assembly-mixin-for-backlog); dual review (software-architect REJECT + qa-engineer REJECT → Q1–Q9 / A1–A5 / N1–N4 folded) → `Aprovado` | `2049b8ec` · phase-flip `b840ee5e` (squash `8bab315a`) |
| T-57-10 | W1 FR1 — capture + commit the behaviour goldens BEFORE extraction (6 goldens under `_golden/`, `_scope` model fields excluded per Q1, path-normalized per v0.1.55) | `ad886b52` (squash `8bab315a`) |
| T-57-11 | W1 FR1 — extract `FragmentGateWorkflow[StepT, ResultT]` (PEP-695) + `_FragmentAssemblyMixin`; migrate the 4 handoff-ledger bodies to thin subclasses; backlog mixes in the assembly + converges `_scope` (Problem #8 RED-first); run-scoped sequence iteration | `552708ae` (squash `8bab315a`) |
| T-57-20 | W2 FR2 — `role_atoms.py` (`ROLE_ATOM_MAP` + single-sourced `inject_role_atoms`) wired into all 3 surfaces; `SpecContext.phase` + resolve from `ACTIVE.md` at the 5 builders (fail-open); production-builder wiring assertion; `implementation.qa_review` gains `quality_assurance_atom` | `604b681a` (squash `8bab315a`) |
| T-57-30 | W3 FR3 — `fragment_coherence_doctor.py` (FRAG-COH-1..4, stable ids + fixed severities); `sel_constitution` kept + `write_set_guidance` indirection documented; per-input `input_policies` frontmatter key (test-fixture-only, N2) | `303fb482` (squash `8bab315a`) |
| T-57-40 | W4 FR4 — ratify self-pull; `ctx_inject.py` byte-identical (zero code change); byte-identical `_build_memory` bootstrap lock test + AC-10(f) sabotage | `97f18a9d` (squash `8bab315a`) |
| T-57-50 | W5 FR5+FR6 — `TransitionDecision.advanced` (A5) applied to both pipeline seams + stale-comment replace; hard-remove `--model` + `_warn_model_deprecated` across the 12 run verbs; 5 deprecation tests inverted to stderr-pinned `No such option` | `1f504401` (squash `8bab315a`) |
| T-57-60 | W6 gates + ship — full local gates (AC-11); dead-anchor archival at SHIP; public re-projection; QA ship gate APPROVE; security push gate; push; CI watch; PR #104; merge | ship-archival `cc4f4f63` · gate-evidence `876aed49` · CI-fix `1aec51a4` · merge `8bab315a` |
| T-57-70 | W7 closure — this CLOSURE.md + memory truth + disposition sweep + backlog return + candidates R9 row shipped | (this closure) |

## Validations

Each row is a triple: description, command, evidence (SHA / stdout snippet / handoff path). Gate
evidence captured at the W6 tree (`cc4f4f63`); pytest re-verified at `1f504401`, `cc4f4f63`, and on
PR #104 (`8bab315a`).

| Description | Command | Evidence |
|-------------|---------|----------|
| AC-11 full suite green (unpiped, real exit) — 3 runs | `pytest tests/` (no pipe) | `4490 passed, 17 skipped, exit 0` at W5 `1f504401`, W6 `cc4f4f63`, and re-verified on the merged tree — QA ship-gate handoff `2026-07-04T082055Z-qa-engineer-v0157-ship-gate` |
| AC-11 format + lint clean | `ruff format --check` · `ruff check --no-cache` | both exit 0 (783 files ruff format) — W6 |
| AC-11 types clean | `mypy --strict dadaia_workspace` | exit 0, 305 files — W6 |
| AC-11 import contracts + ignore-cap unchanged | `lint-imports --no-cache` · `pytest …/test_import_linter_ignore_cap.py` | `8 kept, 0 broken`; ignore-cap `== 26` + per-family `9/4/13` **UNCHANGED** (`_fragment_gate.py` / `role_atoms.py` / `fragment_coherence_doctor.py` import only lifecycle internals + `core.models.lifecycle` — no new cross-feature/infra edge) — W6 |
| AC-11 SDD doctor | `dadaia specs doctor` | exit 0 — W6 |
| AC-11 backlog doctor clean post dead-anchor archival | `dadaia backlog doctor` | exit 0; BL-SCHEMA fired on the deleted `_warn_model_deprecated` anchor exactly as planned → `hard-remove-model-flag-across-run-verbs` archived at SHIP (`cc4f4f63`), doctor green after | 
| AC-11 public re-projection (`public/lifecycle_fragments/**` changed) | `dadaia public stage && install --target all && public doctor` | `[ok] public-privacy`, exit 0 (sole public edit: `implementation/qa-review.md`) — W6 |
| Frozen v0.1.50 no-steal suite untouched | `git diff <base> -- <frozen lease/gate files>` | **zero-diff** — release lives entirely in `features/lifecycle/**`, `hooks/ctx_inject.py`, `cli/commands/lifecycle.py`, `container.py`, `public/lifecycle_fragments/**`; never enters `spec_context`/lease/gate — W6 |
| FR4 ratification — ctx_inject byte-identical | `git diff main..HEAD -- dadaia_workspace/hooks/ctx_inject.py` | **empty** (zero code change to the hook); `test_ctx_inject_bootstrap_lock.py` byte-identical `_build_memory` golden green — W4/W6 |
| AC-1 goldens byte-identical post-extraction | `pytest …/test_fragment_gate_goldens.py` | 7 passed; W2/W3 re-baselines recorded per wave (role-atom banners + fixture atom content only, platform-invariant) — W1..W3 |
| AC-3 role→atom map delivers grounding (incl. production wiring) | `pytest …/test_role_atoms_injection.py` | 28 passed: base (product-engineer→catalog, architect→architecture.md, qa→quality-assurance.md, multi-role plan_review), pipeline `review_qa` RED-first, phase_workflow, `build_lifecycle_pipeline`/`build_lifecycle_phase_workflow` wire the resolver with a real specs_dir — W2 |
| AC-5 coherence doctor green + RED-first | `dadaia lifecycle workflow doctor` · `pytest …/test_fragment_coherence_doctor.py` | `ok=True`, 0 ERROR, 25 FRAG-COH-2 WARNs on the current tree; sabotaged selector-wired `spec_create` input fires FRAG-COH-2 ERROR (`ok=False`) — W3 |
| AC-8 illegal-transition bug fixed at both seams | `pytest …/test_accepted_advanced_bugfix.py` | 6 passed: pipeline + phase_workflow steps `accepted=False` with `run.blocked is None` on an illegal transition (RED-first pre-fix `accepted=True`); legal blocked review still `accepted=False`; legal success `accepted=True` — W5 |
| AC-9 `--model` removed (parametrized × 12) | `pytest …/test_model_flag_removed_ac9.py` | 14 passed: `--model X` → `exit_code == 2`, `"No such option: --model"` in `result.stderr`, empty stdout, no `mix_stderr` kwarg; `_warn_model_deprecated` zero-ref grep; sole surviving `--model` = `pi_runtime.py`/`test_pi_runtime.py` — W5 |
| AC-10 mutation-sanity (7 sabotages → FAIL → revert) | one-line plant per new test | (a) module-global `_SEQUENCE` ⇒ custom-sequence test FAIL; (b) drop qa-engineer from map ⇒ pipeline `review_qa` grounding FAIL; (c-pipeline)/(c-twin) revert one seam ⇒ that seam's AC-8 FAIL only; (d) re-add one `--model` decl ⇒ AC-9 FAIL; (e) unregistered input on selector-wired `spec_create` ⇒ FRAG-COH-2 FAIL; (f) append atom to `_build_memory` ⇒ AC-7 byte-identical FAIL — all reverted, zero residue — W1..W5 |
| QA ship gate | `dadaia reports validate <handoff>` | **APPROVE**, zero blockers (AC-1..AC-9 each mapped to named passing tests; golden-first verified by commit order; all 7 AC-10 evidences specific; slop clean) — handoff `2026-07-04T082055Z-qa-engineer-v0157-ship-gate` |
| Security push gate (per push-cycle) | pre-push security-verdict chokepoint | **APPROVED**, zero findings — **re-keyed to `1aec51a4`** (the CI Rich-box-wrap fix moved the pushed ref sha; the earlier approval was superseded, not reused) |
| CI (PR #104) | GitHub Actions | 35 checks, 0 failures — merge gate `8bab315a` (green after the W6 Rich box-wrap stderr-assert fix `1aec51a4`) |

## Drifts

### w5-ci-rich-box-wrap-stderr-assert

**Description:** The W5 `--model`-removed tests (AC-9, parametrized × 12) asserted the substring
`"No such option: --model"` directly against `result.stderr`. They passed locally **twice** but the
first CI run went **red** on the `--model` verb cases. GitHub Actions enables Rich's ANSI + panel
boxing (a TTY-ish environment / different terminal width than the local run), so Click's usage error
renders **inside a Rich-drawn box** with line-wrapping and box-drawing characters injected mid-string
— the flat `"No such option: --model"` substring no longer appeared contiguously in the wrapped
stderr. This is the exact v0.1.26 Typer/Rich box-wrap gotcha, re-encountered because the assertion
was written width-dependently.

**Resolution:** Applied the established width-independent normalization: the assertions route
`result.stderr` through the `_norm_stderr` helper (strip ANSI, collapse box-drawing + whitespace to
single spaces) before the substring check, so the assert is terminal-width-independent. Fixed in
`1aec51a4`; CI went green (35/35); the security verdict was re-keyed to that sha.
**LESSON (recorded into memory):** any new CLI stderr **substring** assert must use the
width-independent helper from **day one** — the v0.1.26 gotcha is a **default practice**, not a
per-release rediscovery. This is why `quality-assurance.md` gains the CLI stderr-assertion law below.

**Memory updates:** `specs/memory/quality-assurance.md` — added the width-independent CLI
stderr-assertion law (Rich box-wrap) as a sibling of the golden-authoring law.

### w3-fragcoh4-self-contained-oracle

**Description:** FRAG-COH-4 (role→atom-map coverage) was first implemented to resolve each
model-driven step's injected refs against the **ambient** `specs_dir` of the running workspace. That
coupled the doctor to whatever memory tree happened to be present and **broke the clean-workspace
tests** (a freshly-scaffolded tree with a partial `specs/memory/` made the coverage check flap).

**Resolution:** FRAG-COH-4 was reworked to ground against a **self-contained canonical-layout
oracle** — a fixed in-module expectation of which role→atom the map must cover per governed step —
so the check is a **pure code-coherence proof**, ambient-tree-independent. `backlog_definition` is
explicitly EXCLUDED from FRAG-COH-4 (the W2 boundary: it shares only the assembly mixin, not
`_run_model_step`). The doctor is green on the current tree (`ok=True`, 0 ERROR); the RED-first
sabotage still bites.

**Memory updates:** recorded in `lifecycle-foundation.md` (the coherence-doctor description states
FRAG-COH-4 is a self-contained canonical-layout oracle and `backlog_definition` is out of scope).

### w1-pep695-stepoutcome-carrier

**Description:** The FR1 base extraction deviated from the plan's implied plain-generic signature in
two mechanical ways: (1) `FragmentGateWorkflow[StepT: FragmentGateStep, ResultT]` uses **PEP-695**
type-parameter syntax with a `FragmentGateStep` Protocol bound (rather than a pre-695 `TypeVar`
bound), and (2) an internal `_StepOutcome` carrier dataclass was introduced to thread each step's
(request, result, payload) tuple through the run-scoped sequence without a module-global.

**Resolution:** Both are behaviour-invisible: the goldens are byte-identical post-extraction (AC-1),
`mypy --strict` is clean on the PEP-695 form, and the custom-`_SEQUENCE` iteration test (AC-2) proves
`_StepOutcome` is threaded from the run-scoped sequence, not a module global. The deviation is a
structural improvement (self-documenting bound + a single carrier type), not a scope change.

**Memory updates:** `lifecycle-foundation.md` names the `FragmentGateWorkflow` base + `_StepOutcome`
carrier + run-scoped sequence in the assembly-canon section.

### w1-backlog-not-map-grounded-boundary

**Description:** `backlog_definition` was deliberately **NOT** wired to the role→atom map. It is a
structural outlier (kind-based dispatch, `demand` param, Python-disposing steps, **no**
handoff-ledger data plane); it shares only `_FragmentAssemblyMixin`, not the base's `_run_model_step`
where the map is resolved-and-injected. Grounding it would have required folding it onto the full
base (Ruling C explicitly rejects that — two control-flow shapes must not be coupled).

**Resolution:** The boundary is recorded and mechanically pinned: `backlog_definition` is EXCLUDED
from FRAG-COH-4's coverage set, and the golden `gate_backlog_definition.json` was **not** re-baselined
in W2 (it is not one of the three FR2 surfaces). This is an intentional scope edge, not a grounding
gap — the map covers the four handoff-ledger bodies + the two selector-less pipeline surfaces, which
is the full set of `_run_model_step`-bearing surfaces.

**Memory updates:** `lifecycle-foundation.md` states `backlog_definition` shares the assembly mixin
only (not the base) and is out of the role→atom-map coverage set.

## Memory updates

Memory describes the product **as it is now**; the change history lives here and in `_archive/`.
Written this CLOSURE (phase = CLOSURE, MEMORY gate open):

- `specs/memory/product/sdd/lifecycle-foundation.md` — **primary edit; `summary` changed** (→ catalog
  regen trigger). New `## Prompt-assembly canon (v0.1.57)` body section: the `FragmentGateWorkflow`
  base + `_FragmentAssemblyMixin` behind the 4 handoff-ledger bodies (backlog shares the mixin only);
  the single-sourced `role_atoms.py` role→memory-atom map + `inject_role_atoms` helper across the 3
  assembly surfaces (base / pipeline / phase_workflow, wired from the production builders); phase
  threaded into `SpecContext` (fail-open); per-input `input_policies` overrides; the
  `fragment_coherence_doctor` (FRAG-COH-1..4, `ok=` from ERRORs only, FRAG-COH-4 self-contained
  oracle). The state-machine bullet gains `TransitionDecision.advanced` (dual-signal predicate) and
  the both-seam `accepted = decision.advanced` fix. The CLI-surface line retires `--model` (sole
  surface `--step-model <profile-id>`; the flag is now `No such option: --model`, exit 2). Summary
  fixes `--model/--step-model` → `--step-model`, corrects `apply_resolved_policy` → `apply_entry_to_step`
  (the per-step `runtime_kind` author), and adds the assembly-canon clause. **(N4)** the section states
  Layer-2 grounding is **mechanically recorded/checked** (role→atom map + coherence doctor) while
  Layer-1 grounding is **self-pull DISCIPLINE, NOT mechanically verified** (pending
  `layer1-selfpull-handoff-audit-line`). `release_origin` → v0.1.57. `tldr` **unchanged** (generic,
  within the length cap — Q9).
- `specs/memory/architecture.md` — **body + `release_origin` only; `tldr`/`summary`/`area` UNCHANGED**
  (no catalog regen). The `features/lifecycle` bullet gains `workflows/_fragment_gate.py`,
  `role_atoms.py`, and `fragment_coherence_doctor.py`; the Workflow-control-plane subsystem line is
  corrected `apply_resolved_policy the sole author of runtime_kind` → `apply_entry_to_step the sole
  per-step author` (the v0.1.56-flagged imprecision). Feature count unchanged (23). `release_origin` →
  v0.1.57.
- `specs/memory/product/sdd/dadaia-workflows.md` — **body + `release_origin` only; `tldr`/`summary`/
  `area` UNCHANGED** (no catalog regen). The usage-flow verb example retires `[--model …]` →
  `[--step-model <step>=<profile-id>]` (the flag is gone, not deprecated). The 7-workflow roster copy
  is confirmed unchanged. `release_origin` → v0.1.57.
- `specs/memory/quality-assurance.md` — **body + `release_origin` only; `tldr`/`summary`/`area`
  UNCHANGED** (no catalog regen). Added the **CLI stderr-assertion law (width-independent — Rich
  box-wrap)**: any CLI stderr substring assert must normalize `result.stderr` (strip ANSI, collapse
  box-drawing/whitespace) before the substring check, because GitHub Actions renders Click usage
  errors inside Rich-drawn boxes; a width-dependent assert passes locally and fails on CI (the W5
  drift; the v0.1.26 gotcha is now a default practice). `release_origin` → v0.1.57.
- `specs/memory/product/platform/context-management.md` — **NO CHANGE** (confirmed): `ctx_inject.py`
  is byte-identical (FR4 ratification); no bind/lease/session change.
- `specs/memory/product/sdd/sdd-gate-v3.md` — **NO CHANGE** (confirmed): no gate/hook/chokepoint
  change; the release never entered `spec_context`/lease/gate.
- `specs/memory/tech-stack.md` — **NO CHANGE** (confirmed): no dependency, harness, or model-roster
  change; `AgentRuntimeKind` unchanged.
- `specs/memory/product/catalog.json` + `index.md` — **no hand-edit** (PE has no shell). Only
  `lifecycle-foundation.md`'s `summary` changed, so the CLI catalog regen (`dadaia memory catalog
  generate`) + `lint-memory-atoms` exit-0 is a pending orchestrator step. No other atom's `tldr`/
  `summary`/`area` changed.

## Dispositions

Disposition-sweep ledger. Two consumed backlog anchors SURVIVE this release
(`context-injection-role-phase-canon`: `ContextSelector`/`FragmentLoader`/`ctx_inject#main` all
survive; `fragment-workflow-base-dedup`: `ReleaseDefinitionWorkflow` survives refactored onto the
base) → archived **at CLOSURE** by the orchestrator `git mv`. One consumed anchor DIED
(`hard-remove-model-flag-across-run-verbs`: `_warn_model_deprecated` deleted by W5) → archived **at
SHIP** (dead-anchor BL-SCHEMA, `cc4f4f63`). No implementation-wave commit (W1–W5) staged any
`specs/backlog/**` (AC-12 verified). The bug JSONL terminal event is appended by the orchestrator
(PE has no shell).

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/context-injection-role-phase-canon.md` → `specs/_archive/v0.1.57/consumed-backlog/` | backlog | `DELIVERED — v0.1.57` | this CLOSURE (FR2 role→atom map + phase threading; FR3 coherence doctor + sel_constitution + per-input policy; FR4 L1 ruling); orchestrator `git mv` + `consumed_backlog.json` at CLOSURE |
| `specs/backlog/fragment-workflow-base-dedup.md` → `specs/_archive/v0.1.57/consumed-backlog/` | backlog | `DELIVERED — v0.1.57` | this CLOSURE (FR1 `FragmentGateWorkflow` base + `_FragmentAssemblyMixin`); orchestrator `git mv` + `consumed_backlog.json` at CLOSURE |
| `specs/_archive/v0.1.57/consumed-backlog/hard-remove-model-flag-across-run-verbs.md` | backlog | `DELIVERED — v0.1.57` | **already archived at SHIP** (`cc4f4f63`); recorded in `specs/_archive/v0.1.57/consumed_backlog.json` (FR6 `--model` hard-removal) |
| `pipeline-accepted-true-on-illegal-transition` (JSONL bug stream) | bug | `resolved --release v0.1.57` | FR5 root-cause fix (`TransitionDecision.advanced`, both seams); AC-8 evidence; terminal event appended by the orchestrator |

Bug ledger: **0 open** after this release — `pipeline-accepted-true-on-illegal-transition` (the single
open-bug debt at pick) is resolved; none introduced.

## Backlog returns

Filed one follow-through item (routed through PM curation), per Ruling A (FR4):

- `backlog/candidates.md` (HIGH) ← **`layer1-selfpull-handoff-audit-line`** — Ruling A ratified
  Layer-1 **self-pull** for constitution/architecture/quality-assurance (`ctx_inject.py`
  byte-identical). This entry tracks the **deferred mechanical verifiability** of that discipline: a
  handoff-schema audit line that proves the Layer-1 self-pull atoms were actually read, turning the
  L1 discipline into a checkable contract (handoff-v1.1 schema bump + all-agent adoption + validator).
  Anchored at `hooks/ctx_inject.py#main` + the handoff schema surface. If the operator instead
  prefers bounded phase-aware L1 digests, FR4 reopens.

## Archive decision

**MOVE** — `specs/releases/v0.1.57/` will be moved to `specs/_archive/releases/v0.1.57/` via
`git mv` (by the orchestrator / devops-engineer; PE issues no git mutations), together with the two
CLOSURE-archived consumed backlog entries → `specs/_archive/v0.1.57/consumed-backlog/` +
`consumed_backlog.json` (`hard-remove-model-flag-across-run-verbs` is already there from SHIP).
`specs/releases/ACTIVE.md` is then advanced to the next release (R10 "Harness & projection
distribution") or `release: none` if the operator pauses.
