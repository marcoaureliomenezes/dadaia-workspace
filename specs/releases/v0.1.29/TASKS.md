# TASKS — Release: v0.1.29 — Harness as a governed dimension + catalog completion

**Status:** Aprovado
**Release ID:** v0.1.29
**Owner:** product-engineer (authoring) → software-engineer (implementation)

> Markers: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. One `[-]` per owner at a time
> unless a task declares a disjoint write set. Each wave ends on a green checkpoint
> (`ruff format --check && ruff check && mypy --strict && pytest`). Reserve a task with a
> `chore(tasks): start <id>` commit before editing.

---

## Wave A — Resolver + overlay + CLI harness governance (D-1, D-2, D-3 store/schema)

### [x] T-29-A-01 — Add per-harness default profiles to the resolver CatalogStep
**Goal:** `CatalogStep` carries `default_profiles: dict[str, str]` so the resolver can
auto-select a profile per effective harness.
**Write set:** `dadaia_workspace/features/lifecycle/policy_resolver.py`,
`dadaia_workspace/features/workflows/dadaia_catalog.py` (`_governed_step` populates it).
**Acceptance:** `_governed_step` sets `default_profiles` from the DTO; back-compat default
`{}`; existing tests still green. (AC-2 groundwork.)

### [ ] T-29-A-02 — Resolver: effective-harness precedence
**Goal:** `resolve()` accepts a default-harness override + a `{step -> harness}` map and an
overlay harness; `_resolve_harness` computes the effective harness with precedence
`CLI step > CLI default > overlay step > overlay default_harness > catalog default`.
**Write set:** `dadaia_workspace/features/lifecycle/policy_resolver.py`.
**Acceptance:** AC-1 precedence table test passes; default path (no overrides) unchanged.

### [ ] T-29-A-03 — Resolver: auto-profile-on-harness-override + match effective harness
**Goal:** when a step's harness is overridden with no explicit profile, the library default
becomes `default_profiles[effective_harness]`; `_validate_profile` compares against the
**effective** harness (fixes `policy_resolver.py:288`).
**Write set:** `dadaia_workspace/features/lifecycle/policy_resolver.py`.
**Acceptance:** AC-2 (PI default auto-selected, PI profile accepted on PI-resolved step);
AC-9 (claude/opencode rejected); AC-10 (default path byte-identical).

### [-] T-29-A-04 — Overlay store: harness fields + accessors
**Goal:** `WorkflowModelPolicyOverlay` carries optional per-workflow `default_harness` and
per-step `harnesses`; add `step_harness` + `workflow_default_harness` accessors (default
context only); `_parse_workflow` accepts the new optional fields; `to_dict` round-trips.
**Write set:** `dadaia_workspace/infrastructure/json_workflow_model_policy_store.py`.
**Acceptance:** AC-10 (a v0.1.28 profile-only overlay parses unchanged); round-trip test
for a harness-carrying overlay.

### [ ] T-29-A-05 — Overlay schema: optional harness fields
**Goal:** add optional `default_harness` (enum codex|pi) and `harnesses` (object → enum
codex|pi) under `workflowOverlay`; keep `additionalProperties:false`.
**Write set:** `dadaia_workspace/public/schemas/workflow-model-policy-v1.schema.json`.
**Acceptance:** old overlay validates; harness overlay validates; non-codex/pi value
rejected. (AC-6, AC-9.) Projection deferred to Wave D checkpoint.

### [ ] T-29-A-06 — pipeline.apply_resolved_policy sets runtime_kind from resolved harness
**Goal:** `apply_resolved_policy` maps each entry's resolved harness → `AgentRuntimeKind`
and sets `PipelineStep.runtime_kind`; unmappable harness raises actionable error.
**Write set:** `dadaia_workspace/features/lifecycle/pipeline.py`.
**Acceptance:** AC-3 (runtime_kind == kind of resolved harness for every step).

### [ ] T-29-A-07 — CLI pipeline verb threads harness into resolve; removes post-resolve swap
**Goal:** `pipeline` passes `--harness`/`--step-harness` into `resolver.resolve(...)`;
removes the separate `replace(step, runtime_kind=...)` swap; `--harness fake` still runs
the fake adapter while the snapshot resolves the governed harness; `--show-policy` reflects
harness.
**Write set:** `dadaia_workspace/cli/commands/lifecycle.py` (`pipeline` verb only).
**Acceptance:** AC-4 wiring; `--show-policy` shows pi when `--harness pi`; `fake` dry-run
still completes.

### [ ] T-29-A-08 — Wave A green checkpoint
**Goal:** `ruff format --check && ruff check && mypy --strict && pytest` all pass.
**Write set:** (none — fixes only if red.)
**Acceptance:** full suite green; AC-1/AC-2/AC-3/AC-9/AC-10 unit tests added and passing.

---

## Wave B — Catalog completion to 7 workflows (D-4)

### [ ] T-29-B-01 — Catalog: add closure as its real single worker step
**Goal:** `_closure_steps()` returns the real `close` worker step (role product-engineer,
generic/no-fragment) + a `closure_removal_gate` Python gate step; register `closure` in
`_all_workflows()` (availability PARTIAL), purpose, display name; `_governed_step` projects
the `close` step onto the resolver seam; `_assert_catalog_defaults_resolve` covers it.
**Write set:** `dadaia_workspace/features/workflows/dadaia_catalog.py`.
**Acceptance:** `governed_workflow_catalog()` includes `closure` with a `close` step;
`resolve("closure")` resolves a policy for `close`; WMP-5 does not flag the generic step.

### [ ] T-29-B-02 — Catalog: confirm audit/research/bug_report enumerated as deferred
**Goal:** verify the 3 deferred workflows appear in `list_dadaia_workflows()` with
`availability=deferred` and zero governed steps; assert `governed_workflow_catalog()`
omits them from the resolver seam and `resolve(<deferred>)` raises the actionable
"no governed steps / unknown workflow" message.
**Write set:** `dadaia_workspace/features/workflows/dadaia_catalog.py` (tests; code likely
unchanged).
**Acceptance:** AC-7 (all 7 enumerated; deferred resolve raises actionable error).

### [ ] T-29-B-03 — CLI `policy show` + container reach completed catalog
**Goal:** confirm `dadaia lifecycle workflow policy show closure` resolves and the resolver
factory/container sees the closure step; no second catalog source introduced.
**Write set:** `dadaia_workspace/cli/commands/lifecycle.py` (only if a help/list string
needs closure), `dadaia_workspace/container.py` (verify).
**Acceptance:** AC-7 (`policy show closure` prints the `close` step).

### [ ] T-29-B-04 — Wave B green checkpoint
**Goal:** full suite green; catalog-completion tests passing.
**Write set:** (none — fixes only if red.)
**Acceptance:** AC-7 satisfied; `ruff/mypy/pytest` green.

---

## Wave C — Panel toggle persistence + E2E (D-3 panel, D-5 proof)

### [ ] T-29-C-01 — Panel view: harness flag in catalog diff + harness-carrying overlay
**Goal:** `_effective_steps` adds `harness_overridden` + `default_harness` per row; confirm
PUT/validate accepts a harness-only overlay (resolvable via auto-profile).
**Write set:** `dadaia_workspace/features/panel/views/workflow_policy.py`.
**Acceptance:** AC-6 (catalog row shows pi harness + flag); a harness-only PUT returns 200.

### [ ] T-29-C-02 — Panel JS: codex/pi toggle persists harness
**Goal:** the segmented toggle writes the step `harness` into the PUT body and renders the
harness-overridden flag in the diff. Re-stage/install the projected asset at the Wave D
checkpoint.
**Write set:** `dadaia_workspace/features/panel/views/assets/js/workflow_policy.js`.
**Acceptance:** AC-6 (panel E2E: toggle → PUT → GET round-trips harness; catalog diff
reflects it).

### [ ] T-29-C-03 — E2E: CLI `--harness pi` proof via FakeAgentRuntime
**Goal:** an `implementation` pipeline run with `--harness pi` against `FakeAgentRuntime`
asserts every `received_models[i].harness == "pi"`, `.model` is a PI catalog model, and
the persisted run snapshot records `harness=pi` per step.
**Write set:** test module under `tests/` (e.g.
`tests/features/lifecycle/test_pipeline_harness_governance.py`).
**Acceptance:** AC-4 passes.

### [ ] T-29-C-04 — E2E: overlay `default_harness: pi` proof (no CLI flag)
**Goal:** same three assertions as AC-4 with the harness from a persisted overlay only.
**Write set:** same/adjacent test module.
**Acceptance:** AC-5 passes.

### [ ] T-29-C-05 — Wave C green checkpoint
**Goal:** full suite + panel E2E green.
**Write set:** (none — fixes only if red.)
**Acceptance:** AC-4/AC-5/AC-6 satisfied; `ruff/mypy/pytest` green.

---

## Wave D — Doctor + final checkpoint (D-doctor, AC-8, AC-11)

### [ ] T-29-D-01 — Doctor: validate the harness dimension
**Goal:** `policy_doctor` flags an overlay harness referencing an unsupported harness on a
step (WMP-PROFILE/WMP-OVERLAY) and a forbidden Layer-2 harness (WMP-LAYER2-RESIDUE);
confirm WMP-1..WMP-7 pass over the completed catalog (closure added).
**Write set:** `dadaia_workspace/features/lifecycle/policy_doctor.py`.
**Acceptance:** AC-8 (zero ERROR over good catalog; deliberate-bad overlay yields the
specified findings).

### [ ] T-29-D-02 — Projection + full-suite final checkpoint
**Goal:** project the schema asset and run the full gate.
**Write set:** (no source — runs `dadaia public stage && dadaia public install --target all
&& dadaia public doctor`; surfaces to operator/devops since PE has no Bash). Then
`ruff format --check && ruff check && mypy --strict && pytest`.
**Acceptance:** AC-11 — full suite green; `dadaia public doctor` exit 0 with
`[ok] public-privacy`; schema projection consistent.

### [ ] T-29-D-03 — Re-assert carried-forward laws (§3.7)
**Goal:** confirm default-first (AC-10), auditability snapshot (run reads snapshot
verbatim), invalid-blocks-execution, resolve-once-before-step-1, Layer-2 codex|pi only
(AC-9) all still hold after the changes.
**Write set:** tests only (assertions across the changed seams).
**Acceptance:** all §3.7 invariants covered by green tests.

---

## Task count

- Wave A: 8 tasks (T-29-A-01..08)
- Wave B: 4 tasks (T-29-B-01..04)
- Wave C: 5 tasks (T-29-C-01..05)
- Wave D: 3 tasks (T-29-D-01..03)
- **Total: 20 tasks**, 4 waves, 4 green checkpoints.
