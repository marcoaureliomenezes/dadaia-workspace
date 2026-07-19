> **AI agent rules.** This file is generated from
> `dadaia_workspace/public/data/AGENTS.md` by `dadaia public install`.
> Do not put project-specific instructions here. Put them in a scoped
> `AGENTS.md` / `CLAUDE.md` inside the repo or directory they govern.

# dadaia-workspace — Root Rules

You are in a dadaia-workspace SDD workspace. Keep this root file as the global
contract only. More specific rules live closer to the files being edited and
take precedence.

## Operating Defaults

- Language: follow the operator's preference; default to English.
- Tone: direct, concise, operational.
- Use `.dadaia/.venv/bin/python` and `.dadaia/.venv/bin/pip`; do not use system
  Python tooling for workspace commands.
- Temporary files go under `.dadaia/tmp/`, not under `repos/`, `specs/`, or
  `tests/`.
- Public defaults must stay generic: no private repo names, hostnames, IPs,
  customer names, operator-local paths, or optional domain-pack assumptions.

## Credential Boundary

**Always no:** credential material is allowed only in the operator-managed
workspace-root `.env`. Never create, copy, persist, commit, print, or report
tokens, passwords, private keys, cookies, auth payloads, or secret files in a
repository, runtime mount, image, generated configuration, cache, report, or
handoff. Runtime processes may receive only the minimum required values from
that root `.env`; they must not write a second credential store.

## Workspace Root Law

The workspace **root** may contain **only**:

- Directories: `.agents/`, `.claude/`, `.codex/`, `.dadaia/`, `.kimi-code/`,
  `.pi/`, `repos/`
- Files: `AGENTS.md`, `CLAUDE.md` (Claude Code bridge importing `@AGENTS.md`),
  `prompt.md` (optional operator long-prompt file)

`.pi/` is the PI (`pi-coding-agent`) Layer-1 projection. It is lib-originated like the
other projection dirs, but its assets are **post-trust executable**: PI loads `.pi/**`
only after the operator grants trust and runs it as unsandboxed TypeScript. It carries
no secrets and no operator-local paths, and must never be hand-edited in place — a
deliberate privilege grant, not inert config.

`.kimi-code/` is the Kimi Code Layer-1 projection. Its workspace tree is inert
Markdown (`AGENTS.md`); the live wiring is a managed, marker-delimited `[[hooks]]`
block in the user-level `$KIMI_CODE_HOME/config.toml` plus POSIX shims under
`$KIMI_CODE_HOME/hooks/` — Kimi Code has no project-level config file. Both are
written by `dadaia public install --target kimi-code`, carry no secrets and no
workspace-absolute paths, and fail open outside dadaia workspaces.

**Operator exception:** any file or directory created by the human operator is always
allowed and MUST never be auto-deleted (e.g. `prompt.md`, screenshots). Operator
authorship is determined by human judgment — the hook fails open when origin is ambiguous.

Everything else at root is forbidden. If a legitimate process regenerates an artifact,
it MUST be redirected into a canonical `.dadaia/<subdir>` — never left loose at root.
Agent-generated temp files go to `.dadaia/tmp/<agent>/<YYYYMMDD>/` (see the
`tmp-file-guardrail` rule). Tool caches go under `.dadaia/` (ruff `cache-dir`, coverage
`data_file`, etc.). MCP server working dirs go under `.dadaia/mcps/<server>/`.

This law is enforced deterministically **for file-write tools** by the root-whitelist
policy inside the merged `dadaia_workspace.hooks.pre_gate` PreToolUse entrypoint
(Python — see the SDD Gate section). Any such write that would create a new top-level
root entry not in the whitelist above is **blocked**. Writes performed through the
`Bash` tool are not classified by this policy — they are governed by this rule as
discipline, with `dadaia doctor` as the after-the-fact backstop. The policy reads an
optional operator exception list from `.dadaia/states/root_exceptions.txt` (one glob
per line) for documented, deliberate exceptions (e.g. tool configs that a specific
tool hard-requires at root).

## Repository Hygiene

This repository is the `dadaia-workspace` source library, not a generated
consumer workspace. Never leave generated runtime projections or local harness
files at the repo root.

Forbidden root artefacts:

- `.dadaia/`, `.agents/`, `.claude/`, `.codex/`, `.kimi-code/`, `.pi/`
- `CLAUDE.md`, `Makefile`, `playwright.config.ts`
- `playwright-report/`, `test-results/`, coverage/cache directories

Run projection/install smoke tests in a temp workspace under `.dadaia/tmp/` or
pytest `tmp_path`, never against the repository root. If a validation command
must run on the root, remove generated projections before finishing and confirm
`git status --short` contains only intentional source/test changes.

## Repo cleanliness — no temp/cache/state dirs

No repo — neither the `dadaia-workspace` library repo nor any Spec Context Project repo — may contain tool-generated cache, state, or artifact directories. These dirs are unconditionally forbidden inside any repo working tree:

| Forbidden dir | Origin |
|---|---|
| `.dadaia/` | workspace-level only — lives at the workspace root, NEVER inside a repo |
| `.venv/` | virtual-environment bootstrap artefact |
| `.pytest_cache/` | pytest cache |
| `.mypy_cache/` | mypy incremental cache |
| `.hypothesis/` | hypothesis database |
| `.ruff_cache/` | ruff lint cache |
| `test-results/` | test runner artefact |
| `playwright-report/` | Playwright HTML report artefact |
| `coverage/`, `.coverage` | coverage artefact |

**`.dadaia/` is workspace-level ONLY.** Creating `.dadaia/` inside a repo is a hard violation — it corrupts workspace-vs-repo boundary detection and breaks context resolution for every tool that walks the directory tree.

**Tools must run with caching disabled or redirected outside the repo:**

- pytest: pass `-p no:cacheprovider` (or set `cache_dir` to a path under `.dadaia/tmp/`)
- mypy: set `incremental = false` in config
- hypothesis: set `database = None`
- ruff: pass `--no-cache`
- Playwright: direct `outputDir` and `reporter` to `.dadaia/tmp/<agent>/<date>/`

Ephemeral agent files go to the workspace `.dadaia/tmp/` landing zone (see `tmp-file-guardrail` rule), not into any repo.

Gitignore entries for these dirs are defence-in-depth only. **Gitignore is not a licence to create them.** They must not appear in the working tree at all. CI repo-hygiene checks enforce this.

## Scoped Rules

Before editing, check for the nearest scoped rule file:

- `specs/AGENTS.md` governs SDD artifacts, memory, release gates, backlog, bugs.
- `.dadaia/reports/AGENTS.md` governs human-readable report files.
- `.dadaia/handoff/AGENTS.md` governs machine-readable agent handoff files.
- `repos/<slug>/AGENTS.md` governs production source for that repo.
- Nested `AGENTS.md` / `CLAUDE.md` files govern their subtree only.

If a scoped file exists, follow it. Do not duplicate its details in root-level
instructions.

## Rule-Law Corpus (by-name → on-disk surface)

Agent instructions cite governance rules **by name** (e.g. the `workspace-protocol`
rule, the `release-governance` rule, the `backlog-ownership` rule). Every by-name rule
is a real on-disk Markdown file at the workspace root:

```text
.claude/rules/<rule-name>.md
```

This corpus is reachable from **every** harness — Claude Code loads it natively, and
Codex (and any other harness) can read it directly with a file read. When an
instruction references "the `<name>` rule", open `.claude/rules/<name>.md` to load the
full rule body. The corpus is generated from `dadaia_workspace/public/rules/` by
`dadaia public install` and is identical across harnesses; it is the single source of
truth for the by-name law surface.

## Active Spec Context

See `workspace-protocol` rule for the full context-resolution and spec-loading procedure.

## Bug Registration (all runtimes)

Any time you hit a **bug** while operating dadaia-workspace tooling — projection,
`specs doctor`/`upgrade`, scaffolding/onboarding, hooks, the SDD gate, presence,
context bind/alive/dead, panel, reports, the `dadaia` CLI, or any production
behavior that breaks its own contract — you MUST register the bug before the
turn ends by appending a `reported` event with `dadaia bugs append` (event-sourced
JSONL, v0.1.46 — **not** a hand-authored `specs/bugs/<slug>.md`). Events land in
`specs/bugs/<YYYYMMDDTHH>Z-<n>.jsonl`. In this self-hosting source workspace, bugs go
to `repos/dadaia-workspace/specs/bugs/`; in a consumer workspace, to the active
context's `specs/bugs/` plus an upstream report. Bug events are ADDITIVE — the gate's
path classifier resolves `specs/bugs/` (at the workspace root **and** inside any
`repos/<slug>/`) to the ADDITIVE class, which is never blocked — there is no excuse to
defer. Do NOT file a bug for an error in
your own throwaway script or for a validation the tool is *designed* to emit
(e.g. doctor correctly flagging a non-compliant tree, or the gate correctly
blocking an unauthorized write). See the `bug-registration-guardrail` rule for
the `dadaia bugs append` event contract and redaction requirement.

## SDD Gate — NO-LOCKS DOCTRINE (v0.1.76)

Races between sessions are ACCEPTED and SURFACED, never prevented. No path in
dadaia-workspace blocks an agent or operator because of another session's presence:
there is no blocking lease, no `LockHeldError`, no lease acquisition/adoption, and no
`lock steal` verb. Quality gates (pre-push security verdict, CI preflight) and
non-concurrency path-class policy (PROTECTED/FROZEN/MEMORY-phase/READ-mode) are NOT
locks and stay in force.

The gate has two layers. Know which one you are relying on.

**Deterministic enforcement** — a single merged PreToolUse entrypoint
(`dadaia_workspace.hooks.pre_gate`, Python) reads each tool payload once and evaluates
three policies in fixed order, **first-block-wins**:

1. **root-whitelist** — blocks file-tool writes that would create a new top-level
   workspace-root entry outside the whitelist (see Workspace Root Law).
2. **venv-guard** — Bash-only, fixed leading-token patterns (no general shell
   parsing): `dadaia`, `pip`, and `python -m dadaia_workspace` invocations must be
   rooted in `.dadaia/.venv/bin/`; the block message carries the corrected command.
3. **SDD gate** — evaluates every file-write tool call as
   **path-class × presence × phase × mode**:
   - **Path class** (context-relative — the same `specs/` taxonomy applies at the
     workspace root and inside every `repos/<slug>/`): ADDITIVE (`specs/bugs/`,
     `specs/backlog/`, `specs/audits/`, `.dadaia/reports|handoff|tmp/`) always allows;
     MEMORY (`specs/memory/`) allows only in `DEFINITION`/`CLOSURE` phase; FROZEN
     (`specs/_archive/`) always blocks; PROTECTED (`.dadaia/sessions/`) always blocks
     (fail-closed, session-identity integrity); everything else in-repo is MUTATING.
   - **Presence**: a MUTATING write upserts an advisory presence record for the
     session at `.dadaia/states/presence/<ctx>/<session_id>.json` — this never fails
     or blocks (presence I/O errors are swallowed and the write proceeds). When another
     live session's presence already exists on the same context, the write is
     **allowed** and a single throttled advisory warning is surfaced naming the other
     session (session id, runtime, heartbeat age). Stale presence is GC'd by doctor
     (PRESENCE-GC) and opportunistically on upsert.
   - **Mode**: resolved env → the session's **own** record → IMPLEMENTATION default
     (there is no context-incumbent-pointer fallback — a foreign session's bind can
     never change your mode). A session resolving READ is non-acquiring and blocks
     only its **own** MUTATING writes as opt-in self-protection; ADDITIVE paths stay
     writable.

**Chokepoint envelope** — the PreToolUse gate does not parse arbitrary shell command
strings; the `Bash`-write hole is closed at the git chokepoints instead, which run as
git hooks and do not depend on any harness hook firing:

- **pre-commit is WARN-only** — a commit into a Spec Context repo keeps detecting
  another live session's presence on the context, but it **always ALLOWs** the commit;
  on detection it prints one advisory line naming the other session. There is no BLOCK
  verdict — commits always flow.
- **pre-push security-verdict gate** — a push is blocked unless an APPROVED
  `security-reviewer` handoff whose `metrics.commit_sha` equals each pushed ref sha
  exists; branch deletions and tag-only pushes pass. Runs alongside the CI preflight
  in the same pre-push hook. Commits are never review-blocked — only pushes. This is a
  quality gate, not a concurrency lock, and is unchanged by the NO-LOCKS DOCTRINE.
- An **advisory reconciler** (PostToolUse) flags out-of-scope dirty MUTATING paths;
  it never blocks. Doctor coherence checks remain the after-the-fact backstop.

**Bind-driven injection** — `dadaia context bind` writes a bind-epoch marker and is
the sole trigger for context-memory injection. An unbound session receives generic
preflight only (no context memory; there is no first-ALIVE injection fallback). Bind
is never a precondition for ADDITIVE work.

**What the gate does NOT do.** The hook reads no SDD artifacts: it does not know the
active phase from `ACTIVE.md`, whether `SPEC.md`/`PLAN.md`/`TASKS.md` are `Aprovado`,
which task is reserved, or whether an edit is inside its declared write set. The
deterministic gate constrains **what** may be written (path-class, presence, phase,
mode) — not **how** the change was produced. (`Aprovado`, `Em revisão`, and `Draft` are
the canonical SDD status tokens — do not translate or change them.)

**Ordered lifecycle is owned by the dadaia-workflows, not by this file.** The ordered
ritual — reading SPEC/PLAN/TASKS, reserving a task, the per-phase definition →
implementation → review → closure sequence — is executed by the **dadaia-workflows**
(the four `dadaia lifecycle` commands: `backlog-definition`, `release-definition`,
`implementation-reviews`, and `audit`). Each is a Python workflow body that assembles
fragment-scoped per-step prompts,
selects dynamic context, calls worker agents, and advances **Python-validated gates**.
Each model-driven worker step prompt is assembled from its **fragment**
(`public/lifecycle_fragments/<workflow>/<step>.md` — the step-specific instruction:
inputs, the exact task, output schema) **plus** its **persona**. A persona
(`public/personas/<role>.md`) is the Layer-2 (codex/pi) equivalent of a Claude
sub-agent: the role's behavioral mandate, injected into the step prompt alongside the
fragment as an operative directive, resolved from the step's `role`. The persona roster
is the **8 non-PM core roles** (`ai-engineer`, `code-reviewer`, `product-engineer`,
`project-auditor`, `qa-engineer`, `security-reviewer`, `software-architect`,
`software-engineer`); `project-manager` is the Layer-1 orchestrator, not a Layer-2
persona, so it has no persona atom.
**Harness preference (convention):** in a Codex or PI entry session, dadaia-workflows
are the preferred execution path, and the Layer-2 worker harness defaults to the entry
harness (enter `codex` ⇒ prefer `--harness codex`; enter `pi` ⇒ prefer `--harness pi`);
an explicit `--harness`/`--step-harness` always wins. Claude Code is Layer-1-only —
never a Layer-2 worker.
Layer-1 agents are **oriented toward** those workflows; the disk/commit boundary is
**safety-gate-enforced** by the deterministic gate and git chokepoints described above
(write-scope, presence, and phase) — there is no procedural check that a given
workflow verb was actually run. For the full per-workflow description — purpose,
ordered steps, per-step harness/model, flow diagram, and availability — open the
**`dadaia panel` → 2º Agentic Layer**.

## Memory

Memory is current product truth, not history.

- Read memory before changing production behavior.
- Do not write `specs/memory/**` during implementation. The gate enforces the phase
  half deterministically: `specs/memory/` (root or in-repo) is the MEMORY class,
  writable via file tools only when `ACTIVE.md` phase is `DEFINITION` or `CLOSURE`.
- Only `product-engineer` writes memory, in the `DEFINITION` or `CLOSURE` phase
  (constitution §13). The who half is discipline — the hook cannot see persona identity.
- Changelog/history belongs in `CLOSURE.md` and `_archive/`.

## Reports and Panel

Emission is **handoff-first** (`workspace-protocol` rule §4): the default output of any
agent task is a handoff JSON under:

```text
.dadaia/handoff/<context>/<UTC>-<agent>-<slug>.handoff.json
```

An HTML report is written **only** when the operator explicitly requests one or the
next handoff target is human, under:

```text
.dadaia/reports/<context>/<agent>/<UTC>-<slug>.html
```

Validate the report's **handoff JSON** (the validator takes handoff files only; the
HTML's integrity rides on the handoff's `content_hash`):

```bash
dadaia reports validate <path-to>.handoff.json
```

`dadaia panel` reads context state, reports, handoffs, servers, workflows, and
projection health. Keep report and handoff paths machine-readable.

## Lib-Originated Assets

Files listed in `.dadaia/agentic/manifest.json` are generated projections.
Do not edit them in place. Edit the source under `dadaia_workspace/public/`,
then run:

```bash
dadaia public stage
dadaia public install --target all
dadaia public doctor
```

`dadaia public doctor` must include `[ok] public-privacy`.

## Core CLI

```bash
dadaia context show --json
dadaia specs doctor
dadaia public doctor
dadaia server list
dadaia reports validate <path-to>.handoff.json
dadaia panel
```
