# Backlog

This directory contains backlog entry files for this Spec Context Project.

## Authoring Rules

- Each backlog entry is a single Markdown file named `<slug>.md` where `<slug>` matches
  `^[a-z][a-z0-9-]+$`.
- Files are created with `dadaia backlog new <slug>` — do NOT create them manually, so the
  frontmatter stays canonical.
- Required frontmatter fields:
  - `title`: short human-readable name
  - `status`: one of `idea`, `candidate`, `deferred`, `rejected`
  - `opened`: ISO date (YYYY-MM-DD)
  - `description`: one-paragraph description of the need
- Backlog entries are **not** specs. They do not authorise implementation. An entry must be
  promoted to a release (via `dadaia release new`) to enter the SDD lifecycle.
- Never delete backlog entries — change `status` to `rejected` or `deferred` instead.

## Idea-stage freedom vs bound intents

An entry's `status` gates how much structure `dadaia backlog doctor` requires:

- **`status: idea`** — an unbound brainstorm. **No `intents[]` are required.** A freshly
  scaffolded stub is born here and is `backlog doctor`-clean with no further edits.
- **`status: candidate` and beyond** — the entry must carry a typed **`intents[]`** frontmatter
  block, and every subject must resolve to a canonical anchor. `backlog doctor` raises
  `BL-SCHEMA` otherwise. (A malformed `intents:` block and an invalid `status` are always
  `BL-SCHEMA`, at any status.)

An `intents[]` block binds each proposed change to a typed subject anchor:

```yaml
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/core/models/lifecycle.py#AgentRuntimeKind
    change: what changes about this subject
```

### The five subject kinds

| kind        | ref shape                          | derived from |
|-------------|------------------------------------|--------------|
| `code`      | `path/to/module.py#Symbol`         | Python sources (auto-derived) |
| `cli`       | `dadaia <command>`                 | the CLI command tree |
| `catalog`   | a `catalog.json` feature slug      | `specs/memory/product/catalog.json` |
| `doc`       | a SPEC-DOC id or memory heading    | `specs/memory/**/*.md` |
| `invariant` | an `INV-*` identifier              | invariant declarations |

Discover the bindable anchors for this repo with:

```bash
dadaia backlog subjects            # list canonical anchors (optionally --kind <kind>)
dadaia backlog subjects <ref> --kind <kind>   # preview how one subject resolves
```

### Non-Python repos

`code` anchors are derived from **Python sources only**. In a repo with no Python (e.g. a
JavaScript/TypeScript project), there are no `code` anchors — bind `catalog`, `doc`, or
`invariant` anchors instead. Use `dadaia backlog subjects` to see what is bindable.

## Relationship to Releases

A backlog entry may be referenced by a release SPEC using its slug. When a release is opened to
address a backlog item, add `release: <release-id>` to the backlog entry's frontmatter to track
the promotion.
