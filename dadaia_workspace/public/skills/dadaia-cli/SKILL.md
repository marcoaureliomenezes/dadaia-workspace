---
name: dadaia-cli
description: >
  Use this skill whenever you need to operate the dadaia-workspace CLI — open the
  panel, bind a Spec Context, author backlog/release artifacts, check state, register
  a bug, or discover any command. The CLI is self-documenting; this is the map plus the
  few non-obvious idioms. Granted to every shell-capable agent (any agent whose tools
  include `Bash`); the two shell-less roles (`product-engineer`, `software-architect`)
  carry no grant — see §Reachability below.
---

# Skill: dadaia-cli

The `dadaia` CLI is the single control surface for the workspace. It is **self-documenting** — discover, don't guess.

## Reachability (FR5, per-agent decision — derivation surface)

A CLI-literacy grant to an agent with no `Bash` tool is inert: it can never run a
command. The rule is mechanical, not a blanket grant: **grant iff `Bash` is in the
agent's `tools:` list.**

| Agent | `Bash`? | Grant `dadaia-cli`? |
|---|---|---|
| `ai-engineer` | yes | yes |
| `code-reviewer` | yes | yes |
| `project-auditor` | yes | yes |
| `project-manager` | yes | yes |
| `qa-engineer` | yes | yes |
| `security-reviewer` | yes | yes |
| `software-engineer` | yes | yes |
| `product-engineer` | no (D-1, shell-less) | no — inert |
| `software-architect` | no | no — inert |

`dadaia_workspace/public/scripts/lint-dadaia-cli-reachability.py` derives this same
table from each agent frontmatter's `tools:`/`skills:` lists at projection time and
fails loud on drift (`--self-test` proves both directions).

## Discover

- `dadaia --help` — all command groups.
- `dadaia <group> --help` — a group's subcommands (e.g. `dadaia context --help`, `dadaia backlog --help`).
- Always call the binary in the workspace venv: `.dadaia/.venv/bin/dadaia`. Never system Python/pip.
- Add `--json` to most read commands for machine-readable output.
- Start every new or upgraded runtime with `dadaia capabilities --json`; this versioned
  document is authoritative over remembered command syntax.

## Panel — see everything

`dadaia panel` starts the local UI (default port 4999). Tabs: Projects (Spec Context Projects, ALIVE/DEAD + advisory presence), Agents (sub-agent model/effort policy + sessions dashboard), Reports (reports/handoffs), Academy, Servers. Use it to inspect state instead of reading files.

## Command groups (`dadaia <group> --help` for detail)

| Group | What |
|---|---|
| `context` | Spec Context Projects: `list show create alive dead bind release heartbeat delete` |
| `specs` | SDD structure: `doctor upgrade init hotfix release segment` |
| `capabilities` / `certify` / `reconcile` | Discover, prove, and converge the installed provider |
| `bugs` | Event-sourced bug telemetry: `append status stats` |
| `backlog` / `release` | Backlog + release entry management |
| `reports` | Handoff/report inspection: `validate lint doctor status …` |
| `server` | Dev-server port registry: `list next register release …` |
| `ci` | Local CI-equivalent preflight + git-hook chokepoints |
| `public` | Lib-asset projection: `stage install doctor` |
| `doctor` / `migrate` | Diagnose+repair / migration helpers |
| `init export import clean` | Workspace bootstrap + portability |

## Spec Contexts (everyday)

```bash
dadaia context show --json          # active context + specs_dir + session
dadaia context list --json          # all contexts, ALIVE/DEAD
dadaia context bind <ctx> --mode implementation --release <id>   # bind THIS session
dadaia context alive <ctx> / dead <ctx>                          # lifecycle transitions
dadaia context baseline <ctx> --yes --push                       # explicit unborn-repo baseline
```

Bind binds the **context** (persists mode + session id in the session record, keyed by your harness session id, self-scoped). In a plain shell — or under kimi-code, which exposes no session-id env — export `DADAIA_CONTEXT=<ctx>` instead: the env var **is** the binding there, and `bind` warns when neither channel can carry it. ADDITIVE work (bugs/backlog/audits/reports) needs no bind.

## SDD stages (agent-dispatched, not a CLI verb)

There is no workflow engine and no lifecycle command group. Each SDD stage —
backlog definition, release definition, implementation with its reviews, and audit — is
carried out by dispatching the owning agent (`DADAIA.md` §2) against the SDD documents,
using the ordinary command groups above (`backlog`, `release`, `specs`) to scaffold and
validate what that agent authors.

## Runtime convergence and certification

An install is not promoted merely because `pip` returned zero. Converge the exact
installed version, then require a green disposable certification ledger:

```bash
version="$(${DADAIA_BIN:-.dadaia/.venv/bin/dadaia} capabilities --json | \
  .dadaia/.venv/bin/python -c 'import json,sys; print(json.load(sys.stdin)["provider"]["distribution_version"])')"
${DADAIA_BIN:-.dadaia/.venv/bin/dadaia} reconcile --expect-version "$version" --json
${DADAIA_BIN:-.dadaia/.venv/bin/dadaia} certify --json
```

`reconcile` validates the exact provider version, migrates state, reinstalls projections,
runs public/workspace doctors, and executes a capability canary. `certify` creates a
disposable workspace and proves init, projections, clean specs scaffolds, empty Git remote
baseline, caller-owned bind/heartbeat, strict handoff validation, panel HTTP/server
registry, and ALIVE/DEAD/delete teardown (checks: `capability-contract`,
`exact-version-reconciliation`, `context-empty-remote-baseline`, `context-list-show-json`,
`context-bind-heartbeat`, `reports-handoff-validation`, `panel-and-server-registry`,
`context-dead-alive-delete-roundtrip`). Any failed check is a release blocker.

## Agent operating sequence

1. Read `dadaia capabilities --json`; never infer features from an older conversation.
2. Select the target with `context list/show --json`, then bind this session explicitly.
3. Run `specs doctor --context <ctx> --json`; do not implement against errors or warnings.
4. Reserve your task in TASKS.md (`dadaia-task-manager`) before writing any production
   file, with explicit `--context` and `--release-id` for every command you run.
5. Preserve the complete evidence trail when blocked (command, exit code, output); never
   reduce it to a vague "it failed".
6. Use `dadaia panel` for the human view and the server registry for ports.
7. Emit/validate the final handoff and register genuine provider bugs before workarounds.

## Bug registration, and when a command fails

Classify-first, the `dadaia bugs append` command, redaction and context routing:
`dd-bug-registration`. Never hand-edit a projected asset to fake a result; fix the
source and re-project (`dadaia public stage && dadaia public install --target all
&& dadaia public doctor`).
