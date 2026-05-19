# dadaia-workspace — AI Coding Assistant

This document is auto-loaded by **Claude Code** (`CLAUDE.md`), **Codex**, **OpenCode**,
and every harness that reads top-level `AGENTS.md`. It defines the lib-general
workspace guardrails that ship with `dadaia-workspace` to every consumer repo.

You are inside a Spec-Driven Development (SDD) workspace governed by
`dadaia-workspace`. Treat the rules here as binding. Domain-specific guardrails
live in nested `CLAUDE.md` / `AGENTS.md` files (e.g. `services/CLAUDE.md`) and
override these rules within their subtree.

- **Language:** Portuguese (BR) by default; English for technical terms.
- **Tone:** direct, concise. Do not narrate diffs; the operator reads them.

---

## 2. Python `venv` policy + dadaia CLI reference

Use the vendored venv at `.dadaia/.venv/`. The system interpreter is forbidden.

```bash
.dadaia/.venv/bin/python <script>    # CORRECT
.dadaia/.venv/bin/pip install <pkg>  # CORRECT
python3 / pip / pip3 ...             # forbidden
```

Ephemeral artefacts: `.dadaia/tmp/python/` (scripts), `.dadaia/tmp/json/` (data).
Never write temp files into `repos/`, `specs/`, or `tests/`.

`dadaia` CLI surface (one line each):

```bash
dadaia context show --json | activate <name> | list   # Spec Context resolution
dadaia specs doctor                                    # SDD invariants (11 checks)
dadaia public stage | install --target all | doctor    # Projection workflow
dadaia server register | list | unregister             # Dev-server registry
dadaia reports validate <path>                         # Handoff sidecar validator
dadaia academy | panel                                 # Onboarding + live topology
dadaia doctor | export | repos                         # Health + utility commands
```

---

## 3. SDD — release-lifecycle model (ABSOLUTE LAW)

The workspace follows the **release-lifecycle** SDD model. The unit of work is a
**release** under `specs/releases/<release-id>/`, not a "feature folder". The
active release is declared in `specs/releases/ACTIVE.md`.

### 8-phase pipeline

```
DISCOVERY → SPEC → PLAN → TASKS → IMPLEMENTATION → CLOSURE → ARCHIVED
```

- Each artifact (`SPEC.md`, `PLAN.md`, `TASKS.md`, `CLOSURE.md`) advances through
  `Draft → Em revisão → Aprovado`. **Aprovado** is the only marker that unlocks
  the next phase. Verbatim header `**Status:** Aprovado`.
- The `phase:` line in `ACTIVE.md` is the runtime gate pointer. Memory atoms
  under `specs/memory/*.html` are write-locked except during `CLOSURE` phase.
- TASKS.md uses three machine-readable markers: `[ ]` OPEN → `[-]` IN PROGRESS →
  `[x]` DONE. At most one `[-]` per TASKS.md at a time unless the file
  explicitly declares safe parallel tasks with disjoint write sets.
- Implementation may only touch files declared by the active task.

### [SDD HARD STOP] — refuse work without an approved gate

If asked to implement without an approved pipeline:

```
[SDD HARD STOP]
Cannot proceed without an approved gate.
Missing:
- [ ] SPEC.md/PLAN.md/TASKS.md with **Status:** Aprovado
- [ ] a [-] reservation by the calling agent
What I can do now:
- Write the missing artifact as Draft for operator review
- Resolve open questions via dadaia-grill-me
- Diagnose without modifying production files
```

Bypass phrases ("only a small change", "no spec needed", "this is urgent")
trigger the HARD STOP. There is no emergency override at this layer.

If implementation diverges from approved SPEC: stop, describe the divergence,
ask the operator whether to re-implement within scope or open a new release.
Never edit SPEC.md to justify code already written.

---

## 4. Spec Context resolution + ACTIVE.md

The workspace hosts multiple Spec Context Projects under `repos/<slug>/specs/`.
Resolve the active context in priority order:

1. Env var `DADAIA_CONTEXT=<slug>` → `repos/<slug>/specs/`.
2. State file `.dadaia/states/primary_context.json` (field `specs_dir`).
3. CLI fallback: `dadaia context show --json`.

If none resolves: stop and ask the operator to run `dadaia context activate
<name>`. Then load (in order):

```bash
cat <specs-dir>/constitution.md
cat <specs-dir>/memory/{architecture,tech-stack}.html
cat <specs-dir>/memory/product/index.html
cat <specs-dir>/releases/ACTIVE.md
cat <specs-dir>/releases/<release-id>/{SPEC,PLAN,TASKS}.md  # per current phase
```

`_archive/` and `backlog/` are NOT sources of approval; ignore unless the
operator explicitly requests history.

---

## 5. Lib-originated assets — non-edit rule

Any file whose path appears in `.dadaia/agentic/manifest.json` is
**lib-originated**. This covers projections under `.agents/`, `.claude/`,
`.codex/`, `.opencode/`, plus the workspace-root and consumer-repo
`AGENTS.md` / `CLAUDE.md` pair.

- NEVER edit a lib-originated projection file in place.
- NEVER delete a lib-originated projection without re-installing afterwards.

Correct workflow:

1. Edit the source under `dadaia_workspace/public/<type>/<file>` (in the
   `dadaia-workspace` repository).
2. Commit in `dadaia-workspace`.
3. `dadaia public stage && dadaia public install --target all`.
4. Verify with `dadaia public doctor` — every entry must report `[ok]`.

`dadaia public install --target all --force` is reserved for the **operator**
and the `devops-engineer` agent. Dispatchers (`project-manager`,
`project-auditor`) NEVER invoke `--force`; on drift they file a report and
request operator repair.

---

## 6. Domain-scoped guardrails pattern

Operators may place additional `CLAUDE.md` / `AGENTS.md` files inside any
subdirectory to scope guardrails to that subtree (e.g. `services/CLAUDE.md`
for service rules, `repos/<game>/AGENTS.md` for engine-specific rules).

- Claude Code merges parent + nested files automatically; Codex and OpenCode
  do the equivalent.
- Domain-scoped pairs are **operator-authored**, not lib-managed. The lib
  installer and doctor MUST NOT touch them. They are identified by living in
  subdirectories with no `.dadaia/` marker and not registered as consumer repos.

---

## 7. Memory atoms reference

Atomic product memory lives under `<specs-dir>/memory/` as HTML files. Markdown
in `memory/` is legacy and flagged by `dadaia specs doctor`.

| Path | Purpose |
|------|---------|
| `memory/architecture.html` | Layer rules, modules, dependency contracts. |
| `memory/product/index.html` | Vision, users, ordered feature catalog. |
| `memory/product/<slug>.html` | One HTML per feature in production. |
| `memory/tech-stack.html` | Approved technologies and constraints. |
| `assets/<scope>/<id>.png` | Screenshots referenced by memory HTML. |

Atomicity contract: memory describes the product **as it is now**, never as a
changelog. Forbidden sections in any memory HTML: `Changelog`, `History`,
`Histórico`, `Versions`. Change history lives in the release's `CLOSURE.md`
and under `_archive/releases/`. Write permission is gate-locked to the
**CLOSURE** phase and reserved to `product-engineer`.

---

## 8. Agent inventory — 20 agents in 3 tiers

The dispatch model is hierarchical. Only **dispatchers** call other agents.
The **curator** owns specs. **Leaf specialists** do not chain further dispatch.

### Dispatchers — T1 (2)

- **project-manager** — orchestrator. Categorises operator demand, dispatches
  the right specialist, mediates via the Decision Authority Matrix. Reports only.
- **project-auditor** — drift + dead-code auditor. Records and recommends a
  release; never fixes drift. Reports only.

### Curator — T2 (1)

- **product-engineer** — sole author of `specs/releases/<id>/{SPEC,PLAN,TASKS,
  CLOSURE}.md`, `ACTIVE.md`, `specs/memory/**` (CLOSURE-only). No dispatch.

### Leaf specialists — T3 (17, alphabetical)

| Agent | Scope (one line) | Write-allowlist roots |
|-------|------------------|-----------------------|
| ai-engineer | AI entities (skills/rules/workflows/commands/agents/hooks); prompt-efficiency | `public/{agents,skills,workflows,commands,rules,hooks}/**` |
| backend-engineer | Heavy backend (Go, DB), services, APIs | `repos/<service>/**` |
| code-reviewer | Diff review on a PR or staged set (no authoring) | `.dadaia/reports/<ctx>/code-reviewer/**` |
| data-analyst | BI / dashboards / data viz; pairs with design-specialist | `repos/dd-chain-explorer/{notebooks,dashboards}/**` |
| data-engineer | Data pipelines (Spark/Delta/Iceberg/Kafka/Airflow) | `repos/dd-chain-explorer/{pipelines,dbt,airflow}/**` |
| design-specialist | UX/UI specs, sketches, design tokens (handoff to FE) | `.dadaia/reports/<ctx>/design-specialist/**` |
| devops-engineer | CI/CD, GitHub Actions, deploy infra, `dadaia public install` | `.github/**`, `dadaia_workspace/infrastructure/**` |
| frontend-engineer | Browser code (HTML/CSS/TS/React) | `repos/<web-app>/{src,public}/**` |
| game-designer | Game assets, materials, maps, audio, pipeline scripts | `repos/tauan-games/<game>/{Content,assets,scripts}/**` |
| game-developer | Game logic, mechanics, physics, AI (UE5/Three/Phaser) | `repos/tauan-games/<game>/{Source,src}/**` |
| game-tester | Engine test automation, evidence reports | `repos/tauan-games/<game>/Tests/**` |
| qa-engineer | E2E criteria, Playwright/Cypress, deploy validation | `tests/e2e/**`, `repos/*/tests/e2e/**` |
| researcher | External-source investigation against whitelists | `.dadaia/reports/<ctx>/researcher/**` |
| security-reviewer | OWASP / threat-modeling review (no authoring) | `.dadaia/reports/<ctx>/security-reviewer/**` |
| software-architect | Architectural audits, layer design, ADRs | `.dadaia/reports/<ctx>/software-architect/**` |
| software-engineer-node | Server-side Node/TS tooling, CLIs, opencode glue | `dadaia_workspace/{features,infrastructure}/**`, `tests/**`, `scripts/**` |
| software-engineer-python | Python implementation (CLI, lib, tooling), unit + integration tests | `dadaia_workspace/**`, `tests/**`, `scripts/**`, `data/AGENTS.md` |

Every agent emits an HTML report into
`.dadaia/reports/<context>/<agent>/<UTC>-<slug>.html` with a sibling
`<stem>.handoff.json` sidecar (`handoff-v1` schema). The sidecar is mandatory.

---

## 9. Model assignments — 20 agents × 3 runtimes

| Agent | Claude Code (`model:`) | OpenCode (`opencode_model:`) | Codex tier |
|-------|------------------------|------------------------------|------------|
| project-manager | claude-opus-4-7 | (same) | heavy |
| project-auditor | claude-opus-4-7 | (same) | heavy |
| product-engineer | claude-opus-4-7 | claude-sonnet-4-6 | heavy |
| software-architect | claude-opus-4-7 | claude-sonnet-4-6 | heavy |
| ai-engineer | claude-opus-4-7 | (same) | heavy |
| game-designer | claude-opus-4-7 | (same) | heavy |
| game-tester | claude-opus-4-7 | (same) | heavy |
| software-engineer-python | claude-sonnet-4-6 | (same) | light |
| software-engineer-node | claude-sonnet-4-6 | (same) | light |
| backend-engineer | claude-sonnet-4-6 | (same) | light |
| frontend-engineer | claude-sonnet-4-6 | (same) | light |
| qa-engineer | claude-sonnet-4-6 | (same) | light |
| devops-engineer | claude-sonnet-4-6 | (same) | light |
| code-reviewer | claude-sonnet-4-6 | (same) | light |
| security-reviewer | claude-sonnet-4-6 | (same) | light |
| researcher | claude-sonnet-4-6 | (same) | light |
| design-specialist | claude-sonnet-4-6 | (same) | light |
| data-engineer | claude-sonnet-4-6 | (same) | light |
| data-analyst | claude-sonnet-4-6 | (same) | light |
| game-developer | claude-sonnet-4-6 | (same) | light |

Values are sourced from each agent's frontmatter. Do not invent.

---

## 10. dadaia-academy + dadaia-workspace panel

- **`dadaia academy`** — interactive courses for onboarding to SDD and the
  agent topology. Run `dadaia academy` (no args) to launch the picker.
- **`dadaia panel`** — live workspace state and agent-topology visualisation;
  shows active context, active release phase, registered dev servers, agent
  inventory, and projection drift.

These two commands are the recommended entry points for any operator new to
this workspace.

---

## 11. Pre-write checklist

Before editing **any** file under `specs/`, `dadaia_workspace/public/`, or a
consumer repo's production source:

1. `dadaia context show --json` — confirm the active Spec Context.
2. Read `<specs-dir>/constitution.md`.
3. Read `<specs-dir>/memory/architecture.html`,
   `<specs-dir>/memory/product/index.html`,
   `<specs-dir>/memory/tech-stack.html`.
4. Read `<specs-dir>/releases/ACTIVE.md`. Note the `release:` and `phase:`.
5. Read `SPEC.md`, then `PLAN.md`, then `TASKS.md` of the active release. All
   must contain `**Status:** Aprovado` before implementation begins.
6. Identify your task ID in `TASKS.md`. It must be `[ ]` OPEN. Flip to `[-]`
   and commit `chore(tasks): start <task-id>` BEFORE editing production.
7. Run `dadaia specs doctor` and `dadaia public doctor` — both green.
8. After completing the task: flip the marker to `[x]` and commit with a
   conventional-commit message that includes the task ID.
