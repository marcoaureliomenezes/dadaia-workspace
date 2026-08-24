# CLOSURE-CHECKS — dd-release-implement (final-rc closure detail)

Disclosed reference reached at steps 8, 10 and 11 of `SKILL.md`'s arc — `product-engineer`
reads the section named at each step; no other agent needs this file for earlier steps.

## §1 — Memory Markdown update protocol (step 8)

1. **Verify gate phase.** Confirm `specs/releases/ACTIVE.md` phase = `CLOSURE` (memory
   writes are also allowed in `DEFINITION`). Otherwise the gate will block writes to
   `specs/memory/*.md`.
2. **Do not author legacy HTML memory.** If legacy HTML memory exists, treat it as
   read-only migration input. New memory writes are Markdown atoms.
3. **Update Markdown atoms.** Apply the release's deltas to the corresponding
   `specs/memory/*.md` or `specs/memory/product/*.md` files. Memory describes the
   product **as it is now** — not what changed. The change history lives in this
   release's `CLOSURE.md` and the archived release dir.
4. **Diagrams.** Use fenced Mermaid blocks:
   ```mermaid
   flowchart LR
     A --> B
   ```
   For screenshots, place PNGs under `specs/assets/<scope>/<id>.png` and reference via
   `<img src="../assets/<scope>/<id>.png" alt="<text>">`.
5. **Forbidden in memory Markdown:**
   - `<h2>Changelog</h2>`, `<h2>History</h2>`, `<h2>Histórico</h2>`, `<h2>Versions</h2>`
   - `<section class="changelog">` and similar
   - Narrative of past versions ("we used to use X, now we use Y")

   If the operator asks for history, point to `CLOSURE.md` or `_archive/`.
6. **Validate** with `dadaia specs doctor` before moving to archive. Doctor checks
   atomicity, broken `<img>` references, and Mermaid script presence.

## §2 — Disposition sweep (step 10, mandatory)

Before archive, flip every backlog item and bug picked into (or superseded by) the
release to a terminal status token — vocabulary and format: `dd-backlog-definition` §2
(the canonical, single home of the terminal disposition-token table) — and record each
flip as a row in `CLOSURE.md`'s `## Dispositions` table with an evidence pointer
(CLOSURE section or commit SHA). A release whose CLOSURE lacks the sweep is not
closeable.

**CONSUMED → terminal token is an UPDATE, never a duplicate (BL-DUP).** Purge-on-pick
(`dd-backlog-definition` §2) already moved a fully-consumed slug out of `## ACTIVE` at
SPEC time, sometimes recording it provisionally as `CONSUMED` in the SPEC's provenance
section. The disposition sweep does not add a second `## LEDGER` line for that slug — it
**updates** the one line purge-on-pick is responsible for to its final terminal token
(`DELIVERED`/`SUPERSEDED`/`RESOLVED`/…), same slug, same line. Two `## LEDGER` lines for
one slug is a defect.

Never-delete law (`DADAIA.md` §6 (Backlog)): a bug or backlog file is **never deleted** —
always marked with a terminal token and a reason. A bug is never silently dropped:
either it is fixed (`Closed`) or a superseding backlog item covers its acceptance
(`Closed` + `superseded_by: <slug>`). Stale or invalid items are dispositioned
`DEFERRED` or `REJECTED` with a reason, never removed.

`dadaia specs doctor` backstops the sweep: SPEC-DOC-031 (FR14 semantics) WARNs when an
**archived** SPEC's `**Consumes:**` declaration or an **archived** CLOSURE's
`## Dispositions` rows name a still-non-terminal `ACTIVE` slug; SPEC-DOC-032 WARNs on a
bug `status:` outside the {`Open`, `Closed`} canon.

**Standing note.** Because SPEC-DOC-031 only counts archived-document assertions, this
closure's own `git mv` archive step (step 12) adds one such WARN per non-terminal slug
the just-archived SPEC/CLOSURE names — capture the SPEC-DOC-031 count **after** this
closure's archive move, never before.

## §3 — Artifact GC sweep (step 11, FR25, mandatory)

Run once `CLOSURE.md`'s `## Validations`/`## Dispositions` evidence pointers are final —
before the archive move, never before. The sweep needs the finished evidence list to
know what survives.

**Scope:** this release's own working artifacts under `.dadaia/` — its coordination
handoffs, its HTML reports, its `.dadaia/tmp/<agent>/` captures, and its lifecycle run
records. Never another release's artifacts, and never anything outside `.dadaia/`.

**Keep/delete rule (inviolable):**

- KEEP anything a surviving CLOSURE evidence pointer references — `## Validations` or
  `## Dispositions`, no exception. Cross-check every candidate path against those
  pointers before deleting; when in doubt, keep.
- DELETE the rest, once unreferenced: this release's consumed coordination handoffs
  (ack-on-consume already deletes most as they are read — the rule is canonical at
  `dadaia-handoff-emitter`, not restated here; this sweep catches only what per-consume
  deletion missed), report/handoff artifacts superseded by `CLOSURE.md` itself, and tmp
  captures scoped to this release.
- **Lane guard (AG.1, stated verbatim — inherited by every deletion lane in this
  release):** resolve the target, refuse any resolved target outside `.dadaia/`, never
  follow a symlinked directory.

Record what was swept in `CLOSURE.md`'s `## Artifact GC sweep` table (kept/deleted
counts per artifact class, with evidence).

## §4 — Test dispositions (feeds step 9's CLOSURE table)

Demotion — replacing a LARGE test with equivalent cheaper coverage — and the
quarantine/SCAFFOLD expiry sweep are closure-time work, per `dadaia-test-stewardship`
§D/§E. The closer **records** each disposition in `CLOSURE.md`'s `## Test dispositions`
table; it never authors the replacement test itself (that stays `software-engineer` /
`qa-engineer`, executing a `qa-engineer` verdict).

## §5 — Out of scope for closure

- Writing source code, tests, or pipelines (other agents). The closer **records** test
  dispositions — it never authors a test.
- Modifying `specs/constitution.md` (requires explicit operator approval).
- Memory updates happen in the CLOSURE phase, or the DEFINITION phase under its own §13
  authorization (not this closure flow). Memory edits by any other agent, or in any
  other phase, are gate-blocked.
- Re-opening an archived release. Once archived, a new release supersedes it.

## §6 — Segments (ADR-1/ADR-5)

When the active release carries a `segment:` in `ACTIVE.md` (schema v2), each segment
closes independently: write `specs/releases/<release-id>/<segment>/CLOSURE.md` for that
segment. Per ADR-3, qa-only gates an `alpha-N` (commit, no closure/ship), and the full
trio + release `CLOSURE.md` + archive happen at the shipping `rc-N` — the final-rc steps
of `SKILL.md`'s arc (steps 8–12). Flat releases are unchanged.
