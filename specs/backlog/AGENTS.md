# specs/backlog/ — Backlog Rules

Scope: this file governs only `specs/backlog/`.

- `BACKLOG_PY` is `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py` — the only verb that writes this ledger; it never moves a status after `new`.
- Create and append entries with `BACKLOG_PY new <slug>`.
- The backlog is the operator's demand queue: only the operator creates demand, `dd-product-engineer` curates `active[]`.
- An entry materializes only through the main thread's operator-facing intake report; an operator-ratified in-release deferral already counts as intake.
- The backlog is a single JSON document: `specs/backlog/BACKLOG.json`, `{schema: "backlog-v1", active: [...]}`.
- Full schema: `dd-backlog-definition` (The document), `.dadaia/agentic/schemas/backlog/backlog-v1.schema.json`.
- A closed item's history lives beside the document, in `specs/backlog/_archive/backlog_histo.jsonl`.

## 1. The document, plus its histo

- Fields: `{id, ts, disposition, release, reason, summary, entry}`.
- One record per slug, ever — a duplicate exit is structurally impossible.

## 2. Authoring rules

- `<slug>` matches `^[a-z][a-z0-9-]+$`.
- Every `active[]` entry carries five required fields: `title`, `opened` (`YYYY-MM-DD`), `status`, `description`, `provenance`.
- `BACKLOG_PY new` writes `status: idea`; a later lowercase live token (`candidate`, …) is a hand edit, which `BACKLOG_PY check` validates: no terminal status on a live entry, and a status past `idea` binds `intents[]`.
- Optional: `intents` (§4) and `relates` (`BACKLOG_PY new --help`).
- An entry leaves only by `BACKLOG_PY exit <slug> --disposition …`, which removes the `active[]` object and appends its one histo record.

## 3. Terminal disposition tokens

- An entry exits with one disposition of the vocabulary `BACKLOG_PY exit --help` lists: a delivery or supersession carries the release id in `release`, a rejection a one-line `reason`, a `to-bug` the id of its `BUGS.jsonl` record in `reason` — registration and exit share one `backlog` worktree.
- A postponed item stays in `active[]` with its status unchanged — it never exits.

## 4. Idea-stage freedom vs bound intents

- `idea` — an unbound brainstorm; no `intents` array required; doctor-clean with no further edits.
- `candidate` and beyond — the entry must carry a typed `intents[]` array; every subject must resolve to a canonical anchor.
- `BACKLOG_PY check` (`LEDGER-BACKLOG-SCHEMA`) refuses a malformed `intents[]`, an invalid `status` or an entry past `idea` with no `intents[]`.

```json
{"subject": {"kind": "code", "ref": "src/billing/models.py#Invoice"},
 "change": "what changes about this subject"}
```

### 4.1 The subject kinds

| kind | ref shape | derived from |
|---|---|---|
| `code` | `path/to/file[#word]`, any language | the repo's git paths; `#word` must occur in the file |
| `catalog` | a `catalog.json` feature slug | `specs/memory/product/catalog.json` |
| `doc` | a SPEC-DOC id or memory heading | `specs/memory/**/*.md` |
| `invariant` | an `INV-*` identifier | `INV-*` ids in `specs/memory/**/*.md` |

- Every ref is judged only by the doctor's `BL-SCHEMA`, which names the ref it cannot resolve.

## 5. Relationship to releases

- The pick is the SPEC's `**Origin:** backlog:<ids>` line; no status is written at pick time.
- `exit --disposition delivered --release <id>` is refused unless that SPEC's Origin names the slug.
- It exits once, at closure's disposition sweep, into `_archive/backlog_histo.jsonl`.
