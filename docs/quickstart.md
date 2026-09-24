# Quickstart

A bare machine to a workspace whose first project is cloned, ALIVE and bound,
compliance checked, one backlog entry filed and one release live. Terms are defined in
[concepts](concepts.md); the long walkthrough is [getting started](getting-started.md).

## 1. Install

<!-- derived-from: pypi-distribution sha256:ed8fdd86720a -->
<!-- derived-from: workspace-init sha256:d7239f43e736 -->

```bash
uvx dadaia-workspace init demo --harness claude --repo https://github.com/<you>/<your-repo>.git
cd demo
```

One command, nothing installed globally (needs uv); `pip install dadaia-workspace`
into any venv gives the same `init`. Every later command runs from `demo/` through the
workspace's own CLI, `.dadaia/.venv/bin/dadaia`.

`pip install dadaia-workspace` installs the library and one CLI under two
console-script names, `dadaia` and `dadaia-workspace`, so the name a reader knows from
PyPI works as a command. The wheel ships the full public asset tree; `init` resolves
the workspace venv's dependencies from PyPI, so it needs network access. The workspace
it creates keeps its own virtualenv at `.dadaia/.venv`.

## 2. What the one line provisioned

<!-- derived-from: workspace-init sha256:d7239f43e736 -->

`--harness` names one registered harness: `claude` | `codex` | `kimi-code` | `cursor` |
`devin` | `copilot`. The directory is required, a re-run is idempotent, and a directory
holding a foreign tree is refused with one `fix:` line.

What the one line produces:

- `.dadaia/.venv`, the `.dadaia/` zones init and install create, `.agents/skills`, and
  the named harness's projection.
- the seeded state documents and the harness roster, never overwriting existing data.
- the staged and installed public assets, the one writer of every hook wiring;
  `--skip-assets` leaves the workspace ungated until `dadaia public install` runs, and
  the output says so.
- with `--repo <url>`, the repo cloned into `repos/<slug>/`, a context named after
  that slug (`<your-repo>` here) created with it as its main repo, made ALIVE and bound — `init` prints the `--print-env`
  line — and the pre-push hook installed.

Without `--repo`, `init` prints the `dadaia context create <name> --main-repo <slug> --url <url>`
that makes the first project instead.

## 3. Bind the session

<!-- derived-from: context-management sha256:cbeec31adb58 -->

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

## 4. Check compliance

<!-- derived-from: workspace-doctor sha256:11d53d7927db -->

```bash
.dadaia/.venv/bin/dadaia doctor --context <your-repo>
```

`doctor` is the one instance validator; three sections run in fixed order —
`workspace`, `specs`, `ledgers`. Every finding prints as one `<CODE> <verdict>
<message>` line, every error-class finding carries one `fix: <command>` line, and any
error-class finding exits 1. There is no score: the findings and the exit code are the
run. `--fix` moves slop to `.dadaia/reaped/` and deletes only what a TTL expired.

## 5. File the first backlog entry

<!-- derived-from: backlog-ledger sha256:46382434daf2 -->

```bash
python3 .agents/skills/dd-backlog-definition/scripts/backlog.py new my-first-idea \
  --specs repos/<your-repo>/specs --title "What I want" --description "Why I want it"
```

It appends one entry, born `idea`, to `specs/backlog/BACKLOG.json`'s `active[]` — the
operator's demand queue; from the workspace root `--specs` names the context's specs
tree, since no `specs/` sits at or above the cwd. The script is the
document's one writer and validator: every write validates the bytes it is about to
commit. Only the operator creates demand.

## 6. Open the first release

<!-- derived-from: release-lifecycle sha256:09607348cc88 -->

```bash
python3 .agents/skills/dd-release-implementation/scripts/release.py new 0.1.0 \
  --specs repos/<your-repo>/specs --origin backlog:my-first-idea
```

One birth act, all or nothing: a `SPEC.md` stub plus `_RELEASE.json` in `DEFINITION`
under `specs/releases/<id>/`, refusing a second live release or a non-SemVer id with a
`fix:` line. From there, author `SPEC.md`, `PLAN.md` and `TASKS.md` at the release
root; `release.py phase IMPLEMENTATION --sha <sha>` opens implementation once all three
carry `**Status:** Approved`.

Next: [positioning](positioning.md) for why this shape, [the bug loop](bug-loop.md)
for the path a defect takes.
