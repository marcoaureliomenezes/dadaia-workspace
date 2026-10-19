---
slug: workspace-init
title: workspace-init
tldr: Level 1 — uvx dadaia-workspace init [DIR] provisions venv, zones, law, harnesses; re-init upgrades; --repo adds level 2; --from replicates an export.
summary: dadaia init fills one plan from flags or prompts, provisions the venv and workspace tree, seeds state, and invokes the install path that stages current public assets before projection; re-init upgrades, and one ordered real-state step list drives onboarding guidance.
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

- Level 1 is the workspace (`init`); level 2 a Spec Context Project (`context create`, [[context-management]]) and the session's bind; level 3 its specs — 3a canonical specs (`specs init`, [[specs-migration]]), 3b the first pass ([[audits-canon]]), 3c the project publication (`context baseline`, [[context-management]]).
- A new project in an existing workspace is levels 2 and 3; nothing records the level reached — it is derived from real state on every read.

## Bootstrap

- `uvx dadaia-workspace init [DIR] [--harness <name>] [--repo <url> [--associated-repo <url>]... | --from <artifact>] [--template <id>] [--skip-assets]` is the only verb that works on an empty directory; every later command runs through the workspace's own `.dadaia/.venv/bin/dadaia`.
- Flags and prompts fill ONE plan: on a TTY a missing DIR or harness is asked (a bare name becomes `./<name>`), then the main-repo URL (blank = none) and associated URLs until a blank line; with no TTY a missing DIR or harness exits 1 with the init line completed from the plan (the first entry harness when none is named), an absent DIR making it `Agent action: run <init> with the new workspace's directory as its first argument`; a missing `--repo` is never an error.
- Every refusal's `fix:` line is rendered from the plan itself (`InitPlan.command`), so it repeats the invocation's `--harness`, `--from`, `--repo` and every `--associated-repo`.
- `--harness` names one registered harness (`claude`, `codex`, `kimi-code`, `cursor`, `devin`, `copilot`); on an existing workspace it defaults to the persisted profile's first harness; with `--from` the harnesses are every one the artifact names, so none is asked, and `--from` with `--repo` is refused ([[context-portability]]).
- DIR is created if absent and never resolved from the cwd; a non-directory or a non-empty directory without `.dadaia/` is refused, exit 1, with a sibling `<dir>-workspace` in the `fix:` line; every refusal happens before any write.
- It provisions `.dadaia/.venv` (stdlib venv plus pip, the package's dependencies resolved from PyPI), every `.dadaia/` zone whose creator is init or install, and `.agents/skills`; each harness's own directory comes from its projection. An absent zone is [[workspace-doctor]]'s `WS-<zone>-missing`.
- The venv mirrors the running distribution: editable from a source checkout, else its re-packed wheel written to a system temp directory deleted after the install; `DADAIA_BOOTSTRAP_PACKAGE=<wheel>` names another wheel. A base Python without `ensurepip` is reported as missing `ensurepip`/`venv`; any other venv creation failure names a `noexec` target as its likely cause.
- A failed dependency install says the venv resolves its dependencies from PyPI (network required) and quotes the installer's last whole lines, never a mid-line cut; a failed bootstrap's fix line is the plan's `init` again — the chosen harness, `--from` and every repo flag kept — run by the venv's own CLI when it exists, else by `uvx dadaia-workspace init`.
- The tree it lays down is a view of `dadaia_workspace/core/workspace_layout.py` — the root law, `DADAIA_ZONES`, `STATES_CANON` — the same rows `dadaia public install` renders into the law files as it stages ([[public-asset-distribution]]).
- It seeds `states/spec_contexts.json` and `states/server_registry.json` as empty documents without overwriting existing data ([[server-registry]]), and the absent level-1 root files from `workspace_layout.LEVEL1_SEEDS`: `.dadaiaignore` from the legacy `states/instance_exceptions.txt`, verbatim, else a comment-only template, and an empty `prompt.md`; an entry already present — a dangling link included — is never rewritten (one exception: a list-form `states/privacy_denylist.json` is converted once to the one object form, the original held in `.dadaia/reaped/`; any other content is left for the loader to refuse, [[sdd-gate-v3]]), each file is the operator's from then on, and the doctor's SessionStart lane re-creates one that goes missing ([[workspace-doctor]]); the root `AGENTS.md` comes from `public install`, which saves the `--template` agent-model template when one is named ([[agent-orchestration]]).
- `states/harness_profile.json` is the roster, written through the profile store's one writer (shared with `dadaia doctor --fix`); a re-init with another harness merges into the persisted roster, never narrowing it.
- Unless `--skip-assets`, init invokes public install, which refreshes staging before projecting every hook wiring; with `--skip-assets` the output warns that the workspace is ungated until `dadaia public install` runs.
- Output is at most twelve lines: the workspace line, one asset-count line (never a per-path listing), `CLI: <absolute path of .dadaia/.venv/bin/dadaia>`, the root-launch note, then the next step; no harness-specific or user-settings advice is printed; no line names a bare `dadaia` verb.
- The only write outside the workspace is the documented Kimi Code user config ([[harness-kimi-code]]); init deletes no projection.
- `dadaia harness add <name>` invokes the staging install path for that harness and appends it to the roster; `dadaia harness list` reads it.

## From an export

- `init DIR --from <artifact>` reads and checks the `export-v1` artifact, soft or hard, before any write, then lays down the workspace with every harness it names, registers its contexts DEAD, places a hard artifact's bundles in `.dadaia/dist/` and prints `context alive <name>` for each context that was ALIVE where it was written ([[context-portability]]); the output's workspace line names every harness installed.

## Upgrade

- Re-running `init` on an existing workspace is the upgrade; the venv's identity — its installed build (version plus a digest of the package payload's installed bytes, so a damaged installed file is another build) and its binding (the `dadaia` entrypoint names this venv's own python) — is compared with the running distribution's by one decider.
- An older venv, another build of the same version, or a venv copied from another workspace (its entrypoint names the original's python) is reinstalled from the running distribution by one `<venv python> -m pip install --force-reinstall` (a failed install keeps the old build) and reconciled, printing `upgraded A -> B`; a venv whose build cannot be read (its probe fails) gets the same reinstall and prints `repaired -> B`; a failed reconcile exits 1 with `fix: <cli> reconcile --expect-version B`.
- Every run of the venv's python goes through one runner: a venv whose python cannot be started is refused, exit 1, with `workspace venv python cannot run: <reason>.` and one fix line, an `Agent action:` to delete the venv and run `uvx dadaia-workspace init <ws>`, each word spelled once by the kernel for the host shell.
- Every init also refreshes the `pre-push` and `reference-transaction` hooks of every ALIVE repo where the installed hook is absent or byte-identical to an earlier version the library shipped (`service.hook_state`); an operator's own hook is kept ([[context-management]]).
- The same build, bound to its own venv, prints `already at A` and writes no file under the workspace.
- A newer venv is refused before any write, exit 1, `fix: <cli> init <ws> --harness <h>` — the workspace's own newer CLI.
- Versions order by PEP 440 (`packaging.version`), so a pre-release sorts above the release before it.
- The upgrade never writes a project repo; `<cli> specs init --context <ctx>`, re-run per project, then refreshes that project's specs law ([[specs-migration]]).

## First project

- `--repo <url>` with repeatable `--associated-repo <url>` calls `context create` and produces exactly what it produces — cloned, hooked and ALIVE, never bound: it writes no session record; only `context bind` binds ([[context-management]]).
- A re-run naming a context already holding that main-repo URL reuses it through `context alive`; any failure exits 1 with the same fix line `context create` prints — the create invocation, every `--associated-repo` kept, a failed URL an `Agent action:` to rerun it with a reachable clone URL.

## Onboarding status

- `dadaia_workspace/features/workspace/onboarding.py` holds the one ordered step list; each step is an id, a kind — `command` (the fix line is a shell command) or `agent` (it names a skill section and what is pending) — a real-state predicate (files, git, the session registry; never a stamp, never the network) and one fix line.
- In order: `context` — no ALIVE context (`Agent action: run <cli> context create with a context name and --main-repo set to the main repo's clone URL`); `bind` — the caller has a resolvable session id and that session is unbound (`<cli> context bind <name>`), never shown without a session identity; `constitution` (agent) — `specs/constitution.md` is not UTF-8 (`Agent action: re-encode line <n> of <constitution.md> as UTF-8 in place; every other line stays`) or its frontmatter or `gitflow:` block does not parse (`Agent action: repair the YAML frontmatter of <constitution.md>: <reason>`); `specs` — the main repo's `specs/` is not at the canonical pattern version (`<cli> specs init --context <name>`, plus `--replace-foreign` only for a foreign tree; with no work branch it cuts the local one and commits the scaffold on it, [[specs-migration]]); `first-pass` (agent) — `ARCHITECTURE.md` or `QUALITY.md`, fixed sections stripped, is still a shipped scaffold digest, or the catalog holds no atom (`Agent action: open the lane <cli> worktree new <repo> <v>/wt-backlog-first-pass, then run the dd-audit-project first pass in it — <pending items>`, `<v>` the work branch's version, naming the skill, never its projected file; with several local work branches the act leads with that refusal's own act — switch to the kept branch, merge the lower into it when it does not contain it, delete the lower — and `<v>` is the kept version, [[audits-canon]], [[worktrees]]); `publish` — the project is not published: `origin/<integration>` is absent or `specs/constitution.md` is on no `origin` ref (`<cli> context baseline <name>`, [[context-management]]).
- One context is judged: the focus (the one just created, doctored or bound), else the only ALIVE one; the next step is its first pending step, else none — another context's step is never named. With no ALIVE context the step is `context`.
- Its text is `Next (<kind> step <id>): <reason>` plus one fix line, a command or an `Agent action:`; `<cli>` is the absolute path of the workspace venv's CLI; each line is spelled by the kernel for the host shell, and one holding a word that shell cannot spell is printed as an `Agent action:` naming it ([[cross-platform-portability]], [[sdd-gate-v3]]).
- Four callers print the same text: `init`, `context create`, [[workspace-doctor]]'s `ONBOARDING` finding (its `--json` carrying `step` and `kind`) and the SessionStart injection through one helper, unbound or bound (focused on the bound context) ([[context-management]]).
- An agent loops on it — run `doctor`, execute the `fix:` line, repeat — from an empty directory to a published project; an end-to-end test drives that loop over local bare remotes.

## Workspace not found

- The running CLI's own workspace (the one owning its venv) is resolved first, so a CLI that owns one never fails here; a command that needs a workspace and finds none fails with one error: the searched directory, any skipped partial `.dadaia/`, and an `Agent action:` fix to run `uvx dadaia-workspace init` with the new workspace's directory.

## Dependencies

[[public-asset-distribution]], [[cross-platform-portability]], [[workspace-doctor]], [[context-management]], [[specs-migration]], [[audits-canon]], [[harness-kimi-code]], [[server-registry]], [[agent-orchestration]].
