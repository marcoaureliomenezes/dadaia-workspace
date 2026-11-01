# Positioning

Your product repositories never carry agent configuration. One law governs many
projects.

## The paradigm

Governance lives outside every repository: the root map, the scoped `AGENTS.md` files,
the skills, the personas and `.dadaia/`. The root map, `dadaia_workspace/public/data/AGENTS.md`,
states the folder layout and the one-folder, never-a-monorepo rule.

That inversion is the whole position. A repository is a repository: production source,
its own history, its own CI. What steers an agent (law, skills, personas, hooks, memory,
releases, backlog, bugs) is workspace state, not repository content.

## The unit is the context

A context is one canonical `specs/` tree owned by one main repository, and it can carry
associated repositories that own production source only. Scope, bind and the resolution
order are stated once, in `dadaia_workspace/public/data/dadaia-AGENTS.md`, heading
*Context, scope and races*. A repo checkout receives only merges from its worktrees.

## Ten repositories, one law

A team with ten repositories does not maintain ten copies of anything:

- **Zero agent config in a product repo.** Every project in the workspace is governed by
  one set, outside every repository.
- **One authored set, every harness.** Public assets originate once; `harness list`
  names the registered runtimes that read them.
- **One project, however many repos.** Ten repositories can be one context or ten
  contexts. The specs tree follows the product, and the repositories it spans are its
  associated repos.

The consequence for a reviewer: everything that steers the agents is in one tree, so
changing how ten projects are governed is one diff, and reading how they are governed
is one place.

See [concepts](concepts.md) for the vocabulary and [quickstart](quickstart.md) for the
first steps.
