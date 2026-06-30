# TASKS — Release: v0.1.43

**Status:** Aprovado
**Release ID:** v0.1.43
**Segment:** alpha-1
**Owner:** product-engineer
**Depends on:** SPEC.md + PLAN.md (Aprovado)

Markers: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. At most one `[-]` per owner unless a
disjoint-write-set parallel pair is declared below.

**Parallelism note.** T-43-1, T-43-2, T-43-6, T-43-6b, T-43-7b/c, and T-43-10 touch disjoint
files (distinct fragment files / distinct workflow + core/hook bodies) and may run in parallel
across owners. T-43-6b (classifier clamp) **must land before** T-43-6 wires the model consult
(it is the boundary guard the consult relies on). T-43-3, T-43-4, T-43-5 all edit
`release_definition.py` and **must be serialized** (one `[-]` among them at a time). T-43-8
(guardrail) and T-43-9 (reprojection/CI) run last.

---

## WS-1 — Coverage: author + wire the two review-gate fragments

- [ ] **T-43-1 — Author `implementation.security_review` + wire `pipeline.review_security`.**
  Owner: ai-engineer.
  Write set: `dadaia_workspace/public/lifecycle_fragments/implementation/security-review.md`
  (NEW); `dadaia_workspace/features/lifecycle/pipeline.py` (`implementation_ladder`,
  `review_security` step ~:534); `tests/integration/cli/...` (pipeline-prompt body assertion).
  Preconditions: none.
  Done: fragment has all 8 frontmatter keys (`role: security-reviewer`, `workflow:
  implementation`, `step: review_security`), an OWASP-style rubric body ≤ ~300 words emitting
  `APPROVED`/`REJECTED` + severity-tagged findings; passes the universality lint; the step now
  carries `fragment_id="implementation.security_review"` +
  `shared_fragment_ids=("shared.anti_slop","shared.output_handoff")`; loads via FragmentLoader
  (no `_generic_prompt`). **Pipeline-prompt assertion (AC-1):** a test proves the built
  `review_security` prompt CONTAINS the fragment-body marker
  `<!-- fragment:implementation.security_review -->` AND the generic suffix
  `Run the {label} step for release` is ABSENT — mirror
  `test_release_definition_workflow.py::test_emitted_prompts_are_fragment_scoped_not_generic`
  (static wiring alone is insufficient because the FAKE adapter ignores the prompt).
  Parallel: with T-43-2, T-43-6.

- [ ] **T-43-2 — Author `implementation.code_review` + wire `pipeline.review_code`.**
  Owner: ai-engineer.
  Write set: `dadaia_workspace/public/lifecycle_fragments/implementation/code-review.md`
  (NEW); `dadaia_workspace/features/lifecycle/pipeline.py` (`review_code` step ~:543);
  `tests/integration/cli/...` (pipeline-prompt body assertion).
  Preconditions: none.
  Done: fragment has all 8 keys (`role: code-reviewer`, `step: review_code`), a code-quality
  rubric body ≤ ~300 words (correctness vs spec / readability / arch-boundary fidelity / no
  dead-dup code / error handling / diff-minimality) emitting `APPROVED`/`REJECTED` with
  `file:line` findings; passes the lint; step carries
  `fragment_id="implementation.code_review"` +
  `shared_fragment_ids=("shared.anti_slop","shared.output_handoff")`. **Pipeline-prompt
  assertion (AC-1):** a test proves the built `review_code` prompt CONTAINS the fragment-body
  marker `<!-- fragment:implementation.code_review -->` AND the generic suffix
  `Run the {label} step for release` is ABSENT.
  Parallel: with T-43-1, T-43-6.

## WS-2 — Shared wiring (serialize T-43-3/4/5: same file)

- [ ] **T-43-3 — Wire `shared.anti_slop` to create + substantive review steps.**
  Owner: ai-engineer.
  Write set: `dadaia_workspace/features/lifecycle/workflows/release_definition.py` (`_SEQUENCE`);
  `dadaia_workspace/features/lifecycle/workflows/backlog_definition.py` (`backlog_author` step).
  Preconditions: none.
  Done: `shared.anti_slop` added to `shared_fragment_ids` of `release_scope`, `spec_create`,
  `plan_create`, `tasks_create`, `spec_arch_review`, `plan_review` (release_definition) and
  `backlog_author` (backlog_definition); existing entries preserved, no duplicates.
  Serialize: with T-43-4, T-43-5 (shared `release_definition.py`).

- [ ] **T-43-4 — Wire `shared.output_handoff` to verdict + audit/bug/research model steps.**
  Owner: ai-engineer.
  Write set: `release_definition.py` (`spec_arch_review`, `spec_qa_review`, `plan_review`,
  `tasks_implementability_review`); `pipeline.py` (`review_qa`, `review_security`,
  `review_code` — already covered for the latter two by T-43-1/2; reconcile to avoid
  duplication); `workflows/audit.py`, `workflows/bug_report.py`, `workflows/research.py`
  (model steps lacking it).
  Preconditions: none.
  Done: every verdict-emitting review step and every audit/bug/research model step cites
  `shared.output_handoff`; no duplicate citations.
  Serialize: with T-43-3, T-43-5.

- [ ] **T-43-5 — Wire `shared.memory_selection` to spec/plan/tasks create + their reviews.**
  Owner: ai-engineer.
  Write set: `release_definition.py` (`spec_create`, `plan_create`, `tasks_create`,
  `spec_arch_review`, `spec_qa_review`, `plan_review`, `tasks_implementability_review`).
  Preconditions: none.
  Done: `shared.memory_selection` cited by each listed step; the WS-5 orphan check no longer
  flags it.
  Serialize: with T-43-3, T-43-4.

## WS-3 — classifier clamp + conflict_scan downgrade-only model consult

- [x] **T-43-6b — Clamp `_classify_pair` to accept only safe downgrade verdicts (CRITICAL).**
  Owner: software-engineer.
  Write set: `dadaia_workspace/features/backlog/classifier.py` (`_classify_pair`, ~:107-111);
  `tests/...` (classifier clamp test).
  Preconditions: none. **Must land before T-43-6 wires the model consult.**
  Done: `_classify_pair` accepts the `downgrade` callable's verdict **only if** it is in
  `{OVERLAP, SUPERSEDES, DEPENDS_ON}`; any other value (`UNRELATED`, `DUPLICATE`, garbage,
  `None`) keeps `DIVERGENT_CONFLICT`. **Adversarial test (AC-5):** a downgrade verdict of
  `UNRELATED`/`DUPLICATE`/garbage/`None` on a differing-change shared-anchor pair leaves the
  pair `DIVERGENT_CONFLICT` (never upgraded, never masked). The existing `no_downgrade`
  (returns `None`) caller is unaffected.
  Parallel: with T-43-1, T-43-2 (distinct file).

- [ ] **T-43-6 — Add the conflict_scan downgrade-only model-consult sub-step in `backlog_definition`.**
  Owner: software-engineer (non-trivial Python) — ai-engineer pairs on fragment frontmatter.
  Write set: `dadaia_workspace/features/lifecycle/workflows/backlog_definition.py`
  (new sub-step feeding the existing `downgrade` seam at `_run_existing_review` ~:354);
  `dadaia_workspace/public/lifecycle_fragments/backlog_definition/conflict_scan.md`
  (frontmatter `step:` realign only if the new step label requires it; body unchanged).
  Preconditions: T-43-6b (classifier clamp) landed.
  Done: a model consult loads `conflict_scan` for shared-anchor differing-change pairs and
  supplies the `downgrade` decision; the **WS-3 wrapper** maps ONLY a parsed
  `OVERLAP`/`SUPERSEDES` verdict → `Verdict`, anything else or unparseable → `None`. It may
  downgrade `DIVERGENT_CONFLICT` → `OVERLAP`/`SUPERSEDES` ONLY on structured proven-compatible
  evidence; never upgrades, never masks a conflict (Python + the T-43-6b clamp keep
  fail-closed — defence-in-depth). A test proves a compatible merge folds and a divergent pair
  stays `DIVERGENT_CONFLICT` (AC-5). `conflict_scan` is no longer an orphan.
  Parallel: with T-43-1, T-43-2.

## WS-4 — Rewrites / token-economy trims

- [ ] **T-43-7a — (Conditional) drop double-injected `static_inputs` from 4 release-def fragments.**
  Owner: ai-engineer.
  Write set: `public/lifecycle_fragments/release_definition/{spec-create,plan-create,
  spec-review-architecture,plan-review}.md`.
  Preconditions: confirm against the **production `release_definition` prefix path** that the
  base `PromptPrefix` is non-`None` AND already carries constitution/architecture (so
  `_prefix_with_static_inputs` re-injects them) before dropping — not a test fixture/hand-built
  prefix.
  Done: only confirmed-duplicate `static_inputs` removed and replaced by a cite-by-name in the
  body; any non-duplicated input — and any case where the production base prefix is `None` —
  preserved (AC-7); fragments still load with 8 keys.

- [ ] **T-43-7b — Trim `implementation.implement_tdd` (~440 → ~370 words).**
  Owner: ai-engineer.
  Write set: `public/lifecycle_fragments/implementation/implement-tdd.md`.
  Preconditions: none.
  Done: marker-discipline bullet deferred to the cited `shared.write_scope`; TDD loop kept;
  word count ~370; still passes lint.
  Parallel: with T-43-7c.

- [ ] **T-43-7c — De-dup the schema-id sentence in `shared.output_handoff`.**
  Owner: ai-engineer.
  Write set: `public/lifecycle_fragments/shared/output-handoff.md`.
  Preconditions: none.
  Done: the `schema=...` sentence the builder's `_required_output_section` already injects is
  removed; the full field table is retained.
  Parallel: with T-43-7b.

## WS-5 — Regression guardrail

- [ ] **T-43-8 — Add the no-generic-prompt + no-orphan + per-step shared-fragment guardrail.**
  Owner: software-engineer (test) — ai-engineer if implemented as a doctor check.
  Write set: `tests/...` (new test module) and/or a `specs doctor`/`public doctor` AI-surface
  check in `dadaia_workspace/`.
  Preconditions: T-43-1..T-43-7 merged (so the first run is green).
  Done: the check **discovers the workflow step sequences dynamically** (or asserts the
  discovered set equals the enumerated 6: `release_definition._SEQUENCE`, `audit`,
  `bug_report`, `research`, `backlog_definition._SEQUENCE`,
  `pipeline.implementation_ladder()`) so a future 7th workflow cannot silently escape the
  guardrail (item E). It FAILS if:
  (a) any prompt-bearing model step has `fragment_id is None`;
  (b) any shipped fragment (excluding `_README.md`) is uncited (orphan);
  (c) **per-step enumeration (AC-2/AC-3):** the exact set of create/review steps that must cite
  `shared.anti_slop` and the exact set that must cite `shared.output_handoff` each do — a
  single step dropping a shared fragment must fail this (a `>=1` orphan count is insufficient).
  Passes after all wiring is in.

## WS-6 — Fix the archived-release lease pid-veto deadlock (HIGH bug)

- [ ] **T-43-10 — Make lease reclaim release-aware (fix `lease-pid-veto-ignores-archived-release`).**
  Owner: software-engineer.
  Write set: `dadaia_workspace/core/lock_liveness.py` (liveness verdict);
  `dadaia_workspace/hooks/sdd_gate.py` (lease check consuming the verdict); the `dadaia lock
  steal` reclaim path; `tests/...` (lock-liveness tests).
  Preconditions: none (fully independent of WS-1..WS-5).
  Done: the lease-liveness verdict AND `lock steal` reclaim a lease whose `release` is **not**
  the context's ACTIVE release (or whose release is archived) **regardless of holder-pid
  liveness**; the pid-veto is retained **only** for a lease pinned to the live ACTIVE release.
  Tests prove (AC-8): (a) an archived/non-ACTIVE-release lease with a **live** holder pid is
  reclaimable by both the verdict and `lock steal`; (b) a live-ACTIVE-release lease with a
  live pid is **still pid-vetoed** (no false steal). The bug
  `lease-pid-veto-ignores-archived-release-blocks-next-release` is marked `Closed` with a
  `## Resolution` section at closure (CLOSURE disposition sweep).
  Parallel: with T-43-1, T-43-2, T-43-6, T-43-6b.

## Closing — reprojection + gate

- [ ] **T-43-9 — Reproject the instance and run the full doctor/CI gate.**
  Owner: ai-engineer (commands surfaced to operator / devops-engineer; PE does not run CLI).
  Write set: none (regenerates projected `.claude/`, `.codex/`, `.agents/`, `.pi/` assets).
  Preconditions: T-43-1..T-43-8, T-43-6b, T-43-10 done.
  Done: `dadaia public stage && dadaia public install --target all` run; `dadaia public
  doctor` includes `[ok]` and exits 0; `dadaia specs doctor` exits 0; `ruff format --check`,
  `ruff check`, `mypy --strict`, `pytest` all exit 0 (AC-9).

---

## Open questions (do not block SPEC approval)

- **OQ-1** — The new review fragments' `output_schema` is a prompt-facing label (the gate
  keys on `is_review` + `verdict ∈ {APPROVED,REJECTED}` via `_validate_review_verdict`, not on
  a fragment-named validator). Confirm whether a registered named-payload validator
  (e.g. `security-review-verdict-v1`, `code-review-verdict-v1`) should be added in
  `workflow_handoffs.py` for the pipeline review steps, or whether the existing review-verdict
  path is sufficient. ai-engineer/software-engineer to confirm during T-43-1/2; no SPEC
  impact.
- **OQ-2** — WS-5 surface choice: pytest-only vs pytest + `public doctor` AI-surface check.
  Default to pytest (minimum); operator may request the doctor surface in addition.
