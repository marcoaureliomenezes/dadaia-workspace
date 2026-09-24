# Positioning

Your product repositories never carry agent configuration. One law governs many
projects.

## The paradigm

<!-- derived-from: product-vision sha256:16060412dc8a -->

A workspace is one folder, and the agent session launches at its root, always.
Projects live in repos inside it — `repos/<slug>/`. Governance lives outside every
repo: the root `AGENTS.md` map, the scoped `AGENTS.md` files, `.agents/skills`,
`.agents/agents` and `.dadaia/` sit above them all.

That inversion is the whole position. A repository is a repository: production source,
its own history, its own CI. What steers an agent — law, skills, personas, hooks,
memory, releases, backlog, bugs — is workspace state, not repository content.

A workspace holds many contexts and a context many repos. It is never a monorepo, and a
single-repo context is the minimal case of the multi-repo one.

## The unit is the context

<!-- derived-from: spec-context-project sha256:4984ba691799 -->

A context — a Spec Context Project — is one canonical `specs/` tree owned by one main
repository: the unit for memory, backlog, bugs, releases, reports and handoffs. A
product spanning several repositories is still one project: the context carries
associated repositories, added by `dadaia context repo add` and removed by
`dadaia context repo remove`, which live and die with it.

The asymmetry is deliberate:

- the main repository owns production source **and** `specs/`;
- an associated repository owns production source only;
- specs, bind, memory, releases and backlog resolve from the main repo alone — an
  associated repo's own `specs/` is never read.

`dadaia context bind <ctx>` selects a context and nothing else, changing only the
caller's own session record; a session without a harness-native id carries the binding
in `DADAIA_CONTEXT`. The bind carries a scope — the main repo plus its associated
repos — and a bound session's MUTATING write into a repo another context owns is
refused, naming the bind that would allow it. An unbound session is never
scope-judged.

## Ten repositories, one law

<!-- derived-from: product-vision sha256:16060412dc8a -->
<!-- derived-from: spec-context-project sha256:4984ba691799 -->

A team with ten repositories does not maintain ten copies of anything:

- **Zero agent config in a product repo.** Governance lives outside every repository,
  and every project in the workspace is governed by that one set.
- **One authored set, every harness.** Claude Code, Codex, Kimi Code, Cursor, Devin and
  GitHub Copilot are entry harnesses over the same canonical rules: public assets
  originate once, stage once, and each harness reads them natively or through
  per-entry symlinks.
- **One project, however many repos.** Ten repositories can be one context or ten
  contexts. The specs tree follows the product, and the repositories it spans are
  declared as its associated repos.
- **Boundaries are mechanical.** Path class, bind scope, root hygiene, venv-rooting and
  the push gate refuse mechanically, each refusal carrying its own runnable fix. No
  phase and no mode is enforced.
- **Concurrency stays visible.** Concurrent sessions never block each other; overlap
  surfaces through git, and nothing waits on a lock.

The consequence for a reviewer: everything that steers the agents is in one tree, so
changing how ten projects are governed is one diff, and reading how they are governed
is one place.

See [concepts](concepts.md) for the vocabulary and [quickstart](quickstart.md) for the
first steps.
