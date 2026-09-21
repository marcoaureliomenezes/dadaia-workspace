# Positioning

Your product repositories never carry agent configuration. One law governs ten
projects.

## The paradigm

<!-- derived-from: product-vision sha256:89dc2ce6898d -->

A workspace is one folder, and the agent session launches at its root, always.
Projects live in repos inside it — `repos/<slug>/`. Governance lives outside every
repo: the root `AGENTS.md` map, the scoped `AGENTS.md` files, `.agents/skills`,
`.agents/agents` and `.dadaia/` sit above them all.

That inversion is the whole position. A repository is a repository: production source,
its own history, its own CI. What steers an agent — law, skills, personas, hooks,
memory, releases, backlog, bugs — is workspace state, not repository content.

One workspace holds many contexts; one context holds many repos. It is never a
monorepo: the repositories keep their own remotes and their own lifecycles, and a
single-repo project is simply the degenerate case of the multi-repo one.

## The unit is the context

<!-- derived-from: spec-context-project sha256:b39739176d42 -->

A context — a Spec Context Project — is one canonical `specs/` tree owned by one main
repository: the unit for memory, backlog, bugs, releases, reports and handoffs. A
product spanning several repositories is still one project, because the context may
carry associated repositories, which live and die with it.

The asymmetry is deliberate:

- the main repository owns production source **and** `specs/`;
- an associated repository owns production source only;
- specs, bind, memory, releases and backlog resolve from the main repo alone — an
  associated repo's own `specs/` is never read.

A session binds to a context and to nothing else, changing only its own session
record. The bind carries a scope — the main repo plus its associated repos — and a
bound session's mutating write into a repo another context owns is refused, naming the
bind that would allow it. An unbound session is never scope-judged.

## Ten repositories, one law

<!-- derived-from: product-vision sha256:89dc2ce6898d -->
<!-- derived-from: spec-context-project sha256:b39739176d42 -->

A team with ten repositories does not maintain ten copies of anything:

- **Zero agent config in a product repo.** The law and the skills are authored once,
  outside every repository, and every project in the workspace is governed by that one
  set. Nothing to copy at repo creation, nothing to sync afterwards, nothing to drift.
- **Per-harness views are generated, not written.** Claude Code, Codex, Kimi Code,
  Cursor, Devin and GitHub Copilot are entry harnesses over one authored set: public
  assets originate once, stage once, and each harness reads them natively or through
  per-entry symlinks. A second copy of the law is drift waiting to happen.
- **One project, however many repos.** Ten repositories can be one context or ten
  contexts. Group by product, not by git remote: the specs tree follows the product,
  and the repositories it spans are declared, not implied.
- **Boundaries are mechanical.** The gate is three refusals — a new entry at the
  workspace root, a non-venv command, a write that is PROTECTED or outside the bind's
  scope — plus the git chokepoints. Each refusal carries its own runnable fix. No
  phase and no mode is enforced anywhere.
- **Concurrency stays visible.** Several sessions may work at once; overlap surfaces
  through git rather than through a lock, and nothing freezes waiting.

The consequence for a reviewer: everything that steers the agents is in one tree, so
changing how ten projects are governed is one diff, and reading how they are governed
is one place.

See [concepts](concepts.md) for the vocabulary and [quickstart](quickstart.md) for the
first five minutes.
