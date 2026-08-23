---
name: dd-backlog-definition
description: "Use when: curating specs/backlog/**, sanitizing for staleness, adjudicating an intake report, or checking the terminal disposition-token vocabulary. Owns the BACKLOG.md ACTIVE/LEDGER schema and the operator-gated intake gate — the only path to a new backlog entry. project-manager runs this continuously."
applyTo: "specs/backlog/**"
---

# dd-backlog-definition

> **Not a hook-enforced mechanism.** No engine curates the backlog. `project-manager`
> runs this protocol continuously; this skill is its authoritative source.

## 1. When to invoke

`project-manager`, continuously — not a release-boundary event. Any time a backlog file
is touched, an intake report is compiled, or a release-definition session needs the
picked, sanitized set.

## 2. Entry schema and status vocabulary

Single source: `specs/backlog/BACKLOG.md` (ADR #14) — two sections, no per-entry files,
no JSONL (JSONL stays bugs-only; backlog is a re-consolidated document, not an
append log).

**`## ACTIVE`** — one subsection per live candidate, full prose, strict schema — five
required keys plus one optional key:

````markdown
### <slug>
- **Title:** <short name>
- **Opened:** YYYY-MM-DD
- **Status:** idea | candidate | deferred
- **Description:** <one paragraph — the need>
- **Provenance:** operator request | intake-report item <id> (approved <date>)
- **Intents:**
```yaml
<typed intents[] block — see core.models.backlog.parse_intents>
```
````

**`**Intents:**` status gate (ADR D7, OD-1).** Optional at `status: idea`
(`core.models.backlog.INTENTS_EXEMPT_STATUS`) — an idea is an unbound brainstorm.
**Required** at `candidate` and beyond: the anchor-set binding through
`subject_registry.py`/`classifier.py` is how BL-DUP and BL-CONFLICT resolve pairwise
overlap, so a `candidate`+ item with no resolvable `intents[]` is a BL-SCHEMA error, not
a warning.

**`## LEDGER`** — one line per closed item: `<slug> · <disposition> · <release-or-reason>
· <date>`.

`dadaia backlog new <slug>` authors the `## ACTIVE` subsection directly into
`BACKLOG.md` (creating the document with both section headings on first use);
`dadaia backlog doctor` validates the whole file against this schema —
`BL-SCHEMA`/`BL-DUP`/`BL-CONFLICT`/`BL-STALE` (the disposition tokens below are
BL-STALE's terminal-state input). There is no per-entry file and no other schema
authority.

**Terminal disposition tokens** (canonical home — appears nowhere else in `public/`):

| Kind | Terminal tokens |
|---|---|
| Backlog (`BACKLOG.md` LEDGER) | `DELIVERED`, `SUPERSEDED`, `RESOLVED`, `CONSUMED`, `DEFERRED`, `REJECTED` |
| Bug (`specs/bugs/**`) | `Closed` |

`DELIVERED`/`SUPERSEDED`/`RESOLVED`/`CONSUMED` carry the release id (`DELIVERED —
v0.10.0`); `DEFERRED`/`REJECTED` carry a one-line reason. `dd-release-implement` and
`dd-audit-project` route their dispositions to these tokens by reference — this table
is not repeated in either.

**Purge-on-pick (mandatory).** A picked entry leaves `ACTIVE` in the same commit that
creates the release SPEC; the SPEC's provenance section records which entries it
consumed. Leaving a picked entry in `ACTIVE` after its SPEC exists is a defect.

## 3. Continuous sanitize protocol

Run on every touch, not just at pick time:

1. **Staleness scan.** An `ACTIVE` item with no reads/updates past a reasonable window,
   or a bug whose symptom no longer reproduces, is a sanitize candidate.
2. **Dedup scan.** Before adding any entry, compare its title + description against
   every `ACTIVE` subsection for the same subject under different wording (near-duplicate
   normalized text, not just exact match). A match is merged into the existing entry,
   never filed twice.
3. **Disposition or keep.** Confirmed-stale or invalid → `DEFERRED`/`REJECTED` with a
   one-line reason, moved to `LEDGER`. Still valid → stays in `ACTIVE`.
4. **Total-consolidation review.** Every new entry triggers a read of the whole file —
   `BACKLOG.md` is small enough that partial review is a discipline failure, not a
   shortcut.

`dd-release-definition` references step 1 of its own protocol here instead of
restating this scan.

## 4. Never-delete (cited, not restated)

No backlog file or bug is ever deleted — `DADAIA.md` §6 Backlog. A dead item moves
`ACTIVE` → `LEDGER`; it never leaves the tree.

## 5. Operator-gated intake (ADR #15 — the only path to a new entry)

**The doctrine.** The backlog is the **operator's demand queue**. Only the operator
creates demand. No agent — `project-manager` included — writes a technical residual (a
review finding, a CLOSURE return, a reviewer note, an audit observation) directly into
`BACKLOG.md`. At each release close and each review round, the PM **compiles residuals
into an intake report** and presents it to the operator; each item is approved, rejected
or discarded **before** it can become an `ACTIVE` entry.

**Pre-approved intake.** An operator-ratified deferral taken during a release ("defer to
backlog", recorded in the SPEC or at approval) is already-approved intake and is **not**
re-adjudicated through a later intake report. `dd-audit-project` and `dd-release-implement`
apply this carve-out when they route a disposition — this is its one full statement.

**Record-only vs actionable (FR6/R4).** Reviews record everything — never-silent holds,
zero observations lost. But not every recorded observation is a residual: **record-only**
observations (INFO-grade, awareness-only, already-fixed-at-HEAD) terminate in the
release CLOSURE record or the reviewer's own handoff and **never** enter an intake
report. Only **actionable defects** (LOW+ with a concrete fix surface) are compiled into
the operator-facing intake report — "each item" above means each actionable defect, not
every observation a reviewer recorded.

**The intake report artifact.** No new artifact class: it is the existing handoff-first
shape (`DADAIA.md` §5 (handoff-first)) — a JSON handoff with `next_handoff.agent:
"human"`, plus the HTML
report it points at, at `.dadaia/reports/<context>/project-manager/<UTC>-intake.html`.

An agent reading only this section knows: it may not create a backlog entry itself; a
discovered residual goes into the compiled intake report instead; and an
operator-ratified deferral is the one exception that skips re-adjudication.

## 6. Picked-set handoff to `dd-release-definition`

Release-definition step 2 ("pick the set") reads `BACKLOG.md`'s `ACTIVE` section plus
`specs/bugs/*.jsonl` directly — this skill supplies a sanitized, deduplicated set with no
further triage needed on the release-definition side. Purge-on-pick (§2) is the receipt.

## 7. CLI reference

```bash
dadaia backlog new <slug>          # appends an ## ACTIVE subsection to BACKLOG.md
dadaia backlog doctor              # validates BACKLOG.md — BL-SCHEMA/DUP/CONFLICT/STALE
dadaia bugs status                 # open/closed bug counts
dadaia bugs stats                  # bug-ledger aggregate view
```
