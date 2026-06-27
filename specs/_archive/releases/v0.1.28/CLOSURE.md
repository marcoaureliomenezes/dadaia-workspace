# Closure: Release — v0.1.28 — Workflow Model Governance + Panel Control Plane

> **Status:** Aprovado
> **Release ID:** v0.1.28
> **Owner:** product-engineer
> **Closed:** 2026-06-26

## Summary

v0.1.28 turns dadaia-workflows from a powerful-but-opaque execution surface into a
**governed, inspectable, reproducible control plane**. Before this release the Layer-2
model choice was a raw `<id>:<effort>` string picked ad hoc on the CLI: there was no
named profile registry, no operator-editable policy, no per-run proof of which model each
step used, and the panel could only read workflow docs. After this release an operator can
see, change, audit, and reproduce which model runs each prompt — without ever reading
Python source.

The release ships the whole epic as four independently-tested waves (D-1). **Wave A** adds
the governance foundation: a named built-in **model-profile registry**
(`features/lifecycle/model_profiles.py` — 5 profiles: 2 Codex + 3 recommended PI aliases)
layered over the existing discrete `core/harness_models.py` catalog (never a second model
table — an import-time assert ties every profile back to the registry), an atomic JSON
**overlay store** (`.dadaia/states/workflow_model_policy.json`, missing ≠ invalid,
`.last-good.json` backup), and a single shared **`WorkflowExecutionPolicyResolver`** with
the precedence CLI > context overlay > default overlay > library default (only the
`default` context honored this release). Each lifecycle run now persists a
`workflow_policy` snapshot resolved once before step 1, so an in-flight run ignores later
panel edits and historical run inspection sees the model actually used. **Wave B** makes
the Python `dadaia_catalog` the single governed source of workflow truth, demoting the old
`*.workflow.md` files to reference-only. **Wave C** promotes Workflows to a first-class
panel area with a guarded policy editor (per-step profile dropdown filtered by harness,
reset-to-default, validate-before-save) over new GET/PUT/validate mutation routes under the
existing loopback + Host-header guard. **Wave D** adds a read-only fragment inspector and
governance doctor coverage (`WMP-*` invariants + a `public doctor` workflow-policy residue
scan).

The Layer-2 harness law is now enforced at three points: the CLI rejects `claude`/
`opencode` as workflow workers, `--step-model` accepts profile ids only (raw strings,
unknown ids, harness mismatches, and deprecated profiles are rejected with actionable
messages), and the `WMP-LAYER2-RESIDUE` doctor check fails on any `claude`/`opencode`
residue in a product policy or profile. `fake` remains test-only.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-28-A-01 | Resolved-policy core DTOs (`ResolvedModelConfig`, `WorkflowModelProfile`, `WorkflowPolicySnapshot`) | `feature/v0.1.28` |
| T-28-A-02 | Built-in model-profile registry (2 Codex + 3 PI; import-time no-second-table assert) | `feature/v0.1.28` |
| T-28-A-03 | Atomic overlay JSON store + `.last-good.json`; missing ≠ invalid; `default` context only | `feature/v0.1.28` |
| T-28-A-04 | `WorkflowExecutionPolicyResolver` with full precedence + override validation | `feature/v0.1.28` |
| T-28-A-05 | `AgentRunRequest.resolved_model` + `LifecycleRun.workflow_policy` (additive, back-compat read) | `feature/v0.1.28` |
| T-28-A-06 | Codex/PI/fake adapters consume the per-request resolved model (AC-12) | `feature/v0.1.28` |
| T-28-A-07 | Pipeline + phase workflow + prompt builder resolve+snapshot before step 1 (LAW 7) | `feature/v0.1.28` |
| T-28-A-08 | Container wiring for the governance layer (registry/store/resolver) | `feature/v0.1.28` |
| T-28-A-09 | CLI profile-id `--step-model`, `--show-policy`, `workflow policy show` / `profiles list` | `feature/v0.1.28` |
| T-28-A-10 | Wave A green checkpoint — D-4 implementation-pipeline e2e demo | `feature/v0.1.28` |
| T-28-B-01 | Catalog carries default harness + default profile per step (governed source) | `feature/v0.1.28` |
| T-28-B-02 | Demote `*.workflow.md` to reference/doc-only (AC-15) | `feature/v0.1.28` |
| T-28-B-03 | Wave B green checkpoint | `feature/v0.1.28` |
| T-28-C-01 | Panel GET routes: catalog, profiles, policy, runs | `feature/v0.1.28` |
| T-28-C-02 | Panel mutation routes: PUT/validate policy (415/413/400, atomic, last-good) | `feature/v0.1.28` |
| T-28-C-03 | First-class Workflows nav + detail/step-matrix/policy editor | `feature/v0.1.28` |
| T-28-C-04 | Wave C green checkpoint — panel E2E | `feature/v0.1.28` |
| T-28-D-01 | Read-only fragment inspector per step (AC-14) | `feature/v0.1.28` |
| T-28-D-02 | Governance doctor checks (`WMP-*` + public-doctor residue) (AC-10) | `feature/v0.1.28` |
| T-28-D-03 | Wave D green checkpoint — all SPEC §6 acceptance satisfied | `feature/v0.1.28` |

> Per-task commit SHAs are on branch `feature/v0.1.28`. The review trio below is keyed to
> the rc-ship HEAD `28379a71729befa34bd4350a235a2a999f30598f`; the coordinator records the
> exact final pushed SHA at ship time per the release-governance rc cadence.

## Validations

Each validation is a triple: description, command, evidence.

| Description | Command | Evidence |
|-------------|---------|----------|
| Ruff format clean | `ruff format --check` | `pass (676 files)` (qa-impl handoff `metrics.ruff_format`) |
| Ruff lint clean | `ruff check --no-cache` | `pass` (qa-impl `metrics.ruff_check`) |
| Mypy strict clean | `mypy --strict` | `pass (278 source files)` (qa-impl `metrics.mypy_strict`) |
| Full test suite green | `pytest -p no:cacheprovider` | `3777 passed, 14 skipped, 0 failed` (464s); the 14 skips are opt-in live-credit, Windows-only file-lock/permission, and a no-LAN-IPv4 skip — all expected (qa-impl `metrics.pytest_*`) |
| Panel policy-editor E2E | `playwright test workflow-policy-editor.spec.ts` | `5/5 passed` headless — dropdown-filter / edit-diff / reset / validate-banner / save-persists-via-PUT (qa-impl `metrics.playwright_policy_editor_passed`) |
| Workflows-tab E2E | `playwright test workflows-tab.spec.ts` | `7/7 passed` headless — first-class Workflows nav (qa-impl `metrics.playwright_workflows_tab_passed`) |
| Governance doctor on live tree | `dadaia lifecycle workflow doctor` | `0 ERROR findings` against the live workspace tree (qa-impl `metrics.governance_doctor_errors_live_tree`) |
| Public projection clean | `dadaia public doctor` | exit 0 with `[ok] public-privacy`; overlay schema staged + installed to all targets (ACTIVE.md) |
| AC-6 in-flight isolation | `pytest tests/integration/cli/test_pipeline_policy_e2e.py::test_pipeline_ac6_in_flight_ignores_later_overlay_edit` | PASS — overlay mutated between step 1 and step 2; step 2 uses the pre-mutation snapshot; a fresh resolve sees the mutation (proves only the in-flight run is shielded) (qa-impl finding) |
| AC-7 persisted-snapshot read | (qa review) | PASS — runs view takes only the run store, no resolver; structurally cannot re-resolve (qa-impl finding) |
| Invalid-vs-missing distinction | (qa review) | PASS — invalid blocks BEFORE any model call (FakeAgentRuntime recorded ZERO calls AND `.last-good.json` byte-unchanged); missing resolves to library default (qa-impl finding) |
| QA rc-ship verdict | (review) | **APPROVED** — `.dadaia/handoff/dadaia-workspace/2026-06-26T214500Z-qa-engineer-v0128-impl-review.handoff.json` (0 CRITICAL/HIGH/MEDIUM; 1 LOW, 2 INFO) |
| Code-review rc-ship verdict | (review) | **APPROVED** (APPROVE-WITH-NITS) — `.dadaia/handoff/dadaia-workspace/2026-06-26T234403Z-code-reviewer-v0128.handoff.json` (0 CRITICAL/HIGH; 1 MEDIUM → v0.1.29 follow-up; 3 LOW, 2 INFO; 92/92 targeted tests) |
| Security rc-ship verdict | (review) | **APPROVED** — `.dadaia/handoff/dadaia-workspace/2026-06-26T000000Z-security-reviewer-v0128.handoff.json` (`metrics.commit_sha = 28379a71…`; 0 CRITICAL/HIGH/MEDIUM/LOW; 4 INFO; 103 security tests; 0 secrets) |

### Acceptance criteria → result

All AC-1..AC-16 (SPEC §6) have concrete, non-slop backing tests (qa-impl handoff). Highlights:
AC-1/AC-3 reject `claude`/`opencode` and raw/unknown/mismatched/deprecated profiles with
actionable CLI errors; AC-6 proves LAW-7 mid-run safety at the strongest seam; AC-7 reads
the persisted snapshot verbatim; AC-10 governance doctor (`WMP-1..WMP-8` + public-surface
residue scan) errors on each broken fixture and reports 0 ERROR on the live tree; AC-12
asserts the resolved model reaches `pi --model <id>` and `codex -m <id> -c
model_reasoning_effort=<effort>` at the adapter argv seam.

## Drifts

Implementation followed PLAN.md and SPEC.md across all four waves; no plan was bent. The
two items below are **not** plan deviations — one is a reviewer-flagged auditability nit
deferred to v0.1.29, and the other restates the D-2 scope boundaries the SPEC already
declared. They are recorded here to make the follow-up surface explicit.

### snapshot-harness-vs-adapter-divergence-under-harness-override

**Description:** code-reviewer MEDIUM. `apply_resolved_policy` (pipeline.py) threads the
governed snapshot's `harness`/`model` into `step.resolved_model` but deliberately leaves
`step.runtime_kind` as the CLI `--harness`/`--step-harness` choice. The only Wave-A
governed worker workflow (`implementation`) hardcodes every step to a **codex** profile, so
`dadaia lifecycle pipeline --harness pi` builds the PI adapter while the persisted snapshot
records `harness=codex` — a mild AC-7 auditability divergence (the snapshot's harness field
can mislead historical run inspection, even though PI does run the resolved model id).

**Resolution:** Not a ship-blocker — the divergence is explicitly acknowledged in the
pipeline docstring, bounded by the codex-defaulted Wave-A catalog, and the panel governance
editor enforces harness-matched profiles. **Deferred to v0.1.29**: either reconcile
`step.runtime_kind` with the resolved profile's harness, or record the actual adapter
`runtime_kind` alongside the governed harness so the snapshot distinguishes "governed
harness" from "adapter that ran". Carried into the follow-up backlog entry below.

**Memory updates:** none — current product truth is that the snapshot records the *governed*
harness/model resolved by policy, and the memory describes exactly that. The fidelity
refinement is a future-release behavior, not current truth.

### d-2-deferrals-operator-pi-profiles-and-per-context-overlays

**Description:** SPEC §7 declared two scope deferrals confirmed by the grill (D-2):
**operator-added PI profiles** (`.dadaia/states/workflow_model_profiles.local.json`) are
NOT loaded/validated this release (built-in recommended profiles only), and **per-context
overlays + `extends` inheritance** are NOT honored (the overlay schema may reserve the
`contexts{}` shape, but only the `default` context is honored/validated — a non-`default`
context key is inert, never silently treated as active).

**Resolution:** Intentional scope boundaries per the grill, not deviations. The built-in
profiles cover every governed step's default for both supported harnesses, so the release
is fully runnable. **Deferred** to the follow-up backlog entry below for a future release.

**Memory updates:** memory describes the current truth (built-in profiles only,
`default`-context overlay only); no changelog of the deferral is written into memory.

## Memory updates

Memory files written during this CLOSURE phase to reflect current product truth (the
workflow control plane as it now is — no changelog):

- `specs/memory/product/sdd/lifecycle-foundation.md` — added the **workflow model
  governance** layer to current truth: the named `WorkflowModelProfile` registry over
  `core/harness_models.py` (5 built-in profiles, import-time no-second-table assert), the
  atomic `JsonWorkflowModelPolicyStore` overlay (missing ≠ invalid, `.last-good.json`), the
  single shared `WorkflowExecutionPolicyResolver` (precedence CLI > context overlay >
  default overlay > library default; `default` context only), the per-run `workflow_policy`
  snapshot resolved-once-before-step-1, the profile-id `--step-model` + inspection verbs,
  the governed `dadaia_catalog` (Markdown demoted to reference-only), and the
  `dadaia lifecycle workflow doctor` `WMP-*` checks. Bumped `last_updated` + `release_origin`.
- `specs/memory/product/panel/panel.md` — added the **Workflows control plane** to the
  panel's current truth: Workflows promoted to a first-class nav area (Agents/Kanban
  retained), the workflow detail step matrix + default-vs-effective diff + run-snapshot
  evidence, the guarded policy editor, the new GET (catalog/profiles/policy/runs) and
  mutation (PUT/validate) routes with their 415/413/400 → atomic-write + last-good guard
  posture, and the read-only fragment inspector. Bumped `last_updated`.
- `specs/memory/architecture.md` — added a **Workflow control plane subsystem** section
  (profile registry → overlay store → resolver → run snapshot → panel routes, the resolver
  as the single policy seam shared by CLI and panel) and runtime-state entries for
  `.dadaia/states/workflow_model_policy.json` + `.last-good.json` + the
  `workflow-model-policy-v1` schema; noted the governed `dadaia_catalog` and the
  `WMP-*` / public-doctor residue checks. Bumped `last_updated` + `release_origin`.
- `specs/memory/tech-stack.md` — no change: this release added no dependency and changed no
  approved technology. The overlay store, resolver, panel routes, and doctor checks are all
  stdlib-only Python over the existing seams; no new runtime dependency.
- `specs/memory/product/index.md` + `catalog.json` — no catalog change: the control plane
  is captured by extending the existing `lifecycle-foundation` and `panel` atoms (it is a
  governance layer over the lifecycle engine, not a new standalone product feature). No
  feature atom added or removed; daily-relevance order unchanged.

## Dispositions

Disposition-sweep ledger. v0.1.28 consumes one backlog item (declared via the SPEC
`**Consumes:**` line); no bugs were picked into this release.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/workflow-model-governance-panel-control-plane.md` | backlog | `status: delivered` + `delivered_in: v0.1.28` | this CLOSURE `## Summary` + `## Validations`; qa/code/security APPROVED handoffs |

**Note on the mechanical removal.** As with v0.1.27, the v0.1.28 lifecycle was run **via
agents** (PM dispatch + sub-agent authoring), not via the `dadaia lifecycle release define`
CLI verb, so no live `consumed_backlog.json` ledger was written for v0.1.28's own archive —
this is expected, not a gap. The consumed backlog item file is gitignored in this source
repo (privacy backstop), so the frontmatter disposition above (`status: delivered` +
`delivered_in: v0.1.28`) is the live-SET removal equivalent and the authoritative record of
consumption. The terminal status uses the BL-SCHEMA-valid form (`status: delivered` +
`delivered_in: v0.1.28`) — NOT a free-text `DELIVERED — v0.1.28` status line, which
BL-SCHEMA rejects (see bug
`backlog-doctor-bl-schema-vs-spec-doc-031-terminal-status-format-conflict`).

## Backlog returns

One follow-up candidate is filed for the deferred breadth and the reviewer MEDIUM, to be
picked into a future release per SPEC §7:

- `backlog/candidates.md` ← **`workflow-model-governance-operator-profiles-and-context-overlays`**
  (new candidate). Covers: (1) operator-added PI profiles via
  `.dadaia/states/workflow_model_profiles.local.json` (D-2 deferral); (2) per-context
  overlays + `extends` inheritance, honoring non-`default` context keys (D-2 deferral); and
  (3) the code-reviewer MEDIUM — reconcile snapshot `harness`/`runtime_kind` so run-history
  inspection distinguishes the governed harness from the adapter that actually ran under a
  `--harness` override.

> The candidate write is a backlog mutation; per the `backlog-ownership` rule, the
> coordinator (`project-manager`) curates the actual `candidates.md` entry. This CLOSURE
> records the required follow-up; PM files it.

## Archive decision

**MOVE** — the release directory will be moved to
`specs/_archive/releases/v0.1.28/` via `git mv` (run by the coordinator;
product-engineer has no Bash). `specs/releases/ACTIVE.md` is then updated to `release: none`
with a pointer to the archived release and the next planned work.
</content>
</invoke>
