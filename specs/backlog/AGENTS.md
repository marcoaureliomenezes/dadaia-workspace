# specs/backlog/ — Backlog Rules

Scope: this file governs only `specs/backlog/`. Replaces the retired `backlog/README.md` (v6 canon, FR1).

- The backlog is a single JSON document: `specs/backlog/BACKLOG.json`, `{schema: "backlog-v1", active: [...]}`.
- No per-entry file per backlog item — every live candidate/idea is one `active[]` object (ADR #14).
- Full schema: `dd-backlog-definition` §2, `schemas/backlog/backlog-v1.schema.json`.
- A closed item's history lives beside the document, in `specs/backlog/_archive/backlog_histo.jsonl`.

## 1. The document, plus its histo

- `active[]` (in `BACKLOG.json`) — one object per live candidate or idea, the document's only array.
- `backlog_histo.jsonl` (in `_archive/`) — one append-only record per closed item.
- Fields: `{id, ts, disposition, reason, release, by, entry_md, entry_md_source}`.
- An item's whole life is `active[]` -> one histo record; it never lives in both places at once.
- One record per slug, ever — a duplicate exit is structurally impossible.

## 2. Authoring rules

- Create and append entries with `dadaia backlog new <slug>` — never hand-edit `BACKLOG.json`.
- `<slug>` matches `^[a-z][a-z0-9-]+$`.
- Every `active[]` entry carries five required fields: `title`, `opened` (`YYYY-MM-DD`), `status`, `description`, `provenance`.
- `status` is `idea`, `candidate`, `picked`, or another live (non-terminal) token.
- Plus one optional field: `intents` (see §4).
- Backlog entries are not specs — they do not authorize implementation on their own.
- An entry must be picked into a release (`dadaia release new`, naming the slug under `**Consumes:**`) to enter SDD.
- Never delete an entry — a closed item's `active[]` object is removed, one terminal-disposition record is appended, same act.

## 3. Terminal disposition tokens

- Canonical home: `dd-backlog-definition` §2 — six tokens: `DELIVERED`, `SUPERSEDED`, `RESOLVED`, `CONSUMED`, `DEFERRED`, `REJECTED`.
- `DELIVERED`/`SUPERSEDED`/`RESOLVED`/`CONSUMED` carry the release id in `release`.
- `DEFERRED`/`REJECTED` carry a one-line reason in `reason` instead.
- A provisional `CONSUMED` is rewritten in place to its terminal token at closure — never a second record for the same slug.

## 4. Idea-stage freedom vs bound intents

- `idea` — an unbound brainstorm; no `intents` array required; `backlog doctor`-clean with no further edits.
- `candidate` and beyond — the entry must carry a typed `intents[]` array; every subject must resolve to a canonical anchor.
- A malformed `intents[]` or an invalid `status` is always `BL-SCHEMA`, at any status.

```json
{"subject": {"kind": "code", "ref": "dadaia_workspace/core/models/lifecycle.py#AgentRuntimeKind"},
 "change": "what changes about this subject"}
```

### 4.1 The five subject kinds

| kind | ref shape | derived from |
|---|---|---|
| `code` | `path/to/module.py#Symbol` | Python sources (auto-derived) |
| `cli` | `dadaia <command>` | the CLI command tree |
| `catalog` | a `catalog.json` feature slug | `specs/memory/product/catalog.json` |
| `doc` | a SPEC-DOC id or memory heading | `specs/memory/**/*.md` |
| `invariant` | an `INV-*` identifier | invariant declarations |

```bash
dadaia backlog subjects            # list canonical anchors (optionally --kind <kind>)
dadaia backlog subjects --resolve <ref> --kind <kind>   # preview how one subject resolves
```

### 4.2 Non-Python repos

- `code` anchors derive from Python sources only.
- A repo with no Python has no `code` anchors — bind `catalog`, `doc`, or `invariant` anchors instead.
- Use `dadaia backlog subjects` to see what is bindable.

## 5. Relationship to releases

- A release SPEC names a picked entry's slug under `**Consumes:**`.
- The entry stays in `active[]` (typically flipped to `status: picked`) until the release closes.
- At closure, the disposition sweep exits it: `active[]` entry removed, terminal histo record appended or rewritten in place.
