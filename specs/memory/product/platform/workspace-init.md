---
slug: workspace-init
title: workspace-init
tldr: Level 1 — uvx dadaia-workspace init [DIR] provisions venv, zones, law, one harness; re-init upgrades; --repo adds level 2; next step derived from disk.
summary: dadaia init fills one plan from flags or TTY prompts, provisions the venv, the registry's init/install zones, the shared skills root and one harness's projection, seeds the states and stages and installs public assets in at most twelve lines of output naming the absolute venv CLI; on an existing workspace it upgrades an older venv, reports an equal one and refuses a newer one; with --repo it delegates to context create; every onboarding caller prints the one derived next step.
tags: [workspace, init, setup, upgrade, onboarding]
sources:
  - dadaia_workspace/cli/commands/init.py
  - dadaia_workspace/cli/commands/harness.py
  - dadaia_workspace/features/workspace/**
  - dadaia_workspace/infrastructure/python_env.py
  - dadaia_workspace/infrastructure/json_harness_profile_store.py
  - dadaia_workspace/core/workspace_resolver.py
---

## Onboarding levels

- Level 1 is the workspace (`init`), level 2 a Spec Context Project (`context create`, [[context-management]]), level 3 its canonical specs plus the first-pass audit (`specs init`, [[specs-migration]]; first pass, [[audits-canon]]).
- A new project in an existing workspace is levels 2 and 3; nothing records the level reached — it is derived from disk on every read.

## Bootstrap

- `uvx dadaia-workspace init [DIR] [--harness <name>] [--repo <url> [--associated-repo <url>]...] [--skip-assets]` is the only verb that works on an empty directory; every later command runs through the workspace's own `.dadaia/.venv/bin/dadaia`.
- Flags and prompts fill ONE plan: on a TTY a missing DIR or harness is asked (a bare name becomes `./<name>`), then the main-repo URL (blank = none) and associated URLs until a blank line; with no TTY a missing DIR or harness exits 2 with `fix: uvx dadaia-workspace init <dir> --harness <h>`; a missing `--repo` is never an error.
- Every refusal's `fix:` line is rendered from the plan itself, so it repeats the invocation's `--repo` and every `--associated-repo`.
- `--harness` names one registered harness (`claude`, `codex`, `kimi-code`, `cursor`, `devin`, `copilot`); on an existing workspace it defaults to the persisted profile's first harness.
- DIR is created if absent and never resolved from the cwd; a non-directory or a non-empty directory without `.dadaia/` is refused, exit 2, with a sibling `<dir>-workspace` in the `fix:` line; every refusal happens before any write.
- It provisions `.dadaia/.venv` (stdlib venv plus pip, the package's dependencies resolved from PyPI), every `.dadaia/` zone whose creator is init or install, and `.agents/skills`; the harness's own directory comes from its projection. An absent zone is [[workspace-doctor]]'s `WS-<zone>-missing`.
- The venv mirrors the running distribution: editable from a source checkout, else its re-packed wheel written to a system temp directory deleted after the install; `DADAIA_BOOTSTRAP_PACKAGE=<wheel>` names another wheel. A base Python without `ensurepip` is reported as missing `ensurepip`/`venv`; any other venv creation failure names a `noexec` target as its likely cause.
- A failed dependency install says the venv resolves its dependencies from PyPI (network required) and quotes the installer's last whole lines, never a mid-line cut.
- The tree it lays down is a view of `dadaia_workspace/core/workspace_layout.py` — the root law, `DADAIA_ZONES`, `STATES_CANON` — the same rows `dadaia public stage` renders into the law files ([[public-asset-distribution]]).
- It seeds `states/spec_contexts.json` and `states/server_registry.json` as empty documents without overwriting existing data ([[server-registry]]).
- `states/harness_profile.json` is the roster, written through the profile store's one writer (shared with `dadaia doctor --fix`); a re-init with another harness merges into the persisted roster, never narrowing it.
- Unless `--skip-assets`, init runs public stage and install, the one writer of every hook wiring; with `--skip-assets` the output carries the warning that the workspace is ungated until `dadaia public install` runs.
- Output is at most twelve lines: the workspace line, one asset-count line (never a per-path listing), `CLI: <absolute path of .dadaia/.venv/bin/dadaia>`, the root-launch note, then the next step; no harness-specific or user-settings advice is printed; no line names a bare `dadaia` verb.
- The only write outside the workspace is the documented Kimi Code user config ([[harness-kimi-code]]); init deletes no projection.
- `dadaia harness add <name>` stages if needed, installs that harness's set and appends it to the roster; `dadaia harness list` reads it.

## Upgrade

- Re-running `init` on an existing workspace is the upgrade; the venv's installed version is compared with the running distribution by one decider.
- An older venv is reinstalled from the running distribution and reconciled, printing `upgraded A -> B`; a failed reconcile exits 1 with `fix: <venv cli> reconcile --expect-version B`.
- An equal venv prints `already at A` and writes no file under the workspace.
- A newer venv is refused before any write, exit 1, `fix: uvx dadaia-workspace@A init <ws>`.
- Versions order as `M.m.p` with an optional local segment sorting after its base.
- The upgrade never writes a project repo; `<cli> specs init --context <ctx>`, re-run per project, then refreshes that project's specs law ([[specs-migration]]).

## First project

- `--repo <url>` with repeatable `--associated-repo <url>` calls `context create` and produces exactly what it produces — cloned, hooked, ALIVE and bound, printing the `--print-env` lines ([[context-management]]).
- A re-run naming a context already holding that main-repo URL reuses it through `context alive`; any failure exits 1 with `fix: uvx dadaia-workspace init <dir> --harness <h> --repo <a reachable clone URL>`.

## Onboarding status

- `dadaia_workspace/features/workspace/onboarding.py` derives the next unmet step from real state (files, git, the session registry), never from a stamp: no ALIVE context -> `context` (`<cli> context create <name> --main-repo <clone-url>`); an unbound resolvable session -> `bind` (`<cli> context bind <name>`); a main repo whose `specs/` is not current -> `specs` (`<cli> specs init --context <name> --replace-foreign`); a memory whose `ARCHITECTURE.md` or `QUALITY.md` is still the shipped scaffold, or whose catalog holds no atom -> `first-pass` (the `dd-audit-project` first pass, [[audits-canon]]); specs on no remote branch -> `publish` (`<cli> context baseline <name>`); else nothing.
- `<cli>` is the workspace's absolute venv CLI path (`Scripts\dadaia.exe` under Windows); the text is `Next: <reason>` plus one `fix: <command>` line.
- A focus context (the one just created, doctored or bound) is judged first, then every ALIVE context in registry order.
- Four callers print the same text: `init`, `context create`, [[workspace-doctor]]'s `ONBOARDING` finding and the SessionStart injection, unbound or bound (focused on the bound context) ([[context-management]]).

## Workspace not found

- A command that needs a workspace and finds none fails with one error: the searched directory, any skipped partial `.dadaia/`, and one `fix:` — `cd <root>` of the running CLI's own workspace when that root is initialized, else `uvx dadaia-workspace init <dir>`.

## Dependencies

[[public-asset-distribution]], [[cross-platform-portability]], [[workspace-doctor]], [[context-management]], [[specs-migration]], [[audits-canon]], [[harness-kimi-code]], [[server-registry]].
