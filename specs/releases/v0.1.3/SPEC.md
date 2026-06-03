# SPEC: v0.1.3 - codex-runtime-readiness

**Status:** Draft
**Release ID:** v0.1.3
**Owner:** product-engineer
**Created:** 2026-06-02

---

## 1. Objective

Make `dadaia-workspace` genuinely ready for Codex, not just Claude Code with a
Codex-shaped projection. The release fixes confirmed Codex runtime gaps in context
loading, memory path contracts, agent dispatch wording, public asset hygiene, and drift
checks.

This release is based on an inspection of the current checkout on
`release/memory-markdown-source-v1`, local Codex CLI `0.135.0`, and a temporary
`dadaia public install --target codex` projection under `.dadaia/tmp/codex-readiness/`.

---

## 2. Confirmed findings

### BUG 1 - Codex config is written to the workspace but local Codex reads `~/.codex/config.toml`

`dadaia public install --target codex` emits:

- `.codex/config.toml`
- `.codex/agents/*.toml`
- `.codex/hooks.json`
- `.codex/skills/{memory-ctx,design-ctx,frontend-ctx}/SKILL.md`

But `codex doctor` on this machine reports the active config as:

```text
config.toml  ~/.codex/config.toml
```

It does not report the workspace `.codex/config.toml` as the active config source. That
means the generated Codex agent, hook, and skill config can be present on disk but not
actually loaded by the Codex CLI unless the operator has separately bridged it.

**Impact:** high. A consumer may run Codex in a dadaia workspace and still get only
`AGENTS.md` plus global Codex config, not the 21 generated Codex agents or hooks.

### BUG 2 - Markdown memory migration is incomplete in Codex-facing instructions

The current memory tree contains Markdown atoms only:

- `specs/memory/architecture.md`
- `specs/memory/tech-stack.md`
- `specs/memory/product/index.md`
- `specs/memory/product/<slug>.md`
- `specs/memory/product/catalog.json`

Several Codex-relevant files still instruct agents to read `.html` memory:

- `dadaia_workspace/public/runtime/codex/memory-ctx/SKILL.md`
- `dadaia_workspace/public/skills/dadaia-workspace-spec-navigator/SKILL.md`
- `dadaia_workspace/public/data/AGENTS.md`
- `specs/AGENTS.md`
- some agent bodies, e.g. `project-auditor.md`

**Impact:** high. A fresh Codex session following `memory-ctx` can fail to load memory
because it is told to read files that no longer exist.

### BUG 3 - Codex-only adapters may not be discoverable

The generated `.codex/config.toml` contains:

```toml
[skills]
paths = [".agents/skills"]
```

Codex-only adapters are installed under `.codex/skills/`, not `.agents/skills/`.
The current session happened to expose `.codex/skills/*`, but the generated config does
not make that dependency explicit.

**Impact:** medium-high. `memory-ctx`, `design-ctx`, and `frontend-ctx` are the primary
Codex context adapters; they must not rely on implicit discovery.

### BUG 4 - Claude dispatch wording survives in Codex personas

`project-manager` is transformed from "Agent tool" to "`subagent` dispatch", but current
Codex exposes multi-agent capability through tool discovery (`tool_search`) and deferred
multi-agent tools, not a literal `subagent` tool in the normal tool list.

**Impact:** medium. The intent is clear to a human, but weak for Codex automation. PM and
auditor personas should say exactly how Codex discovers and invokes multi-agent tools.

### BUG 5 - `public doctor` includes `__pycache__/*.pyc` as stage assets

`dadaia public doctor` reports:

```text
[missing] stage:scripts/__pycache__/generate-memory-catalog.cpython-312.pyc
[missing] stage:scripts/__pycache__/lint-memory-atoms.cpython-312.pyc
```

The files exist under `dadaia_workspace/public/scripts/__pycache__/`. `_iter_files()`
currently returns every file under `public/`, including Python bytecode.

**Impact:** medium. Local cache files become asset drift. This is especially bad for
Codex because agents run Python frequently and can accidentally create new cache noise.

### BUG 6 - Codex workflow policy is contradictory

The installer copies workflows to `.codex/workflows/`, while `_classify_workflows()` still
reports Codex workflows as `[not-applicable] (no workflow runtime)`, and memory text still
describes older states. This may be intentional as "reference-only workflows", but the
contract is not explicit.

**Impact:** medium. Agents and doctor output disagree about whether Codex workflows are
installed runtime assets or documentation-only assets.

### BUG 7 - Codex hooks are weaker than Claude Code hooks

Claude Code receives `PreToolUse`, `PostToolUse`, and `UserPromptSubmit` hooks. The Codex
projection only generated `PreToolUse` and `PostToolUse`, and both were limited to
write-like tools. That is weaker than Claude because heartbeat should run after every
tool call, not only writes, and context injection needs an explicit Codex hook path where
the runtime supports it.

The shell hooks also invoked `python3` directly instead of preferring the workspace venv.

**Impact:** high. Long Codex sessions can let implementation locks go stale, and a green
projection can still behave weaker than the Claude Code SDD workflow.

---

## 3. Product deltas

1. Codex bootstrap must have an explicit, tested activation path:
   - either install into `~/.codex/config.toml` safely, or
   - generate an operator-visible command/profile that launches Codex with the workspace
     config, or
   - document that only `AGENTS.md` is automatic and `.codex/config.toml` is a projected
     reference until bridged.

2. All Codex and shared agent instructions must use Markdown memory paths:
   - `architecture.md`
   - `tech-stack.md`
   - `product/index.md`
   - `product/<slug>.md`
   - `product/catalog.json`

3. Codex skill config must explicitly include both shared and Codex-only skill roots.

4. Codex persona transform must replace Claude dispatch wording with Codex-native wording.

5. Public asset staging and doctor must ignore cache/generated bytecode files.

6. Codex workflow projection policy must be made coherent:
   - either remove `.codex/workflows/` and keep `[not-applicable]`, or
   - keep `.codex/workflows/` as reference docs and change doctor/memory wording to
     "installed reference, no runtime executor".

7. Scoped AGENTS.md projections must cover the dadaia runtime control plane:
   - root `AGENTS.md` stays short and routes agents to scoped rule files.
   - `.dadaia/AGENTS.md` defines runtime-control-plane ownership.
   - `.dadaia/tmp/AGENTS.md` defines temporary artifact policy.
   - `.dadaia/states/AGENTS.md` defines machine-state policy.
   - `.dadaia/reports/AGENTS.md` defines report and handoff sidecar policy.

---

## 4. Acceptance criteria

| AC | Description |
|----|-------------|
| AC-1 | `dadaia public install --target codex` produces a Codex setup whose activation path is explicit and tested against local `codex doctor` / config behavior. |
| AC-2 | No Codex-facing runtime adapter references `.html` memory atoms. |
| AC-3 | No shared workspace bootstrap instruction tells agents to read `.html` memory atoms in the Markdown-source world. |
| AC-4 | Generated `.codex/config.toml` declares all skill paths needed for shared skills and Codex-only adapters, or a test proves `.codex/skills` is auto-discovered without config. |
| AC-5 | Generated Codex personas do not instruct PM/auditor to use a literal unavailable `subagent` tool. |
| AC-6 | `dadaia public doctor` does not report `__pycache__` or `*.pyc` under `stage:`. |
| AC-7 | Codex workflow policy is documented consistently in installer, doctor, AGENTS, and memory. |
| AC-8 | `dadaia specs doctor --specs-dir specs` exits with no errors. Existing unrelated warnings are documented. |
| AC-9 | `dadaia public doctor` exits 0 without cache noise after staging. |
| AC-10 | Focused tests for public assets, Codex runtime projection, and memory bootstrap pass. |
| AC-11 | `dadaia public install --target all` installs scoped AGENTS.md files for `.dadaia/`, `.dadaia/tmp/`, `.dadaia/states/`, and `.dadaia/reports/`; `dadaia public doctor` detects their drift. |
| AC-12 | Generated Codex hooks include `PreToolUse`, `PostToolUse`, and `UserPromptSubmit`; `PostToolUse` is broad enough for heartbeat after non-write tools; hook scripts prefer workspace venv Python. |
| AC-13 | Writes to legacy `specs/memory/**/*.html`, `*.yaml`, and `*.yml` are blocked even during CLOSURE; editable memory source is Markdown. |
| AC-14 | The `dadaia-workspace` source repo has no tracked or physical root runtime projections/local harness files: `.dadaia/`, `.agents/`, `.claude/`, `.codex/`, `.opencode/`, `CLAUDE.md`, `opencode.json`, `Makefile`, root `playwright.config.ts`, `playwright-report/`, or `test-results/`. |

---

## 5. Out of scope

- Publishing a new public release.
- Changing the 20-agent topology.
- Changing Claude Code behavior except where shared docs must be updated from HTML to Markdown memory.
- Editing generated runtime projections directly.
- Changing user-level `~/.codex/config.toml` automatically without an explicit operator-approved design.
