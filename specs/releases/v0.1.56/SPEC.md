# SPEC — v0.1.56 — Lifecycle Verb Governance

**Status:** Aprovado
**Branch:** `feature/v0.1.56` (base: v0.1.55 closure `53a14e57` — the orchestrator branches after `Aprovado`)
**Origin:** R8 of the operator-approved 12-release plan; **final** release of the operator's
R6→R8 continuation mandate. Settles the runtime/policy seam before prompt assembly is rebuilt
(R9). Definition-time inspection verified by the orchestrator + PE code read (2026-07-03) — every
verb→governance fact below is a read fact from the source, not a dossier restatement.
**Release-definition grill** (mandatory, from-backlog) run on the picked set before this SPEC.
**Dual definition review 2026-07-03 (software-architect REJECT + qa-engineer REJECT — strongly
convergent; ALL amendments folded):** architect A1 FR2 workflow-body seam (R-4), A2 `apply_entry_to_step`
+ structural Protocol (R-2), A3 structural-only loop gate (R-1), A4 in-scope bug_report fake (R-5),
A5 FAKE-preservation seed (R-3), A6 run-store AC-1 channel (R-6); qa A1 7-verbs, A2 FAKE-aware AC-2,
A3 evidence-only gate, A4 loop-test-fate ledger, A5 3 inverted CLI-test rewrites, A6 frozenset pins,
A7 run-store channel, A8 workflow-vs-verb count, A9 public-asset note; + the `--model` deprecation-warning
ruling. Decisions A (WIRE) + B (REMOVE) RATIFIED. QA re-verifies this Draft before `Aprovado`.
**Consumes:** backlog `lifecycle-verb-governance-uniformity` (1). Open-bug debt at pick: **none**
(bug ledger 0 open).

## 1. Problem

The v0.1.28/29 governance control plane — the shared `WorkflowExecutionPolicyResolver`, the
per-run `WorkflowPolicySnapshot` frozen before step 1, and `apply_resolved_policy` as the single
author of `runtime_kind` — governs **exactly one verb**: `dadaia lifecycle pipeline`. Every other
run-a-worker verb still runs the legacy **raw `<id>:<effort>` second path** and authors
`runtime_kind` itself. Three catalog-AVAILABLE workflows with real bodies have no way to be run.
The implement/review loop drops its rejection digest and never touches the runner gate. The
TRANSITIONS table carries three review→implementation backtrack edges that no code path uses.

**Verb → governance matrix (derived by reading the source, 2026-07-03):**

| Verb | CLI fn (`cli/commands/lifecycle.py`) | Step type / workflow | Container builder | Resolver-governed today? | Snapshot frozen? | `apply_resolved_policy` authors `runtime_kind`? |
|---|---|---|---|---|---|---|
| `pipeline` | `pipeline` l.1041 | `PipelineStep` / `implementation_ladder` | `build_lifecycle_pipeline` | **YES** (`resolver.resolve` l.1129 → `apply_resolved_policy` l.1152) | **YES** (`policy_snapshot` frozen onto run before step 1) | **YES** |
| `release define` | `release_define` l.489 | `ReleaseStep` / `release_definition._SEQUENCE` | `build_release_definition_workflow` | **NO** — raw `_resolve_model` id:effort; CLI `_replace(step, runtime_kind=…)` l.573 authors it | **NO** (run built with no `workflow_policy`) | **NO** |
| `backlog define` | `backlog_define` l.345 | backlog step / `backlog_definition._SEQUENCE` | `build_backlog_definition_workflow` | **NO** — raw id:effort; CLI `_replace` l.434 | **NO** | **NO** |
| `implement` | `implement`→`_run_phase_step` l.676 | `LifecyclePhaseWorkflow` (`PromptScope`) | `build_lifecycle_phase_workflow` | **NO** — raw `_resolve_model` l.836; no `policy_snapshot` passed to `.run()` | **NO** | **NO** |
| `review qa` | `review_qa`→`_run_phase_step` l.896 | `LifecyclePhaseWorkflow` | `build_lifecycle_phase_workflow` | **NO** | **NO** | **NO** |
| `review security` | `review_security` l.926 | `LifecyclePhaseWorkflow` | `build_lifecycle_phase_workflow` | **NO** | **NO** | **NO** |
| `review code` | `review_code` l.956 | `LifecyclePhaseWorkflow` | `build_lifecycle_phase_workflow` | **NO** | **NO** | **NO** |
| `close` | `close`→`_run_phase_step` l.986 | `LifecyclePhaseWorkflow` | `build_lifecycle_phase_workflow` | **NO** | **NO** | **NO** |

Verified defects (read from the source):

1. **Model/harness governance covers only the pipeline verb** (matrix above). `apply_resolved_policy`
   (`pipeline.py` l.597) operates on `PipelineStep` only; `ReleaseStep`/the backlog step carry a
   nullable `runtime_kind` and **no** `resolved_model`/`model_profile` field, so the model reaches
   the adapter only through the `models: dict[kind, HarnessModelOption]` factory baked in the
   builder (`build_release_definition_workflow` l.937). `_run_phase_step` (l.810) never passes a
   `policy_snapshot` to `LifecyclePhaseWorkflow.run` (which already **accepts** one, `phase_workflow.py`
   l.97 — the seam exists, unused). `--step-model` is profile-ids-only (D-3) **only** on `pipeline`;
   every other verb takes `--model '<id>:<effort>'` via `_resolve_model` (l.721).

2. **Three catalog-AVAILABLE workflows are not operator-invocable.** `audit`/`research`/`bug_report`
   have **real fragment+gate bodies** (`AuditWorkflow`/`ResearchWorkflow`/`BugReportWorkflow`,
   mirroring `ReleaseDefinitionWorkflow` field-for-field — read `workflows/audit.py`), are projected
   into the governed catalog as `AVAILABILITY_AVAILABLE` (`governed_catalog.py` l.683-685), and are
   resolvable by the resolver + rendered in the panel. But there is **no** container builder
   (`build_{audit,research,bug_report}_workflow` do not exist — grep) and **no** CLI verb. The
   `dadaia-workflows` atom documents this honestly: **7 defined / 4 invocable**.

3. **`run_implement_review_loop` (`pipeline.py` l.259) is defective and unreachable.** (a) The
   resolved rejection digest is **dropped** — l.309 literally `_ = resolved  # digest would be
   injected into the implement prompt here.` — so `implement#N` never sees the `review#N-1`
   rejection. (b) The loop's worker runner `_run_loop_worker` (l.375) calls `runtime.run(built.request)`
   **directly**, bypassing `LifecycleAgentRunner`; it reads `review_result.structured_output.get("verdict")`
   (l.329) with **no** gate — no `artifact_refs` check, no out-of-scope check, no schema validity —
   unlike `pipeline.run` (l.219, uses the runner) and the workflow bodies (`evaluate_gate_with_result`).
   (c) **Zero production callers** (grep: only `tests/unit/features/lifecycle/test_implement_review_loop.py`).

4. **TRANSITIONS backtrack edges are unused.** `core/models/lifecycle.py` l.64 declares
   `QA_REVIEW → IMPLEMENTATION`, `SECURITY_REVIEW → IMPLEMENTATION`, `CODE_REVIEW → IMPLEMENTATION`.
   The only consumer of `is_legal_transition` is `state_machine.py` l.49. No production path
   transitions a (non-blocked) review phase back to IMPLEMENTATION: the pipeline advances forward
   only; the single-step review verbs advance forward; `run_implement_review_loop` never uses the
   state machine (it re-runs `implement` via `_run_loop_worker` and sets phase manually). The
   operator-driven rework path that *is* used is `BLOCKED → IMPLEMENTATION` (resume). The three
   direct review→implementation edges are dead table entries — an "unused path".

**Inspection facts recorded (no contradiction with the dossier, refinements only):**
- **(a)** The single-step review verbs use step labels `qa`/`security`/`code` (`_run_phase_step`
  l.913/942/972) while the governed catalog + pipeline use `review_qa`/`review_security`/`review_code`.
  FR1 must reconcile the verb→catalog-step label (a map, not a rename of the user-facing verb).
- **(b)** `implement`/`review *` belong to the `implementation` workflow; `close` to `closure`;
  `release define`→`release_definition`; `backlog define`→`backlog_definition`. Each single-step
  verb resolves a **multi-step** snapshot and selects its one step entry.
- **(c)** The two consumed anchors — `pipeline.py#LifecyclePipeline` and `lifecycle.py#TRANSITIONS`
  — **both survive** this release (governance changes, not deletions). See §6 archival note.

## 2. Goals

1. **Every** run-a-worker verb resolves its policy through the one shared
   `WorkflowExecutionPolicyResolver`, freezes the resolved `WorkflowPolicySnapshot` onto the run
   **before step 1**, and lets a generalized `apply_resolved_policy` be the **sole** author of each
   step's `runtime_kind` (FAKE preserved for dry-run). `--step-model` is **profile-ids-only** on
   every verb; the raw `<id>:<effort>` second path is retired.
2. `audit`/`research`/`bug_report` are **invocable** CLI verbs backed by container builders, **born
   resolver-governed** (they reuse the FR1 seam — no second raw path is ever introduced for them);
   the governed catalog stays AVAILABLE and is now honestly **7 invocable**.
3. `run_implement_review_loop` **injects** the resolved rejection digest into the next implement
   prompt, **gates** every loop worker through `LifecycleAgentRunner`, and has a **CLI caller**
   (`dadaia lifecycle implement-review`), born resolver-governed.
4. The TRANSITIONS table implies **no unused path**: the three direct review→implementation edges
   are **removed** (RATIFIED — see §9), keeping every forward edge and the full `BLOCKED → {…}`
   resume fan-out; the loop's rework is the bounded attempt ledger, not a phase backtrack.

## 3. Functional requirements

### FR1 — Policy resolver on every run-a-worker verb (retire the raw id:effort path)

- **Extract `apply_entry_to_step` — the single FAKE-preserving per-step author (A2/R-2).** Factor
  `apply_entry_to_step(entry, *, base_kind, preserve_fake) -> tuple[AgentRuntimeKind, ResolvedModelConfig]`
  in `pipeline.py`: it authors the step's `runtime_kind` from the snapshot entry's resolved harness
  (`codex→CODEX_EXEC`, `pi→PI_HEADLESS`), returning **FAKE when `preserve_fake`** (i.e. `base_kind is
  FAKE`), plus the `ResolvedModelConfig`. `apply_resolved_policy(steps, snapshot)` becomes a **map** of
  `apply_entry_to_step` over a **structural** Protocol `PolicyApplicableStep`
  (`label`/`runtime_kind`/`resolved_model`/`model_profile`) satisfied by `PipelineStep`, `ReleaseStep`,
  `BacklogStep`, `AuditStep`, `ResearchStep`, `BugReportStep` — the frozen step dataclasses are covered
  **structurally**, no enumerated type-union. Add `resolved_model: ResolvedModelConfig | None = None`
  and `model_profile: str | None = None` to `ReleaseStep` and the backlog step (additive-optional,
  mirror `PipelineStep`) and thread `step.resolved_model` into their `_scope` →
  `PromptScope.resolved_model`. **The single-step verb has NO step object** — a `PromptScope` is not a
  step and cannot be iterated by `apply_resolved_policy`; it calls `apply_entry_to_step` **once** with
  its selected snapshot entry and applies the result to its local `kind` + `scope.resolved_model`.
- **FAKE preservation seam (A5/R-3) — MANDATORY, before applying.** Every run verb seeds each base
  step's `runtime_kind = default_kind` (which is `FAKE` for a `--harness fake` run) **before** the
  applier — mirroring the pipeline (l.1148-1151) — and passes `preserve_fake=(default_harness is None)`.
  `ReleaseStep`/`AuditStep`/… default `runtime_kind=None`; applying to a raw `None`-kind sequence would
  map `None → codex/pi` and drive a **live** adapter on `--harness fake`. Seeding `default_kind` first
  keeps FAKE preserved while the snapshot still records the governed harness.
- **Multi-step verbs (`release define`, `backlog define`).** Each verb: builds the resolver
  (`build_workflow_policy_resolver`), `resolve("<workflow_id>", context="default", cli_overrides=…,
  default_harness=(None if fake else harness), step_harness_overrides=…)` → snapshot; **seeds base
  kinds** (above); applies the snapshot to `_SEQUENCE` via `apply_resolved_policy` (sole `runtime_kind`
  author, FAKE preserved); freezes the snapshot onto the run **before step 1**. The
  `ReleaseDefinitionWorkflow`/backlog workflow `__init__` gains an optional `policy_snapshot` frozen
  onto the run it constructs (mirror `LifecyclePipeline`/`LifecyclePhaseWorkflow`). The CLI's own
  `_replace(step, runtime_kind=…)` swap (l.434/573) is **removed** — the applier is the only author.
- **Single-step verbs (`implement`, `review qa|security|code`, `close`).** `_run_phase_step` gains a
  `workflow_id` + `catalog_step_label` (the verb→catalog-step map: `implement→implement`,
  `qa→review_qa`, `security→review_security`, `code→review_code`, `close→close`). It resolves the
  workflow snapshot, selects the step's snapshot entry, and calls `apply_entry_to_step(entry,
  base_kind=kind, preserve_fake=(default_harness is None))` **once** to author its local `runtime_kind`
  (FAKE preserved) + `resolved_model`; it threads the `resolved_model` into the `PromptScope` and passes
  the frozen `policy_snapshot` to `LifecyclePhaseWorkflow.run(policy_snapshot=…)` (the accepting seam
  already exists). It does **not** call `apply_resolved_policy` (no step object to iterate).
- **Profile-ids-only; retire the raw path; `--model` is a non-fatal deprecation warning (ruling).**
  `--step-model` takes **profile ids** on every verb, resolved+validated through the shared resolver
  (a raw `<id>:<effort>` is rejected with the same actionable message as `pipeline`'s D-3, via
  `_parse_step_profile_overrides`). The raw `_resolve_model` per-verb path is **deleted** from the run
  verbs. `--model` is **accepted but non-fatal-deprecated**: the verb emits a one-line **stderr
  deprecation warning** naming `--step-model <profile-id>` + `workflow profiles list`, then **proceeds
  with the resolved policy** — a silent no-op would be the anti-slop hidden-side-effect defect (the
  operator's model choice ignored with zero signal); a hard error would break every script/test still
  passing `--model` mid-mandate. A closure-time **backlog return** tracks hard-removing `--model` across
  all run verbs once callers migrate (no-legacy-code path). *(Optional this release, for coherence:*
  `pipeline`'s own silent `_ = model` l.1094 adopts the same warning.) `--harness` (fake/codex/pi;
  `claude` rejected, LAW 1) is unchanged and threads into `resolve` as `default_harness`.
- **Container builders.** `build_release_definition_workflow`/`build_backlog_definition_workflow`
  accept + forward an optional `policy_snapshot`; the model-by-kind factory arg is retired in favour
  of the snapshot's per-step `resolved_model` (the factory keeps FAKE→driving-fake).

### FR2 — Wire audit / research / bug_report as invocable, resolver-governed verbs

- **Decision: WIRE (not demote)** — see §9. Ratified conditioned on the workflow-body seam edit
  (A1/R-4) + the in-scope bug_report fake (A4/R-5).
- **Workflow-body seam edit (A1/R-4) — FR2 is NOT builder+verb only.** `AuditWorkflow`/
  `ResearchWorkflow`/`BugReportWorkflow` mirror `ReleaseDefinitionWorkflow` field-for-field and today
  take **no** `policy_snapshot` (their `run()` builds the `LifecycleRun` with no `workflow_policy=`;
  `audit.py` l.207-216) and their `AuditStep`/`ResearchStep`/`BugReportStep` carry **no**
  `resolved_model`/`model_profile`. Each body gets the **same three-part FR1 seam** `ReleaseStep`/
  `ReleaseDefinitionWorkflow` received in W1: **(a)** `resolved_model`/`model_profile` fields on its Step
  dataclass; **(b)** `step.resolved_model` threaded into `_scope` → `PromptScope.resolved_model`;
  **(c)** optional `policy_snapshot` on `__init__`, frozen in `run()` via `workflow_policy=self._policy_snapshot`.
  **Decoupling:** because the FR1 applier binds a **structural** Protocol (R-2), adding these two fields
  **auto-satisfies** `apply_resolved_policy` — **no `pipeline.py` edit in W2**.
- **Container builders.** Add `build_audit_workflow`/`build_research_workflow`/`build_bug_report_workflow`
  in `container.py`, mirroring `build_release_definition_workflow` (same `ContextSelector` + run-store +
  driving-fake factory; each accepts + forwards an optional `policy_snapshot`).
- **CLI verbs.** Add `dadaia lifecycle audit|research|bug_report --context --release-id --run-id
  --harness --step-model --json` (shaped like `release define` minus the synthetic demand; the bodies
  take `run(run_id, sequence=_SEQUENCE)`). Each is **born resolver-governed** via the FR1 seam: seed base
  kinds → `resolve("audit"|…)` → apply → freeze onto the run. No raw id:effort path is introduced.
- **bug_report fake is in-scope (A4/R-5).** The `bug_report` driving fake returns an **in-scope**
  `.dadaia/handoff/<ctx>/**` artifact_ref (the workflow `_scope`'s `allowed_paths` law) so the run
  COMPLETES; a `specs/bugs/` artifact_ref would be **out-of-scope** for the step and BLOCK. The verb's
  real `bug_write` target is the ADDITIVE `specs/bugs/` class — a structural property of the verb, not
  something a fake-run lease observation proves.
- **Availability stays AVAILABLE**; the governed catalog is unchanged (the bodies were always
  AVAILABLE — this closes the invocability gap). After FR2 the roster is **7 defined / 7 invocable
  workflows**.

### FR3 — Fix `run_implement_review_loop` (digest injection + STRUCTURAL runner gate + CLI caller)

- **Digest injection.** Replace the l.309 `_ = resolved` drop: render the resolved `review#N-1`
  rejection into a compact digest (`WorkflowHandoffResolver.render_digest` — a real staticmethod,
  `workflow_handoffs.py` l.374) and inject it into the `implement#N` prompt (N ≥ 1). The digest must
  reach the built request the implement worker receives.
- **Runner gate — STRUCTURAL ONLY (A3/R-1, architect ≡ qa; the single fold).** Route **both** loop
  workers through `LifecycleAgentRunner.evaluate_gate_with_result` (gate **without** a phase
  transition, as `release_definition`/`audit` do) **with `is_review=False`** — so the gate blocks
  **only** on a structural failure: non-SUCCEEDED / empty `artifact_refs` / out-of-scope paths. **Do
  NOT gate the review worker on its verdict.** The APPROVED/REJECTED verdict is read from the returned
  `worker_result.structured_output` and drives the **attempt ledger** exactly as today (l.329):
  `APPROVED → COMPLETED`; a **structurally-valid REJECTED → the next attempt** (inject the digest);
  retry exhaustion → BLOCK. A structural block on either worker BLOCKS the loop. (Gating the review
  worker `is_review=True` returns a `BlockedState` on the first REJECTED verdict — `agent_runner.py`
  l.196 — which would break the loop on round 0 and destroy the retry-with-digest model.)
  `_run_loop_worker` stops calling `runtime.run` directly.
- **CLI caller.** Add `dadaia lifecycle implement-review --context --release-id --run-id --harness
  --step-model [--max-review-retries] --json`, born resolver-governed (seed base kinds → resolve the
  `implementation` snapshot → apply to the implement + a review step → freeze onto the run; wire the
  `handoff_resolver` the loop requires). The verb reports the rounds + final verdict/blocked.

### FR4 — TRANSITIONS reconciliation (remove the unused review→implementation edges)

- **Decision: REMOVE** — see §9 for rationale + the coherence with FR3.
- Remove `QA_REVIEW → IMPLEMENTATION`, `SECURITY_REVIEW → IMPLEMENTATION`, `CODE_REVIEW →
  IMPLEMENTATION` from `TRANSITIONS` (`core/models/lifecycle.py` l.64). **Retain** every forward
  edge (IMPLEMENTATION→QA_REVIEW→SECURITY_REVIEW→CODE_REVIEW→CLOSURE), every `*→BLOCKED` edge, and
  the full `BLOCKED → {BACKLOG_DEFINITION, RELEASE_DEFINITION, IMPLEMENTATION, QA_REVIEW,
  SECURITY_REVIEW, CODE_REVIEW, CLOSURE}` resume fan-out (the operator-driven rework path stays via
  `BLOCKED → IMPLEMENTATION`).
- Update `tests/unit/core/test_lifecycle_models.py` to **assert the removal** (three new negative
  `not is_legal_transition(...)` cases) alongside the retained forward + resume assertions. No
  production consumer of the removed edges exists (verified), so nothing else changes.

## 4. Non-goals

- **No prompt-assembly / fragment-dedup work (R9).** FR2/FR3 reuse the **existing** fragment bodies
  verbatim; no fragment is added, edited, or deduped; the `context-injection-role-phase-canon` +
  `fragment-workflow-base-dedup` work is R9.
- **No new workflows.** FR2 **wires** three already-defined, already-AVAILABLE workflows; it does
  not author a new workflow body.
- **No persona changes.** Persona injection is already threaded on every verb (v0.1.44); the new
  verbs inherit it.
- **No public-asset change.** This release touches only `dadaia_workspace/` source + tests (CLI,
  lifecycle, core, container) — **no** `public/` scaffold/README/agent/fragment/persona edit, so no
  `stage`/`install` and no projection. The only `public/` references to `TRANSITIONS`/`is_legal_transition`
  (`public/skills/dadaia-task-manager/SKILL.md` l.42; `public/skills/project-orchestration/SKILL.md`
  l.108/110) name the **symbol generically**, not the removed edges (A9, verified), so FR4 triggers no
  `public/` edit and the CLOSURE `public doctor` zero-change is pre-justified (AC-8 grep still confirms).
  Confirmed at CLOSURE.
- **No import-linter contract change and no cap change.** The new container builders + CLI verbs
  import only already-imported lifecycle internals; the ignore-cap stays **26 = 9/4/13**; `lint-imports`
  stays `8 kept, 0 broken`.
- **Constitution unchanged; no new deprecations.** The `--model` legacy no-op is a soft-deprecation
  of a flag argument, not a constitution/roster change.

## 5. Acceptance criteria

- **AC-1 (resolver-governance per verb — snapshot artifact via the run-store; RED-first, all 7+3+1):**
  every run-a-worker verb — the **7** FR1 verbs (`release define`, `backlog define`, `implement`,
  `review qa`, `review security`, `review code`, `close`), **and** the FR2 `audit`/`research`/`bug_report`
  + the FR3 `implement-review` — run under `--harness fake` persists a `LifecycleRun.workflow_policy`
  snapshot whose per-step `harness`/`model` came from the resolver. The assertion channel is the
  **persisted `LifecycleRun.workflow_policy` in the run-store record** (`JsonLifecycleRunStore`;
  `lifecycle.py` `to_dict` l.328 / `from_dict` l.362) — the universal seam. `--show-policy` stays
  **pipeline-only** and is **not** added elsewhere; a per-verb `--json workflow_policy` is optional and
  only if declared in the write set. **RED-first, parametrized over all exact verb ids:** each asserts
  `workflow_policy is None` pre-fix and a resolver-derived snapshot post-fix.
- **AC-2 (`apply_entry_to_step` sole author + FAKE-aware + profile-ids-only + `--model` deprecation):**
  **(i)** `apply_entry_to_step` is the single per-step author over the structural `PolicyApplicableStep`
  Protocol; a **non-fake** unit test asserts the harness→kind mapping (`codex→CODEX_EXEC`,
  `pi→PI_HEADLESS`) and FAKE preservation. **(ii)** Under **`--harness fake`** (the path all AC-1/2/3
  tests use), each verb asserts: **(a)** the step's `runtime_kind` stayed **FAKE**; **(b)** the persisted
  snapshot entry's `harness`/`model_profile`/`model`/`reasoning` are **resolver-derived**; **(c)** the
  request's `resolved_model.profile_id == the resolved profile`. **The `FAKE == codex` equality is NOT
  asserted** (it would be false — the fake path preserves FAKE while the snapshot records the governed
  harness). **(iii)** A raw `--step-model label=<id>:<effort>` is **rejected** (D-3) on **every** run
  verb; a valid `--step-model label=<profile-id>` resolves. **(iv)** `--model <anything>` is **accepted**
  and emits the one-line stderr **deprecation warning** (naming `--step-model` + `workflow profiles
  list`) while the run proceeds under the resolved policy — asserted with
  `CliRunner(mix_stderr=False)`: (a) the warning text is in `result.stderr`; (b) on the
  `--model X --json` path the warning is ABSENT from stdout so the payload stays parseable
  (`json.loads(result.stdout)` succeeds); the default merged-stream runner would false-green a
  warning wrongly emitted to stdout (R-QA-1). **(v)** A `--harness fake` run of each verb
  drives the **FAKE adapter** (the injected `FakeAgentRuntime`), never a live codex/pi adapter.
- **AC-3 (FR2 invocability):** `dadaia lifecycle audit`, `research`, `bug_report` each run end-to-end
  under `--harness fake` to **COMPLETED** (exit 0 — the `bug_report` fake returns an **in-scope**
  `.dadaia/handoff/<ctx>/**` artifact_ref so its `bug_write` step does not out-of-scope-BLOCK), leave a
  resolver snapshot (AC-1), and appear as registered CLI verbs; the governed catalog reports all 7
  workflows AVAILABLE and now invocable. The `bug_report` **ADDITIVE/no-lease** property is asserted
  **structurally** — the verb routes through no MUTATING/lease-acquiring path by construction (its real
  `bug_write` target is the ADDITIVE `specs/bugs/` class); under `--harness fake` "no lease" is vacuous
  (the fake writes nothing), so it is **not** a fake-run lease observation.
- **AC-4 (FR3 loop fixes):** (a) **digest injection** — a fake runtime that records prompts shows the
  `implement#N` (N ≥ 1) prompt **contains** the `review#N-1` rejection digest; RED-first: pre-fix the
  prompt lacks it (the digest was dropped). (b) **structural runner gate** — a fake worker that returns
  no `artifact_refs` (or out-of-scope paths, or non-SUCCEEDED) makes the loop **BLOCK**; RED-first:
  pre-fix the loop passes because it read `verdict` directly. (c) **CLI caller** —
  `dadaia lifecycle implement-review` exists, drives the loop, and freezes a resolver snapshot (AC-1); an
  APPROVED review completes it, exhausted retries BLOCK it. (d) **REJECTED retries, never blocks on a
  well-formed rejection** — a round-0 review that is **structurally valid but REJECTED** (populated
  `artifact_refs`) drives `implement#1` **with the digest** and a round-1 **APPROVED → COMPLETED**; the
  loop does **not** BLOCK on the REJECTED round (only structural failure or retry exhaustion blocks).
- **AC-5 (FR4 TRANSITIONS — exact frozenset pins):** the table test pins the post-removal targets by
  **frozenset equality** (not spot-checks, so a future stray edge fails): `TRANSITIONS[QA_REVIEW] ==
  frozenset({SECURITY_REVIEW, BLOCKED})`, `TRANSITIONS[SECURITY_REVIEW] == frozenset({CODE_REVIEW,
  BLOCKED})`, `TRANSITIONS[CODE_REVIEW] == frozenset({CLOSURE, BLOCKED})`. The existing
  `test_blocked_phase_can_resume_*` (covering `BLOCKED → IMPLEMENTATION`, the retained operator rework
  path) stays green; `state_machine` behavior for the retained edges is unchanged.
- **AC-6 (full gates):** `ruff format --check`, `ruff check --no-cache`, `mypy --strict`, the full
  **unpiped** `pytest` (real exit), `lint-imports --no-cache` (`8 kept, 0 broken`; cap `== 26` +
  per-family `9/4/13` **unchanged**), `dadaia specs doctor` (exit 0), `dadaia backlog doctor` (exit 0),
  and `dadaia public doctor` (`[ok] public-privacy`, exit 0) are green locally and in CI.
- **AC-7 (mutation-sanity per new test — sabotage → FAIL → revert):** (a) break one verb's resolver
  wiring ⇒ its AC-1 snapshot assertion FAILS; (b) revert the digest-injection line ⇒ AC-4(a) FAILS;
  (c) revert the **structural runner-gate wiring** (`evaluate_gate_with_result`, `is_review=False`) ⇒
  AC-4(b) FAILS (the loop passes an ungated worker); (d) re-add one removed backtrack edge ⇒ AC-5
  frozenset-equality FAILS; (e) accept a raw `<id>:<effort>` `--step-model` ⇒ AC-2(iii) rejection test
  FAILS. Each captured on its task line, then reverted.
- **AC-8 (surviving/dead behavior ledger, per wave):** each wave records a two-column ledger on its
  task line; every move/rename/repoint grep includes `tests/` **and** non-import textual references
  (docstrings/comments). The FR4 wave's grep confirms the only `public/` mentions of `TRANSITIONS`/
  `is_legal_transition` (the two `SKILL.md` files) are **generic symbol references**, not the removed
  edges (A9) → no `public/` edit. **No** implementation-wave commit stages any `specs/backlog/**` (both
  anchors survive → archival is at CLOSURE, but the discipline holds).

## 6. Consumed bugs & backlog

| Item | Kind | Priority | Consumed → FR | Note |
|---|---|---|---|---|
| `lifecycle-verb-governance-uniformity` | backlog (candidate) | HIGH | resolver-on-every-verb → FR1; invocability wire → FR2; loop fixes → FR3; TRANSITIONS reconciliation → FR4 | Anchors `pipeline.py#LifecyclePipeline` (intent #1) + `lifecycle.py#TRANSITIONS` (intent #2) **both SURVIVE** (governance change, not deletion). |

**Archival timing — at CLOSURE (normal), not at SHIP.** Both consumed anchors survive this release:
`LifecyclePipeline` is modified (its `run_implement_review_loop` method is fixed) and `TRANSITIONS`
is edited (contents, not the symbol). No anchor-killing wave exists, so `dadaia backlog doctor`
never sees a live entry referencing a dead anchor mid-branch — the R4/R5 dead-anchor archival-at-SHIP
law does **not** apply. The consumed entry is dispositioned + archived to
`specs/_archive/v0.1.56/consumed-backlog/` with `consumed_backlog.json` at CLOSURE. (Discipline: still
no `specs/backlog/**` staged in W1-W4, per AC-8.)

**Frozen-suite check — NO interaction.** The v0.1.50 no-steal lease/gate suite is untouched: this
release lives entirely in `features/lifecycle/**`, `core/models/lifecycle.py`, `cli/commands/lifecycle.py`,
`container.py`, and lifecycle tests — it touches no `spec_context/lease`, no gate hook, no no-steal
test file. Expect **zero** frozen-file diff.

## 7. Risks

- **`apply_resolved_policy` generalization blast radius (FR1).** Making one function author
  `runtime_kind` across four step shapes could regress the pipeline path. Mitigation: the pipeline's
  existing `apply_resolved_policy` tests stay green as the invariant; add `ReleaseStep`/backlog/scope
  cases; per-verb AC-1 RED-first proves each new path.
- **CLI contract change (retire raw `--model`/`--step-model` id:effort).** Tests + operators that
  drive `release define --model gpt-5.5:medium` (or `--step-model step=<id>:<effort>`) break.
  Mitigation: `--model` degrades to a legacy no-op (not a removal); `--step-model` rejects raw
  strings with the D-3 message pointing at `workflow profiles list`; the RED-first surface is the
  existing raw-path tests, repointed to profile ids in the same wave.
- **Verb→catalog-step label mismatch (FR1 single-step).** `qa`/`security`/`code` verb labels vs
  `review_qa`/`review_security`/`review_code` catalog labels. Mitigation: an explicit map in
  `_run_phase_step`; AC-1 asserts each single-step verb leaves a snapshot for the right step.
- **Loop phase-model coherence (FR3 ↔ FR4).** If the loop were rewired to transition phases per step
  it would need the backtrack edges FR4 removes. Mitigation: FR3 gates via `evaluate_gate_with_result`
  (gate **without** transition) — the loop keeps its attempt-ledger phase model and never drives a
  review→implementation transition, so removing those edges (FR4) is coherent.
- **New-verb availability drift (FR2).** Wiring a verb without governance would re-open a raw path.
  Mitigation: the new verbs are born on the FR1 seam; AC-1 requires their snapshot.
- **Bug-report lease misfire (FR2).** A `bug_report` verb that took the MUTATING lease would violate
  the ADDITIVE contract. Mitigation: it writes only `specs/bugs/**` (ADDITIVE class); AC-3 asserts no
  lease.

## 8. Memory files affected at CLOSURE

- `specs/memory/product/sdd/dadaia-workflows.md` — **`tldr` + `summary` change** (invocability), pinned
  to **7 invocable WORKFLOWS** (A8 — not "7 verbs"): the 7 workflows (`release_definition`,
  `backlog_definition`, `implementation`, `closure`, `audit`, `research`, `bug_report`) are now all
  invocable, **surfaced by these CLI verbs**: `release define`, `backlog define`, `pipeline`, `implement`,
  `review qa|security|code`, `close`, `audit`, `research`, `bug_report`, `implement-review` (≈12 verbs on
  7 workflows; `implement-review` is a new **verb on the `implementation` workflow**, not a new
  workflow). Separate the workflow-count (7) from the verb roster in the copy. The invocability table's
  three "no verb — pending" rows flip to their CLI verbs; drop the `lifecycle-verb-governance-uniformity`-pending
  note. Because `tldr`/`summary` change, `catalog.json` + `index.md` are **regenerated**. `release_origin`
  → v0.1.56.
- `specs/memory/product/sdd/lifecycle-foundation.md` — the control-plane note generalizes: the
  resolver + per-run snapshot frozen before step 1 + `apply_resolved_policy` as the single
  `runtime_kind` author now govern **every** run-a-worker verb (not just `pipeline`); the CLI-surface
  line gains `audit`, `research`, `bug_report`, `implement-review`; the `run_implement_review_loop`
  description updates (digest injected + runner-gated + CLI-invocable); the TRANSITIONS backtrack
  removal noted. Assess `summary`/`tldr` for the "single control plane governs all verbs" refinement
  at CLOSURE (regenerate catalog only if `tldr`/`summary`/`area` changed).
- `specs/memory/architecture.md` — review the lifecycle module map + the `dadaia lifecycle` verb
  roster if enumerated; update the verb list. Feature count **unchanged (23)**. `release_origin` →
  v0.1.56 if edited.
- `specs/memory/quality-assurance.md` — **no change expected**: this release's ACs are structural
  assertions on the snapshot artifact + captured prompts via the fake runtime, **not** byte-goldens,
  so the golden-authoring law is not triggered. Confirm at CLOSURE (if any implementer introduces a
  new byte-golden, the R7 golden-authoring law + `-cross` proof apply).
- `specs/memory/tech-stack.md` — **no change** (no dependency added; no harness/model roster change).
  Confirmed at CLOSURE.

## 9. Definition-review rulings (dual REJECT×2 folded — binding)

Software-architect REJECT + qa-engineer REJECT, strongly convergent; diagnosis + both decisions
ratified; amendments A1-A6 (architect) + A1-A9 (qa) folded via coordinator rulings R-1..R-6. QA
re-verifies this Draft before `Aprovado`.

- **Decision A — FR2 invocability: WIRE — RATIFIED (conditioned on A1/R-4 + A4/R-5).** `audit`/
  `research`/`bug_report` have **real**, complete, AVAILABLE (`governed_catalog.py` l.683-685),
  resolver-resolvable, panel-rendered bodies; demoting deletes tested code and regresses the product.
  The wire requires the three-part workflow-body seam edit (FR2) + the in-scope bug_report fake — not
  builder+verb only.

- **Decision B — FR4 TRANSITIONS: REMOVE — RATIFIED.** The three review→IMPLEMENTATION edges are
  **provably dead** (only consumer of `is_legal_transition` is `state_machine.py` l.49; the pipeline
  blocks a REJECTED review to BLOCKED, never review→IMPLEMENTATION; no positive test asserts them;
  `BLOCKED → IMPLEMENTATION` resume survives; FR3's rework is the attempt ledger, not a phase
  backtrack). REMOVE makes the table honest.

- **Ruling — `--model` = non-fatal deprecation warning (NEITHER silent no-op NOR hard error).** Accept
  the flag, emit a one-line stderr warning naming `--step-model <profile-id>` + `workflow profiles
  list`, and proceed with the resolved policy (folded into FR1 + AC-2(iv)). A silent no-op is a hidden
  side-effect (anti-slop defect class); a hard error breaks every script/test still passing `--model`
  mid-mandate. A CLOSURE **backlog return** tracks hard-removing `--model` across all run verbs once
  callers migrate. Optionally (this release, for coherence) the pipeline's own silent `_ = model`
  l.1094 adopts the same warning.
