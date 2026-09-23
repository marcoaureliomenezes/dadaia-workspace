# Quickstart

A bare machine to a workspace whose first project is cloned, ALIVE and bound,
compliance checked, one backlog entry filed and one release live. Terms are defined in
[concepts](concepts.md); the long walkthrough is [getting started](getting-started.md).

## 1. Install

<!-- derived-from: pypi-distribution sha256:c4d89365ff10 -->
<!-- derived-from: workspace-init sha256:ca5c835e94af -->

```bash
uvx dadaia-workspace init demo --harness claude --repo https://github.com/<you>/<your-repo>.git
```

One command, nothing installed globally (needs uv); or install once with pip:

```bash
python -m venv .venv && .venv/bin/pip install dadaia-workspace
```

`pip install dadaia-workspace` installs the library and one CLI under two
console-script names, `dadaia` and `dadaia-workspace`, so the name a reader knows from
PyPI works as a command. The wheel ships the full public asset tree, so `init` works
offline; the workspace it creates keeps its own virtualenv at `.dadaia/.venv`.

## 2. Provision the workspace and its first project

<!-- derived-from: workspace-init sha256:ca5c835e94af -->

```bash
dadaia init demo --harness claude --repo https://github.com/<you>/<your-repo>.git
cd demo
```

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
- with `--repo <url>`, the repo cloned into `repos/<slug>/`, a context created with
  that slug as its main repo, made ALIVE and bound — `init` prints the `--print-env`
  line — and the pre-push hook installed.

Without `--repo`, `init` prints the `dadaia context create <name> --main-repo <slug>`
that makes the first project instead.

## 3. Bind the session

<!-- derived-from: context-management sha256:0227a5e43894 -->

```bash
eval "$(dadaia context bind demo --print-env)"
dadaia context show demo --json
```

`bind` writes one record, `.dadaia/sessions/<session-id>.json` (context, runtime, pid,
`bound_at`), and acquires nothing; `--print-env` emits `DADAIA_CONTEXT` and
`DADAIA_SESSION_ID` for the `eval $(…)` flow. The bind names the session's scope — the
context's main repo plus its associated repos — and the bound context's memory is
injected once into the session. The bind is read from `DADAIA_CONTEXT` then the session
record, never the cwd: sitting inside a repository is not a binding.

## 4. Check compliance

<!-- derived-from: workspace-doctor sha256:ef9c81d0d181 -->

```bash
dadaia doctor --context demo
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
  --title "What I want" --description "Why I want it"
```

It appends one entry, born `idea`, to `specs/backlog/BACKLOG.json`'s `active[]` — the
operator's demand queue; `--specs <path>` points it at a specs tree. The script is the
document's one writer and validator: every write validates the bytes it is about to
commit. Only the operator creates demand.

## 6. Open the first release

<!-- derived-from: release-lifecycle sha256:09607348cc88 -->

```bash
python3 .agents/skills/dd-release-implementation/scripts/release.py new 0.1.0 \
  --origin backlog:my-first-idea
```

One birth act, all or nothing: a `SPEC.md` stub plus `_RELEASE.json` in `DEFINITION`
under `specs/releases/<id>/`, refusing a second live release or a non-SemVer id with a
`fix:` line. From there, author `SPEC.md`, `PLAN.md` and `TASKS.md` at the release
root; `release.py phase IMPLEMENTATION --sha <sha>` opens implementation once all three
carry `**Status:** Approved`.

Next: [positioning](positioning.md) for why this shape, [the bug loop](bug-loop.md)
for the path a defect takes.
