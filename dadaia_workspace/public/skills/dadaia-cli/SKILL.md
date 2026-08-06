---
name: dadaia-cli
description: >
  Use this skill whenever you need to operate the dadaia-workspace CLI — open the
  panel, bind a Spec Context, run a lifecycle workflow, check state, register a bug,
  or discover any command. The CLI is self-documenting; this is the map plus the few
  non-obvious idioms. All agents may use it.
---

# Skill: dadaia-cli

The `dadaia` CLI is the single control surface for the workspace. It is **self-documenting** — discover, don't guess.

## Discover

- `dadaia --help` — all command groups.
- `dadaia <group> --help` — a group's subcommands (e.g. `dadaia context --help`, `dadaia lifecycle --help`).
- Always call the binary in the workspace venv: `.dadaia/.venv/bin/dadaia`. Never system Python/pip.
- Add `--json` to most read commands for machine-readable output.
- Start every new or upgraded runtime with `dadaia capabilities --json`; this versioned
  document is authoritative over remembered command syntax.

## Panel — see everything

`dadaia panel` starts the local UI (default port 4999). Tabs: Contexts (ALIVE/DEAD + advisory presence), Workflows (verbs, diagrams, model pickers), Servers, Reports/Handoffs, Sub-agents, projection health. Use it to inspect state instead of reading files.

## Command groups (`dadaia <group> --help` for detail)

| Group | What |
|---|---|
| `context` | Spec Context Projects: `list show create alive dead bind release heartbeat delete` |
| `lifecycle` | Deterministic workflow verbs (see below) |
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

Bind binds the **context** (persists mode + session id in the session record, self-scoped); no shell `eval` needed. ADDITIVE work (bugs/backlog/audits/reports) needs no bind.

## Workflows (`dadaia lifecycle <verb>`)

Deterministic, Python-gated. Pass `--context <ctx> --release-id <id>` on every workflow command; add `--harness pi|codex|fake` + `--step-model` to select the Layer-2 worker.

| Verb | Purpose |
|---|---|
| `backlog-definition` | Research/grill a demand or bug and author one consistent backlog item |
| `release-definition` | Author and review SPEC, PLAN, and TASKS |
| `implementation-reviews` | Implement, self-verify, run QA/security/code review, correct, and close |
| `audit` | Scope, inspect, disposition findings, and verify handoff coherence |

These are the only workflow commands. Status, cleanup, report validation, model policy,
and handoff doctors are diagnostics under their owning top-level command groups; they are
not workflows.

Full per-verb detail (steps, harness/model, diagrams): the panel **Workflows** tab.

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
baseline, caller-owned bind/heartbeat, all four fake workflows through closure, strict
handoff validation, panel HTTP/server registry, and ALIVE/DEAD/delete teardown. Any failed
check is a release blocker. Real Codex and PI canaries remain required before publishing a
provider release; `fake` is only the deterministic workflow contract harness.

## Agent operating sequence

1. Read `dadaia capabilities --json`; never infer features from an older conversation.
2. Select the target with `context list/show --json`, then bind this session explicitly.
3. Run `specs doctor --context <ctx> --json`; do not implement against errors or warnings.
4. Use exactly one current lifecycle verb with explicit `--context` and `--release-id`.
5. Preserve the complete JSON result and worker diagnostic when blocked; never reduce it
   to “workflow failed”.
6. Use `dadaia panel` for the human view and the server registry for ports.
7. Emit/validate the final handoff and register genuine provider bugs before workarounds.

## Register a bug (any runtime, ADDITIVE)

```bash
dadaia bugs append --bug-id <slug> --event reported --reported-by <agent> \
  --title "…" --severity LOW|MEDIUM|HIGH|CRITICAL --surface "<cmd>" \
  --component "<module>" --context <ctx> --tag <t> \
  --symptom "…" --repro "…" --expected "…" --notes "… (redacted)"
dadaia bugs status        # open bugs
```

## When a command fails

Classify BEFORE registering anything (consumer deep-dive, v0.2.9): a failure is a
**product bug of the library** only when the library's own contract is violated.
Environment (quota/rate limits, network, sandbox), invalid input, and wrong usage are
NOT product bugs — diagnose first, register with evidence second. When it IS a
product bug, register it with `dadaia bugs append` before working around it. Never
hand-edit a projected asset to fake a result; fix the source and re-project
(`dadaia public stage && dadaia public install --target all && dadaia public doctor`).
