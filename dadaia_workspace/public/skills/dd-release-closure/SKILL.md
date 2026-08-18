---
name: dd-release-closure
description: "Use when: closing a release that has all TASKS marked [x] DONE. Defines the CLOSURE.md template, the memory Markdown update protocol, the evidence-triple validation format, the disposition sweep, and the move-to-archive command. Only product-engineer invokes this skill, and only in the CLOSURE phase."
applyTo: "specs/releases/*/CLOSURE.md"
---

# dd-release-closure

> **Not a hook-enforced mechanism.** There is no workflow engine that runs the closure
> sequence or its gates. `product-engineer` drives every step of this protocol directly.
> This skill is the authoritative protocol for that flow.

## When to invoke

After every task in `specs/releases/<release-id>/TASKS.md` is marked `[x] DONE` and
implementation is verified. Set `specs/releases/ACTIVE.md` phase to `CLOSURE` **before**
writing CLOSURE.md or memory Markdown — gate v3 allows memory writes in the DEFINITION and CLOSURE phases (this skill operates in CLOSURE).

**Order (D8/FR5): review → closure → archive → ship.** The pre-PR six-axis code review
of the delta runs on the thawed tree, before the `git mv` archive step — never after;
only ship steps (merge to `develop`, diff security review, push, PR to `main`) follow
archive. `dd-release-implement` §4 states the same order.

**Finalization order: memory → CLOSURE → sweep → archive**, in one commit on `develop`
that rides the next push (the branch/commit mechanics are the `dadaia-gitflow` skill's
contract): with the code review already `APPROVE`d, update the memory atoms first, write
`CLOSURE.md` next (it records which atoms changed and finalizes its evidence pointers),
run the artifact GC sweep (below) once those pointers are final, then move the release
directory to `_archive/` last.

## CLOSURE.md template

```markdown
# Closure: Release — <release-id>

> **Status:** Aprovado
> **Release ID:** <release-id>
> **Owner:** product-engineer
> **Closed:** <YYYY-MM-DD>

## Summary

<1–3 paragraphs describing what shipped, from the product owner's perspective. No
implementation detail.>

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-X.Y | <one-liner> | `<sha>` |
| ...   | ...         | ...    |

## Validations

Each validation is a triple: description, command, evidence. Evidence MUST be one of:
commit SHA, stdout snippet (in fenced code), or path to a report HTML under
`.dadaia/reports/<context>/`.

| Description | Command | Evidence |
|-------------|---------|----------|
| <what was validated> | `<command>` | `<sha\|snippet\|path>` |
| ...                  | ...         | ...                  |

## Size accounting

**Mandatory** (FR21b/A21.4). Production-code size and complexity delta for this release,
measured — never estimated. Ceilings ratchet only downward; a decrease is justified here.

| Metric | Value |
|--------|-------|
| Production LOC added | `<n>` |
| Production LOC deleted | `<n>` |
| Production LOC net | `<+n \| -n>` |

**Three largest additions by file:**

| File | LOC added |
|------|-----------|
| `<path>` | `<n>` |
| `<path>` | `<n>` |
| `<path>` | `<n>` |

**Three largest deletions by file:**

| File | LOC deleted |
|------|-------------|
| `<path>` | `<n>` |
| `<path>` | `<n>` |
| `<path>` | `<n>` |

| Ceiling | Before | After | Justification (only if decreased) |
|---------|--------|-------|------------------------------------|
| `C90` (`max-complexity`) | `<n>` | `<n>` | `<reason \| n/a — unchanged or increased-refused>` |
| `PLR1702` (`max-nested-blocks`) | `<n>` | `<n>` | `<reason \| n/a — unchanged or increased-refused>` |

**Nesting-violation count:** `<n>` (against the pinned `PLR1702` ceiling).

Law: ceilings ratchet only downward; a decrease is justified in CLOSURE.

## Drifts

For every place where reality diverged from PLAN.md during implementation, document it:

### <slug-of-drift>

**Description:** What happened? Why did the plan need to bend?

**Resolution:** How was it resolved? What was the trade-off?

**Memory updates:** Which `specs/memory/*.md` files needed adjustment because of this
drift?

### <another-drift>

...

## Memory updates

Explicit list of memory files written during this CLOSURE phase. If a memory file was not
updated, state the reason here (e.g. "memory/tech-stack.md: no change — release did not
touch dependencies").

- `specs/memory/product/index.md` — <one-liner of what changed in the catalog>
- `specs/memory/product/<slug>.md` — <one-liner per feature page updated>
- `specs/memory/architecture.md` — <one-liner>
- `specs/memory/tech-stack.md` — <one-liner or "no change: reason">

## Dispositions

Disposition-sweep ledger (mandatory — see "Disposition sweep" below). One row per
backlog item and bug picked into (or superseded by) this release. A backlog disposition
is **never** a per-entry file — it adds a `## LEDGER` line to `BACKLOG.md` and drops the
slug's `## ACTIVE` subsection, in the same commit (`sdd-bug-backlog-governance`).

| Record | Kind | Terminal disposition | Evidence |
|--------|------|-----------------------|----------|
| `specs/bugs/*.jsonl` (bug-id `<slug>`) | bug | `Closed` | `<CLOSURE section \| commit sha>` |
| `specs/backlog/BACKLOG.md` (`<slug>` — adds a `## LEDGER` line, drops the `## ACTIVE` subsection) | backlog | `<terminal token — dd-backlog-definition §2>` | `<CLOSURE section \| commit sha>` |
| ... | ... | ... | ... |

## Test dispositions

Demotion map (S-15) and the quarantine/SCAFFOLD expiry sweep, per `dadaia-test-stewardship`.
Every LARGE test demoted or deleted during this release, and every quarantine/SCAFFOLD that
expired, is a row here — the closer **records** the disposition, it does not author the
replacement test.

| Kind | Deleted/expired test | Replacement / disposition | Evidence |
|------|----------------------|----------------------------|----------|
| demotion | `tests/e2e/<file>::<test>` | `tests/{unit,contract,integration}/<file>:<line>` or "kept as SENTINEL" | `<CLOSURE section \| commit sha>` |
| quarantine expiry | `tests/<path>::<test>` | `disabled` / `restored` / `deleted` | `<bug-id \| commit sha>` |
| SCAFFOLD expiry | `tests/<path>::<test>` | `deleted` / `promoted to CONTRACT` | `<commit sha>` |
| ... | ... | ... | ... |

## Record-only observations

INFO-grade, awareness-only, or already-fixed-at-HEAD observations from this release's
reviews and audits. Never-silent still held — each was recorded in its reviewer's own
findings array or handoff — but a record-only observation carries no actionable fix
surface, so it **terminates here** and never enters the PM's intake report (FR6/R4).

| Source (reviewer/handoff) | Observation | Why record-only |
|---|---|---|
| `<agent>` `<ts>` handoff | <one-liner> | INFO-grade / awareness-only / already-fixed-at-HEAD |
| ... | ... | ... |

## Intake candidates

Residuals discovered during implementation that did not fit this release's scope, plus
every **actionable defect** (LOW+ with a concrete fix surface) surfaced by this
release's reviews — never a record-only observation (those stop in the section above).
The closer creates **no backlog entry** — ADR #15's operator-gated intake doctrine (full
statement: `dd-backlog-definition` §5) means every residual is only ever **listed**
here, for the PM to compile into its next operator-facing intake report. List each
residual under one of two headings:

- **To be adjudicated** — a residual with no prior operator ruling; the PM's intake
  report will present it for approval, rejection or discard.
- **Pre-approved intake** — an operator-ratified deferral taken *during this release*
  (recorded in its own SPEC or at approval); already-approved, not re-adjudicated by a
  later intake report.

## Artifact GC sweep

**Mandatory** (FR25/A25.1). Run after this CLOSURE's `## Validations`/`## Dispositions`
evidence pointers are final, before the archive move. Keep/delete rule: `dd-release-closure`'s
"Artifact GC sweep" section below — referenced, not restated. Nothing a surviving row
above references may appear in the deleted column.

| Artifact class | Kept (still referenced) | Deleted/archived | Evidence |
|----------------|--------------------------|-------------------|----------|
| `.dadaia/handoff/<context>/*.handoff.json` (this release) | `<n>` | `<n>` | `<CLOSURE section \| commit sha>` |
| `.dadaia/reports/<context>/**` (this release) | `<n>` | `<n>` | `<CLOSURE section \| commit sha>` |
| `.dadaia/tmp/<agent>/**` (this release's captures) | `<n>` | `<n>` | `<CLOSURE section \| commit sha>` |
| lifecycle run records (this release) | `<n>` | `<n>` | `<CLOSURE section \| commit sha>` |

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/<release-id>/` via
`git mv`. ACTIVE.md will be updated to point to the next release or `release: none`.

(Alternative: `KEEP` — leave the release in `specs/releases/` only if explicitly justified
by the operator. Should be rare.)
```

## Disposition sweep (mandatory)

Before archive, flip every backlog item and bug picked into (or superseded by) the
release to a terminal status token — vocabulary and format: `dd-backlog-definition` §2
(the canonical, single home of the terminal disposition-token table) — and record each
flip as a row in the CLOSURE `## Dispositions` table with an evidence pointer (CLOSURE
section or commit SHA). A release whose CLOSURE lacks the sweep is not closeable.

Never-delete law (`DADAIA.md` §5 (Backlog)): a bug or backlog file is **never deleted** —
always marked with a terminal token and a reason. A bug is never silently dropped:
either it is fixed (`Closed`) or a superseding backlog item covers its acceptance
(`Closed` + `superseded_by: <slug>`). Stale or invalid items are dispositioned
`DEFERRED` or `REJECTED` with a reason, never removed.

`dadaia specs doctor` backstops the sweep: SPEC-DOC-031 (FR14 semantics) WARNs when an
**archived** SPEC's `**Consumes:**` declaration or an **archived** CLOSURE's
`## Dispositions` rows name a still-non-terminal `ACTIVE` slug; SPEC-DOC-032 WARNs on a
bug `status:` outside the {`Open`, `Closed`} canon.

**Standing note.** Because SPEC-DOC-031 only counts archived-document assertions, this
closure's own `git mv` archive step adds one such WARN per non-terminal slug the
just-archived SPEC/CLOSURE names — the next closer captures the SPEC-DOC-031 count
**after** this closure's archive move, never before.

## Memory Markdown update protocol

1. **Verify gate phase.** Confirm `specs/releases/ACTIVE.md` phase = `CLOSURE` (memory
   writes are also allowed in `DEFINITION`). Otherwise the gate will block writes to
   `specs/memory/*.md`.

2. **Do not author legacy HTML memory.** If legacy HTML memory exists, treat it as
   read-only migration input. New memory writes are Markdown atoms.

3. **Update Markdown atoms.** Apply the release's deltas to the corresponding
   `specs/memory/*.md` or `specs/memory/product/*.md` files. Memory describes the
   product **as it is now** — not what changed. The change history lives in this
   CLOSURE.md and the archived release dir.

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

   If the operator asks for history, point to CLOSURE.md or `_archive/`.

6. **Validate** with `dadaia specs doctor` before moving to archive. Doctor checks
   atomicity, broken `<img>` references, and Mermaid script presence.

## Artifact GC sweep (FR25, mandatory)

Run once CLOSURE.md's `## Validations`/`## Dispositions` evidence pointers are final —
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
  deletion missed), report/handoff artifacts superseded by CLOSURE.md itself, tmp
  captures, and lifecycle run records scoped to this release.
- **Lane guard (AG.1, stated verbatim — inherited by every deletion lane in this
  release):** resolve the target, refuse any resolved target outside `.dadaia/`, never
  follow a symlinked directory.

Record what was swept in CLOSURE's `## Artifact GC sweep` table (kept/deleted counts per
artifact class, with evidence).

## Move-to-archive command

After CLOSURE.md is written, the disposition sweep is complete, memory is updated, and
`dadaia specs doctor` reports green:

```bash
git mv specs/releases/<release-id> specs/_archive/releases/<release-id>
# Edit specs/releases/ACTIVE.md to point at the next release or `release: none`
```

The git history preserves the release's evolution; archive is the human-browsable
snapshot.

## Out of scope for this skill

- Writing source code, tests, or pipelines (other agents). The closer **records** test
  dispositions (the `## Test dispositions` table above) — it never authors a test.
- Modifying `specs/constitution.md` (requires explicit operator approval).
- Memory updates via this skill happen in the CLOSURE phase only. (product-engineer
  may also write memory in the DEFINITION phase under a separate §13 authorization —
  that path is not this skill.) Memory edits by any other agent, or in any other phase,
  are gate-blocked.
- Re-opening an archived release. Once archived, a new release supersedes it.

## Segments (ADR-1/ADR-5)

When the active release carries a `segment:` in `ACTIVE.md` (schema v2), each segment closes independently: write `specs/releases/<release-id>/<segment>/CLOSURE.md` for that segment. Per ADR-3, qa-only gates an `alpha-N` (commit, no closure/ship), and the full trio + release CLOSURE + archive happen at the shipping `rc-N`. Flat releases are unchanged.
