# Closure: Release — v0.1.30 — super release: PI/Codex Layer-2 + workflow system maturation

> **Status:** Aprovado
> **Release ID:** v0.1.30
> **Owner:** product-engineer
> **Closed:** 2026-06-27

## Summary

v0.1.30 finishes the two-layer architecture's Layer-2 worker stack (PI + Codex) and matures
the dadaia-workflow system into a first-class, consistent surface. Six correlated residuals
that had left the worker stack and the workflow engine inconsistent across v0.1.16–v0.1.29
are now closed: the three real headless adapters share one base (no more copy-pasted
security invariants); Codex's by-name rule-law corpus is demonstrably reachable and its
interactive-vs-headless trust boundary is surfaced honestly; PI appears in the telemetry
panel as the fourth harness; workflow model-governance gained operator-registered PI
profiles and per-context overlay inheritance; workflow steps now communicate over a
run-scoped producer→consumer ledger instead of stale prose / "latest handoff by agent"
filename scans; and the `audit` / `research` / `bug_report` workflows are now real
fragment+gate bodies (no more fail-loud stubs) with the AI surface dehydrated of lifecycle
ritual.

From the product owner's perspective: PI and Codex are now peers to Claude as governed
Layer-2 workers, the operator can govern workflow model selection per-harness and
per-context, the workflow engine carries its own auditable handoff data plane between
steps, and three more lifecycle workflows (audit, research, bug-report) are runnable on the
same fragment+gate engine that already powers release-definition and backlog-definition.

The release was implemented as five dependency-ordered waves (A→E) on `feature/v0.1.30`,
each green-checkpointed and reviewed before the next began. All 30 implementation tasks are
`[x]`; every wave's review ladder returned APPROVE. This CLOSURE was authored CLOSURE-ONLY
per the operator's decision — no push, no PR, no `git mv` to `_archive` (the coordinator
performs the archive/ledger/repoint mechanics after this document, the memory atoms, and the
disposition sweep are written).

## Tasks completed

All 30 tasks are `[x]` in `specs/releases/v0.1.30/TASKS.md`, grouped by wave. Per-task
commit SHAs live in `git log main..feature/v0.1.30` (the coordinator running git fills exact
SHAs at archive; product-engineer has no Bash). The committed per-wave evidence is the
software-engineer handoffs under `.dadaia/handoff/dadaia-workspace/` (one per wave), cited in
the `Evidence` column.

| Task ID | Description | Final commit (wave handoff evidence) |
|---------|-------------|--------------------------------------|
| T-30-A-01 | Author shared headless-adapter base (`infrastructure/headless_adapter_base.py`) | Wave A — `2026-06-27T055826Z-software-engineer-T-30-A-wave-a.handoff.json` |
| T-30-A-02 | Refactor `pi_runtime` onto the base | Wave A — same handoff |
| T-30-A-03 | Refactor `codex_runtime` onto the base | Wave A — same handoff |
| T-30-A-04 | Refactor `claude_sdk_runtime` (redaction + git seam only) | Wave A — same handoff |
| T-30-A-05 | Divergence test + base unit coverage | Wave A — same handoff |
| T-30-B-01 | WS-CDX-PROTOCOL: rule-law corpus reachable from Codex (AGENTS.md surface + `codex_doctor` check) | Wave B — `2026-06-27T000000Z-software-engineer-wave-b.handoff.json` |
| T-30-B-02 | WS-CDX-HYGIENE: trust-boundary INFO + keep/drop + inert-key removal | Wave B — same handoff |
| T-30-B-03 | WS-PI-6: PI telemetry reader (`reader/pi.py`) | Wave B — same handoff |
| T-30-B-04 | WS-PI-6: `PiRuntimeAdapter` + `ADAPTER_REGISTRY["pi"]` + panel A12 wiring | Wave B — same handoff |
| T-30-B-05 | PI fourth-harness academy module | Wave B — same handoff |
| T-30-C-01 | WS-PROFILES: local PI-profile store + port | Wave C — `2026-06-27T120000Z-code-reviewer-v0130-wave-c.handoff.json` (review) |
| T-30-C-02 | WS-PROFILES: merge operator profiles into `model_profiles` | Wave C — same review |
| T-30-C-03 | WS-OVERLAYS: `extends` inheritance in the overlay store | Wave C — same review |
| T-30-C-04 | WS-OVERLAYS: resolver chain resolution | Wave C — same review |
| T-30-C-05 | WS-NITS: de-dup `_DEFAULT_PROFILE_BY_HARNESS_PURPOSE` + docstring + panel 3-map union | Wave C — same review |
| T-30-D-01 | Workflow-handoff models + additive `LifecycleRun.workflow_steps` | Wave D — `2026-06-27T140000Z-software-engineer-wave-d-workflow-handoff-data-plane.handoff.json` |
| T-30-D-02 | Payload + run-steps JSON schemas; `output-handoff.md` `detail`→`detail_md` fix | Wave D — same handoff |
| T-30-D-03 | Workflow-handoff resolver/service (`workflow_handoffs.py`) | Wave D — same handoff |
| T-30-D-04 | Persist step payloads under `.dadaia/runs/lifecycle/<run>/steps/` + run-store extension | Wave D — same handoff |
| T-30-D-05 | Wire release-definition produces/consumes + terminal graph-completeness gate | Wave D — same handoff |
| T-30-D-06 | Implementation/review loop attempt tracking + bounded retry (default 2 → BLOCK) | Wave D — same handoff |
| T-30-D-07 | Retention + hygiene for step payloads | Wave D — same handoff |
| T-30-D-08 | `dadaia lifecycle handoffs doctor` + minimal panel run-ledger API | Wave D — same handoff |
| T-30-E-01 | Real `audit` workflow body (fragment+gate, consumes Wave-D ledger) | Wave E — `2026-06-27T140000Z-software-engineer-T-30-E-wave.handoff.json` |
| T-30-E-02 | Real `research` workflow body | Wave E — same handoff |
| T-30-E-03 | Real `bug_report` workflow body (ADDITIVE-safe) | Wave E — same handoff |
| T-30-E-04 | Remove the three from `DEFERRED_WORKFLOWS` | Wave E — same handoff |
| T-30-E-05 | WS-C ctx-inject dehydration | Wave E — same handoff |
| T-30-E-06 | Record OQ decisions (OQ-3/4/6/7) | Wave E — same handoff; `specs/releases/v0.1.30/OQ-DECISIONS.md` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full pytest suite green | `pytest` | 4047 passed / 14 skipped (ACTIVE.md status 2026-06-27; per-wave handoffs) |
| Strict type-check clean | `mypy --strict dadaia_workspace` | clean, 288 files |
| Lint + format green | `ruff format --check` + `ruff check` | green (CI preflight 4/4 per Wave-A handoff) |
| Public asset projection consistent | `dadaia public doctor` | exit 0 — `[ok] public-privacy`, `[ok] ai-surface` (no reintroduced lifecycle ritual), `[ok] codex:rule-corpus-reachable` |
| SDD structural invariants | `dadaia specs doctor --specs-dir specs` | 0 errors (pre-existing ADR-11 status-hygiene WARNINGs only — see Wave-E qa handoff) |
| Panel end-to-end (A12 PI surface + handler routes) | panel Playwright e2e (local; `e2e-panel` GH job not run by `ci preflight`) | 69/69 green locally (ACTIVE.md status) |
| Wave A — pure de-dup, byte-preserved | divergence test + 3 adapter suites unchanged | `2026-06-27T055826Z-software-engineer-T-30-A-wave-a.handoff.json` (45→45 adapter passes; divergence test proven twice) |
| Wave D — exact (run,step,attempt) ledger consumption | A18–A27 acceptance | `2026-06-27T143000Z-qa-engineer-wave-d-acceptance.handoff.json` (APPROVE) |
| Wave E — falsifiable fragment+gate bodies + dehydration | A28–A32 acceptance | `2026-06-27T130500Z-qa-engineer-wave-e-acceptance.handoff.json` (40/40, APPROVE) |
| Per-wave security verdicts | security-reviewer per wave (A,B,C,D,E) | APPROVE handoffs under `.dadaia/handoff/dadaia-workspace/` |
| Per-wave code reviews | code-reviewer per wave (A,B,C,D,E) | APPROVE handoffs under `.dadaia/handoff/dadaia-workspace/` |

## Drifts

### a12-panel-wiring-outside-declared-write-set

**Description:** The Wave-B software-engineer handoff flagged (MEDIUM) that for PI sessions
to actually appear in the panel Agents/Sessions tab, `features/telemetry/service.py` had to
call `read_pi_sessions` and the panel needed a `pi` runtime button — both outside the
literal declared write sets of T-30-B-03/T-30-B-04 (which named `reader/pi.py` and
`runtimes.py` only).

**Resolution:** A12 is conditional ("when a real local source exists"). The wiring was
completed within Wave B (service.py reader call + panel `pi` runtime button + handler route
changes), and the substantive review findings (A12 panel wiring + CSP hash + PI styling)
were fixed inline during the Wave-B review (per ACTIVE.md). The write-set widening is
recorded here as the honest drift; it stayed inside the Item-3 telemetry surface (no parallel
subsystem). The panel Playwright e2e (69/69 local) covers the end-to-end appearance.

**Memory updates:** `specs/memory/product/agents/agent-monitoring.md` (PI telemetry reader +
adapter + panel surface); `specs/memory/product/panel/panel.md` (PI runtime in the
Agents/Sessions runtime switcher).

### overlay-todict-3-map-union-bug

**Description:** During Wave C, an overlay `to_dict` bug was found that dropped a
harness-only workflow from the resolved 3-map union (`contexts | default_harness_overlay |
step_harness_overlay`).

**Resolution:** Fixed inline within Wave C and pinned by a test; the bug
`overlay-todict-drops-harness-only-workflow` is `Closed` (fixed in C). The panel
`_semantic_check` was aligned to the same explicit 3-map union as the doctor (WS-NITS iii),
so panel and doctor now agree on the resolved overlay map without relying on the empty-steps
parse side effect.

**Memory updates:** none required — the overlay/3-map-union behavior is internal resolver
logic; the product-facing capability (operator profiles + per-context overlay inheritance) is
captured in `specs/memory/product/sdd/lifecycle-foundation.md` and the architecture atom.

### wave-d-retention-data-loss-path-fixed-in-review

**Description:** The Wave-D `is_cleanup_eligible` retention path had a data-loss branch under
a specific retention mode (live-run step payloads could become eligible for reclaim).

**Resolution:** Fixed inline during the Wave-D review with a real-provider retention test
(`preserves_live_run_step_payloads`); live-run step artifacts are protected via the extended
`live_claims` injection and are never reclaimed while the run is live. A23 proves
live/promoted payloads survive.

**Memory updates:** `specs/memory/architecture.md` (the workflow-handoff data plane:
control plane = `LifecycleRun.workflow_steps`, data plane = run-scoped immutable step
payloads with retention protect/reclaim).

## Known issues (out-of-scope, carried forward)

These are NOT drifts from PLAN — they are pre-existing or deliberately-deferred items
recorded for the coordinator and the next planning round.

- **`import-linter-contracts-red-but-not-ci-enforced`** (bug, Open) — a pre-existing
  import-linter baseline break (`features.backlog.subject_registry -> cli.main ->
  infrastructure.bug_reporter / subprocess`) present before Wave A and unrelated to this
  release; `ci preflight` does not run import-linter so the 4-check pre-push gate is
  unaffected. Filed; left Open for a future remediation release.
- **`backlog-doctor-blocks-consumed-item-refactor-commit`** (bug, Open) — the pre-commit
  backlog doctor (BL-SCHEMA) blocks a commit when a consumed backlog item's `subject.ref`
  anchors point at code locations the same refactor moved. Encountered on the Wave-A A-02
  commit; worked around by updating the anchors in
  `specs/backlog/shared-headless-adapter-base.md`. Filed; left Open.
- **Deferred review LOWs (3)** recorded in the Wave-D/Wave-E review handoffs under
  `.dadaia/handoff/dadaia-workspace/` for a follow-up nit-sweep (none blocking):
  1. research workflow second consume hop (`synthesis consumes investigate`) not
     independently asserted (Wave-E qa handoff LOW);
  2. terminal-gate graph-completeness BLOCK branch (`_graph_completeness_block`) untested in
     all three bodies — defence-in-depth, primary block path covered (Wave-E qa handoff LOW);
  3. doctor symlink-rglob robustness + doctor UNCONSUMED_REQUIRED FAILED-scoping (Wave-D
     review LOWs).

## Memory updates

Memory describes the product as it is **after** v0.1.30 (atomic snapshot, not a changelog).
Files written during this CLOSURE phase:

- `specs/memory/architecture.md` — added the shared headless-adapter base layer
  (`infrastructure/headless_adapter_base.py`); the workflow-handoff data plane (control plane
  = `LifecycleRun.workflow_steps`, data plane = run-scoped immutable step payloads under
  `.dadaia/runs/lifecycle/<run>/steps/` + resolver/service + retention protect-reclaim +
  attempt loop + handoffs doctor + minimal panel run-ledger API); the three real
  `audit`/`research`/`bug_report` workflow bodies on the fragment+gate engine; PI telemetry
  adapter/reader in the telemetry registry; the local PI-profile store + overlay `extends`
  inheritance in governance.
- `specs/memory/tech-stack.md` — PI session-store reader source documented
  (`~/.pi/agent/sessions/` jsonl, metadata-only T1); Codex rule-corpus-reachable doctor check;
  `DEFERRED_WORKFLOWS` now empty.
- `specs/memory/product/sdd/lifecycle-foundation.md` — workflow model-governance operator PI
  profiles + per-context overlay inheritance; the workflow-step handoff data plane; the three
  new fragment+gate workflow bodies; ctx-inject dehydration (lifecycle prompts composed from
  the dynamic selector).
- `specs/memory/product/agents/agent-monitoring.md` — PI as the fourth telemetry runtime
  (reader/pi.py + PiRuntimeAdapter + `ADAPTER_REGISTRY["pi"]`; cost unknown; metadata-only).
- `specs/memory/product/panel/panel.md` — PI runtime in the Agents/Sessions runtime switcher.
- `specs/memory/product/index.md` — no catalog reorder / no add/remove (all touched features
  already cataloged); not re-written.
- `specs/memory/product/catalog.json` — no slug add/remove (`last_updated` bumps only flow
  through the per-atom frontmatter; regenerate via `dadaia memory catalog generate` if the
  coordinator wants the index refreshed — no new/removed feature this release).

## Dispositions

Disposition-sweep ledger. Backlog files are gitignored in this source repo, so these
on-disk flips are not committed — the committed disposition record is this CLOSURE table plus
the consumed_backlog ledger written by the release-definition consumes hook. The flips are
made on disk anyway (live-instance truth + they pre-empt SPEC-DOC-031 once the coordinator
archives v0.1.30). No bugs were picked into this release (it was define-from-backlog only),
so the bug rows below are the two known-issue bugs left Open and the one fixed inline.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/shared-headless-adapter-base.md` | backlog | `DELIVERED — v0.1.30` | Item 1 / Wave A (T-30-A-01..05); CLOSURE Tasks |
| `specs/backlog/codex-runtime-fidelity.md` | backlog | `DELIVERED — v0.1.30` | Item 2 / Wave B (T-30-B-01/02); CLOSURE Tasks |
| `specs/backlog/workflow-model-governance-operator-profiles-and-context-overlays.md` | backlog | `DELIVERED — v0.1.30` | Item 4 / Wave C (T-30-C-01..05); CLOSURE Tasks |
| `specs/backlog/workflow-step-handoff-data-plane-cleanup.md` | backlog | `DELIVERED — v0.1.30` | Item 5 / Wave D (T-30-D-01..08); CLOSURE Tasks |
| `specs/backlog/lifecycle-prompt-fragments-ai-surface-dehydration.md` | backlog | `DELIVERED — v0.1.30` | Item 6 frontmatter intents (WS-A audit, WS-A research, WS-C); Wave E; OQ-DECISIONS.md frontmatter-intent note |
| `specs/backlog/pi-agent-fourth-harness.md` | backlog | `candidate` (rewritten to WS-PI-5 residual only) | NOT delivered — WS-PI-5 deferred (GRILL D-2, SPEC §4); stays live; never deleted (L6) |
| `specs/bugs/overlay-todict-drops-harness-only-workflow.md` | bug | `Closed` | fixed inline in Wave C |
| `specs/bugs/import-linter-contracts-red-but-not-ci-enforced.md` | bug | `Open` (out-of-scope) | pre-existing baseline break; not CI-enforced; carried forward |
| `specs/bugs/backlog-doctor-blocks-consumed-item-refactor-commit.md` | bug | `Open` (out-of-scope) | workflow tooling friction; carried forward |

**`pi-agent-fourth-harness` rewrite (D-2 / L6):** WS-PI-1..4 shipped v0.1.18–v0.1.21 and
WS-PI-6 ships this release; the item is rewritten to its **WS-PI-5 residual only** (the
destructive DEAD-mark of the standalone `dadaia-pi-workspace` context + its deprecation
README), which stays deferred because `dead()` auto-commits + pushes (leak risk) and is
operator-gated. The item stays `status: candidate` and is never deleted.

## Backlog returns

No new backlog candidates or ideas were discovered during implementation beyond the two
out-of-scope bugs already filed (above) and the deferred review LOWs (recorded in the review
handoffs, not promoted to backlog). The bounded follow-ups named in SPEC §4 remain tracked
in their existing epic bodies:

- Item-5 Slice C (rich panel Workflows-tab data-plane graph) + Slice D (broad ledger
  adoption across all workflow bodies) — tracked in
  `specs/backlog/workflow-step-handoff-data-plane-cleanup.md` epic body (item itself
  DELIVERED for its frontmatter intents).
- Item-6 WS-B (deep AGENTS.md/skill dehydration + AI-surface doctor fleet-shrink) + WS-D
  (independent fragment versioning — OQ-6 deferred, see below) — tracked in
  `specs/backlog/lifecycle-prompt-fragments-ai-surface-dehydration.md` epic body.

## OQ-6 deferral rationale

OQ-6 (independent per-fragment versioning) is **resolved by explicit deferral**, satisfying
Item-6's "OQ-6 resolved" acceptance (A31) without implementation. Full rationale is recorded
in `specs/releases/v0.1.30/OQ-DECISIONS.md`: independent per-fragment versioning is only
valuable behind a concrete archived-replay need (an operator replaying a closed release's
exact prompt bundle), and no such need exists today — closed releases are reconstructed from
their committed SPEC/PLAN/TASKS plus each run record's `injected_context` audit (fragment ids
+ resolved refs + prefix hash + model), which already pins *what was injected* per step
without a parallel fragment-version store. Building a versioned-asset subsystem (storage,
resolution, GC) now would add speculative complexity with no consumer, against the anti-slop
law. WS-D stays epic-body breadth behind that concrete future need. OQ-3/OQ-4/OQ-7 decisions
are reflected in the affected docs/fragments per OQ-DECISIONS.md.

## Archive decision

**MOVE** — the release directory will be moved to
`specs/_archive/releases/v0.1.30/` via `git mv`, and `ACTIVE.md` repointed to the next
release (or `release: none`), **by the coordinator** (the operator's CLOSURE-ONLY decision
defers the archive/ledger/repoint mechanics to the coordinator after this document, the
memory atoms, and the disposition sweep are written). Product-engineer does not push, open a
PR, or `git mv` in this turn.
