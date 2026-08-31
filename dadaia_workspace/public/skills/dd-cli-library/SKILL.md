---
name: dd-cli-library
description: >
  Use this skill whenever you need to operate the dadaia-workspace CLI — open the
  panel, bind a Spec Context, author backlog/release artifacts, check state, register
  a bug, or discover any command. The CLI is self-documenting; this is the map plus the
  few non-obvious idioms. Granted to every shell-capable agent (any agent whose tools
  include `Bash`); the two shell-less roles (`product-engineer`, `software-architect`)
  are ungranted — see §Reachability below.
tldr: "dadaia CLI is self-documenting; use --help/--json; grant only to Bash-capable agents."
---

# Skill: dd-cli-library

Cache of expensive lookups, not a transcription of the live command tree — when a table here and `--help` disagree, `--help` wins.

## 1. When

- Operating the CLI: panel, binding a context, authoring backlog/release artifacts.
- Checking state, registering a bug, or discovering any command.
- Starting any new or upgraded runtime session.
- Only when `Bash` is in the agent's `tools:` list — see §4 reachability table.

## 2. Steps

1. Run `dadaia --help` for all command groups; `dadaia <group> --help` for a group's subcommands.
2. Call the venv binary always: `.dadaia/.venv/bin/dadaia` — never system Python/pip.
3. Add `--json` to read commands for machine-readable output.
4. Run `dadaia capabilities --json` first in any new/upgraded session.
5. Use `dadaia panel` (default port 4999) for the human view.
6. Bind the session: `dadaia context bind <ctx> --mode implementation --release <id>`.
7. Export `DADAIA_CONTEXT=<ctx>` instead in a plain shell or under kimi-code — the env var **is** the binding there.
8. Skip binding for ADDITIVE work (bugs/backlog/audits/reports) — none needed.
9. Run `specs doctor --context <ctx> --json` before implementing; do not proceed against errors or warnings.
10. Reserve the task in TASKS.md (`dadaia-task-manager`) before writing any production file.
11. Pass explicit `--context`/`--release-id` on every command.
12. Converge a runtime: resolve `provider.distribution_version` from `dadaia capabilities --json`.
13. Run `dadaia reconcile --expect-version "$version" --json`, then `dadaia certify --json`.
14. Treat any failed `certify` check as a release blocker.
15. On a failing command: preserve the full evidence trail (command, exit code, output).
16. Classify and register a genuine bug (`dd-bug-registration`) before any workaround.
17. Emit/validate the final handoff (`dadaia-handoff-emitter`).

## 3. Done when

- The command run matches live `--help` output, not a remembered table.
- `specs doctor` is clean before any implementation write.
- `certify --json` is green before promoting a runtime.
- Every dev server started is registered (`dadaia server register`).

## 4. References

- Reachability — grant iff `Bash` in `tools:`: `ai-engineer`, `code-reviewer`, `project-auditor`, `project-manager` — yes.
- Reachability — grant iff `Bash` in `tools:` (continued): `qa-engineer`, `security-reviewer`, `software-engineer` — yes.
- Reachability — ungranted (no `Bash`): `product-engineer` (D-1, shell-less), `software-architect`.
- `dadaia_workspace/public/scripts/lint-dadaia-cli-reachability.py` — derives this table at projection time; `--self-test` proves both directions.
- Command groups (`dadaia <group> --help` for detail): `context`, `specs`, `capabilities`/`certify`/`reconcile`.
- Command groups (continued): `bugs`, `backlog`/`release`, `reports`, `server`, `ci`, `public`, `doctor`/`migrate`, `init`/`export`/`import`/`clean`.
- `DADAIA.md` §2 — SDD stages are agent-dispatched, not a CLI verb group.
- `dd-bug-registration` — classify-first, redaction, `dadaia bugs append` reference.

## 5. Workspace-management idioms (absorbed from dadaia-workspace-manager, T-053-25)

- State is CLI-owned: never edit `.dadaia/states/*.json`, never `git clone` into `repos/`, never `rm -rf repos/<slug>/`, never `tar xzf` an import — `dadaia context alive|dead`, `dadaia import|export` own those.
- Bind is the context choice: `dadaia context bind <name> [--mode read|implementation|review] [--release <id>]`; a plain shell exports `DADAIA_CONTEXT=<ctx>` instead.
- Lifecycle: `create (dead) -> alive -> bind -> dead -> delete`; `context dead` removes the repo from disk — never run it casually mid-switch.
- Import flow: export on source, move the archive, `dadaia import <archive>`, then verify `dadaia context list` + `dadaia doctor`.
- NO-LOCKS: binds acquire nothing; MUTATING writes leave advisory presence; a live foreign presence is one throttled warning, never a block.

## 6. Dev-server law (absorbed from dev-server-registry, T-053-25)

- Never open a port without the registry: `dadaia server list` -> `dadaia server next --project <name> --json` -> start -> `dadaia server register --port N --project <name> [--pid ...]`.
- Use the returned port even when `is_base_port: false`; release on stop (`dadaia server release --port N | --project <name>`).
- On `PortConflictError`: `server list`, `server clean` if stale, `server next` again.
- Every discovery detail: `dadaia server --help`.
