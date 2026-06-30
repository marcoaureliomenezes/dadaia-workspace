# Closure: Release — v0.1.43

> **Status:** Aprovado
> **Release ID:** v0.1.43
> **Segment:** alpha-1
> **Owner:** product-engineer
> **Closed:** 2026-06-30

## Summary

v0.1.43 closed the two model-driven review-gate coverage holes in the
lifecycle-fragment library and hardened the surrounding wiring and lease governance.
The pipeline's `review_security` and `review_code` steps — the steps that mechanically
gate every push and PR — were running on a ~2-sentence generic placeholder; this release
authored `implementation.security_review` (OWASP-style diff rubric) and
`implementation.code_review` (correctness/readability/architecture-boundary/diff-minimality
rubric) and wired both pipeline steps to load them, with a pipeline-prompt body assertion
proving the right fragment body actually reaches the built prompt (not merely the wiring).

It broadly wired the previously under-/un-wired shared fragments — `shared.anti_slop` to
every create step plus the substantive review steps, `shared.output_handoff` to every
verdict-emitting review step and the audit/bug/research model steps, and
`shared.memory_selection` to the spec/plan/tasks create steps and their reviews — and made
the orphaned `backlog_definition.conflict_scan` reachable as a **downgrade-only** model
consult. To keep a model verdict from ever masking a real conflict, the classifier boundary
(`_classify_pair`) was clamped to accept a downgrade verdict only when it is in
`{OVERLAP, SUPERSEDES, DEPENDS_ON}` — anything else leaves the pair `DIVERGENT_CONFLICT`.
A no-generic-prompt / no-orphan regression guardrail was added so the coverage holes cannot
silently regress, and redundant fragment token bloat was trimmed. Finally, the one
genuinely-open HIGH bug — `lease-pid-veto-ignores-archived-release-blocks-next-release` —
was fixed at its root cause by making lease reclaim release-aware, so an archived-release
lease can no longer deadlock the next release.

The release shipped rebased clean onto `main` (it is **not** built on the unmerged
v0.1.33–v0.1.42 line), squash-merged via PR #76 at `66b12df8` with all CI green.

## Tasks completed

All tasks landed on `feature/v0.1.43-*` and were squash-merged into `main` at `66b12df8`
(PR #76). Per-task commits are collapsed by the squash; the squash SHA is the durable
final commit for every task below.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-43-1 | Author `implementation.security_review` + wire `pipeline.review_security` + pipeline-prompt body assertion | `66b12df8` |
| T-43-2 | Author `implementation.code_review` + wire `pipeline.review_code` + pipeline-prompt body assertion | `66b12df8` |
| T-43-3 | Wire `shared.anti_slop` to create + substantive review steps | `66b12df8` |
| T-43-4 | Wire `shared.output_handoff` to verdict + audit/bug/research model steps | `66b12df8` |
| T-43-5 | Wire `shared.memory_selection` to spec/plan/tasks create + their reviews | `66b12df8` |
| T-43-6b | Clamp `_classify_pair` to accept only `{OVERLAP, SUPERSEDES, DEPENDS_ON}` downgrade verdicts (CRITICAL) | `66b12df8` |
| T-43-6 | Add the `conflict_scan` downgrade-only model-consult sub-step in `backlog_definition` | `66b12df8` |
| T-43-7a | (Conditional) drop double-injected `static_inputs` — **KEPT**, double-injection not confirmed | `66b12df8` |
| T-43-7b | Trim `implementation.implement_tdd` (~440 → ~370 words) | `66b12df8` |
| T-43-7c | De-dup the `schema=...` sentence in `shared.output_handoff` | `66b12df8` |
| T-43-8 | Add the no-generic-prompt + no-orphan + per-step shared-fragment guardrail | `66b12df8` |
| T-43-10 | Make lease reclaim release-aware (fix `lease-pid-veto-ignores-archived-release`) | `66b12df8` |
| T-43-9 | Reproject the instance + run the full doctor/CI gate | `66b12df8` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Coverage gate (AC-9 supporting) | `pytest -m "unit or contract" --cov-fail-under=80` | 82.35% — pass (≥80% gate) |
| Full test suite green | `pytest` | `4160 passed` |
| Strict type check clean | `mypy --strict` | clean (exit 0) |
| Lint + format clean | `ruff format --check && ruff check` | clean (exit 0) |
| Projection consistency | `dadaia public doctor` | `[ok]` (exit 0) |
| SDD health | `dadaia specs doctor` | 0 errors (exit 0) |
| Review gates fragment-driven; no generic prompt; right fragment body in prompt (AC-1) | WS-5 guardrail test + pipeline-prompt body assertion | pass — `<!-- fragment:implementation.security_review -->` / `<!-- fragment:implementation.code_review -->` present, generic suffix absent |
| No orphan + per-step shared-fragment enumeration (AC-2/3/4) | WS-5 guardrail test | pass — `conflict_scan` + `memory_selection` cited; per-step `anti_slop`/`output_handoff` sets asserted |
| Conflict-boundary clamp, adversarial (AC-5) | new classifier test | pass — `UNRELATED`/`DUPLICATE`/garbage/`None` downgrade keeps `DIVERGENT_CONFLICT`; compatible folds to `OVERLAP`/`SUPERSEDES` |
| Lease pid-veto release-aware (AC-8) | new lock-liveness tests | pass — archived/non-ACTIVE lease + live pid reclaimable (verdict + `lock steal`); live-ACTIVE lease + live pid still vetoed |
| Architect review | trio review (architect) | APPROVED |
| QA review | trio review (qa-engineer) | APPROVED |
| Security review | trio review (security-reviewer) | APPROVED |
| Merge to main + CI | PR #76 squash-merge | `main` `66b12df8`, 29 CI checks green |

## Drifts

### ws-4a-static-inputs-kept

**Description:** WS-4a was conditional on confirming that `constitution.md` /
`architecture.md` are double-injected via the production `release_definition` prefix path.
On inspection, the production CLI path (`cli/commands/lifecycle.py::release_define`) calls
`build_release_definition_workflow` with **no** `prefix` argument, so the base
`PromptPrefix` defaults to `None` (`container.py:984`); `_prefix_with_static_inputs`
(`release_definition.py:798`) builds the prefix from that `None` base, making the
fragments' `static_inputs` the **sole** deterministic carrier of that content.

**Resolution:** Per AC-7, the inputs were **preserved unchanged** — dropping them would
have removed constitution/architecture from the prompt entirely. No fragment was edited
for WS-4a; T-43-7a was completed as a confirmed no-op. No plan deviation beyond the
explicitly-conditional branch the SPEC anticipated.

**Memory updates:** none required for this drift.

## Memory updates

- `specs/memory/architecture.md` — one-line edit to the "Liveness = TTL com PID veto"
  bullet recording the v0.1.43 **release-aware reclaim**: the pid-veto now applies only to
  a lease pinned to the live ACTIVE release; a lease pinned to a non-ACTIVE/archived release
  is reclaimable despite a live holder pid (both the liveness verdict and `lock steal`), so
  an archived-release lease can no longer deadlock the next release. This corrects an
  inaccuracy in the prior text, which described the pid-veto as unconditional.
- `specs/memory/architecture.md` — review-gate fragment coverage + conflict_scan consult
  seam: **no change.** architecture.md documents the fragment library at the subsystem level
  and does not track per-step fragment wiring at the granularity these AI-surface changes
  touch; recording them would be narration, not a correction of current product truth.
- `specs/memory/tech-stack.md` — no change: release touched no dependencies.
- `specs/memory/product/**` — no change: AI-surface-only release, no end-user
  product-behaviour delta.

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/bugs/lease-pid-veto-ignores-archived-release-blocks-next-release.md` | bug | `Closed` | T-43-10 / commit `66b12df8`; see WS-6 + Validations (AC-8 tests) |

> **Note on the bug file:** `specs/bugs/**` is gitignored in this source repo, so the
> bug file's `status: Closed` flip is **not version-controlled**. This CLOSURE row is the
> durable record of the resolution. Root cause: the lease-liveness pid-veto was
> release-agnostic, so an archived-release lease with a live holder pid vetoed reclaim
> forever and `lock steal` correctly refused (pid alive), deadlocking the next release.
> Fixed by making both the liveness verdict and the `lock steal` reclaim path
> release-aware (T-43-10).

## Backlog returns

- `backlog/candidates.md` ← the closure 5-fragment suite + the closure workflow body
  (out of scope per SPEC §5 / ADR-2; blocked on the unshipped closure workflow body —
  a dangling closure fragment id fails the loader). Tracked for a dedicated item.
- No other backlog returns: residual scope items below are already tracked.

## Out of scope / residual

- **Unmerged v0.1.33–v0.1.42 line** (including the constitution realignment) and its
  coverage-gate debt remain for separate handling. v0.1.43 deliberately shipped rebased
  clean onto `main`, not on that line.
- **The 19 historically-open bugs other than the picked one** — all already fixed +
  validated on the prior branch line; not re-touched by this release.
- **OQ-6 fragment versioning**, **WS-B deep AGENTS.md / skill dehydration**, and re-doing
  the v0.1.24 fragment engine/loader/context selector — all out of scope per SPEC §5.
- **OQ-1** (registered named-payload validator for the review fragments) was resolved in
  implementation: the existing `is_review` + `verdict ∈ {APPROVED,REJECTED}` path is
  sufficient; the new fragments' `output_schema` remains a prompt-facing label. No
  follow-up required.

## Archive decision

**MOVE** — the release directory will be moved to
`specs/_archive/releases/v0.1.43/` via `git mv` by the coordinator, and `ACTIVE.md`
updated to point at the next release or `release: none`. (Product-engineer does not run
git/archive commands; this CLOSURE authoring does not perform the move.)
