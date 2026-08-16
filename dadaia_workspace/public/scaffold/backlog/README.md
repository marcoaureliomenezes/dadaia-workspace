# Backlog

The backlog is a **single document**: `specs/backlog/BACKLOG.md`. There is no per-entry
file per backlog item — everything lives in one of this document's two sections (ADR #14;
full schema: `dd-backlog-definition` §2).

## The two sections

- **`## ACTIVE`** — one `### <slug>` subsection per live candidate or idea.
- **`## LEDGER`** — one line per closed item, in the grammar `<slug> · <disposition> ·
  <release-or-reason> · <date>`.

An item's whole life is `ACTIVE` → `LEDGER`; it never leaves the document and it never
lives in both sections at once.

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
- **Never delete an entry.** A closed item moves from an `## ACTIVE` subsection to one
  `## LEDGER` line carrying its terminal disposition token — it is never removed from
  the document, and the file itself is never deleted.

## Terminal disposition tokens

`## LEDGER` records exactly one of six canonical tokens per closed item (canonical home:
`dd-backlog-definition` §2): `DELIVERED`, `SUPERSEDED`, `RESOLVED`, `CONSUMED`,
`DEFERRED`, `REJECTED`. `DELIVERED`/`SUPERSEDED`/`RESOLVED`/`CONSUMED` carry the release
id (`<slug> · DELIVERED · v0.10.0 · 2026-06-01`); `DEFERRED`/`REJECTED` carry a one-line
reason in the release-or-reason field instead.

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
point the disposition sweep moves it to `## LEDGER` with its terminal token.
