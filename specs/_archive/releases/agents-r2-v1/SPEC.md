# Spec: Release — agents-r2-v1

> **Status:** Aprovado
> **Approved:** 2026-05-18 (pending operator review)
> **Approved-by:** operator (design pre-approved in dispatch brief)
> **Release ID:** agents-r2-v1
> **Owner:** product-engineer
> **Created:** 2026-05-18
> **Phase:** SPEC
> **Stakeholders:** operator (decision authority), product-engineer (curator + spec author), software-architect (path-scope gate pattern review), software-engineer (gate hook implementation), devops-engineer (projection consistency), qa-engineer (path-violation regression test)
> **Branch:** `release/agents-r2-v1` (cut from `main` at `f449833`, post `agents-r1-v1` archive)
> **Predecessor:** `agents-r1-v1` (CLOSED at `f449833`) — shipped 16 agents + 15 workflows + 3-tier topology + declarative `paths` field
> **Discovery inputs:**
> - Operator dispatch brief (workflow trimming rationale + path-scope activation + tool reductions)
> - Atomic memory (post agents-r1-v1 CLOSURE): `specs/memory/architecture.html`, `specs/memory/product/index.html`, `specs/memory/product/agent-orchestration.html`
> - Constitution: `specs/constitution.md` Pilar 2 (orquestração multi-agente)
> - Backlog candidates referencing this release: "Promote `paths` field from declarative to gate-enforced (target release: `agents-r2-v1`)" and "Sub-agent promotion of `dadaia-grill-me` (target release: `agents-r2-v1`)" — the grill-me sub-agent promotion is **explicitly deferred again** to a later release (see §6 Out of scope).

---

## 1. Sumário

After shipping the 3-tier dispatcher topology in `agents-r1-v1` (16 agents + 15 workflows
+ declarative `paths` field), this release performs **seven surgical refinements** that
turn the topology from "complete" into "lean + consolidated":

**Lean (FR1–FR3 — original r2 scope):**

1. **Workflow trim 15 → 7** — drop 8 routing-only workflows and re-express their intent
   as **PM playbooks** inside the `project-orchestration` skill. Keeps every workflow
   where prompt-chaining gates or parallelization justify the declarative cost.
2. **Path-scope gate activation** — promote the `paths:` frontmatter field from
   declarative-only (r1) to runtime-enforced via a pre-write hook that validates the
   target path against the active agent's `write_allowlist`. Rule-of-prose
   (`.claude/rules/*-scope.md`) becomes human documentation; the gate becomes
   the actual enforcement.
3. **Tool surface reductions (Bash from PE and software-architect)** — after the
   path-scope gate prevents writes outside declared allowlists, drop `Bash` from
   `product-engineer` (delegate `dadaia specs doctor` and `git status` invocations to
   PM, which holds the orchestrator role) and `software-architect` (Bash present but
   unused in the actual workflow).

**Consolidated (FR6–FR10 — expanded scope after operator review):**

4. **Rules folder trim 6 → 2** — inline per-agent scope rules (PM / project-auditor /
   design-specialist) into their respective agent bodies; move the workspace-wide
   lib-projection invariant into `AGENTS.md`. Only genuine cross-agent boundaries
   (`game-agents-coordination`, `game-developer-scope`) remain as rule files.
5. **Workspace-root `CLAUDE.md` and `AGENTS.md` unified** — the lib ships an
   **identical** pair (same content under two filenames; Claude Code reads
   `CLAUDE.md`, Codex/OpenCode read `AGENTS.md`). Both files contain **lib-general
   workspace guardrails only**: venv policy, SDD release-lifecycle enforcement,
   `dadaia` CLI reference, dadaia-academy mention, dadaia-workspace panel mention,
   16-agent inventory + PM-led dispatch model, lib-projection invariant, memory
   atoms reference, and the domain-scoped guardrails pattern. Final shape ≤ 280
   lines. Hostinger / redacted-infra / redacted-infra / Traefik / VPS content is **excluded** from
   both files — that content moves to operator-managed `services/CLAUDE.md` +
   `services/AGENTS.md` (FR10).
6. **Skill assignment fixes** — wire 2 orphan skills (`dadaia-workspace-doctor`,
   `dev-server-registry`) to their correct owners (devops + PM, frontend respectively).
   No other skill changes; all 31 others are correctly assigned.
7. **Workspace operator-notes archival (optional)** — record CLOSURE-time TODO for
   the operator to decide on archiving `multi-agent-orchestration-v{1,2}.md` from
   the workspace root. No silent move; FR9 is not a hard criterion.
8. **Domain-rule extraction to `services/`** — the lib release coordinates with a
   manual operator migration: redacted-infra/redacted-infra/Traefik content currently sitting in
   workspace-root `/home/marco/workspace/dadaia/CLAUDE.md` moves to operator-authored
   `services/CLAUDE.md` + `services/AGENTS.md` (identical pair, NOT lib-projected).
   The lib ships the new identical projection; the operator does the manual content
   move. The end state: workspace-root files are thin lib projections; domain rules
   live next to the domain (`services/` for VPS services).

No new agents, no new skills, no new rules, no new workflows. The release is
**subtractive + consolidative + enforcement-flip + scope-boundary clarification**,
with one new file in `dadaia_workspace/` (the path-scope gate logic), edits to
existing agent frontmatter + the `project-orchestration` skill + 3 agent bodies
(FR6 inlining) + lib source `data/AGENTS.md` rewrite (Option C: single source
fanned out to `AGENTS.md` + `CLAUDE.md` at each projection target),
a manifest update (rewritten source SHA for `data/AGENTS.md`; `data/CLAUDE.md`
does not exist as a source), a new installer function that performs the
dual-name projection at workspace root + each consumer-repo root with `.dadaia/`
marker, and a 4 → archive `git mv` for the dropped rule files. FR10 declares a
coordinated manual operator migration step outside the lib release's own CI
gates.

---

## 2. Motivação

The operator's diagnosis after using the 3-tier topology for one day:

1. **15 workflows are too many to scan.** Anthropic's "Building Effective Agents"
   guidance is explicit: declarative workflows earn their weight only for
   prompt-chaining with gates or parallelization. **Pure routing** (classify →
   dispatch single agent → done) is exactly what the PM agent does natively as
   its intake protocol. Declaring routing as YAML duplicates intent and creates
   maintenance drag — every new agent edit touches multiple workflow files.
2. **The `paths:` field is dead weight without enforcement.** r1 added it to
   `AgentDTO._ALLOWED_FIELDS` but no agent declares it and no code reads it.
   Until the gate enforces, the prose rule files (`.claude/rules/<agent>-scope.md`)
   are the *only* statement of what an agent may write — and they live outside
   the loop that the harness actually runs. The risk is silent scope creep:
   an agent writes outside its rule-of-prose allowlist and nothing blocks it.
3. **PE and software-architect have `Bash` that is mostly idle.** PE used Bash
   for `dadaia specs doctor` and `dadaia context show --json`; both are
   discoverable by PM and can be invoked there before/after PE writes the spec.
   software-architect has Bash on its frontmatter but the audit flow does not
   actually shell out — it reads, greps, writes a report. Trimming both moves
   them closer to the "no side effects outside reports" pattern that the leaf
   specialists already follow.

These three motivators converge on a single release because (b) is the
**precondition** for safely doing (c): without the gate, PE losing Bash is
just a description change; with the gate, PE losing Bash is enforced — PE
cannot shell out even if the description forgot to forbid it.

---

## 3. Requisitos Funcionais

### FR1 — Trim workflow set from 15 to 7

**KEEP (7 workflows):** each justified by prompt-chaining with gates OR by parallelization.

| Workflow | Justification |
|---|---|
| `spec-refinement` | 5 stages, parallel discovery + 3 gates (SPEC/PLAN/TASKS approved) |
| `cross-cutting-feature` | 4 stages, contract-review gate |
| `onboarding-new-repo` | 4 stages with gates (scan → SPEC → PLAN → TASKS) |
| `hotfix-release` | 4 stages, release-lifecycle gates (origin in `## Hotfixes pendentes`) |
| `game-dev-cycle` | 4 stages, game-lifecycle gates |
| `audit-cycle` | 6 stages, 4-way parallel + synthesis (project-auditor primary) |
| `code-review-fan-out` | 4 stages, 3-way parallel (code/security/design) |

**DROP (8 workflows):** routing-only — move their intent into PM playbook text recipes.

| Workflow | Migration target |
|---|---|
| `game-spec-definition` | MERGE into `spec-refinement` playbook entry with `scope=game` note |
| `architecture-review` | PM playbook: "dispatch software-architect; on output, PM filters and asks PE for TASKS" |
| `tdd-cycle` | PM playbook: "dispatch software-engineer with TDD framing prompt" |
| `bug-fix-fastlane` | PM playbook: "classify bug severity; dispatch SE or BE; close via qa-engineer" |
| `game-bugfix` | PM playbook: "dispatch game-developer; close via game-tester" |
| `security-patch` | PM playbook: "dispatch security-reviewer; if HIGH/CRITICAL, dispatch SE; close via QA + security-reviewer re-check" |
| `deploy-validation-only` | PM playbook: "dispatch qa-engineer; return verdict to operator" |
| `design-validation` | PM playbook: "dispatch qa-engineer for screenshots; then dispatch design-specialist for review" |

All 8 `*.workflow.md` files MUST be deleted from `dadaia_workspace/public/workflows/`.
The `project-orchestration` skill gains a new `## PM Playbooks` section with one
recipe per dropped workflow (≤ 20 lines per recipe; 8 recipes ≤ 160 lines total).

### FR2 — Activate `paths:` field with runtime enforcement

**FR2.1 — Every agent declares `paths:` in frontmatter.** Schema:

```yaml
paths:
  write_allowlist:
    - <glob relative to workspace root>
    - <glob>
  read_allowlist:   # optional; absent = read-all
    - <glob>
```

Default `write_allowlist` per agent (operator-validated in dispatch brief):

| Agent | `write_allowlist` |
|---|---|
| `project-manager` | `.dadaia/reports/<ctx>/project-manager/**` |
| `project-auditor` | `.dadaia/reports/<ctx>/project-auditor/**` |
| `code-reviewer` | `.dadaia/reports/<ctx>/code-reviewer/**` |
| `security-reviewer` | `.dadaia/reports/<ctx>/security-reviewer/**` |
| `researcher` | `.dadaia/reports/<ctx>/researcher/**` |
| `design-specialist` | `.dadaia/reports/<ctx>/design-specialist/**`, `specs/assets/**` |
| `product-engineer` | `specs/**` (except `_archive/`), `.dadaia/reports/<ctx>/product-engineer/**` |
| `software-engineer` | `dadaia_workspace/**` (except `dadaia_workspace/public/`), `tests/**`, `.dadaia/reports/<ctx>/software-engineer/**` |
| `backend-engineer` | analogous to SE, scoped to backend-relevant globs |
| `frontend-engineer` | analogous to SE, scoped to FE-relevant globs + `specs/assets/**` for ASCII references |
| `qa-engineer` | `tests/**`, `.dadaia/reports/<ctx>/qa-engineer/**` |
| `devops-engineer` | `.github/**`, `dadaia_workspace/**` (CI-related), `services/**`, `.dadaia/reports/<ctx>/devops-engineer/**` |
| `software-architect` | `.dadaia/reports/<ctx>/software-architect/**` |
| `game-developer` | `repos/redacted-slug/**` (logic globs), `.dadaia/reports/<ctx>/game-developer/**` |
| `game-designer` | `repos/redacted-slug/**` (design globs + Python pipeline scripts), `.dadaia/reports/<ctx>/game-designer/**` |
| `game-tester` | `repos/redacted-slug/**` (test globs), `.dadaia/reports/<ctx>/game-tester/**` |

`<ctx>` is the active Spec Context Project name resolved by the hook from
`primary_context.json`.

**FR2.2 — Pre-write hook validates the target path.** Implementation surface
(PE proposes; software-architect picks the pattern in PLAN):

- Extend the existing `sdd-spec-gate.sh` (already a `Write/Edit/MultiEdit` PreToolUse
  hook) with a **path-scope check** that runs after the existing TASKS-marker check.
- The hook reads the active agent from the runtime (Claude harness env var or
  agent-id surfaced in tool input metadata; software-architect picks).
- The hook resolves the agent's `write_allowlist` from its frontmatter via the
  agent reader (caches the resolution).
- On mismatch, the hook returns `{"decision":"block","reason":"[PATH SCOPE ERROR] agent <X> cannot write to <path>; allowlist: <list>"}`.

**FR2.3 — Hard error format.** Violations return the message:

```
[PATH SCOPE ERROR] agent <name> cannot write to <path>. write_allowlist: <comma-separated>.
```

**FR2.4 — Fallback behaviour.** If the active agent cannot be determined (env var
missing, agent not in store), the hook **fails open** with a warning logged to
`/tmp/sdd-gate.log` — consistent with the existing v3 fail-open philosophy of the
gate. This preserves human-driven invocations (cli + Claude top-level) where no
agent persona is active.

### FR3 — Remove `Bash` from `product-engineer` and `software-architect`

**FR3.1 — product-engineer frontmatter loses `Bash`.** New `tools` list:

```yaml
tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
```

PE's prompt body MUST be updated where it tells PE to "run `dadaia specs doctor`,
`dadaia context show --json`, `cat .../ACTIVE.md`" — replace these with: "ask
project-manager (the orchestrator) to run the check before invoking you, OR ask
the operator directly if invoked without PM in the loop". The fix is descriptive
only; PM is already responsible for the gate-readiness check before dispatching PE.

**FR3.2 — software-architect frontmatter loses `Bash`.** New `tools` list:

```yaml
tools:
  - Read
  - Glob
  - Grep
  - Write
```

software-architect's body has no Bash invocations in its actual flow — review/audit
output is purely textual. The removal is a documentation-truth alignment.

**FR3.3 — All other agents keep their Bash tool exactly as today.** No other tool
edits in this release.

### FR4 — Update `project-orchestration` skill with PM Playbooks

The skill gains a new `## PM Playbooks` section after the current "Agent + workflow
inventory matrices" content. One subsection per dropped workflow:

```markdown
### Playbook — <workflow-name-now-dropped>

**When operator says:** <pattern, e.g. "review my code", "fix this bug fast", "deploy validation">

**Recipe:**
1. <step 1: classify / interview operator if ambiguous>
2. <step 2: dispatch <agent> with input <X>>
3. <step 3: on output, dispatch <next agent> OR return verdict to operator>
4. <step 4: close + report-emit>

**Anti-pattern (not this playbook):** <a sibling playbook that this is NOT — disambiguate>
```

Eight playbooks, target ≤ 20 lines each, total addition ≤ 160 lines to the skill
(current size 214 → target ≤ 380, well below the SDD-PLAN-300-line ceiling which
applies only to PLAN.md, not skills).

### FR5 — Memory updates at CLOSURE

- `specs/memory/product/agent-orchestration.html` — re-render reflecting:
  - 16 agents + **7** workflows (was 15) + **8 PM playbooks**
  - Path-scope gate is now runtime-enforced
  - PM Playbooks are the new home of routing-only flows
  - Rules folder shrunk from 6 → 2; per-agent scope now lives in each agent body
  - Lib `AGENTS.md` is the canonical lib-level system doc; workspace
    `CLAUDE.md` holds operator product content (disjoint scopes)
  - Skill→agent inverted index is complete (zero orphans)
- `specs/memory/product/index.html` — catalog item `agent-orchestration` description
  bumped from "15 workflows" → "7 workflows + 8 PM playbooks + 2 cross-agent rules";
  capability-map Mermaid `WF[15 workflows]` → `WF[7 workflows]`.
- `specs/memory/architecture.html` — `<section id="layers">` gains:
  (a) note that the path-scope gate is the runtime enforcement layer for the
  agent-`paths` declaration; (b) note that per-agent scope rules are now agent-body
  sections, not separate rule files; (c) note that `AGENTS.md` is the lib-level
  cross-cutting doc, projected identically to all consumers.
- `specs/memory/tech-stack.html` — **no change** (no dependencies touched).

### FR6 — Rules folder reorganization (6 → 2 files)

After r1 settled the 16-agent topology, the `dadaia_workspace/public/rules/` folder
mixed two distinct concerns:

1. **Per-agent scope rules** (`project-manager-scope.md`, `project-auditor-scope.md`,
   `design-specialist-scope.md`) — these belong **inside the agent file** itself.
   Keeping them as separate rule documents creates a second source-of-truth that
   drifts from the agent body. Each agent must own its own scope statement.
2. **Workspace-wide invariants** (`dadaia-workspace-dev-guardrail.md`) — these
   describe rules that apply to ALL agents (e.g. "do not edit lib-originated
   projections"). They belong in the lib-shipped `AGENTS.md`, where every harness
   loads them automatically as cross-cutting context.
3. **Genuine cross-agent coordination rules** (`game-agents-coordination.md`,
   `game-developer-scope.md`) — these define **multi-agent boundaries** and
   Decision Authority Matrices. They cannot be inlined into a single agent without
   losing the cross-cutting semantics, so they STAY as separate rule files.

**FR6.1 — Inline `project-manager-scope.md` into `project-manager.md`.** Add a new
`## Scope and forbidden actions` section (use heading verbatim) to the agent body,
containing the rule's content (Domínio / Permitido / Proibido / Output mandatório /
Escalation). The rule file is then `git mv`'d to `_archive/legacy-rules/<UTC-timestamp>/`.

**FR6.2 — Inline `project-auditor-scope.md` into `project-auditor.md`.** Same
pattern as FR6.1. Same archival destination.

**FR6.3 — Inline `design-specialist-scope.md` into `design-specialist.md`.** Same
pattern as FR6.1. Same archival destination.

**FR6.4 — Move `dadaia-workspace-dev-guardrail.md` content into `AGENTS.md`.**
The rule body becomes a new section in `AGENTS.md` titled
`## Lib-originated assets — non-edit rule` (see FR7). The rule file is then
`git mv`'d to `_archive/legacy-rules/<UTC-timestamp>/`. This consolidates the
single-source-of-truth for the lib-projection invariant.

**FR6.5 — Keep `game-agents-coordination.md` and `game-developer-scope.md`.**
These are cross-agent boundaries (Decision Authority Matrix and the 13-agent
forbid-list for `repos/redacted-slug/` respectively); both must remain as rule files.

**FR6.6 — Final state.** `dadaia_workspace/public/rules/` contains exactly two
files: `game-agents-coordination.md`, `game-developer-scope.md`. Acceptance:
`ls dadaia_workspace/public/rules/ | wc -l` returns `2`. Projections in
`.claude/rules/`, `.codex/rules/`, `.opencode/rules/` mirror this state
after `dadaia public install`.

### FR7 — Lib-shipped `CLAUDE.md` + `AGENTS.md` rewrite (identical pair)

The lib-shipped `dadaia_workspace/public/data/AGENTS.md` (currently 365 lines)
mixes lib-general content with workspace-specific (Hostinger / redacted-infra / redacted-infra)
content, and is stale on multiple axes. This release **rewrites it** into a pure
lib-level workspace guardrail document AND **introduces a new lib-tracked
`CLAUDE.md`** with **byte-identical** content. The two filenames exist because
different harnesses read different conventions (Claude Code reads `CLAUDE.md`;
Codex and OpenCode read `AGENTS.md`); the lib guarantees the content is the same.

**Why identical pair:** the operator's words — *"AGENTS.md and CLAUDE.md should
even contain the same information. GUARDRAILS for the workspace, like using venv,
SDD pattern enforced, endorsement of the use of dadaia-workspace CLI to operate
it"*. Both files are lib-projected to the workspace root and to consumer-repo
roots; both files are read by the harness that owns each convention.

**FR7.0 — Source of truth and identical-content invariant (Option C, architect-decided).**

The software-architect ADR `2026-05-19T003956Z-adr-claude-agents-parity` resolved
the prior PLAN-deferred choice. The chosen mechanism is **Option C — single source
file, dual-name projection at every target**:

- **Single source of truth (one file only):**
  `dadaia_workspace/public/data/AGENTS.md` — REWRITTEN (currently 365 lines).
  - `dadaia_workspace/public/data/CLAUDE.md` **does NOT exist** as a source file.
    Do not create it; do not commit it; do not track it in the manifest.
- **Dual-name projection at install time.** `dadaia public install` reads the
  single source `data/AGENTS.md` and writes it under TWO filenames at EACH
  projection target:
  - At each target directory `T`: write `T/AGENTS.md` AND `T/CLAUDE.md`, both
    byte-copied from the same source.
  - Because both files originate from the same byte stream, byte-identity is a
    structural property of the installer, not a doctor-enforced invariant.
- **Projection targets — 4 in total (2 directories × 2 filenames each):**
  1. `<workspace-root>/AGENTS.md`
  2. `<workspace-root>/CLAUDE.md`
  3. `<workspace-root>/repos/<consumer-slug>/AGENTS.md` (each registered consumer repo)
  4. `<workspace-root>/repos/<consumer-slug>/CLAUDE.md` (each registered consumer repo)

  The "registered consumer repo" set is discovered at install time by scanning
  `<workspace-root>/repos/*/` for the presence of a `.dadaia/` marker directory
  (the same discovery contract already used by the lib-projection rule). Repos
  without `.dadaia/` are skipped with a `[skip]` log line — idempotent, never
  errors.

- **Doctor parity reporting.** `dadaia public doctor` emits four separate
  `[ok|fail]` lines per source file — one per projection target. The label
  format is:

  ```
  [ok]   root:AGENTS.md     → <workspace>/AGENTS.md
  [ok]   root:CLAUDE.md     → <workspace>/CLAUDE.md
  [ok]   repos/<slug>:AGENTS.md → <workspace>/repos/<slug>/AGENTS.md
  [ok]   repos/<slug>:CLAUDE.md → <workspace>/repos/<slug>/CLAUDE.md
  ```

  All four comparisons are run against the **same** source SHA-256
  (`data/AGENTS.md`). A `[fail]` on any of the four indicates projection drift
  (manual edit of a projected file, or installer bug). There is NO separate
  `data/CLAUDE.md` source SHA — it does not exist.

- **Nested-pair non-interference invariant.** When FR10 adds
  `services/CLAUDE.md` and `services/AGENTS.md` (operator-authored, NOT
  lib-managed), the installer MUST NOT touch them and the doctor MUST NOT
  include them in any parity check involving the lib source. The
  identification contract: nested pairs live in subdirectories that contain
  no `.dadaia/` marker and are not registered consumer repos.

**FR7.1 — Lib content scope: lib-general workspace guardrails ONLY.** Both
files contain (the operator's literal scope list):

- venv policy (`.dadaia/.venv` enforcement; never `pip install` outside venv).
- SDD release-lifecycle enforcement (8-phase pipeline, `Status: Aprovado` gates,
  HARD STOP semantics, ACTIVE.md as phase pointer).
- `dadaia` CLI reference: `context`, `specs`, `public`, `server`, `reports`,
  `academy`, `doctor`, `export`, `repos` — each with one-line semantics.
- **dadaia-academy** mention — "interactive courses available via
  `dadaia academy` for onboarding to SDD + agent topology".
- **dadaia-workspace panel** mention — "live workspace state and agent topology
  visualisation via `dadaia panel`".
- 16-agent inventory + PM-led dispatch model (the 3-tier topology:
  dispatchers / curator / leaf specialists).
- Lib-projection invariant: never edit `.agents/`, `.claude/`, `.codex/`,
  `.opencode/` directly; always edit `dadaia_workspace/public/` then
  `stage → install --target all → doctor`.
- Memory atoms reference: `specs/memory/architecture.html`,
  `specs/memory/product/index.html` (catalog) +
  `specs/memory/product/<slug>.html` (per-feature), `specs/memory/tech-stack.html`;
  atomicity contract; gate-locked to CLOSURE phase.
- **Domain-scoped guardrails pattern** (NEW — explained explicitly): workspace
  operators can author per-subdirectory `CLAUDE.md` and `AGENTS.md` files to
  scope domain-specific guardrails to that directory. Claude Code merges
  parent + nested files automatically; Codex/OpenCode do the equivalent.
  Example: `services/CLAUDE.md` for VPS service rules. Per-subdirectory files
  are **NOT lib-managed** — they are operator-authored and operator-maintained.

**FR7.2 — Forbidden content in the lib pair.** Neither
`dadaia_workspace/public/data/CLAUDE.md` nor
`dadaia_workspace/public/data/AGENTS.md` may contain ANY of these strings
(case-insensitive):

- `redacted-infra`, `redacted-infra`, `Traefik`, `Hostinger`
- `tirith`, `dmPolicy`, `REDACTED_CONFIG`
- `redacted-host`, `0.0.0.0`, `0.0.0.0`, `hstgr`, `vps-`
- Any reference to specific containers (`vps-redacted-infra-jobs-1`, etc.), VPS infra,
  firewall rules, watchdog cron, OS-level config, Telegram allowlists, redacted-infra
  channels.

Verification: a single grep invocation (case-insensitive) over the lib pair
must exit non-zero (no matches). See C16 update.

**FR7.3 — §2 SDD pipeline rewrite for release-lifecycle model.** Replace any
reference to `specs/features/<service>/<feature>/` with
`specs/releases/<release-id>/`. Document the 8-phase release lifecycle
(DISCOVERY → SPEC → PLAN → TASKS → IMPLEMENTATION → CLOSURE → ARCHIVED),
atomic-memory HTML model, and the `Status: Aprovado` marker.

**FR7.4 — Lib-projection invariant section consolidates the rule.** The
section sourced from `dadaia-workspace-dev-guardrail.md` (which FR6.4
archives) becomes a section in the lib pair titled
`## Lib-originated assets — non-edit rule`. Includes: prohibition (no direct
edits in `.agents/.claude/.codex/.opencode/`), workflow
(`stage → install --target all`), force-install authority (operator +
devops-engineer ONLY; PM and project-auditor NEVER), verification
(`dadaia public doctor`).

**FR7.5 — Agent inventory section for 16 agents.** Replace the 6-agent list
with all 16 currently shipped agents in three tiers:

- **Dispatchers (2):** `project-manager`, `project-auditor`.
- **Curators (1):** `product-engineer`.
- **Leaf specialists (13):** `software-architect`, `software-engineer`,
  `backend-engineer`, `frontend-engineer`, `qa-engineer`, `devops-engineer`,
  `code-reviewer`, `security-reviewer`, `researcher`, `design-specialist`,
  `game-developer`, `game-designer`, `game-tester`.

For each agent: 1-line "when to use" + 1-line "NOT for" + report path. Total
section size ≤ 120 lines.

**FR7.6 — Model assignments section for 16 agents.** A table with all 16
agents and their `model:` frontmatter values (Claude Code column). OpenCode
column lists `opencode_model:` value or `(same)`. Codex column lists the
workload tier (heavy / light). Source the values from each agent's actual
frontmatter — do not invent.

**FR7.7 — Checklist update for HTML memory atoms and release-lifecycle paths.**
Replace `specs/memory/architecture.md` → `specs/memory/architecture.html`,
`specs/memory/product.md` → `specs/memory/product/index.html` (catalog entry)
+ `specs/memory/product/<feature-slug>.html` (specific feature on demand),
`specs/memory/tech-stack.md` → `specs/memory/tech-stack.html`. Remove
references to `specs/foundation/SPEC.md` and `specs/SPEC.md` (legacy
root-level specs not used in release-lifecycle model). Add
`specs/releases/ACTIVE.md` as the first read.

**FR7.8 — CLI reference section.** Document the surface:

- `dadaia context show --json` / `activate` / `list` — Spec Context resolution.
- `dadaia specs doctor` — SDD-specific structural validator (11 invariants).
- `dadaia public stage` / `install --target all` / `doctor` — projection
  workflow.
- `dadaia server register` / `list` / `unregister` — dev-server registry.
- `dadaia reports validate <path>` — handoff sidecar validator.
- `dadaia academy` — interactive course launcher.
- `dadaia panel` — live workspace + agent topology panel.
- `dadaia doctor` — overall workspace health check.
- `dadaia export` / `repos` — additional utility commands.

**FR7.9 — Final shape.** Both files end as pure lib-level workspace guardrail
documents, ≤ 280 lines each (byte-identical), structured as:

```
1. Identity and tone (≤ 15 lines)
2. venv policy + dadaia CLI reference (≤ 35 lines)
3. SDD — release-lifecycle model (≤ 60 lines)
4. Spec Context resolution + ACTIVE.md (≤ 25 lines)
5. Lib-originated assets — non-edit rule (≤ 25 lines)
6. Domain-scoped guardrails pattern (≤ 15 lines)
7. Memory atoms reference (≤ 20 lines)
8. Agent inventory — 16 agents in 3 tiers (≤ 120 lines)
9. Model assignments — 16 agents x 3 runtimes (≤ 30 lines)
10. dadaia-academy + dadaia-workspace panel pointers (≤ 10 lines)
11. Pre-write checklist (≤ 20 lines)
```

Total ≤ 280 lines; byte-identical across `CLAUDE.md` and `AGENTS.md`.

**FR7.10 — Projection parity.** After
`dadaia public stage && dadaia public install --target all`:

- `<workspace>/CLAUDE.md` and `<workspace>/AGENTS.md` are byte-identical.
- `<repos/<consumer>>/CLAUDE.md` and `<repos/<consumer>>/AGENTS.md` are
  byte-identical (where the consumer applies).
- The four projection roots receive consistent content; no harness sees
  divergent rules.
- Verified by `dadaia public doctor` reporting `[ok]` for every entry AND by
  a new explicit `sha256sum` parity check comparing `CLAUDE.md` vs `AGENTS.md`
  at every projection root.

**FR7.11 — Manifest update (Option C alignment).** `.dadaia/agentic/manifest.json`
tracks a **single source asset**: `data/AGENTS.md`. The manifest entry retains
its existing shape (`path`, `sha256`, `type`), updated to the new content hash
after the rewrite.

- `data/CLAUDE.md` is **NOT a manifest entry**. It does not exist as a source
  file; therefore it has no source SHA and no manifest entry.
- The projection targets generated by `dadaia public install` are
  **runtime-derived** from the single `data/AGENTS.md` source: the installer
  function (see PLAN P11b — proposed name `_install_workspace_guardrail_pair`)
  fans the single source out to four target file paths (workspace root × 2
  filenames, plus each `repos/<slug>/` × 2 filenames, where `<slug>` has a
  `.dadaia/` marker). The manifest does NOT enumerate these targets; the
  installer enumerates them on each invocation by walking `repos/` and reading
  the marker contract.
- `dadaia public doctor` reports four `[ok|fail]` lines per projection (see
  FR7.0 doctor parity reporting), all comparing to the manifest's single
  `data/AGENTS.md` source SHA-256.

### FR8 — Skill→agent assignment fixes (2 orphans wired)

Inverted-index audit of `dadaia_workspace/public/skills/` against agent frontmatter
`skills:` lists found **2 orphan skills** (no agent references them) and 0 wrong
assignments. This release wires the orphans to their correct owners.

**FR8.1 — Wire `dadaia-workspace-doctor` to two agents.**

- `devops-engineer.md` — add `dadaia-workspace-doctor` to its `skills:` list.
  Justification: devops runs `dadaia doctor` and `dadaia public doctor` as part
  of every projection-related task; the skill embeds the doctor invocation
  protocol.
- `project-manager.md` — add `dadaia-workspace-doctor` to its `skills:` list.
  Justification: PM runs doctor as a gate-readiness check before dispatching
  any agent whose work depends on a healthy workspace state.

**FR8.2 — Wire `dev-server-registry` to one agent.**

- `frontend-engineer.md` — add `dev-server-registry` to its `skills:` list.
  Justification: operator's "end-of-work dev server guardrail" (recorded in
  user memory) makes dev-server registration a HARD RULE for FE; the skill
  embeds the `dadaia server register` protocol.

**FR8.3 — Verification script.** A Python script (≤ 50 lines) walks
`dadaia_workspace/public/skills/*/` and checks each skill is referenced in at
least one agent's `skills:` frontmatter. Output: list of orphans (must be empty)
+ list of agents-without-skills (must be empty). To be added under
`tests/scripts/check_skill_orphans.py` (or equivalent) and invoked from CI.
Acceptance: script exits 0 (no orphans, no agents without skills).

**FR8.4 — No other skill rewires.** All 31 other skills are correctly assigned.
This FR only touches the 3 agent files listed above (devops-engineer,
project-manager, frontend-engineer).

### FR9 — Workspace operator notes archival (optional, operator-decided)

The workspace-level files `/home/marco/workspace/dadaia/multi-agent-orchestration-v1.md`
and `/home/marco/workspace/dadaia/multi-agent-orchestration-v2.md` are historical
analyses authored on 2026-05-14 (pre `agents-r1-v1`). They live in the workspace
root, which is operator-owned (not lib-tracked).

**FR9.1 — Operator decision required.** This release does NOT auto-archive these
files. Instead, it records a CLOSURE-time TODO: ask the operator whether to
`git mv` both files to `.dadaia/reports/dadaia-workspace/operator-notes/` (keeps
workspace root clean) or KEEP in place (if still used as working refs).

**FR9.2 — Not a hard FR.** Unlike FR1–FR8, FR9 has no failure mode that blocks
release CLOSURE. If the operator says "leave them", the release ships and the
two files stay. The CLOSURE.md `## Backlog returns` section records the
operator's decision verbatim.

**FR9.3 — Scope boundary.** This release rewrites the workspace-root
`CLAUDE.md` / `AGENTS.md` pair (FR7) and coordinates with a manual operator
migration of redacted-infra/redacted-infra/Traefik content to `services/` (FR10). FR9 is
about a different pair of files (`multi-agent-orchestration-v{1,2}.md`),
not the workspace-root pair.

### FR10 — Domain-rule extraction to `services/CLAUDE.md` + `services/AGENTS.md` (coordinated manual operator migration)

This release reframes the workspace-root `CLAUDE.md` from "operator product
content" into "thin lib projection identical to `AGENTS.md`" (FR7). To preserve
the redacted-infra/redacted-infra/Traefik domain rules that currently live in the workspace
`CLAUDE.md`, those rules must migrate to a new domain-scoped pair at
`services/CLAUDE.md` + `services/AGENTS.md` BEFORE (or at the same moment as)
the lib release ships. Without this migration, the lib release would overwrite
the workspace `CLAUDE.md` with the new identical projection and the domain
rules would be lost from view.

**FR10.0 — Operator-owned step, lib-coordinated.** The lib release ships the
new identical `CLAUDE.md`/`AGENTS.md` projection (FR7); the **operator**
performs the content migration into `services/`. Both steps land together via
the release's PR + the operator's manual action. The lib release's CI gates
do NOT verify the operator step (it happens outside the lib repo's tree);
instead, CLOSURE.md includes an explicit **operator checklist** with the
manual steps and post-conditions (see R10 mitigation update).

**FR10.1 — Target file pair.** The operator creates two new files in the
workspace:

- `/home/marco/workspace/dadaia/services/CLAUDE.md` — NEW.
- `/home/marco/workspace/dadaia/services/AGENTS.md` — NEW (byte-identical to
  the above).

Both files contain ALL of the redacted-infra / redacted-infra / Traefik / Hostinger / VPS
content that currently sits in the workspace-root `CLAUDE.md` (services table,
compose & secrets, redacted-infra Agent section, redacted-infra section, Infrastructure,
Security Checklists). The two files MUST be byte-identical (same convention
as FR7: Claude Code reads `CLAUDE.md`; Codex/OpenCode read `AGENTS.md`).

**FR10.2 — Domain-scope semantics.** Both `services/CLAUDE.md` and
`services/AGENTS.md` are domain-scoped guardrails per the pattern that FR7.1
documents in the lib pair. They apply to ANY task touching files under
`services/`; harnesses merge the parent (`/home/marco/workspace/dadaia/CLAUDE.md`)
with the nested (`/home/marco/workspace/dadaia/services/CLAUDE.md`)
automatically.

**FR10.3 — NOT lib-managed.** Neither `services/CLAUDE.md` nor
`services/AGENTS.md` is tracked by `.dadaia/agentic/manifest.json`. They do
not appear in `dadaia_workspace/public/`. They are operator-authored,
operator-maintained, and never overwritten by `dadaia public install`. The
lib does not own this file pair.

**FR10.4 — Migration coordination protocol.** To land the lib release safely,
the operator and the lib release coordinate as follows (order matters):

1. **Operator BEFORE lib install:** creates `services/CLAUDE.md` and
   `services/AGENTS.md` with the migrated content (copy-paste from current
   workspace-root `CLAUDE.md`, both files identical).
2. **Lib release ships:** `dadaia public stage && dadaia public install --target all`
   propagates the new identical `CLAUDE.md`/`AGENTS.md` pair to workspace root,
   overwriting the prior workspace-root `CLAUDE.md` (which held the
   pre-migration content).
3. **Operator AFTER lib install:** runs the post-condition checks (see FR10.5)
   to confirm the migration landed correctly.

If the operator skips step 1, step 2 will erase the redacted-infra/redacted-infra content
from view (it remains in `git log` history, so it is recoverable, but the
operator must then perform step 1 retroactively). R10 in §7 codifies this
mitigation.

**FR10.5 — Acceptance (recorded in CLOSURE.md and the PR checklist).**

After the release ships AND the operator completes the manual migration, all
of these must hold:

- `services/CLAUDE.md` exists, is non-empty, contains the migrated redacted-infra /
  redacted-infra / Traefik / Hostinger / VPS content from the prior workspace-root
  `CLAUDE.md`.
- `services/AGENTS.md` exists and is byte-identical to `services/CLAUDE.md`
  (`sha256sum` of both must match).
- Workspace-root `/home/marco/workspace/dadaia/CLAUDE.md` is byte-identical to
  `/home/marco/workspace/dadaia/AGENTS.md` (the lib projection — both files
  installed by `dadaia public install`).
- Workspace-root `/home/marco/workspace/dadaia/CLAUDE.md` does NOT contain
  any of the strings in the FR7.2 forbidden list (`redacted-infra`, `redacted-infra`,
  `Traefik`, `Hostinger`, `tirith`, `dmPolicy`, `REDACTED_CONFIG`,
  `redacted-host`, `0.0.0.0`, `0.0.0.0`, `hstgr`, `vps-`).
- `services/CLAUDE.md` DOES contain the migrated domain content (at minimum
  the strings `redacted-infra`, `redacted-infra`, `Traefik` appear).

**FR10.6 — Documentation of the manual step.** CLOSURE.md MUST include a
section `## Operator manual migration (FR10)` with the literal commands the
operator runs (the copy from workspace-root `CLAUDE.md` to `services/`, the
identical-pair sync, the verification commands). The PR description for the
release MUST link to that CLOSURE section so the operator cannot miss it.

> See `CLOSURE.md` §"Operator manual migration (FR10)" for the literal
> command sequence (5 numbered groups, copy-paste ready).

**FR10.7 — Out-of-band relative to lib CI.** Because FR10 happens in the
operator's workspace (not in the `dadaia-workspace` repo's own tree), the
lib release's CI does not assert FR10 post-conditions. The lib release's CI
only asserts FR7 post-conditions (the lib pair is correct). FR10's
assertions are documented in CLOSURE.md as operator-verified, not
CI-verified. This is an intentional scope boundary.

---

## 4. Requisitos Não-Funcionais

| NFR | Requirement |
|---|---|
| NFR1 | All 7 remaining `*.workflow.md` files MUST load via `MarkdownWorkflowStore` without warning. Panel renders 7 workflow cards (down from 15). |
| NFR2 | The path-scope gate MUST add < 50ms per Write/Edit invocation (cached agent lookup). Measured by gate's existing `/tmp/sdd-gate.log` timestamps. |
| NFR3 | The path-scope gate MUST never block legitimate top-level human invocations (fail open when no agent persona detected). |
| NFR4 | `dadaia specs doctor` MUST remain `[ok] 0 errors, 0 warnings` after the changes. |
| NFR5 | `dadaia public stage && dadaia public install --target all && dadaia public doctor` MUST report `[ok]` for every entry post-trim — deletions of workflow files MUST cascade through projections (`.claude/`, `.codex/`, `.opencode/`, `.agents/`) without stale leftovers. |
| NFR6 | Full pytest suite MUST remain green (`pytest -q tests/`). Updated fixtures: workflow count = 7 (was 15); agent count = 16 (unchanged). |
| NFR7 | The 8 dropped workflows are removed via `git mv` to `_archive/legacy-workflows/<timestamp>/` (one-way; never reintroduced under that name). |
| NFR8 | Backwards compat: if a user-local `.claude/settings.json` references one of the dropped workflow names by id, the panel + CLI MUST surface a deprecation note pointing at the PM playbook (not silently fail). |
| NFR9 | The PR3-style consumer-repo audit (`dadaia public doctor` in every consumer) MUST remain `[ok]` (with `[not-applicable]` cyan for Codex workflows) after the trim. |
| NFR10 | PE and software-architect description budgets stay ≤ 300 chars — no description rewrite required (only `tools:` and body wording). |

---

## 5. Critérios de Aceitação

The release is complete only when ALL of the following hold:

- **C1** — `dadaia_workspace/public/workflows/` contains exactly 7 files:
  `spec-refinement.workflow.md`, `cross-cutting-feature.workflow.md`,
  `onboarding-new-repo.workflow.md`, `hotfix-release.workflow.md`,
  `game-dev-cycle.workflow.md`, `audit-cycle.workflow.md`,
  `code-review-fan-out.workflow.md`.
- **C2** — The 8 dropped workflows live under
  `specs/_archive/legacy-workflows/<UTC-timestamp>/` (read-only).
- **C3** — `dadaia_workspace/public/skills/project-orchestration/SKILL.md` contains a
  `## PM Playbooks` section with exactly 8 named playbooks
  (one per dropped workflow; `game-spec-definition` merged into the `spec-refinement`
  playbook as a `scope=game` sub-entry).
- **C4** — Every agent file in `dadaia_workspace/public/agents/*.md` declares a
  `paths:` block with at minimum `write_allowlist`. Verified by:
  `grep -L "^paths:" dadaia_workspace/public/agents/*.md` returns empty.
- **C5** — The `sdd-spec-gate.sh` hook contains a path-scope check that emits the
  documented `[PATH SCOPE ERROR]` message on mismatch. New regression test:
  agent X (e.g. `code-reviewer`) attempting to write to `dadaia_workspace/foo.py`
  is rejected.
- **C6** — `product-engineer.md` frontmatter `tools:` list does NOT contain `Bash`.
  Verified: `grep -A10 '^tools:' product-engineer.md | grep -q Bash && exit 1 || true`.
- **C7** — `software-architect.md` frontmatter `tools:` list does NOT contain `Bash`.
  Verified similarly.
- **C8** — `dadaia panel` renders 7 workflow cards (was 15); 16 agent cards
  (unchanged). Operator visual smoke OK.
- **C9** — Full pytest green: `pytest -q tests/` from repo root.
- **C10** — `dadaia specs doctor` reports `[ok] 0 errors, 0 warnings`.
- **C11** — `dadaia public stage && dadaia public install --target all && dadaia public doctor`
  reports `[ok]` for every entry; no stale workflow projections.
- **C12** — Consumer-repo `dadaia public doctor` reports `[ok]` (or documented
  `[not-applicable]`) in every consumer repo.
- **C13** — CLOSURE.md written with Validation triples; memory atoms updated
  atomically (see FR5); release directory moved to `_archive/releases/`.
- **C14** — `dadaia_workspace/public/rules/` contains exactly **2 files**:
  `game-agents-coordination.md`, `game-developer-scope.md`. Verified by
  `ls dadaia_workspace/public/rules/ | wc -l` → `2`. The 4 dropped rule files
  live under `specs/_archive/legacy-rules/<UTC-timestamp>/` (read-only).
- **C15** — `project-manager.md`, `project-auditor.md`, `design-specialist.md`
  each contain a `## Scope and forbidden actions` section in their body sourced
  verbatim from the archived rule file. Verified by `grep -l '^## Scope and forbidden actions' dadaia_workspace/public/agents/{project-manager,project-auditor,design-specialist}.md`
  returning all 3 paths.
- **C16** — The single lib source `dadaia_workspace/public/data/AGENTS.md`
  contains none of the strings: `Hostinger`, `redacted-infra`, `redacted-infra`, `Traefik`,
  `dmPolicy`, `tirith`, `REDACTED_CONFIG`, `redacted-host`, `hstgr`,
  `0.0.0.0`, `0.0.0.0`, `vps-`. Verified by
  `grep -iE 'hostinger|redacted-infra|redacted-infra|traefik|dmpolicy|tirith|redacted-infra_write_safe_root|redacted-host|hstgr|45\.180\.188\.119|187\.77\.42\.229|vps-' dadaia_workspace/public/data/AGENTS.md`
  exiting 1 (no matches). Because Option C projects from this single source to
  both `CLAUDE.md` and `AGENTS.md` at every target, the forbidden-strings
  invariant transitively holds across all 4 projections.
- **C17** — Lib `AGENTS.md` references `specs/releases/` (not `specs/features/`)
  for the SDD pipeline section. Verified by
  `grep -c 'specs/releases/' dadaia_workspace/public/data/AGENTS.md` returning ≥ 1
  AND `grep -c 'specs/features/' dadaia_workspace/public/data/AGENTS.md` returning 0.
- **C18** — Lib `AGENTS.md` agent inventory section lists all 16 agents.
  Verified by `grep -cE '^### @' dadaia_workspace/public/data/AGENTS.md` returning 16.
- **C19** — Lib `AGENTS.md` checklist section references `.html` memory atoms,
  not `.md`. Verified by `grep -c 'specs/memory/.*\.html' dadaia_workspace/public/data/AGENTS.md`
  returning ≥ 3 AND `grep -c 'specs/memory/.*\.md' dadaia_workspace/public/data/AGENTS.md`
  returning 0.
- **C20** — Skill-orphan verification script (`tests/scripts/check_skill_orphans.py`
  or equivalent) exits 0: zero orphan skills, zero agents without skills.
  Verifies that `dadaia-workspace-doctor` is referenced from both
  `devops-engineer.md` and `project-manager.md`, and that `dev-server-registry`
  is referenced from `frontend-engineer.md`.
- **C21** — Single-source invariant (Option C): only
  `dadaia_workspace/public/data/AGENTS.md` exists in the source tree;
  `dadaia_workspace/public/data/CLAUDE.md` does NOT exist as a source file.
  Verified by `test -f dadaia_workspace/public/data/AGENTS.md && \
  ! test -e dadaia_workspace/public/data/CLAUDE.md`. Byte-identity of projected
  outputs (`<workspace>/CLAUDE.md` vs `<workspace>/AGENTS.md`) is a structural
  property of the installer (both projections written from the same source) and
  is enforced by C25 below.
- **C22** — The single lib source `dadaia_workspace/public/data/AGENTS.md`
  references the lib-general scope explicitly: it contains the strings
  `dadaia-academy`, `dadaia panel` (or `dadaia-workspace panel`), `venv`,
  `Status: Aprovado`, `release-lifecycle` (or equivalent SDD phrasing).
  Verified by
  `f=dadaia_workspace/public/data/AGENTS.md; grep -q dadaia-academy "$f" && grep -q panel "$f" && grep -q venv "$f" && grep -q "Status: Aprovado" "$f"`.
  Projected `CLAUDE.md` copies (Option C) inherit the same content.
- **C23** — The single lib source documents the domain-scoped guardrails
  pattern (FR7.1). Verified by
  `grep -ci 'domain-scoped\|domain scope\|services/CLAUDE' dadaia_workspace/public/data/AGENTS.md`
  returning ≥ 1.
- **C24** — Manifest tracks the single source asset `data/AGENTS.md` (Option C —
  see FR7.0 / FR7.11). Verified by
  `grep -c '"data/AGENTS.md"' .dadaia/agentic/manifest.json` returning `1` AND
  `grep -c '"data/CLAUDE.md"' .dadaia/agentic/manifest.json` returning `0`
  (the latter MUST NOT appear — `data/CLAUDE.md` does not exist as a source).
- **C25** — Projection byte-identity at workspace root: after
  `dadaia public install --target all`, `<workspace>/CLAUDE.md` and
  `<workspace>/AGENTS.md` are byte-identical. Verified by
  `sha256sum <workspace>/{CLAUDE,AGENTS}.md | awk '{print $1}' | sort -u | wc -l`
  returning `1`. (Note: this check is part of the lib release's CI; it
  asserts the projection mechanism, not the operator-side FR10 migration.)
- **C26** — FR10 operator-checklist captured in CLOSURE.md. Verified by
  `grep -c '^## Operator manual migration' specs/releases/agents-r2-v1/CLOSURE.md`
  returning ≥ 1 at CLOSURE time. (This is a CLOSURE-phase criterion, not a
  pre-CLOSURE CI gate.)

**Definition of Done** = C1 ∧ C2 ∧ ... ∧ C25 ∧ operator's verbal "OK" on the panel
smoke ∧ CLOSURE-time confirmation of C26. FR9 (workspace operator notes archival)
is recorded in CLOSURE.md as a decision, not as a hard criterion. FR10
(operator manual migration to `services/`) post-conditions are operator-verified
at CLOSURE time, not CI-gated.

---

## 6. Fora de Escopo

Explicit non-deliverables for this release:

- **NS1** — Bash command allowlists (per-binary restriction inside the gate). The
  gate enforces *path* scope only; what binaries Bash invokes remains the agent's
  responsibility per its rule-of-prose. Defer to a future release if real abuse
  is observed.
- **NS2** — Description tightening / routing-budget reduction across agents.
  Every agent description is already ≤ 303 chars (within Anthropic's routing
  ceiling). Defer to a future release unless a stage discovers genuine bloat.
- **NS3** — Removing PE from any KEPT workflow. PE remains the spec author in
  `spec-refinement`, `onboarding-new-repo`, and `hotfix-release`.
- **NS4** — New agents. None in this release.
- **NS5** — Sub-agent promotion of `dadaia-grill-me` (was a candidate carried over
  from `agents-r1-v1` CLOSURE backlog). Operator confirmed: defer again. The
  grill-me skill remains a skill, invoked by PM (primary) and PE (secondary).
- **NS6** — Read-scope enforcement. The `paths:` field's `read_allowlist` is
  parsed and stored but NOT enforced this release. The gate only checks
  `write_allowlist`. Read-scope is a deliberate v3 design choice: blocking
  Read would hurt the "specialist needs context" flow more than it prevents
  abuse. Promote if real exfiltration risk emerges.
- **NS7** — Edits to `specs/backlog/ideas.md` (operator working memory).
- **NS8** — Changing the workflow schema. The 7 surviving workflows retain
  the same YAML shape they had in r1.
- **NS9** — Re-organising agent files into subdirectories or splitting agent
  bodies into multiple files. r2 keeps the single-file-per-agent convention.
- **NS10** — **(RESCINDED — superseded by FR7 + FR10.)** The prior NS10 said
  "workspace `CLAUDE.md` stays untouched". That framing was wrong: this release
  DOES rewrite the workspace-root `CLAUDE.md` (via the lib projection — see
  FR7), and the Hostinger/redacted-infra/redacted-infra content migrates to `services/`
  (see FR10). The correct not-in-scope clarification: the operator-managed
  `services/CLAUDE.md` and `services/AGENTS.md` pair (FR10) is NOT
  lib-projected. The lib only ships and projects the workspace-root identical
  `CLAUDE.md`/`AGENTS.md` pair (FR7). `services/CLAUDE.md` /
  `services/AGENTS.md` lives entirely in operator-owned space — never in
  `dadaia_workspace/public/`, never in `.dadaia/agentic/manifest.json`,
  never overwritten by `dadaia public install`.
- **NS11** — Auto-archival of `multi-agent-orchestration-v{1,2}.md`. FR9 makes
  this operator-decided at CLOSURE; the release does not silently move
  operator-owned files in the workspace root.
- **NS12** — Re-writing or merging any of the 31 already-correctly-assigned
  skills. FR8 only wires the 2 orphans; no skill content changes.
- **NS13** — Adding new rules to `dadaia_workspace/public/rules/`. The folder
  shrinks 6 → 2; no new rule files are introduced. A future release may add
  rules only if a genuine cross-agent boundary emerges (e.g. a new game agent
  family).

---

## 7. Riscos e Dependências

| Risk | Severity | Mitigation |
|---|---|---|
| **R1 — PM playbook section in `project-orchestration` skill grows unbounded over time.** Every new ad-hoc routing pattern adds another playbook entry; without a cap, the skill becomes its own dumping ground. | MEDIUM | Hard cap at 8 playbooks for this release (one per dropped workflow). Future playbooks require either (a) PE-approved entry in the skill OR (b) promotion to a real workflow if gates/parallelism justify it. Re-evaluate at next agent topology release. |
| **R2 — Path-scope gate requires runtime hook integration with an "active agent" signal.** Claude Code surfaces this via env var; Codex / OpenCode may not. The hook must detect the active agent reliably or fail-open gracefully. | HIGH | software-architect picks the pattern during PLAN; if no reliable signal is available across all three harnesses, the gate degrades to fail-open with a logged warning. NFR3 codifies this. PM dispatches a software-architect consultation as the first PLAN sub-task. |
| **R3 — PE losing Bash means PM must now run `dadaia specs doctor` before merging PE's spec output.** New hop in the `spec-refinement` workflow. | LOW | Add a doctor-validation sub-stage to `spec-refinement`: after PE writes SPEC.md, PM dispatches devops-engineer (or runs Bash itself, since PM keeps Bash) to validate. The added latency is bounded by doctor's runtime (~1s). |
| **R4 — Consumer-repo projections cache the dropped workflows.** A consumer repo may still have `.claude/workflows/architecture-review.workflow.md` after the trim if `dadaia public install` did not delete absent files. | MEDIUM | Verify `_atomic_write_text` + cleanup pattern in `public_assets.py` does delete-on-absence. If not, devops-engineer adds the missing cleanup pass as part of PLAN. NFR5 + NFR9 codify the green-bar. |
| **R5 — Frontmatter `paths:` declarations are wrong in initial draft, breaking legitimate writes.** E.g. PE missing `specs/assets/**` blocks a legitimate screenshot reference. | MEDIUM | Path-scope gate logs every block to `/tmp/sdd-gate.log` with the rejected path + allowlist. First 24h post-merge: operator monitors the log; PE files hotfix release with corrected allowlist if needed. |
| **R6 — Operators with custom local workflows referenced in their personal `.claude/settings.json` see "workflow not found" after trim.** | LOW | Add a one-shot deprecation table to the panel header for 1 release cycle: "Workflows removed in r2: <list>. See `project-orchestration` skill > PM Playbooks for the replacement recipe." NFR8 codifies. |
| **R7 — software-architect losing Bash causes a regression in some existing audit flow that did use Bash.** | LOW | Audit `software-architect.md` body for any `Bash` invocation in the prompt; if found, replace with "ask PM to run". The prompt is descriptive — no runtime regression. PE validates during P1 review. |
| **R8 — Agent-body bloat after inlining scope rules.** `project-manager.md`, `project-auditor.md`, and `design-specialist.md` each grow by ~30–50 lines after FR6 inlines the rule content. If any agent body crosses a routing-description budget downstream, the harness may complain. | LOW | The inlined content lives in the body (after frontmatter), not in `description:`. The Anthropic routing budget applies to `description:` only (≤ 303 chars), which this release does not touch. Body length is unconstrained. Verify post-merge with `wc -l dadaia_workspace/public/agents/{project-manager,project-auditor,design-specialist}.md` (expect ≤ 350 lines each). |
| **R9 — AGENTS.md projection drift across the 3 install targets.** The rewritten `AGENTS.md` must project identically to every consumer (workspace root, plus harness folders where applicable). A mistake in `public_assets.py` projection logic could land different bytes in different locations. | MEDIUM | Run `sha256sum` on every projected `AGENTS.md` after `dadaia public install --target all`; all hashes must match. devops-engineer codifies this check in P9. NFR9 covers consumer-repo `[ok]` regression. If projection logic is found to write divergent bytes, that becomes a hotfix-release candidate filed via `qa-engineer`. |
| **R10 — Operator forgets the FR10 manual migration step, leaving workspace-root `CLAUDE.md` overwritten with lib content and redacted-infra/redacted-infra domain rules lost from view.** When the lib release ships, `dadaia public install` overwrites the workspace-root `CLAUDE.md` with the new identical-pair projection (lib-general guardrails only). If the operator has NOT yet migrated the redacted-infra/redacted-infra/Traefik content to `services/CLAUDE.md` + `services/AGENTS.md` (FR10.1), the domain rules are no longer visible to harnesses that read the workspace tree — even though they remain recoverable from `git log`. | HIGH | (a) The release's PR description includes an explicit operator checklist that lists FR10.4 step 1 (migrate to `services/`) as a **prerequisite** to running `dadaia public install`. (b) CLOSURE.md's `## Operator manual migration (FR10)` section (FR10.6) carries the literal commands. (c) The order of operations is documented in BOTH artifacts: migrate FIRST, install SECOND. (d) If the operator misses step 1, recovery is `git show <pre-release-sha>:CLAUDE.md > services/CLAUDE.md && cp services/CLAUDE.md services/AGENTS.md`. The mitigation is documentation + recovery path; the gate cannot enforce a step that happens outside the lib repo's tree (FR10.7). |
| **R11 — Skill-orphan verification script is missing or incorrect at CI time.** FR8.3 declares the script; if the script itself has a bug (false-positive or false-negative), C20 cannot be trusted. | LOW | qa-engineer adds a self-test as part of P8: seed a fake-orphan skill in a tmp dir, assert script detects it; seed a fake-fully-wired skill, assert script passes. Self-test must run in pytest. |
| **R12 — `dadaia public install` does not delete absent rule projections.** After r2 trims `public/rules/` from 6 to 2, the 4 dropped rule files may persist in `.claude/rules/`, `.codex/rules/`, `.opencode/rules/` if the installer does not perform delete-on-absence (same shape as R4 for workflows). | MEDIUM | Same mitigation as R4: devops-engineer verifies cleanup pass in `public_assets.py`; if missing, adds it in P9. NFR5 covers the green-bar across both workflow and rule projections. |

---

## 8. Phase plan (preview for PLAN.md)

(Not the PLAN — declared here so the operator can sanity-check phasing during SPEC review.)

| Phase | Scope | Owner |
|---|---|---|
| **P0** | Confirm gate ACTIVE.md phase = `SPEC` (this dispatch). | PE |
| **P1** | Operator approves SPEC. PE writes PLAN.md with software-architect's path-scope pattern decision. | PE + software-architect (consult) |
| **P2** | TASKS.md decomposition. | PE |
| **P3** | Workflow trim — `git mv` 8 workflows to `_archive/legacy-workflows/`. | software-engineer |
| **P4** | Update `project-orchestration` SKILL.md with 8 PM Playbooks. | software-engineer (mechanical edit) or PE if content-heavy |
| **P5** | Add `paths:` block to all 16 agent frontmatters. | software-engineer |
| **P6** | Implement path-scope check in `sdd-spec-gate.sh`. | software-engineer (pattern from software-architect) |
| **P7** | Remove `Bash` from PE and software-architect frontmatters; update prompt bodies. | software-engineer |
| **P8** | Test updates — workflow count, gate path-violation regression. Run `pytest -q tests/`. | software-engineer + qa-engineer (regression test) |
| **P9** | Stage + install + doctor; consumer-repo sweep. | devops-engineer |
| **P10** | FR6 — Inline scope content into `project-manager.md`, `project-auditor.md`, `design-specialist.md`; move `dadaia-workspace-dev-guardrail.md` content into `AGENTS.md`; `git mv` 4 rule files to `_archive/legacy-rules/<UTC-ts>/`. | software-engineer (mechanical) |
| **P11a** | FR7 — Rewrite `dadaia_workspace/public/data/AGENTS.md` for lib-general-only scope (16 agents + release-lifecycle + HTML memory atoms + current CLI + domain-scoped guardrails pattern); remove Hostinger/redacted-infra/redacted-infra/Traefik strings. | PE (content-heavy; PM dispatches PE explicitly for AGENTS.md rewrite) |
| **P11b** | FR7 — Implement Option C in `public_assets.py`: new function `_install_workspace_guardrail_pair` reads single source `data/AGENTS.md` and writes both `AGENTS.md` and `CLAUDE.md` at 4 target paths (workspace root + each consumer repo root with `.dadaia/` marker × 2 filenames). Update doctor to emit 4 separate parity lines per source. Update `.dadaia/agentic/manifest.json` source SHA for the rewritten `data/AGENTS.md` (single entry; `data/CLAUDE.md` does NOT exist as a source). | software-engineer (mechanism already decided in architect ADR) |
| **P11c** | FR10 — Author the PR description's operator checklist for the manual `services/` migration; author the CLOSURE.md `## Operator manual migration (FR10)` template content (the literal commands the operator will run). NOT executed yet — just authored as documentation that ships with the release. | PE |
| **P12** | FR8 — Add `dadaia-workspace-doctor` to `devops-engineer.md` and `project-manager.md` `skills:`; add `dev-server-registry` to `frontend-engineer.md` `skills:`. Add `tests/scripts/check_skill_orphans.py`. | software-engineer + qa-engineer (script self-test) |
| **P13** | Re-run stage + install + doctor after FR6/FR7/FR8 edits; consumer-repo sweep #2 (R9, R12 mitigation); verify C21 (lib pair byte-identity) + C25 (workspace-root projection byte-identity). | devops-engineer |
| **P14** | CLOSURE — PE writes CLOSURE.md (including the `## Operator manual migration (FR10)` section with literal commands), re-renders memory atoms, records FR9 operator decision in `## Backlog returns`, records C26 confirmation when the operator completes FR10, `git mv` release dir. | PE |

---

## 9. Discovery report (Phase 1–3 distilled)

Reports consumed: dispatch brief (operator-authored, equivalent to a synthesis from
software-architect + project-manager perspectives) **plus expanded-scope audit
brief** (operator widened scope after initial SPEC was drafted; audit covers
rules folder, lib AGENTS.md, skill→agent assignments, workspace doc staleness).

Grill-me passes: 0 — both dispatch briefs are precise enough that no operator
question remained. PE pre-resolved two ambiguities internally during drafting:

- **Ambiguity 1 (original scope):** does FR3 (Bash removal) need a
  software-architect consultation during PLAN, separate from FR2 (path-scope
  gate)?
- **Resolution 1:** no — FR3 is purely declarative (frontmatter edit + prompt
  body wording). software-architect is consulted only for the FR2 gate pattern.
  This keeps the PLAN compact (still well under the 300-line ceiling).

- **Ambiguity 2 (expanded scope):** for FR6, does inlining `project-manager-scope.md`
  content into the agent body belong in the `description:` field (routing budget
  applies) or in the body (no budget)?
- **Resolution 2:** body. The Anthropic ≤ 303-char routing budget applies to
  `description:` only. Agent body length is unconstrained by the harness; only
  the operator's reading comfort matters. R8 codifies the verification.

**Audit findings — incorporated verbatim into FR6/FR7/FR8:**

- **Finding A — Rules folder reorganization (6 → 2 files):** classified all 6
  rules; 3 are per-agent scope (inline into agent body), 1 is workspace-wide
  invariant (move to AGENTS.md), 2 are genuine cross-agent boundaries (keep).
  See FR6 sub-items.
- **Finding B — AGENTS.md drift (8 issues):** §9 lists only 6 of 16 agents;
  §2 still references `specs/features/` (migrated to `specs/releases/` in r1);
  §6/§7 contain Hostinger/redacted-infra/redacted-infra content that belongs in workspace
  `CLAUDE.md`; §11 references `.md` memory files (migrated to `.html` in r1);
  §4 missing recent CLI commands; §10 outdated agent list. See FR7 sub-items.
- **Finding C — 2 orphan skills:** `dadaia-workspace-doctor` (not referenced
  by any agent), `dev-server-registry` (same). All other 31 skills correctly
  wired. See FR8.
- **Finding D — Tool-call audit:** confirmed only PE + software-architect have
  unused Bash (already in FR3); no further cuts. No expansion of FR3 needed.
- **Finding E — Workspace operator notes:** `multi-agent-orchestration-v{1,2}.md`
  are workspace-root operator-owned files; this release records a CLOSURE-time
  decision point (FR9) rather than auto-archiving.

**Post-draft revision (2026-05-18) — operator clarification on workspace-root pair:**

After the first SPEC draft (which marked workspace-root `CLAUDE.md` as
NS10-untouched), the operator clarified the architecture sharply:

> "The general rules `CLAUDE.md` and `AGENTS.md` must be resumed to the rules,
> guardrail about the features of `dadaia-workspace`. [...] `AGENTS.md` and
> `CLAUDE.md` should even contain the same information. GUARDRAILS for the
> workspace, like using venv, SDD pattern enforced, endorsement of the use of
> `dadaia-workspace` CLI to operate it, and more. `dadaia-academy`,
> `dadaia-workspace panel`, we have features from `dadaia-workspace`. What we
> cannot have in this rules / guardrail are things that are stricted to a
> domain. redacted-infra and redacted-infra clearly are these cases."

This rescinds the prior NS10 and reshapes FR7 + introduces FR10:

- **FR7 is expanded:** the lib ships an identical `CLAUDE.md`/`AGENTS.md` pair
  (both files lib-projected, byte-identical, lib-general scope only). The
  manifest gains `data/CLAUDE.md`. Forbidden-strings list is explicit and
  case-insensitive.
- **FR10 is added:** the operator manually migrates redacted-infra/redacted-infra/Traefik
  content from the prior workspace-root `CLAUDE.md` into operator-managed
  `services/CLAUDE.md` + `services/AGENTS.md` (identical pair, NOT
  lib-managed). This is a coordinated migration documented in CLOSURE.md;
  the lib release ships the projection content; the operator runs the file
  migration. R10 is rewritten to track the new risk (operator forgets the
  migration step).
- **NS10 is rescinded** and replaced with a not-in-scope clarification
  about the operator-managed `services/` pair (it is NOT lib-projected; it
  lives outside `dadaia_workspace/public/` and outside the manifest).

No open questions for the operator at SPEC time post-revision. The operator's
literal scope words map cleanly into FR7.1 (lib-general content list),
FR7.2 (forbidden strings), and FR10 (domain-rule extraction to `services/`).

---
