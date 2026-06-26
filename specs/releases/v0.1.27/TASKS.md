# TASKS — Release: v0.1.27 — wire the consumed_backlog PRODUCER at release-definition

**Status:** Aprovado
**Release ID:** v0.1.27
**Owner:** product-engineer (authored) → software-engineer (implements)

> Markers: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE. At most one `[-]` per owner.
> TDD-ordered: write the failing test, then the code, then green. Every task's
> **Done-when** includes: the task's tests green, `ruff format --check` + `ruff check`
> clean on touched files, `mypy --strict` clean, and **no in-repo `.dadaia/`/cache
> pollution** (`git status --short` shows only intended source/test changes; run pytest
> with `-p no:cacheprovider`). All roots injected — no `os.getcwd()` reads.

---

## T-1 — Parser: `parse_consumes_line`

- **Description:** Pure function `parse_consumes_line(spec_text: str) -> tuple[str, ...]`
  that extracts the `**Consumes:**` bold-key line from release SPEC text and returns an
  ordered, de-duplicated slug list. Tolerates surrounding whitespace, a trailing `.md`,
  and an empty/missing line (→ empty tuple). Bold-key match mirrors the existing
  `**Status:**`/`**Branch:**` convention.
- **Write-set:** `dadaia_workspace/features/backlog/consumes.py` (NEW);
  `tests/unit/backlog/test_consumes.py` (NEW).
- **Preconditions:** none.
- **Done-when:** unit tests cover present-line / multi-slug / dedup / `.md`-strip /
  absent-line; RED→GREEN; mypy --strict + ruff clean; maps to A4 substrate.
- **Parallelism:** none (foundation for T-2..T-4).

## T-2 — Binder: `shipped_anchors_for` (happy path)

- **Description:** Pure function `shipped_anchors_for(slugs, *, backlog_dir, registry) ->
  frozenset[str]` returning the UNION of bound anchors of the declared slugs. Reuses
  `load_backlog_items(backlog_dir)` + `bound_anchor_changes(item, registry)`; binds only
  the declared slugs (no full-dir scan).
- **Write-set:** `dadaia_workspace/features/backlog/consumes.py`;
  `tests/unit/backlog/test_consumes.py`.
- **Preconditions:** T-1.
- **Done-when:** unit test with a fixture registry + temp backlog dir asserts the union
  set for one and for two declared slugs; RED→GREEN; mypy/ruff clean.
- **Parallelism:** none.

## T-3 — Binder fail-loud: unknown slug

- **Description:** `shipped_anchors_for` raises `ConsumesBindError` (new local exception in
  `consumes.py`) naming the slug when a declared slug is not a live backlog item file.
  No silent skip; no partial set returned.
- **Write-set:** `dadaia_workspace/features/backlog/consumes.py`;
  `tests/unit/backlog/test_consumes.py`.
- **Preconditions:** T-2.
- **Done-when:** unit test asserts `ConsumesBindError` raised with the unknown slug in the
  message; mypy/ruff clean. Maps to A4.
- **Parallelism:** none.

## T-4 — Binder fail-loud: unbindable intents

- **Description:** `shipped_anchors_for` raises `ConsumesBindError` naming the unresolved
  ref when a declared slug exists but has zero bound anchors or any unresolved intent
  (surface `bound_anchor_changes`'s `unresolved` messages). The ledger is never built from
  a partially-resolved declaration.
- **Write-set:** `dadaia_workspace/features/backlog/consumes.py`;
  `tests/unit/backlog/test_consumes.py`.
- **Preconditions:** T-3.
- **Done-when:** unit test with an intent whose subject does not resolve asserts the raise
  + the ref appears in the message; mypy/ruff clean. Maps to A4.
- **Parallelism:** none.

## T-5 — Producer post-step on `release define` (A1, end-to-end)

- **Description:** Add a guarded producer post-step to the `release_define` CLI verb,
  modeled on `close`'s `_apply_closure_removal` (try/except guard; runs only when
  `result.completed`). The post-step: resolves `<specs_dir>/releases/<release_id>/SPEC.md`
  (via a tiny container seam, e.g. `build_release_spec_path(...)` or the lifecycle facade's
  resolved roots — **no cwd**); parses `**Consumes:**` (T-1); computes the union
  shipped-anchor set (T-2); calls `build_backlog_removal_lifecycle(...).consume(release_id=
  ..., shipped_anchors=...)`; emits the written ledger path + consumed slug list into the
  verb's JSON/text output (symmetric with `close`'s post-step payload). A bind error
  surfaces as `post_step_error`, never a silent skip.
- **Write-set:** `dadaia_workspace/cli/commands/lifecycle.py`;
  `dadaia_workspace/container.py` (SPEC-path seam only if needed);
  `tests/integration/test_release_consume_producer.py` (NEW).
- **Preconditions:** T-1, T-2.
- **Done-when:** integration test `test_define_writes_ledger` runs a real `release define`
  over a temp workspace fixture (SPEC with `**Consumes:** <slug>`) and asserts
  `specs/_archive/<release-id>/consumed_backlog.json` exists, is keyed on the verified
  shipped-anchor set, and the path is under `_archive/` (not the live release dir);
  RED→GREEN; mypy/ruff clean; no cache pollution. Maps to A1.
- **Parallelism:** none (depends on the binder).

## T-6 — Define→close loop (A2, end-to-end)

- **Description:** End-to-end test: over a temp workspace fixture, run `release define`
  (writes ledger) then `lifecycle close` (runs `_apply_closure_removal`). Assert the
  fully-consumed backlog item file is **gone** from the live backlog dir, an archive copy
  exists (copy-precedes-unlink, ADR-C), and `backlog doctor` reports **zero BL-STALE**.
- **Write-set:** `tests/integration/test_release_consume_producer.py`.
- **Preconditions:** T-5.
- **Done-when:** `test_define_close_loop` green: item removed from live SET, archive copy
  present, `backlog doctor` zero BL-STALE; mypy/ruff clean; no cache pollution. Maps to A2.
- **Parallelism:** none.

## T-7 — Document the `**Consumes:**` convention (A3, doc-only)

- **Description:** Document the convention in the canonical home picked by PLAN §4 — the
  `dadaia-release-definition` skill source (`dadaia_workspace/public/skills/
  dadaia-release-definition/SKILL.md`); add a one-line pointer to the §3.6 removal section
  of `specs/memory/architecture.md` only if that section already narrates removal-on-release
  (else extend that section — single home, no duplication). Cover: line placement, grammar
  (comma-separated bare slugs), full-slug-only granularity, fail-loud-on-unbindable.
  Editing `public/skills/**` is a lib-originated asset edit — implementer edits the source,
  then `dadaia public stage && dadaia public install --target all && dadaia public doctor`.
  Memory edit (if any) is gate-allowed in DEFINITION/CLOSURE; for this doc task prefer the
  skill home to avoid a memory write outside closure.
- **Write-set:** `dadaia_workspace/public/skills/dadaia-release-definition/SKILL.md`
  (and/or `specs/memory/architecture.md` per the conditional above).
- **Preconditions:** T-5 (document the shipped behavior).
- **Done-when:** the convention is documented in exactly one canonical home; `dadaia public
  doctor` exit 0 (if skill source edited); no duplication. Maps to A3.
- **Parallelism:** safe to run alongside T-6 (disjoint write set: docs vs tests).

## T-8 — Full gate + hygiene

- **Description:** Run the full lint/type/test gate and confirm clean working tree.
- **Write-set:** none (verification only).
- **Preconditions:** T-1..T-7.
- **Done-when:** `ruff format --check .`, `ruff check .`, `mypy --strict dadaia_workspace`,
  and `pytest -p no:cacheprovider` all green; `git status --short` shows only intended
  source/test/doc changes (no in-repo `.dadaia/`, `.pytest_cache/`, `.mypy_cache/`,
  `.ruff_cache/`, coverage). Pre-push CI gate green.
- **Parallelism:** terminal — run last.

---

## Marker board

- [x] T-1 — Parser `parse_consumes_line`
- [x] T-2 — Binder `shipped_anchors_for` (happy path)
- [x] T-3 — Binder fail-loud: unknown slug
- [x] T-4 — Binder fail-loud: unbindable intents
- [ ] T-5 — Producer post-step on `release define` (A1, E2E)
- [ ] T-6 — Define→close loop (A2, E2E)
- [ ] T-7 — Document `**Consumes:**` convention (A3)
- [ ] T-8 — Full gate + hygiene

## Acceptance traceability

| Acceptance (SPEC §3.4) | Tasks |
|---|---|
| A1 — define writes ledger E2E | T-5 |
| A2 — define→close removes + zero BL-STALE E2E | T-6 |
| A3 — convention documented | T-7 |
| A4 — bad `**Consumes:**` fails loud | T-3, T-4, (boundary in T-5) |
