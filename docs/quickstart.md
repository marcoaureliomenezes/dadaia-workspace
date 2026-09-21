# Quickstart

Five minutes: a bare machine to a workspace whose first project is cloned, ALIVE and
bound, compliance checked, one backlog entry filed and one release live. Terms are
defined in [concepts](concepts.md); the long walkthrough is
[getting started](getting-started.md).

## 1. Install

<!-- derived-from: pypi-distribution sha256:80d67bd879ea -->
<!-- derived-from: workspace-init sha256:871519580ea1 -->

```bash
python -m venv .venv && .venv/bin/pip install dadaia-workspace
```

`pip install dadaia-workspace` installs the library and its `dadaia` CLI. Install into
a virtualenv, never into the system interpreter — the workspace you create next keeps
its own at `.dadaia/.venv`, and every `dadaia` and `pip` invocation inside it is
expected to come from there.

## 2. Provision the workspace and its first project

<!-- derived-from: workspace-init sha256:871519580ea1 -->

```bash
dadaia init demo --harness claude --repo https://github.com/<you>/<your-repo>.git
cd demo
```

`--harness` names exactly one of `claude` | `codex` | `kimi-code` | `cursor` |
`devin` | `copilot`. The directory is a required argument, re-running is idempotent,
and a directory holding a foreign tree is refused with one `fix:` line.

What the one line produces:

- `.dadaia/.venv`, the `.dadaia/` zones, the shared `.agents/skills` and
  `.agents/agents` roots, and the directory the named harness owns.
- the seeded state documents and the harness roster, never overwriting existing data.
- the staged and installed public assets — the law and the harness views of it, plus
  every hook wiring. `--skip-assets` leaves the workspace ungated, and the output
  says so.
- with `--repo <url>`, the repo cloned into `repos/<slug>/` (the URL's last segment,
  minus `.git`, is the slug), a context of that name created with that slug as its
  main repo, made ALIVE, given the pre-push chokepoint and bound to this session —
  `init` prints the two export lines.

Without `--repo`, `init` names `repos/` and the single
`dadaia context create --main-repo <slug>` that makes the first project instead.

## 3. Bind the session

<!-- derived-from: context-management sha256:160b285ee271 -->

```bash
eval "$(dadaia context bind demo --print-env)"
dadaia context show --json
```

`bind` writes exactly one artifact — this session's own record carrying context,
runtime, pid and `bound_at`. It acquires nothing and requires no live release;
`--print-env` emits `DADAIA_CONTEXT` and `DADAIA_SESSION_ID` for the `eval $(…)`
flow, and in a session with no harness-native id that exported variable *is* the
binding. The bind carries a scope — the context's main repo plus its associated
repos — and constrains nothing else. Sitting inside a repository is not a binding.

## 4. Check compliance

<!-- derived-from: workspace-doctor sha256:f37b2ae38ea4 -->

```bash
dadaia doctor --context demo
```

`doctor` is the one validator; three sections run in fixed order — `workspace`,
`specs`, `ledgers`. Every finding prints as one `<CODE> <verdict> <message>` line and
every error-class rule carries a mandatory `fix: <command>`, so an exit-1 run never
stalls you. There is no score: the findings and the exit code are the report.

## 5. File the first backlog entry

<!-- derived-from: sdd-bug-backlog-governance sha256:8e4c85766c6a -->

```bash
python3 .agents/skills/dd-backlog-definition/scripts/backlog.py new my-first-idea \
  --title "What I want" --description "Why I want it"
```

Run it from the workspace root. It appends one entry to the context's
`specs/backlog/BACKLOG.json` under `active[]` — the live candidate set every agent
reads. Maturation (`idea → candidate → picked`) is hand-written and doctor-validated;
only the operator creates demand.

## 6. Open the first release

<!-- derived-from: sdd-bug-backlog-governance sha256:8e4c85766c6a -->

```bash
python3 .agents/skills/dd-release-implementation/scripts/release.py new 0.1.0 \
  --origin backlog:my-first-idea
```

One birth act, one transaction: a `SPEC.md` stub plus `_RELEASE.json` in phase
`DEFINITION` under `specs/releases/<id>/`, refusing a second live release with a
`fix:` line. From there, author `SPEC.md`, `PLAN.md` and `TASKS.md` at the release
root — each carrying `**Status:** Approved` — and the candidate is defined.

Next: [positioning](positioning.md) for why this shape, [the bug loop](bug-loop.md)
for the path a defect takes.
