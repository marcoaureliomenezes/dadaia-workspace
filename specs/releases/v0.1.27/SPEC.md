# SPEC — Release: v0.1.27 — wire the consumed_backlog PRODUCER at release-definition

**Status:** Aprovado
**Release ID:** v0.1.27
**Owner:** product-engineer
**Opened:** 2026-06-26
**Branch:** `feature/v0.1.27`
**Consumes:** wire-consumed-ledger-producer-at-release-definition

> **Consumes contract (this release establishes the convention it practices).** The
> `**Consumes:**` line above is the machine-readable declaration this release introduces:
> a comma-separated list of backlog item slugs (bare slug = the file stem under
> `specs/backlog/<slug>.md`, no `.md`) that the release **fully** consumes. At
> `dadaia lifecycle release define` a guarded post-step parses this line, binds each
> declared slug's `intents[]` through the R1 canonical-subject registry to its verified
> shipped-anchor set, and writes the `consumed_backlog.json` ledger — symmetric with the
> closure-side removal already wired in v0.1.26 R2. This release's own declared slug
> (`wire-consumed-ledger-producer-at-release-definition`) targets the very code this
> release ships, so it is fully consumed at close — the loop is dogfooded.

---

## 1. Problem and context

v0.1.26 R2 shipped the full removal-on-release **mechanism**: the R1-shaped ledger writer
(`consume_at_release_definition`), the residual-aware closure hook (`apply_removal` /
`remove_at_closure`), the `BacklogRemovalLifecycle` container facade, and the closure-side
invocation (`dadaia lifecycle close` calls `lifecycle.remove(...)` as a guarded
`_apply_closure_removal` post-step). The BL-STALE loop is proven both directions at the
function/integration level (`tests/integration/test_backlog_removal_loop.py`).

**The gap (QA MEDIUM, v0.1.26 alpha-1, 2026-06-26):** the *producer* half is not wired
into the real release-definition surface. Nothing writes `consumed_backlog.json` in
production, so `remove_at_closure` always reads an empty ledger and no-ops — the loop
cannot fire end-to-end on a real release. R2 met all 11 of its own acceptance criteria
(producer wiring was not among them), but the §6 removal-on-release feature is
operationally **inert** until this lands.

Deriving the **verified shipped subject-anchor set** at release-definition time was
deliberately deferred in R2: it requires a convention for how a release *declares* which
backlog items it consumed. That convention is now operator-resolved (see §2); this release
implements it and proves the full define→close loop end-to-end.

Source backlog item: `specs/backlog/wire-consumed-ledger-producer-at-release-definition.md`
(`FEAT-BACKLOG-CONSUME-PRODUCER-WIRING-01`, HIGH). It is authoritative; its acceptance
maps 1:1 to this SPEC's §3.

---

## 2. Objective

Wire the consumed_backlog **producer** into the real `dadaia lifecycle release define`
surface — via a `**Consumes:**` SPEC line parsed by a guarded post-step that binds the
declared slugs' anchors and writes the ledger — so removal-on-release fires **end-to-end**
on a real define→close cycle.

### Operator-resolved design decision (2026-06-26 — locked, not re-opened)

A release declares the backlog items it consumes via a machine-readable
`**Consumes:** slug1, slug2` line in the release SPEC — the same bold-key convention
SPEC.md already uses for `**Status:**` / `**Release ID:**` / `**Owner:**` / `**Branch:**`
(the v0.1.26 SPEC already carried a prose `**Consumes (R2 slice):**` line; this release
**formalizes** it into a parsed, machine-readable contract). The mechanism:

1. At `dadaia lifecycle release define`, a guarded **post-step** — symmetric with the
   `close` verb's existing `_apply_closure_removal` post-step — parses the release SPEC's
   `**Consumes:**` line into a slug list.
2. Python binds each declared slug's live R1 `intents[]` through the canonical-subject
   **registry** → the verified shipped-anchor set (the **union** of the bound anchors of
   the declared, fully-consumed slugs).
3. It calls `BacklogRemovalLifecycle.consume(release_id, shipped_anchors=...)` (already
   exists, `features/backlog/removal_lifecycle.py`), which writes
   `specs/_archive/<release-id>/consumed_backlog.json`.
4. **Full-slug granularity.** A declared slug = fully consumed (all its bound anchors
   ship). **Partial consumption is OUT of scope** for this release (see §4); partial items
   stay in the live SET and are hand-rewritten as today.

The closure side (`remove_at_closure` via `dadaia lifecycle close` post-step) is already
wired (R2); this release adds the symmetric producer and proves the full loop.

---

## 3. Scope

Three clusters. Every acceptance criterion is **end-to-end**, not function-level.

### 3.1 — `**Consumes:**` parser + anchor-binding helper (new)

A small helper (in `features/backlog/`) that:
- Parses a release SPEC's `**Consumes:**` line into an ordered, de-duplicated slug list
  (bare slugs; tolerant of surrounding whitespace and a trailing `.md`; an absent line ⇒
  empty list ⇒ producer no-ops cleanly).
- Given the slug list + a `Registry` + the live backlog dir, binds each declared slug's
  `intents[]` to its canonical anchors (via the existing `load_backlog_items` +
  `bound_anchor_changes`) and returns the **union** shipped-anchor set.
- **Fails loud (no silent skip):** a declared slug that does not exist as a live backlog
  item, OR whose intents bind to zero / unresolvable anchors, raises an actionable error
  naming the slug/ref. The producer post-step never writes a ledger built from a partially
  resolved declaration.

### 3.2 — Producer post-step on `dadaia lifecycle release define` (new)

Add a guarded post-step to the `release_define` CLI verb (`cli/commands/lifecycle.py`),
modeled on `close`'s `_apply_closure_removal` (try/except guard; runs only on a
successful/accepted definition run; surfaces a post-step error clearly without corrupting
the definition result). The post-step:
1. resolves the release SPEC path (`<specs_dir>/releases/<release_id>/SPEC.md`);
2. parses its `**Consumes:**` line (§3.1);
3. builds the union shipped-anchor set (§3.1) using the container-composed
   `BacklogRemovalLifecycle`'s registry;
4. calls `lifecycle.consume(release_id=..., shipped_anchors=...)` to write the ledger;
5. emits the written ledger path + the consumed slug list into the verb's JSON/text
   output (symmetric with `close`'s `removed`/`rewritten`/`unchanged` post-step payload).

> **Note on `release_define` plumbing.** Unlike `close`, the `release_define` verb does
> not currently flow through `_run_phase_step` (it calls `workflow.run(...)` directly), so
> it has no `post_step=` parameter today. PLAN resolves whether the post-step is invoked
> inline after `workflow.run(...)` returns `completed=True`, mirroring the same guard
> shape as `_apply_closure_removal`. Either way the convention and behavior are identical.

### 3.3 — Document the convention

Document the `**Consumes:**` declaration convention in memory/architecture **or** the
`dadaia-release-definition` skill (PLAN picks the single canonical home) so an
operator/agent knows how to mark consumption: where the line goes, its grammar (comma-
separated bare slugs), full-slug-only granularity, and the fail-loud-on-unbindable
contract.

### 3.4 — Acceptance criteria (each → a TASK, all end-to-end)

| # | Criterion | Maps to TASK |
|---|-----------|--------------|
| A1 | A real `release define` run with a SPEC `**Consumes:** <slug>` writes `specs/_archive/<release-id>/consumed_backlog.json` keyed on the verified shipped anchor set — tested end-to-end. | T-5 |
| A2 | After a real define→close cycle, a fully-consumed item is removed from the live SET (archive copy precedes unlink) and `backlog doctor` reports zero BL-STALE — tested end-to-end. | T-6 |
| A3 | The `**Consumes:**` convention is documented (memory/architecture or the dadaia-release-definition skill). | T-7 |
| A4 | A `**Consumes:**` slug that does not resolve / has unbindable anchors fails loud (no silent skip) — tested. | T-3, T-4 |

---

## 4. Out of scope

- **Partial consumption.** A backlog item only *partially* shipped by a release is NOT
  recorded by this producer (full-slug granularity only, per §2.4). Partial items stay in
  the live SET and are hand-rewritten to their residual, exactly as today. (The R2
  closure-side `apply_removal` already rewrites-down-to-residual when a ledger lists a
  partial — but this producer never *writes* a partial entry. `consume_at_release_definition`
  itself already drops non-fully-consumed items; this is a documentation+test boundary,
  not new code.)
- **`workflow-model-governance` / panel control-plane.** Untouched. The next release.
- **Any change to the closure-side removal** (`remove_at_closure`, `apply_removal`,
  `dadaia lifecycle close`). It is already correct and wired; this release only feeds it a
  non-empty ledger.
- **Re-opening the declaration-mechanism decision** (SPEC line vs terminal step vs
  operator declaration). Locked to the `**Consumes:**` SPEC line.
- **An alias-map editor or `panel`/`api` anchor auto-derivation.** Binding uses the R1
  registry as-is; a slug whose intents need a panel/api alias that is absent simply fails
  loud (A4), which is correct.

---

## 5. Dependencies and risks

**Upstream:** v0.1.26 R2 (closed + archived) — supplies `consume_at_release_definition`,
`BacklogRemovalLifecycle`, the container builder `build_backlog_removal_lifecycle`, and
the R1 registry + `load_backlog_items` / `bound_anchor_changes`. All present; no blocker.

**Sequencing:** must land before relying on removal-on-release operationally. Does **not**
block `workflow-model-governance`.

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Producer writes ledger into a not-yet-archived release dir; closure later `git mv`s the release dir over it. | Med | Ledger could be duplicated/lost on archive. | `consume` writes to `specs/_archive/<release-id>/` (the *archive* root, not the live release dir) via `write_consumed` — confirmed by reading `removal_lifecycle.py`. PLAN/T-5 asserts the on-disk path is under `_archive/`, decoupled from the live release dir's `git mv`. |
| `**Consumes:**` declares a slug whose intents include an alias-only (panel/api) subject with no alias entry. | Med | Bind HALTs. | This is the desired fail-loud (A4): T-4 asserts an actionable error naming the slug/ref; the producer writes no partial ledger. |
| `release_define` lacks a `post_step` seam (asymmetry vs `close`). | High (confirmed by inspection) | More plumbing than `close`. | PLAN adds the guarded post-step inline after `workflow.run(...)` with the same try/except guard shape; no change to the workflow body or `_SEQUENCE`. |
| Self-referential dogfood: this release's own `**Consumes:**` slug points at code this release ships, so its intents may not bind until the code exists. | Low | A2 dogfood could fail loud prematurely. | The slug's intents are `code` subjects (`removal_lifecycle.py#...`, `release_definition.py#...`) that already exist in the tree (R2 shipped them); they bind today. T-6 verifies on the real tree. |

**Risk of regression to the closure path:** none — no closure code changes.
