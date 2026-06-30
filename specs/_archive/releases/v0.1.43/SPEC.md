# SPEC — Release: v0.1.43

**Status:** Aprovado
**Release ID:** v0.1.43
**Segment:** alpha-1
**Owner:** product-engineer
**Opened:** 2026-06-30

---

## 1. Problem and context

The dadaia-workflows inject **static prompt fragments** into Layer-2 worker prompts
(`dadaia_workspace/public/lifecycle_fragments/`, wired from the Python workflow bodies in
`features/lifecycle/workflows/*.py` and `features/lifecycle/pipeline.py`). A 2026-06-30
ai-engineer audit + the mandatory product-engineer grill (ADR-1..4) found the library is
structurally healthy (27/29 fragments cited, all harness-universal) but carries five
concrete defects that degrade worker-prompt quality and let a coverage hole regress:

1. **Two model-driven review gates run on a generic placeholder.** `pipeline.review_security`
   and `pipeline.review_code` (`pipeline.py:534`, `:543`) have `fragment_id=None`, so
   `_generic_prompt` emits a ~2-sentence "emit a verdict" instruction instead of a real
   rubric. `review_security` is the step that mechanically gates **every push** (pre-push
   security-verdict chokepoint) — the single highest-value authoring gap in the library.
2. **`shared.anti_slop` is wired to one step only** (`implement`), when the create and
   review steps that produce the most slop never receive the root-cause/evidence/SSoT
   discipline.
3. **`backlog_definition.conflict_scan` is an orphan** (273 words, manifest-tracked, never
   loaded). Its declared target `existing_backlog_review` is a `role=python` step that
   runs no model; the fragment's compatible-merge adjudication is unreachable, so every
   shared-anchor differing-change pair fail-closes to `DIVERGENT_CONFLICT` with no path to
   recognize a provably-compatible merge (the C→D vs C→E case central to the dedup item).
4. **`shared.memory_selection` is an orphan** (367 words, cited nowhere) — the
   "context-minimal / prefer catalog summaries over full atoms" discipline never reaches a
   worker.
5. **Token-economy redundancies:** 4 release-definition fragments re-declare
   `constitution.md`/`architecture.md` as `static_inputs` that the cacheable `PromptPrefix`
   may already carry (double-injection); `implementation.implement_tdd` (440 words)
   duplicates the marker table held canonically in `shared.write_scope`; and
   `shared.output_handoff` re-states the `schema=...` sentence the builder's
   `_required_output_section` already auto-injects.

**This is an AI-surface release.** Fragments live in
`dadaia_workspace/public/lifecycle_fragments/`; wiring lives in the Python workflow bodies
(`features/lifecycle/workflows/*.py`, `pipeline.py`). The implementation owner is
**ai-engineer** (fragment bodies + prompt wiring), with **software-engineer** for the one
non-trivial Python sub-step (the conflict_scan model-consult that feeds the existing
`downgrade` seam in `backlog_definition.py`).

The mandatory pre-SPEC grill is DONE; its refinement report
(`.dadaia/reports/dadaia-workspace/product-engineer/2026-06-30T141031Z-refine-specs.html`,
ADR-1..4) and the source audit
(`.dadaia/reports/dadaia-workspace/ai-engineer/2026-06-30T135956Z-fragment-audit.html`)
are the authoritative scope; this SPEC does not re-litigate their settled decisions.

**Bug-state coherence note (for closure):** v0.1.43 **picks and resolves exactly one**
genuinely-open bug — `lease-pid-veto-ignores-archived-release-blocks-next-release` (HIGH,
Open), the only bug on this line that is not already fixed (see WS-6). The other 19
historically-open bugs were all fixed and validated across the v0.1.37→v0.1.42 work
already on this branch; this release does not re-touch them. The closure bug-disposition
set is therefore `{lease-pid-veto-ignores-archived-release-blocks-next-release: resolved}`.
Note that `bug-report-fake-bug-write-emits-stub-and-discards-fields.md` is **already Closed**
(resolved v0.1.37): its body quotes a stub containing `status: Open` inside a code block,
which is a `grep` false-positive, not an open bug — it is not picked.

---

## 2. Objective

Close the lifecycle-fragment coverage and wiring gaps — author the two missing review-gate
fragments, broadly wire the under-/un-wired shared fragments, make `conflict_scan` reachable
as a downgrade-only model consult **clamped at the conflict boundary so a model verdict can
never mask a real conflict**, and trim the redundant fragment bloat — add a guardrail check
so no model-driven lifecycle step can ever again fall back to a generic prompt, and **fix the
one genuinely-open HIGH bug** (`lease-pid-veto-ignores-archived-release-blocks-next-release`)
at its root cause so an archived-release lease can no longer deadlock the next release.

---

## 3. Scope

### WS-1 — Coverage: author + wire the two missing review-gate fragments (HIGH)

- **WS-1a** Author `implementation.security_review` (role `security-reviewer`): an
  OWASP-style review rubric over the change diff — injection / secrets & tokens /
  auth & access-control claims / dependency additions / generated-file & prompt-leakage /
  public-asset privacy — returning `APPROVED`/`REJECTED` with severity-tagged findings.
  Wire it on `pipeline.review_security` (`pipeline.py:534`), replacing the `_generic_prompt`
  fallback. ~300 words.
- **WS-1b** Author `implementation.code_review` (role `code-reviewer`): a review rubric —
  correctness vs spec, readability/naming, architecture-boundary fidelity, no
  dead/duplicated code, error handling, diff-minimality — returning `APPROVED`/`REJECTED`
  with findings citing exact `file:line`. Wire it on `pipeline.review_code`
  (`pipeline.py:543`). ~300 words. Mirrors the shape of the existing
  `implementation.qa_review` fragment.

Both steps already carry `is_review=True`, so the gate keys on the emitted `verdict`. The
fragment `output_schema` is a **prompt-facing label** (rendered into the required-output
section), not a registered validator — see Open Question OQ-1.

### WS-2 — Shared wiring (HIGH/MED)

- **WS-2a** Wire `shared.anti_slop` to all create steps (`release_definition`: `release_scope`,
  `spec_create`, `plan_create`, `tasks_create`; `backlog_definition`: `backlog_author`) **and**
  the substantive review steps (`spec_arch_review`, `plan_review`, the two new review
  fragments). One-line `shared_fragment_ids` citation each. (HIGH)
- **WS-2b** Wire `shared.output_handoff` to the review steps that emit verdicts
  (`release_definition`: `spec_arch_review`, `spec_qa_review`, `plan_review`,
  `tasks_implementability_review`; `pipeline`: `review_qa`, `review_security`, `review_code`)
  and the audit/bug/research model steps that emit findings (`audit.drift_scan`,
  `audit.triage`, `bug_report.dedupe`, `bug_report.bug_intake`, `research.investigate`,
  `research.synthesis` — wire the model steps that lack it). (MED)
- **WS-2c** Wire `shared.memory_selection` to `spec_create`, `plan_create`, `tasks_create`
  and their review steps (`spec_arch_review`, `spec_qa_review`, `plan_review`,
  `tasks_implementability_review`) — ADR-4: wire, do not retire. (MED)

### WS-3 — conflict_scan reachable as a downgrade-only model consult (MED) + boundary clamp (CRITICAL)

Add a **new narrow model-consult sub-step** in the `backlog_definition` workflow that loads
`backlog_definition.conflict_scan` and consults the model on exactly the shared-anchor
differing-change pairs. Per ADR-1 it may **downgrade** a `DIVERGENT_CONFLICT` to
`OVERLAP`/`SUPERSEDES` **only on structured proven-compatible evidence** — it may never
upgrade and never miss a conflict (that stays Python's call). The clean seam already exists:
`_run_existing_review` calls `classify(bound_new, demand.existing, downgrade=self._downgrade)`
(`backlog_definition.py:354`). The model consult supplies the `downgrade` decision; absent a
proven-compatible verdict the class stays `DIVERGENT_CONFLICT` (fail-closed). The
`conflict_scan` fragment's frontmatter `step:` value is realigned to the new sub-step if
needed.

**Boundary clamp (CRITICAL — fixes the architect WS-3 fail-open finding).** Wiring a model
into the `downgrade` seam exposes a latent fail-open in the classifier itself. Today
`_classify_pair` (`dadaia_workspace/features/backlog/classifier.py:107-111`) accepts **any**
non-`None`, non-`DIVERGENT_CONFLICT` verdict the `downgrade` callable returns — safe only
because the sole current caller (`no_downgrade`) returns `None`. A model returning
`UNRELATED`/`DUPLICATE`/garbage would then **mask a real conflict**. The classifier is the
boundary owner and MUST be clamped (software-engineer change in `classifier.py`):

- **Classifier clamp:** `_classify_pair` accepts a downgrade verdict **only if** it is in
  `{OVERLAP, SUPERSEDES, DEPENDS_ON}`. Any other verdict (`UNRELATED`, `DUPLICATE`, garbage,
  `None`) leaves the pair `DIVERGENT_CONFLICT`. The model can narrow the conflict's name but
  can never erase it.
- **WS-3 wrapper:** the model-backed downgrade callable maps **only** a parsed `OVERLAP` /
  `SUPERSEDES` verdict → a `Verdict`; anything else or unparseable → `None`. With the
  classifier clamp this is defence-in-depth (two independent gates), not the sole guard.

### WS-4 — Rewrites / token-economy trims (MED/LOW)

- **WS-4a** **Conditional.** Drop the redundant `constitution.md`/`architecture.md`
  `static_inputs` from the 4 release-definition fragments (`spec_create`, `plan_create`,
  `spec_review_architecture`, `plan_review`) **if and only if** implementation confirms the
  double-injection **against the production `release_definition` prefix path** (not a test
  fixture or a hand-built prefix): the base `PromptPrefix` produced in the real
  `release_definition` flow must be **non-`None` AND demonstrably carry constitution +
  architecture**, and `_prefix_with_static_inputs` (`release_definition.py:798`) must fold the
  de-duplicated fragment `static_inputs` into that prefix as additional `static-input:`
  sections. Note `static_inputs` are the **deterministic carrier** (`_prefix_with_static_inputs`
  always folds them) whereas the base prefix is `PromptPrefix | None` — so dropping a
  `static_input` is safe **only** when the production base prefix is confirmed non-`None` and
  already carries that content. If the base prefix is `None`, or a fragment's static input is
  **not** already in the production base prefix, keep it. Cite by name in the body rather than
  re-declaring as a step input where dropped.
- **WS-4b** Trim `implementation.implement_tdd` (~440 → ~370 words): defer the marker-
  discipline bullet to the cited `shared.write_scope` (canonical marker table); keep the TDD
  loop. (LOW)
- **WS-4c** De-dup the `schema=...` sentence in `shared.output_handoff` vs the builder's
  auto-injected `_required_output_section`; keep the full field table the one-liner omits.
  (LOW)

### WS-5 — Regression guardrail (HIGH)

Add an AI-surface doctor/test check that **FAILS** if any model-driven lifecycle step
(non-gate, non-`role=python`, prompt-bearing) resolves to a generic prompt
(`fragment_id is None`) instead of a fragment. It iterates every workflow step sequence
(`release_definition._SEQUENCE`, `audit`, `bug_report`, `research`,
`backlog_definition._SEQUENCE`, and `pipeline.implementation_ladder()`) and asserts every
prompt-bearing model step names a fragment. It also asserts **no orphan fragments** remain
(every shipped fragment id is cited by at least one step's `fragment_id`/`shared_fragment_ids`).
A pytest check is the minimum; a `specs doctor`/`public doctor` AI-surface check is acceptable
as the surface if ai-engineer prefers it.

### WS-6 — Fix the archived-release lease-pid-veto deadlock (HIGH bug)

Pick and fix the one genuinely-open bug,
`specs/bugs/lease-pid-veto-ignores-archived-release-blocks-next-release.md` (HIGH, Open).

**Root cause.** The lease-liveness pid-veto is **release-agnostic**: a lease pinned to an
**ARCHIVED** (non-ACTIVE) release whose holder pid is still alive vetoes reclaim forever, so
the next release's MUTATING work (release-definition + implementation) is deadlocked with no
self-service path. `dadaia lock steal` correctly refuses (pid alive), which makes the deadlock
total.

**Surface.** `dadaia_workspace/core/lock_liveness.py` (the liveness verdict),
`dadaia_workspace/hooks/sdd_gate.py` (the gate's lease check), and the `dadaia lock steal`
reclaim path.

**Fix (from the bug's suggested fix).** Make the lease-liveness verdict **and** the
`lock steal` reclaim path release-aware: reclaim a lease whose `release` is **not** the
context's ACTIVE release (or whose release is archived) **regardless of holder-pid liveness**.
Keep the pid-veto **only** for a lease pinned to the **live ACTIVE** release — a session
mutating the current release is still never stolen. Owner: **software-engineer**.

**Closure action.** At closure, mark the bug `status: Closed` with a `## Resolution` section
naming the fix and the final commit SHA; record it in the CLOSURE `## Dispositions` sweep.

---

## 4. Acceptance criteria

1. `pipeline.review_security` and `pipeline.review_code` load real fragments; **no**
   model-driven lifecycle step falls back to `_generic_prompt` (WS-5 check asserts this and
   fails if violated). **Beyond static wiring, a pipeline-prompt assertion proves the right
   fragment BODY reaches the prompt** (the FAKE adapter ignores the prompt, so a wrong-but-
   existing `fragment_id` would pass mere wiring checks): for every pipeline model step the
   built prompt CONTAINS that step's own fragment-body marker (e.g.
   `<!-- fragment:implementation.security_review -->` /
   `<!-- fragment:implementation.code_review -->`) **and** the generic suffix
   (`Run the {label} step for release`) is ABSENT. Mirror the sibling pattern
   `tests/integration/cli/test_release_definition_workflow.py::test_emitted_prompts_are_fragment_scoped_not_generic`.
2. `shared.anti_slop` is cited by every create step + every substantive review step. The WS-5
   guardrail (T-43-8) **enumerates the exact set** of create/review steps that must cite
   `shared.anti_slop` and asserts each one does — a per-step regression guard, not merely a
   `>=1`-citation orphan check (which would pass even if a single step silently dropped it).
3. `shared.output_handoff` is cited by every verdict-emitting review step and by the
   audit/bug/research model steps. The WS-5 guardrail likewise **enumerates the exact set** of
   create/review steps that must cite `shared.output_handoff` and asserts each one does.
4. **No orphan fragments remain:** `backlog_definition.conflict_scan` and
   `shared.memory_selection` are each cited by ≥1 step (the WS-5 orphan check fails
   otherwise).
5. The conflict_scan consult can downgrade a `DIVERGENT_CONFLICT` **only** on structured
   proven-compatible evidence: a test proves a compatible merge folds to `OVERLAP`/`SUPERSEDES`
   and a genuinely divergent pair stays `DIVERGENT_CONFLICT` (never upgraded, never missed).
   **Adversarial clamp:** a test proves that a model downgrade verdict of `UNRELATED`,
   `DUPLICATE`, garbage, or unparseable on a differing-change shared-anchor pair leaves the
   pair `DIVERGENT_CONFLICT` — the classifier (`_classify_pair`) accepts a downgrade verdict
   only when it is in `{OVERLAP, SUPERSEDES, DEPENDS_ON}`; anything else can never upgrade or
   mask the conflict.
6. Every fragment (existing + 2 new) passes the loader harness-universality lint
   (`_FORBIDDEN_TOKENS`); the 2 new fragments carry all 8 required frontmatter keys
   (`id, role, workflow, step, static_inputs, dynamic_inputs, output_schema, max_context_policy`).
7. WS-4a only drops a `static_input` whose double-injection vs the **production base prefix**
   is confirmed (production `release_definition` path, base prefix non-`None` and carrying
   constitution/architecture); any non-duplicated input, or any case where the base prefix is
   `None`, preserves the input.
8. **WS-6 lease pid-veto fix:** a test proves that a lease pinned to an **archived /
   non-ACTIVE** release with a **live holder pid** is reclaimable by both the lease-liveness
   verdict and `lock steal`; and a complementary test proves that a lease pinned to the
   **live ACTIVE** release with a live holder pid is **still pid-vetoed** (no false steal of a
   genuinely active session). The bug is marked `Closed` with a `## Resolution` at closure.
9. After fragment-source edits the instance is reprojected
   (`dadaia public stage && dadaia public install --target all`) and `dadaia public doctor`,
   `dadaia specs doctor`, `ruff format --check`, `ruff check`, `mypy --strict`, and `pytest`
   all exit 0.

---

## 5. Out of scope (explicit)

- **The closure 5-fragment suite + the closure workflow body** (ADR-2). The closure
  fragments are blocked on the unshipped closure workflow body — a dangling closure fragment
  id fails the loader. This becomes its own backlog item (mirroring how `backlog_definition`
  was split from the original fragment epic).
- **OQ-6 fragment versioning** (WS-D of the original epic).
- **WS-B deep AGENTS.md / skill dehydration.**
- Re-doing the v0.1.24 fragment engine / loader / context selector.
- **The 19 historically-open bugs other than the picked one** — all already fixed + validated
  on this branch (v0.1.37→v0.1.42). This release does **not** re-touch them. v0.1.43 **does**
  pick and resolve exactly one bug — `lease-pid-veto-ignores-archived-release-blocks-next-release`
  (WS-6); the closure bug-disposition set is `{lease-pid-veto: resolved}` (see §1 bug-state
  coherence note). `bug-report-fake-bug-write-emits-stub-and-discards-fields` is already Closed
  (a `grep` false-positive in its quoted stub) and is not picked.

---

## 6. Dependencies, risks, and memory impact

**Dependencies / sequencing.** WS-1 (author the two review fragments) is independently
shippable and may land first if the operator elects (ADR-3). WS-5 must merge after WS-1+WS-2
so the guardrail's first green run reflects the closed holes. WS-3 depends only on the
existing `downgrade` seam in `backlog_definition.py` plus the classifier clamp (both in the
same workstream). **WS-6 (the lease pid-veto bug fix) is fully independent** of the fragment
work — it touches `core/lock_liveness.py`, `hooks/sdd_gate.py`, and the `lock steal` path, and
may proceed in parallel with WS-1..WS-5. No cross-release blocker.

**Memory impact.** This release touches the **AI surface only** — no product-behaviour
change for end users. At closure, `specs/memory/architecture.md` may take a one-line note on
the now-complete review-gate fragment coverage and the conflict_scan consult seam; product
atoms and `tech-stack.md` are not expected to change. Final memory-update list is recorded in
CLOSURE.md.

**Risks.**

| Risk | Mitigation |
|---|---|
| New review fragment emits a verdict shape the gate rejects | Both steps already `is_review=True`; the gate keys on `verdict ∈ {APPROVED,REJECTED}`. Mirror `qa_review`'s output contract. **The verdict shape is covered by the pipeline review tests; the WS-5 static guardrail does NOT cover prompt *content* — that gap is closed by the AC-1 pipeline-prompt body assertion (fragment-body marker present, generic suffix absent).** |
| A mis-wire (wrong-but-existing `fragment_id`) passes WS-5 because the FAKE adapter ignores the prompt | AC-1 pipeline-prompt body assertion checks the built prompt contains the step's own fragment-body marker and lacks the generic suffix — wiring checks alone are insufficient. |
| WS-4a drops a static input that was NOT actually double-injected | WS-4a is explicitly conditional — confirm against the **production** base prefix (non-`None`, carries constitution/architecture) before dropping; preserve any non-duplicated input and any `None`-prefix case (AC-7). |
| conflict_scan consult or a model verdict upgrades/masks a real conflict | Downgrade-only by construction (feeds `downgrade` callable; Python still fail-closes) **and** the classifier `_classify_pair` clamp accepts a downgrade verdict only in `{OVERLAP, SUPERSEDES, DEPENDS_ON}` — `UNRELATED`/`DUPLICATE`/garbage can never erase the conflict (AC-5 adversarial test). |
| WS-6 fix falsely steals a genuinely-active session's lease | The fix narrows reclaim to leases pinned to a non-ACTIVE/archived release only; a live-ACTIVE-release lease with a live pid stays pid-vetoed — AC-8 proves both directions (reclaim archived, refuse active). |
| Reprojection drift after source edits | `dadaia public stage && install --target all && public doctor` is a mandatory closing task (T-43-9); doctor must exit 0. |
| Harness-specific token slips into a new fragment | Loader `_FORBIDDEN_TOKENS` lint + the dual-parser parity test; AC-6. |

**Open questions** — see TASKS.md OQ list; OQ-1 (review-fragment `output_schema` label vs a
registered named-payload validator) is the only one that may need an operator/ai-engineer
confirmation during implementation and does not block SPEC approval.
