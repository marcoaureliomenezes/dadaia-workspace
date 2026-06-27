# PLAN — Release: v0.1.27 — wire the consumed_backlog PRODUCER at release-definition

**Status:** Aprovado
**Release ID:** v0.1.27
**Owner:** product-engineer

> Implements SPEC v0.1.27. Strategy: add the smallest symmetric producer that feeds the
> already-wired closure remover a non-empty ledger, driven by a `**Consumes:**` SPEC line.
> No change to the closure path, the workflow body, or `_SEQUENCE`.

---

## 1. Strategy

The closure half is already correct: `dadaia lifecycle close` runs `_apply_closure_removal`
which calls `BacklogRemovalLifecycle.remove(...)` → `remove_at_closure` → reads every
archived `consumed_backlog.json`, unions shipped anchors, runs `apply_removal`. It no-ops
only because **nothing writes the ledger**. So the entire release is: **write the ledger at
release-definition from a declared `**Consumes:**` line**, then prove the loop.

Two new units + one wiring + one doc:

1. **Parser/binder helper** (`features/backlog/`) — pure, roots injected, no cwd.
2. **Producer post-step** on the `release_define` CLI verb — guarded, symmetric with
   `_apply_closure_removal`, reuses the container-composed `BacklogRemovalLifecycle`.
3. **Doc** of the convention (single canonical home — §4 picks).

The existing `consume_at_release_definition` already does the *recording* logic correctly:
it loads live backlog items, binds each item's intents, and records an item **only when
every one of its bound anchors is in the shipped set** (full-consumption ⇔ zero residual).
So the producer's job is narrow: compute the **shipped-anchor set** = union of the bound
anchors of the **declared** `**Consumes:**` slugs, then hand that set to `lifecycle.consume`.
The full-vs-partial filtering is already enforced inside `consume_at_release_definition`.

---

## 2. Layers affected

| Layer | File | Change |
|-------|------|--------|
| feature (pure) | `dadaia_workspace/features/backlog/consumes.py` (NEW) | `parse_consumes_line(spec_text) -> tuple[str, ...]`; `shipped_anchors_for(slugs, *, backlog_dir, registry) -> frozenset[str]` (fail-loud). |
| CLI wiring | `dadaia_workspace/cli/commands/lifecycle.py` | Add a guarded producer post-step to `release_define`, invoked after `workflow.run(...)` returns `completed`. |
| container | `dadaia_workspace/container.py` | Reuse `build_backlog_removal_lifecycle` (already exists) — the post-step calls it. Expose `_backlog_context_roots`-derived specs_dir if needed for the SPEC path (helper added if not importable). |
| docs (memory) | `dadaia_workspace/public/skills/dadaia-release-definition/SKILL.md` **or** `specs/memory/architecture.md` | Document the `**Consumes:**` convention. §4 picks the home. |
| tests | `tests/unit/backlog/test_consumes.py` (NEW); `tests/integration/test_release_consume_producer.py` (NEW) | Unit (parser + binder fail-loud) + end-to-end (define writes ledger; define→close removes + zero BL-STALE). |

No change to: `features/backlog/removal_lifecycle.py`, `features/backlog/removal.py`,
`features/backlog/ledger*.py`, `features/lifecycle/workflows/release_definition.py`,
`_SEQUENCE`, or anything on the closure path.

---

## 3. Execution order (TDD)

1. **T-1** — Pure parser `parse_consumes_line`: tests first (RED), then implement (GREEN).
2. **T-2** — Pure binder `shipped_anchors_for` happy path: union of bound anchors of
   declared slugs. Tests first, then implement.
3. **T-3** — Binder fail-loud: unknown slug (not a live backlog item) raises naming it.
4. **T-4** — Binder fail-loud: slug present but intents bind to zero/unresolvable anchors
   raises naming the ref (reuse `bound_anchor_changes`'s `unresolved` list).
5. **T-5** — End-to-end producer post-step: a real `release define` run over a temp
   workspace fixture with a SPEC `**Consumes:** <slug>` writes
   `specs/_archive/<release-id>/consumed_backlog.json` keyed on the verified shipped-anchor
   set. Wires the post-step into the CLI verb. (A1)
6. **T-6** — End-to-end loop: define (writes ledger) → close (removes) over a temp fixture;
   assert the fully-consumed item file is gone from the live backlog dir, an archive copy
   exists (copy-precedes-unlink), and `backlog doctor` reports zero BL-STALE. (A2)
7. **T-7** — Document the `**Consumes:**` convention (doc-only). (A3)
8. **T-8** — Full-suite + lint/type gate: `ruff format --check`, `ruff check`,
   `mypy --strict`, `pytest`; confirm no in-repo `.dadaia/`/cache pollution.

A4 is satisfied by T-3 + T-4 (fail-loud) and re-asserted at the post-step boundary in T-5
(a bad `**Consumes:**` surfaces as the verb's `post_step_error`, never a silent skip).

---

## 4. Key technical decisions

- **Producer reads the SPEC, not the run record.** The `**Consumes:**` line is parsed from
  `<specs_dir>/releases/<release_id>/SPEC.md` at post-step time. `specs_dir` is resolved
  the same way `build_backlog_removal_lifecycle` resolves its roots (`_backlog_context_roots`
  — consumer `repos/<ctx>/specs` else workspace-root `specs`). The post-step gets the SPEC
  path from a tiny container helper (e.g. `build_release_spec_path(workspace_root, context,
  release_id)`) OR by reusing the already-resolved `backlog_dir.parent` from the lifecycle
  facade. Implementer picks the cleanest seam; **no cwd reads** (SPEC §3.8 discipline).
- **`shipped_anchors_for` returns the UNION over declared slugs only.** It does NOT scan
  all live items — it binds exactly the declared slugs. `consume_at_release_definition` then
  re-derives each item's anchors and records only those whose full anchor set ⊆ the union.
  For a single fully-declared slug this is an identity (its own anchors ⊆ its own anchors),
  so it is recorded; a declared slug whose intents are a strict superset of another, smaller
  undeclared item could incidentally make that smaller item "fully consumed" — **document
  this** as expected (the union is the verified shipped set; any live item fully covered by
  it is correctly consumable).
- **Fail-loud raises before any write.** `shipped_anchors_for` raises
  `ConsumesBindError` (a new local exception) on unknown slug or unbindable intent; the
  post-step lets it propagate into the verb's guarded try/except, surfacing as
  `post_step_error` (symmetric with `_apply_closure_removal`'s guard). The ledger is never
  written from a partial/failed declaration.
- **Doc home = the `dadaia-release-definition` skill** (`public/skills/
  dadaia-release-definition/SKILL.md`), because the convention is *how an operator/agent
  declares consumption during release definition* — operational guidance, not a memory
  atom. A one-line pointer is added to `specs/memory/architecture.md` only if the §3.6
  removal section already documents the closure half (implementer checks; if architecture
  already narrates removal-on-release, extend that section instead — single canonical home,
  no duplication). NOTE: editing `public/skills/**` is a lib-originated asset edit — the
  implementer edits the source under `dadaia_workspace/public/` then runs `dadaia public
  stage && install`, per the dev-guardrail. This is OUTSIDE product-engineer's scope and is
  done by the implementer in IMPLEMENTATION (not by product-engineer authoring specs).

---

## 5. Validation plan

| What | Command | Evidence at CLOSURE |
|------|---------|---------------------|
| Parser + binder fail-loud | `pytest tests/unit/backlog/test_consumes.py` | stdout snippet |
| A1 producer writes ledger E2E | `pytest tests/integration/test_release_consume_producer.py::test_define_writes_ledger` | stdout snippet |
| A2 define→close removes + zero BL-STALE | `pytest tests/integration/test_release_consume_producer.py::test_define_close_loop` | stdout snippet |
| A4 fail-loud at post-step boundary | `pytest tests/integration/test_release_consume_producer.py::test_bad_consumes_fails_loud` | stdout snippet |
| Full gate | `ruff format --check . && ruff check . && mypy --strict dadaia_workspace && pytest` | exit 0 / sha |
| No cache pollution | `git status --short` shows no in-repo `.dadaia/` or cache dirs | snippet |

---

## 6. Risks (carried from SPEC §5)

- **Ledger path vs `git mv` at archive.** `write_consumed(archive_root=specs/_archive, …)`
  writes to `specs/_archive/<release-id>/consumed_backlog.json` — the archive root, NOT the
  live release dir. T-5 asserts the on-disk path is under `_archive/`. The later closure
  `git mv specs/releases/<id> specs/_archive/releases/<id>` targets a *different* subtree
  (`_archive/releases/<id>`), so there is no collision. (Confirmed by reading
  `removal_lifecycle.py` + `ledger_writer.py`.)
- **`release_define` post-step seam.** Add inline after `workflow.run(...)` with the same
  try/except guard shape as `_apply_closure_removal`; the post-step runs only when
  `result.completed` is true. No change to the workflow body.
- **Self-referential dogfood.** This release's `**Consumes:**` slug targets `code` anchors
  that already exist (R2 shipped them); they bind today, so the dogfood is safe.

---

## 7. Out of scope (carried from SPEC §4)

Partial consumption, `workflow-model-governance`, any closure-path change, re-opening the
declaration mechanism, alias-map editing / panel-api auto-derivation. See SPEC §4.
