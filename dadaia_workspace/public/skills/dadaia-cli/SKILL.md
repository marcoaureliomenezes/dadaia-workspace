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

## Panel — see everything

`dadaia panel` starts the local UI (default port 4999). Tabs: Contexts (ALIVE/DEAD + advisory presence), Workflows (verbs, diagrams, model pickers), Servers, Reports/Handoffs, Sub-agents, projection health. Use it to inspect state instead of reading files.

## Command groups (`dadaia <group> --help` for detail)

| Group | What |
|---|---|
| `context` | Spec Context Projects: `list show create alive dead bind release heartbeat delete` |
| `lifecycle` | Deterministic workflow verbs (see below) |
| `specs` | SDD structure: `doctor upgrade init hotfix release segment` |
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

## Register a bug (any runtime, ADDITIVE)

```bash
dadaia bugs append --bug-id <slug> --event reported --reported-by <agent> \
  --title "…" --severity LOW|MEDIUM|HIGH|CRITICAL --surface "<cmd>" \
  --component "<module>" --context <ctx> --tag <t> \
  --symptom "…" --repro "…" --expected "…" --notes "… (redacted)"
dadaia bugs status        # open bugs
```

## When a command fails

A failed workspace operation is a **product bug of the library** — register it with `dadaia bugs append` before working around it. Never hand-edit a projected asset to fake a result; fix the source and re-project (`dadaia public stage && dadaia public install --target all && dadaia public doctor`).
