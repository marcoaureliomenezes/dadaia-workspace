# specs/backlog/ — Backlog Rules

Scope: this file governs only `specs/backlog/`. It replaces the retired
`backlog/README.md` (v6 canon, FR1) — its content lives here now.

The backlog is a **live photo**: `specs/backlog/BACKLOG.json` is one JSON document,
`{"schema": "backlog-v1", "active": [...]}` (operator ruling 2026-08-28 — the retired
`BACKLOG.md` Markdown grammar, `## ACTIVE` with `### <slug>` subsections plus a fenced
` ```yaml ` `**Intents:**` block, is DELETED, not kept as a fallback; schema:
`public/schemas/backlog/backlog-v1.schema.json`). There is no per-entry file per backlog
item — every live candidate or idea is one object in the `active` array (full schema:
`dd-backlog-definition` §2). A closed item's history lives beside the document, in
`specs/backlog/_archive/backlog_histo.jsonl`, never folded back into `BACKLOG.json`.

## The document, plus its histo

- **`active`** (array, in `BACKLOG.json`) — one JSON object per live candidate or idea.
  The document's ONLY array.
- **`backlog_histo.jsonl`** (in `specs/backlog/_archive/`) — one append-only record per
  closed item: `{id, ts, disposition, reason, release, by, entry_md, entry_md_source}`.
  `id` is the slug; `entry_md` is the exited entry's own snapshot, as pretty-printed
  JSON text.

An item's whole life is `active` → one histo record. It never leaves the document by any
other route, and it never lives in `active` while also carrying a histo record — with one
record per slug, ever, a duplicate exit is structurally impossible (BL-DUP, deleted not
disabled — v0.5.0 A5.2, unchanged by the Markdown-to-JSON migration: folding the mutable
`active` array and the immutable append-only histo ledger back into one rewritten-in-place
document would resurrect exactly the failure mode this shape retired).

## Authoring Rules

- Create and append entries with `dadaia backlog new <slug>` — do NOT hand-edit
  `BACKLOG.json` to add an entry, so the entry stays canonical (and the document stays
  valid JSON). `<slug>` matches `^[a-z][a-z0-9-]+$`.
- Every `active[]` entry carries six required keys:
  - `id` — the slug (unique within `active`; BL-SCHEMA fires on a duplicate)
  - `title` — short human-readable name
  - `opened` — ISO date (`YYYY-MM-DD`)
  - `status` — `idea`, `candidate`, `picked`, or another live (non-terminal) token
  - `description` — one-paragraph description of the need
  - `provenance` — operator request, or `intake-report item <id> (approved <date>)`
- Plus one **optional** key, `intents` (see below).
- Backlog entries are **not** specs. They do not authorise implementation. An entry must
  be picked into a release (via `dadaia release new`, naming the slug under
  `**Consumes:**`) to enter the SDD lifecycle.
- **Never delete an entry.** A closed item's `active[]` entry is removed and one record
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

An entry's `status` gates how much structure `dadaia backlog doctor` requires:

- **`idea`** — an unbound brainstorm. **No `intents` array is required.** A freshly
  authored entry is born here and is `backlog doctor`-clean with no further edits.
- **`candidate` and beyond** — the entry must carry a typed **`intents`** array, and
  every subject must resolve to a canonical anchor. `backlog doctor` raises `BL-SCHEMA`
  otherwise. (A malformed `intents` value and an invalid `status` are always
  `BL-SCHEMA`, at any status.)

An `intents` array binds each proposed change to a typed subject anchor. Shown here as
it appears inside an `active[]` entry:

```json
{
  "intents": [
    {
      "subject": {
        "kind": "code",
        "ref": "dadaia_workspace/core/models/lifecycle.py#AgentRuntimeKind"
      },
      "change": "what changes about this subject"
    }
  ]
}
```

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

A release SPEC names a picked entry's slug under `**Consumes:**`. The entry stays in
`active` (typically flipped to `status: "picked"`) until the release closes, at which
point the disposition sweep exits it: the `active[]` entry is removed and its terminal
histo record is appended (or a provisional `CONSUMED` record is rewritten in place).
