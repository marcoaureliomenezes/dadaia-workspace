# Constitution — dadaia-workspace

This document is the permanent product law for `dadaia-workspace`. Agents and
contributors must read it before changing architecture, public agentic assets,
SDD behavior, memory, or distribution rules.

## 1. SDD Is Binding

`dadaia-workspace` is developed through release-lifecycle SDD. Production
changes require an approved release gate (`SPEC.md`, `PLAN.md`, `TASKS.md`) and
task ownership before implementation. Bypass language does not override the
gate.

## 2. Public Defaults Must Be Generic

Publicly distributed agents, skills, rules, workflows, hooks, templates, and
AGENTS.md files must be safe for any user. They must not contain private
project names, hostnames, IP addresses, credentials, personal repo paths, or
domain packs that are not general workspace behavior.

Domain-specific knowledge belongs in optional packs or private overlays. The
default public install ships only generic workspace, SDD, engineering, review,
security, design, frontend, backend, QA, DevOps, research, and orchestration
capabilities.

## 3. Memory Is Repository Truth

`specs/memory/**` is committed product memory. It describes the current product
state, not a changelog. Historical detail belongs in release `CLOSURE.md` and
archived release files.

Memory source is Markdown. `specs/memory/**/*.html`, `*.yaml`, and `*.yml` are
legacy or generated formats and must not be committed as product memory.

## 4. Runtime Parity Must Be Honest

Claude Code, Codex, and OpenCode projections must describe what each runtime
actually supports. Runtime adapters may differ, but doctor output and AGENTS.md
instructions must not claim behavior that the runtime does not enforce.

Codex-specific behavior must be expressed in Codex-native terms: `AGENTS.md`
context, `.codex/config.toml`, `.codex/skills`, hooks where supported, and
deferred tool discovery for multi-agent capability.

## 5. Source Repo Must Stay Clean

The `dadaia-workspace` source repository must not track generated local runtime
projections or harness artefacts at its root, including `.dadaia/`, `.agents/`,
`.claude/`, `.codex/`, `.opencode/`, `CLAUDE.md`, `opencode.json`, `Makefile`,
root `playwright.config.ts`, `playwright-report/`, and `test-results/`.

Temporary files belong under `.dadaia/tmp/` in a consumer workspace or external
system temp directories, never as source-root artefacts.

## 6. Layering

Business behavior lives in `dadaia_workspace/features/**`, runtime and I/O
adapters in `dadaia_workspace/infrastructure/**`, CLI wiring in
`dadaia_workspace/cli/**`, and shared pure models/protocols in
`dadaia_workspace/core/**`.

`core` does not import from features, infrastructure, or CLI. Feature modules do
not import CLI modules. Cross-feature composition goes through the container or
explicit service contracts.
