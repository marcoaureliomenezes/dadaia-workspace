# CLOSURE-TEMPLATE — dd-release-implement (final-rc closure only)

Disclosed reference reached only at step 9 of `SKILL.md`'s arc — the final-rc closure,
after the trio (`qa-engineer` + `code-reviewer` + `security-reviewer`) has `APPROVE`d the
same commit. `product-engineer` copies this template to
`specs/releases/<release-id>/CLOSURE.md` and fills every section; a section left as its
placeholder is not filled. The procedural rules behind `## Dispositions` and
`## Artifact GC sweep` live in `CLOSURE-CHECKS.md` — this file is the shape only.

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
- `specs/memory/product/<area>/<slug>.md` — <one-liner per feature page updated>
- `specs/memory/architecture.md` — <one-liner>
- `specs/memory/tech-stack.md` — <one-liner or "no change: reason">

## Dispositions

Disposition-sweep ledger (mandatory — rule and CONSUMED→DELIVERED update discipline:
`CLOSURE-CHECKS.md` §2). One row per backlog item and bug picked into (or superseded by)
this release. A backlog disposition is **never** a per-entry file — it adds a
`## LEDGER` line to `BACKLOG.md` and drops the slug's `## ACTIVE` subsection, in the
same commit (`dd-backlog-definition`).

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
evidence pointers are final, before the archive move. Keep/delete rule:
`CLOSURE-CHECKS.md` §3 — referenced, not restated. Nothing a surviving row above
references may appear in the deleted column.

| Artifact class | Kept (still referenced) | Deleted/archived | Evidence |
|----------------|--------------------------|-------------------|----------|
| `.dadaia/handoff/<context>/*.handoff.json` (this release) | `<n>` | `<n>` | `<CLOSURE section \| commit sha>` |
| `.dadaia/reports/<context>/**` (this release) | `<n>` | `<n>` | `<CLOSURE section \| commit sha>` |
| `.dadaia/tmp/<agent>/**` (this release's captures) | `<n>` | `<n>` | `<CLOSURE section \| commit sha>` |

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/<release-id>/` via
`git mv`. ACTIVE.md will be updated to point to the next release or `release: none`.

(Alternative: `KEEP` — leave the release in `specs/releases/` only if explicitly justified
by the operator. Should be rare.)
```
