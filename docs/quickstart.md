# Quickstart

A bare machine to a workspace whose first project is cloned, ALIVE and bound, its
`specs/` on the canon, compliance checked, one backlog entry filed and one release
live. Terms are defined in [concepts](concepts.md); the long walkthrough is
[getting started](getting-started.md).

## 1. The three levels in one block

<!-- derived-from: pypi-distribution sha256:618098346ed6 -->
<!-- derived-from: workspace-init sha256:aa1f033df140 -->

Set `REPO_URL` to your repository's clone URL; everything else runs as printed (needs
uv and network access):

```bash
REPO_URL=https://github.com/<you>/<your-repo>.git
SLUG=$(basename "$REPO_URL" .git)
uvx dadaia-workspace init demo --harness claude --repo "$REPO_URL"
cd demo
.dadaia/.venv/bin/dadaia specs init --context "$SLUG"
.dadaia/.venv/bin/dadaia doctor --context "$SLUG"
python3 .agents/skills/dd-backlog-definition/scripts/backlog.py new my-first-idea \
  --specs "repos/$SLUG/specs" --title "What I want" --description "Why I want it"
python3 .agents/skills/dd-release-implementation/scripts/release.py new 0.1.0 \
  --specs "repos/$SLUG/specs" --origin backlog:my-first-idea
```

- **Level 1 — workspace.** `uvx dadaia-workspace init` provisions `demo/` with its own
  virtualenv; every later command runs through the workspace's CLI,
  `.dadaia/.venv/bin/dadaia`, which `init` prints by its absolute path.
- **Level 2 — project.** `--repo` clones the repo into `repos/<slug>/`, installs the
  pre-push hook and makes the context (named after the slug) ALIVE; only `context bind`
  binds a session (§3).
- **Level 3 — specs.** 3a `specs init` brings the repo's `specs/` to the canon; a foreign
  `specs/` is moved to `specs-bkp/` after consent (`--replace-foreign` skips the prompt).
  3b the `dd-audit-project` first pass fills memory — done when it holds real content,
  never by a stamp. 3c `context baseline <slug>` publishes the specs. `doctor` prints the
  next pending step with its `fix:` line at every point.

**Upgrade:** re-run the same `uvx dadaia-workspace init demo --harness claude` line
from the parent directory; it prints `upgraded A -> B`, or `already at A` when current.
Then `.dadaia/.venv/bin/dadaia specs init --context <ctx>` refreshes the project's specs law.

## 2. What the init line provisioned

<!-- derived-from: workspace-init sha256:aa1f033df140 -->

`--harness` names one registered harness: `claude` | `codex` | `kimi-code` | `cursor` |
`devin` | `copilot`. The directory is required and a directory holding a foreign tree
is refused with one `fix:` line.

- `.dadaia/.venv`, the `.dadaia/` zones init and install create, `.agents/skills`, and
  the named harness's projection.
- the seeded state documents and the harness roster, never overwriting existing data.
- the staged and installed public assets, the one writer of every hook wiring;
  `--skip-assets` leaves the workspace ungated until
  `.dadaia/.venv/bin/dadaia public install` runs, and the output says so.
- with `--repo <url>` (and any repeatable `--associated-repo <url>`), the project
  cloned and ALIVE, and the pre-push hook installed — never bound.

Without `--repo`, a later project is one step:
`.dadaia/.venv/bin/dadaia context create --main-repo <url> [--associated-repo <url>]`
clones every repo, installs the hook and makes the context ALIVE; `context bind` binds.

## 3. The bind

<!-- derived-from: context-management sha256:3f48eef447f1 -->

```bash
eval "$(.dadaia/.venv/bin/dadaia context bind <your-repo> --print-env)"
.dadaia/.venv/bin/dadaia context show <your-repo> --json
```

`bind` writes one record, `.dadaia/sessions/<session-id>.json` (context, runtime, pid,
`bound_at`), and acquires nothing; `--print-env` emits `DADAIA_CONTEXT` and
`DADAIA_SESSION_ID` for the `eval $(…)` flow. The bind names the session's scope — the
context's main repo plus its associated repos — and the bound context's memory is
injected once into the session. The bind is read from `DADAIA_CONTEXT` then the session
record, never the cwd: sitting inside a repository is not a binding.

## 4. Compliance

<!-- derived-from: workspace-doctor sha256:3fa0c321c7b0 -->

`doctor` is the one instance validator; three sections run in fixed order —
`workspace`, `specs`, `ledgers`. Every finding prints as one `<CODE> <verdict>
<message>` line, every error-class finding carries one `fix: <command>` line, and any
error-class finding exits 1. There is no score: the findings and the exit code are the
run. `--fix` moves slop to `.dadaia/reaped/` and deletes only what a TTL expired.

## 5. The first backlog entry

<!-- derived-from: backlog-ledger sha256:46382434daf2 -->

`backlog.py new` appends one entry, born `idea`, to `specs/backlog/BACKLOG.json`'s
`active[]` — the operator's demand queue; from the workspace root `--specs` names the
context's specs tree, since no `specs/` sits at or above the cwd. The script is the
document's one writer and validator: every write validates the bytes it is about to
commit. Only the operator creates demand.

## 6. The first release

<!-- derived-from: release-lifecycle sha256:ebb8441fde08 -->

`release.py new` is one birth act, all or nothing: a `SPEC.md` stub plus
`_RELEASE.json` in `DEFINITION` under `specs/releases/<id>/`, refusing a second live
release or a non-SemVer id with a `fix:` line. From there, author `SPEC.md`, `PLAN.md`
and `TASKS.md` at the release root, `PLAN.md` opening with the As-is review table
(`unit | today | bugs | verdict | why`); `release.py phase IMPLEMENTATION --sha <sha>`
opens implementation once all three carry `**Status:** Approved` and that table is
present.

Next: [positioning](positioning.md) for why this shape, [the bug loop](bug-loop.md)
for the path a defect takes.
