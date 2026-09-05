# CONTEXT.md Format

Disclosed reference of [`SKILL.md`](SKILL.md): the bounded-context glossary file's
structure. Adapted from the reference corpus (`mattpocock/skills`,
`engineering/domain-modeling`).

## Structure

```md
# {Context Name}

{One or two sentence description of what this context is and why it exists.}

## Language

**Candidate**:
{A one or two sentence definition of the term.}
_Avoid_: release-candidate build, rc build

**Presence**:
The advisory record a session leaves when it writes, surfaced to other sessions.
_Avoid_: lock, lease
```

## Rules

- **Be opinionated.** When multiple words exist for one concept, pick the best and
  list the others under `_Avoid_`.
- **Keep definitions tight.** One or two sentences max; define what it IS, not what
  it does.
- **Only project-specific terms.** General programming concepts (timeouts, error
  types, utility patterns) stay out even when heavily used. Before adding: is this
  unique to this context, or general? Only the former belongs.
- **Group under subheadings** when natural clusters emerge; a flat list is fine for
  one cohesive area.
- **A `§Homonyms` section** carries terms with more than one live sense: each entry
  names every sense and the qualifier that disambiguates it in prose.
- **No implementation details.** The glossary is not a spec, a scratch pad, or a
  decision store — decisions go to `specs/ADRs/decisions.jsonl`, product truth to
  `specs/memory/`.

## Single vs multi-context repos

- **Single context (most repos):** one `CONTEXT.md` at the repo root.
- **Multiple contexts:** a root `CONTEXT-MAP.md` lists each context, where its
  `CONTEXT.md` lives, and the relationships between contexts (events consumed,
  shared types).
- Neither file exists yet: create a root `CONTEXT.md` lazily when the first term is
  resolved.
