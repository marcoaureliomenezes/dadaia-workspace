# specs/backlog/ — Backlog Rules

Scope: this file governs only `specs/backlog/`. It replaces the retired
`backlog/README.md` (v6 canon, FR1) — its content lives here now.

The backlog is a **live photo**: `specs/backlog/BACKLOG.md` holds one section,
`## ACTIVE`, and nothing else (v0.5.0 FR5). There is no per-entry file per backlog item
— every live candidate or idea is one `### <slug>` subsection (ADR #14; full schema:
`dd-backlog-definition` §2). A closed item's history lives beside the document, in
`specs/backlog/_archive/backlog_histo.jsonl`, never in a second in-file section.

## The document, plus its histo

- **`## ACTIVE`** (in `BACKLOG.md`) — one `### <slug>` subsection per live candidate or
  idea. The document's ONLY top-level section.
- **`backlog_histo.jsonl`** (in `specs/backlog/_archive/`) — one append-only record per
  closed item: `{id, ts, disposition, reason, release, by, entry_md, entry_md_source}`.
  `id` is the slug; `entry_md` is the exited subsection's own source text.

An item's whole life is `ACTIVE` → one histo record. It never leaves the document by any
other route, and it never lives ACTIVE while also carrying a histo record — with one
record per slug, ever, a duplicate exit is structurally impossible (the retired in-file
`## LEDGER` duplicate-line failure mode this shape replaces).

## Authoring Rules

- Create and append entries with `dadaia backlog new <slug>` — do NOT hand-edit
  `BACKLOG.md` to add an entry, so the subsection stays canonical. `<slug>` matches
  `^[a-z][a-z0-9-]+$`.
- Every `### <slug>` ACTIVE subsection carries five required bullet keys:
  - `**Title:**` — short human-readable name
  - `**Opened:**` — ISO date (`YYYY-MM-DD`)
  - `**Status:**` — `idea`, `candidate`, `picked`, or another live (non-terminal) token
  - `**Description:**` — one-paragraph description of the need
  - `**Provenance:**` — operator request, or `intake-report item <id> (approved <date>)`
- Plus one **optional** key, `**Intents:**` (see below).
- Backlog entries are **not** specs. They do not authorise implementation. An entry must
  be picked into a release (via `dadaia release new`, naming the slug under
  `**Consumes:**`) to enter the SDD lifecycle.
- **Never delete an entry.** A closed item's ACTIVE subsection is removed and one record
  carrying its terminal disposition token is appended to `backlog_histo.jsonl` in the
  same act — it is never lost, and `backlog_histo.jsonl` itself is append-only, never
  edited or truncated.

## Terminal disposition tokens

A histo record carries exactly one of six canonical tokens (canonical home:
`dd-backlog-definition` §2): `DELIVERED`, `SUPERSEDED`, `RESOLVED`, `CONSUMED`,
`DEFERRED`, `REJECTED`. `DELIVERED`/`SUPERSEDED`/`RESOLVED`/`CONSUMED` carry the release
id in the `release` field; `DEFERRED`/`REJECTED` carry a one-line reason in the `reason`
field instead. A provisional `CONSUMED` (picked at definition, release still in
progress) is rewritten IN PLACE to its terminal token at closure — never a second
record for the same slug (BL-DUP is structurally impossible under this shape).

## Idea-stage freedom vs bound intents

An entry's `**Status:**` gates how much structure `dadaia backlog doctor` requires:

- **`idea`** — an unbound brainstorm. **No `**Intents:**` block is required.** A freshly
  authored subsection is born here and is `backlog doctor`-clean with no further edits.
- **`candidate` and beyond** — the subsection must carry a typed **`**Intents:**`** block
  (a fenced ` ```yaml ` code span), and every subject must resolve to a canonical anchor.
  `backlog doctor` raises `BL-SCHEMA` otherwise. (A malformed `**Intents:**` block and an
  invalid `**Status:**` are always `BL-SCHEMA`, at any status.)

An `**Intents:**` block binds each proposed change to a typed subject anchor. Shown here
as it appears inside a `### <slug>` subsection body:

````markdown
- **Intents:**
```yaml
- subject:
    kind: code
    ref: dadaia_workspace/core/models/lifecycle.py#AgentRuntimeKind
  change: what changes about this subject
```
````

### The five subject kinds

| kind        | ref shape                          | derived from |
|-------------|-------------------------------------|--------------|
| `code`      | `path/to/module.py#Symbol`         | Python sources (auto-derived) |
| `cli`       | `dadaia <command>`                 | the CLI command tree |
| `catalog`   | a `catalog.json` feature slug      | `specs/memory/product/catalog.json` |
| `doc`       | a SPEC-DOC id or memory heading    | `specs/memory/**/*.md` |
| `invariant` | an `INV-*` identifier              | invariant declarations |

Discover the bindable anchors for this repo with:

```bash
dadaia backlog subjects            # list canonical anchors (optionally --kind <kind>)
dadaia backlog subjects --resolve <ref> --kind <kind>   # preview how one subject resolves
```

### Non-Python repos

`code` anchors are derived from **Python sources only**. In a repo with no Python (e.g. a
JavaScript/TypeScript project), there are no `code` anchors — bind `catalog`, `doc`, or
`invariant` anchors instead. Use `dadaia backlog subjects` to see what is bindable.

## Relationship to Releases

A release SPEC names a picked entry's slug under `**Consumes:**`. The entry stays
`## ACTIVE` (typically flipped to `status: picked`) until the release closes, at which
point the disposition sweep exits it: the ACTIVE subsection is removed and its terminal
histo record is appended (or a provisional `CONSUMED` record is rewritten in place).
