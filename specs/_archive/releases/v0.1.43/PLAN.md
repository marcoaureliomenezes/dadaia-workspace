# PLAN — Release: v0.1.43

**Status:** Aprovado
**Release ID:** v0.1.43
**Segment:** alpha-1
**Owner:** product-engineer
**Depends on:** SPEC.md (Aprovado)

---

## 1. Strategy

Predominantly an AI-surface change, with two narrow production-Python workstreams. Edit kinds:

1. **Fragment bodies** — Markdown under `dadaia_workspace/public/lifecycle_fragments/`
   (author 2, trim 3, conditionally edit 4 frontmatters).
2. **Prompt wiring** — `shared_fragment_ids` / `fragment_id` tuples and one new sub-step in
   the Python workflow bodies (`features/lifecycle/workflows/*.py`, `pipeline.py`).
3. **Production Python (software-engineer)** — the WS-3 conflict-boundary clamp in
   `features/backlog/classifier.py`, and the WS-6 release-aware lease reclaim in
   `core/lock_liveness.py` + `hooks/sdd_gate.py` + the `lock steal` path. These are bounded,
   well-localized behaviour fixes, not a redesign.

After every fragment-source edit the instance is reprojected
(`dadaia public stage && dadaia public install --target all && dadaia public doctor`). PE
does not run CLI — reprojection + doctor are delegated to the operator / devops-engineer and
recorded as a task. Implementation owner is **ai-engineer** for the fragment + wiring work;
the WS-3 classifier clamp + model consult and the WS-6 lease fix are owned by
**software-engineer**.

No end-user product-behaviour change (the lease + conflict-boundary fixes are internal
lifecycle/governance correctness). No memory write during implementation (memory note, if any,
is a CLOSURE-phase action by product-engineer).

---

## 2. Layers affected

| Layer | Files | Change |
|---|---|---|
| Fragment library | `public/lifecycle_fragments/implementation/security-review.md` (NEW), `.../code-review.md` (NEW) | author 2 review-gate fragments |
| Fragment library | `public/lifecycle_fragments/implementation/implement-tdd.md`, `shared/output-handoff.md`, `release_definition/{spec-create,plan-create,spec-review-architecture,plan-review}.md`, `backlog_definition/conflict_scan.md` | trim / conditional static_inputs / frontmatter `step:` realign |
| Pipeline wiring | `features/lifecycle/pipeline.py` (`implementation_ladder`, ~:534/:543) | set `fragment_id` + `shared_fragment_ids` on `review_security`, `review_code` |
| Release-def wiring | `features/lifecycle/workflows/release_definition.py` (`_SEQUENCE`, ~:183) | add `anti_slop`/`output_handoff`/`memory_selection` to create+review steps |
| Backlog-def wiring | `features/lifecycle/workflows/backlog_definition.py` (`_SEQUENCE`, `_run_*`, `downgrade` seam) | NEW conflict_scan model-consult sub-step feeding `downgrade` |
| Conflict boundary | `features/backlog/classifier.py` (`_classify_pair`, ~:107-111) | clamp accepted downgrade verdicts to `{OVERLAP, SUPERSEDES, DEPENDS_ON}` (WS-3 CRITICAL) |
| Audit/bug/research wiring | `features/lifecycle/workflows/{audit,bug_report,research}.py` | add `output_handoff` to the model steps lacking it |
| Guardrail | `tests/...` (new test) and/or `specs doctor`/`public doctor` AI-surface check | fail on generic-prompt model step or orphan fragment; per-step shared-fragment enumeration; dynamic sequence discovery |
| Lease liveness (WS-6) | `core/lock_liveness.py` (liveness verdict), `hooks/sdd_gate.py` (lease check), `lock steal` reclaim path | release-aware reclaim: archived/non-ACTIVE-release lease reclaimable despite live pid; pid-veto kept only for live-ACTIVE-release lease |
| Pipeline-prompt test (WS-1) | `tests/integration/cli/...` | assert each pipeline review prompt contains its fragment-body marker + lacks the generic suffix |

---

## 3. Execution order

1. **WS-1a/WS-1b — author the two review fragments + wire pipeline.** Highest value;
   independently shippable (ADR-3). Mirror `qa-review.md` shape and frontmatter.
2. **WS-2a/WS-2b/WS-2c — shared wiring.** Pure tuple edits in the workflow bodies; cheap,
   high leverage. Do after WS-1 so the two new review fragments also receive `anti_slop`
   (WS-2a) and `output_handoff` (WS-2b).
3. **WS-3 — classifier clamp + conflict_scan model-consult sub-step.** Independent of WS-1/2;
   software-engineer. **Land the classifier `_classify_pair` clamp first** (it is the boundary
   guard the model consult relies on), then wire the downgrade-only model consult.
4. **WS-6 — lease pid-veto bug fix.** Fully independent of all fragment work; software-engineer.
   May run in parallel with WS-1..WS-5.
5. **WS-4 — rewrites/trims.** WS-4a conditional confirmation first, then WS-4b/WS-4c.
6. **WS-5 — guardrail check.** Last, so its first green run reflects the closed holes.
7. **Reprojection + full doctor/CI gate.** Closing task; must exit 0 before review/closure.

Tasks within steps 1–4 have **disjoint write sets** at the file level (distinct fragment
files / distinct workflow bodies) and may run in parallel where TASKS.md declares it; the
wiring edits to `release_definition.py` (WS-2a/b/c) all touch one file and must be serialized.

---

## 4. Technical detail per workstream

### WS-1 — review-gate fragments

- Frontmatter (both): `role` = `security-reviewer` / `code-reviewer`; `workflow:
  implementation`; `step: review_security` / `review_code`; `static_inputs: []`;
  `dynamic_inputs` per the audit P1/P2 brief (`[change_diff, spec_criteria,
  dependency_changes, test_evidence]` / `[change_diff, spec_criteria, plan_slice,
  architecture_summary]`); `output_schema` a verdict label (see OQ-1);
  `max_context_policy: exact-files-only`.
- Body: rubric table + explicit `APPROVED`/`REJECTED` output instruction with
  severity-tagged findings citing `file:line`. ≤ ~300 words. No harness-specific token.
- Wiring: in `implementation_ladder()` set `fragment_id="implementation.security_review"` +
  `shared_fragment_ids=("shared.anti_slop","shared.output_handoff")` on `review_security`;
  analogously for `review_code`. `is_review=True` is already set on both.

### WS-2 — shared wiring

- WS-2a `anti_slop` → create steps (`release_scope`, `spec_create`, `plan_create`,
  `tasks_create`, `backlog_author`) + review steps (`spec_arch_review`, `plan_review`,
  `review_security`, `review_code`).
- WS-2b `output_handoff` → verdict-emitting review steps that lack it (`spec_arch_review`,
  `spec_qa_review`, `plan_review`, `tasks_implementability_review`, `review_qa`,
  `review_security`, `review_code`) + audit/bug/research model steps that lack it.
- WS-2c `memory_selection` → `spec_create`, `plan_create`, `tasks_create` +
  `spec_arch_review`, `spec_qa_review`, `plan_review`, `tasks_implementability_review`.
- All are additions to each step's `shared_fragment_ids` tuple — preserve existing entries,
  no duplicates.

### WS-3 — classifier clamp + conflict_scan consult (software-engineer)

- **Classifier clamp (CRITICAL, land first).** In `_classify_pair`
  (`features/backlog/classifier.py:107-111`) accept the `downgrade` callable's verdict **only
  if** it is in `{OVERLAP, SUPERSEDES, DEPENDS_ON}`; for any other value (`UNRELATED`,
  `DUPLICATE`, garbage, `None`) keep `DIVERGENT_CONFLICT`. This closes the latent fail-open
  before a model is ever wired into the seam — the boundary owner clamps, the wrapper is
  defence-in-depth.
- The seam: `_run_existing_review` (`backlog_definition.py:340`) already passes
  `downgrade=self._downgrade` into `classify(...)`. Add a model-consult that runs **only**
  for shared-anchor differing-change pairs (the pairs Python would default to
  `DIVERGENT_CONFLICT`), loads `backlog_definition.conflict_scan`, and produces a structured
  compatible-merge verdict (`OVERLAP`/`SUPERSEDES` + evidence) or nothing.
- **WS-3 wrapper:** the model-backed downgrade callable maps **only** a parsed `OVERLAP` /
  `SUPERSEDES` verdict → a `Verdict`; anything else or unparseable → `None`. Combined with the
  classifier clamp, two independent gates protect the conflict boundary. Never upgrade
  `UNRELATED`, never reclassify a `DUPLICATE`, never mask a conflict.
- Realign `conflict_scan.md` frontmatter `step:` to the new sub-step label if the wiring
  needs a distinct step name; keep the body content (it is sound per the audit).
- Model-consult uses the same `_run_model_step` machinery (FragmentLoader +
  `build_fragment_suffix(..., is_review=False)` — it adjudicates, it does not self-verdict
  the gate).

### WS-4 — rewrites

- WS-4a: confirm double-injection **against the production `release_definition` prefix path** —
  the real base `PromptPrefix` must be non-`None` AND already contain constitution/architecture
  before `_prefix_with_static_inputs` folds the fragment static_inputs (`static_inputs` are the
  deterministic carrier; the base prefix is `| None`). Drop only the confirmed-duplicate
  `static_inputs`; cite by name in the body. Leave any non-duplicated input — and any case where
  the production base prefix is `None` — in place (AC-7).
- WS-4b: move the marker-discipline bullet out of `implement-tdd.md` (it duplicates
  `shared.write_scope`); keep the TDD loop. Target ~370 words.
- WS-4c: drop the `schema=...` sentence in `output-handoff.md` already auto-injected by the
  builder's `_required_output_section`; keep the full field table.

### WS-5 — guardrail

- New test **discovers the workflow step sequences dynamically** (or asserts the discovered
  set equals the enumerated 6: `release_definition`, `audit`, `bug_report`, `research`,
  `backlog_definition`, `pipeline.implementation_ladder()`) so a future 7th workflow cannot
  silently escape the guardrail. Asserts:
  (a) every prompt-bearing model step (not `role=python`, not a `gate`/`commit_gate`) has
  `fragment_id is not None`;
  (b) every shipped fragment id under `public/lifecycle_fragments/` (excluding `_README.md`)
  is referenced by at least one step's `fragment_id` or `shared_fragment_ids` — no orphan;
  (c) **per-step shared-fragment enumeration:** the exact set of create/review steps that must
  cite `shared.anti_slop` and `shared.output_handoff` each do (a `>=1` orphan count is
  insufficient — dropping a shared fragment from a single step must fail this check).
- A `specs doctor`/`public doctor` AI-surface check is an acceptable alternative/addition.

### WS-6 — lease pid-veto bug fix (software-engineer)

- Make lease reclaim **release-aware**. In the lease-liveness verdict (`core/lock_liveness.py`)
  and the `lock steal` reclaim path: a lease whose `release` is **not** the context's ACTIVE
  release (or whose release is archived) is reclaimable **regardless of holder-pid liveness**;
  the pid-veto is retained **only** for a lease pinned to the live ACTIVE release.
- `hooks/sdd_gate.py` lease check consumes the same release-aware verdict so a MUTATING write
  for the next release is no longer blocked by a stale archived-release lease.
- Tests: (a) archived/non-ACTIVE-release lease + live pid → reclaimable (verdict + `lock steal`);
  (b) live-ACTIVE-release lease + live pid → still pid-vetoed (no false steal). Resolves bug
  `lease-pid-veto-ignores-archived-release-blocks-next-release`.

---

## 5. Validation plan

| What | Command | Gate |
|---|---|---|
| Fragments load + 8 keys + universality lint | `pytest tests/.../fragments` + loader lint | green |
| Review gates fragment-driven, no generic prompt | WS-5 guardrail test | green |
| Right fragment BODY reaches the pipeline prompt | new pipeline-prompt test (fragment-body marker present, generic suffix absent) | green |
| No orphan fragments + per-step shared-fragment set | WS-5 orphan + per-step enumeration assertions | green |
| Workflow sequence discovery cannot miss a future workflow | WS-5 dynamic discovery (or discovered == 6) assertion | green |
| conflict_scan downgrade-only behaviour | new backlog_definition test (compatible folds, divergent stays) | green |
| Classifier clamp (adversarial) | new classifier test: `UNRELATED`/`DUPLICATE`/garbage/`None` downgrade verdict keeps `DIVERGENT_CONFLICT` | green |
| WS-6 lease pid-veto fix | new lock-liveness test: archived-release lease + live pid reclaimable; live-ACTIVE-release lease + live pid still vetoed | green |
| Reprojection consistency | `dadaia public stage && install --target all && public doctor` | `[ok]` + exit 0 |
| SDD health | `dadaia specs doctor` | exit 0 |
| Lint/type/test gate | `ruff format --check`, `ruff check`, `mypy --strict`, `pytest` | exit 0 |

Per release-governance, the alpha-1 boundary is **qa-engineer review only** → a commit on
`feature/v0.1.43`; full trio + CLOSURE + archive happen at the shipping `rc-N`.

---

## 6. Risks (carried from SPEC §6)

- WS-4a over-drop → conditional confirmation against the **production** prefix path (AC-7).
- conflict_scan / model verdict masking a real conflict → classifier `_classify_pair` clamp to
  `{OVERLAP, SUPERSEDES, DEPENDS_ON}` + downgrade-only wrapper + AC-5 adversarial test.
- Mis-wire passing WS-5 because FAKE adapter ignores the prompt → AC-1 pipeline-prompt
  body-marker assertion (content, not just wiring).
- Verdict-shape mismatch on new review fragments → mirror `qa_review`; gate keys on
  `verdict`.
- WS-6 false steal of a genuinely-active session → fix narrows reclaim to non-ACTIVE/archived
  leases only; AC-8 proves the live-ACTIVE lease stays pid-vetoed.
- Reprojection drift → mandatory closing reprojection + `public doctor`.
