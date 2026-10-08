# Quickstart

A bare machine to a workspace whose first project is cloned and ALIVE (a session binds
it with `context bind`), its `specs/` on the canon, compliance checked, one backlog entry filed and one release
live. Terms are defined in [concepts](concepts.md); the long walkthrough is
[getting started](getting-started.md).

## 1. The three levels in one block

<!-- derived-from: pypi-distribution sha256:9dadd611ee50 -->
<!-- derived-from: workspace-init sha256:a8f08f87ae76 -->

Set `REPO_URL` to your repository's clone URL; everything else runs as printed (needs
uv and network access):

```bash
REPO_URL=https://github.com/<you>/<your-repo>.git
SLUG=$(basename "$REPO_URL" .git)
uvx dadaia-workspace init demo --harness claude --repo "$REPO_URL"
cd demo
.dadaia/.venv/bin/dadaia specs init --context "$SLUG"
.dadaia/.venv/bin/dadaia doctor --context "$SLUG"
```

After the 3b first pass (below), publish and file the first entry in a `backlog`
worktree (`backlog/<slug>`) — only `context create` (the `--repo` clone) and the first `specs init` write
`specs/` directly (ADR 0154):

```bash
.dadaia/.venv/bin/dadaia context baseline "$SLUG"
B=$(python3 .agents/skills/dd-gitflow-default/scripts/worktree.py new "$SLUG" backlog/my-first-idea | sed 's/^\[ok\] //')
python3 .agents/skills/dd-backlog-definition/scripts/backlog.py new my-first-idea \
  --specs "$B/specs" --title "What I want" --description "Why I want it"
git -C "$B" commit -qam "chore(backlog): new my-first-idea"
```

After an APPROVED `dd-code-reviewer` verdict, `worktree.py merge "$B"` lands it; the
release is born the same way in its `<M.m.p>-rc<N>/define` worktree:
`release.py new 0.1.0 --specs "$R/specs" --origin backlog:my-first-idea`.

- **Level 1 — workspace.** `uvx dadaia-workspace init` provisions `demo/` with its own
  virtualenv; every later command runs through the workspace's CLI,
  `.dadaia/.venv/bin/dadaia`, which `init` prints by its absolute path.
- **Level 2 — project.** `--repo` clones the repo into `repos/<slug>/`, installs the
  pre-push hook and makes the context (named after the slug) ALIVE; only `context bind`
  binds a session (§3).
- **Level 3 — specs.** 3a `specs init` brings the repo's `specs/` to the canon; a foreign
  `specs/` is refused until `--replace-foreign` moves it to `specs-bkp/` (to
  `specs-bkp/<UTC>/` when a backup already exists).
  3b the `dd-audit-project` first pass fills memory — done when it holds real content,
  never by a stamp. 3c `context baseline <slug>` publishes the specs. `doctor` prints the
  next pending step with its `fix:` line at every point.

**Upgrade:** re-run the same `uvx dadaia-workspace init demo --harness claude` line
from the parent directory; it prints `upgraded A -> B`, or `already at A` when current.
Then `.dadaia/.venv/bin/dadaia specs init --context <ctx>` refreshes the project's specs law.

## 2. What the init line provisioned

<!-- derived-from: workspace-init sha256:a8f08f87ae76 -->

`--harness` names one registered harness: `claude` | `codex` | `kimi-code` | `cursor` |
`devin` | `copilot`. The directory is required and a directory holding a foreign tree
is refused with one `fix:` line.

- `.dadaia/.venv`, the `.dadaia/` zones init and install create, `.agents/skills`, and
  the named harness's projection.
- the seeded state documents, the harness roster and an absent root `.dadaiaignore`
  and `prompt.md` (the operator's files), never overwriting existing data.
- the staged and installed public assets, the one writer of every hook wiring;
  `--skip-assets` leaves the workspace ungated until
  `.dadaia/.venv/bin/dadaia public install` runs, and the output says so.
- with `--repo <url>` (and any repeatable `--associated-repo <url>`), the project
  cloned and ALIVE, and the pre-push hook installed — never bound.

Without `--repo`, a later project is one step:
`.dadaia/.venv/bin/dadaia context create --main-repo <url> [--associated-repo <url>]`
clones every repo, installs the hook and makes the context ALIVE; `context bind` binds.

## 3. The bind

<!-- derived-from: context-management sha256:e084ff04890d -->

```bash
.dadaia/.venv/bin/dadaia context bind <your-repo>
.dadaia/.venv/bin/dadaia context show <your-repo> --json
```

`bind` writes one record, `.dadaia/sessions/<session-id>.json` (context, runtime, pid,
`bound_at`), and acquires nothing; the gate and the bind read the session id from the
environment only. The bind names the session's scope — the
context's main repo plus its associated repos — and the bound context's memory is
injected once into the session. The bind is read from the session's own record when it has an
id, else `DADAIA_CONTEXT`, never the cwd: sitting inside a repository is not a binding.

## 4. Compliance

<!-- derived-from: workspace-doctor sha256:84a9bec9fec9 -->

`doctor` is the one instance validator; three sections run in fixed order —
`workspace`, `specs`, `ledgers`. Every finding prints as one `<CODE> <verdict>
<message>` line, every error-class finding carries one fix line (a command, or
`Operator action: <one act>`), and any
error-class finding exits 1. There is no score: the findings and the exit code are the
run. `--fix` moves slop to `.dadaia/reaped/`; a TTL expiry acts by zone class, an OUTPUT
entry held, an EPHEMERAL one deleted.

## 5. The first backlog entry

<!-- derived-from: backlog-ledger sha256:44b145a6a3aa -->

`backlog.py new` appends one entry, born `idea`, to `specs/backlog/BACKLOG.json`'s
`active[]` — the operator's demand queue; from the workspace root `--specs` names the
context's specs tree, since no `specs/` sits at or above the cwd. The script is the
document's one writer and validator: every write validates the bytes it is about to
commit. Only the operator creates demand, and the document is written in a `backlog/<slug>`
worktree.

## 6. The first release

<!-- derived-from: release-lifecycle sha256:7b50f03ee3e9 -->

`release.py new` is one birth act, all or nothing: a `SPEC.md` stub in
`specs/releases/<id>/rc-1/` plus `_RELEASE.json` in `DEFINITION` at the release root, refusing a second live
release or a non-SemVer id with a `fix:` line; the stub opens with `## Bug window review`. From there, author
`SPEC.md`, `PLAN.md` and one job file per job, `tasks/<job>.md`, in that `rc-<N>/`, `PLAN.md`
opening with the As-is review table (`unit | today | bugs | verdict | why`) and carrying the
`## DAG` of jobs and the `### Hot files`; `release.py phase IMPLEMENTATION --sha <sha>` opens
implementation once SPEC and PLAN carry `**Status:** Approved` and every job file is well formed.

Next: [positioning](positioning.md) for why this shape, [the bug loop](bug-loop.md)
for the path a defect takes.
