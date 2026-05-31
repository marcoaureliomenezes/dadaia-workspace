# SPEC — Release: memory-context-enforcement-v1

**Status:** Aprovado
**Release ID:** memory-context-enforcement-v1
**Owner:** product-engineer
**Opened:** 2026-05-30
**Semver target:** minor (additive; no breaking changes; no schema migration required)
**Sequencing:** Decoupled — no dependency on `spec-context-session-locks-v1`,
`spec-context-tree-v2`, `panel-kanban-v1`, or `go-open-source`. Rides live infrastructure.
Ships early / in parallel. `memory-structured-source-v1` (Phase 2, YAML source-of-truth)
depends on THIS release being CLOSED first.

---

## 1. Problem and context — the read-side gap

dadaia-workspace enforces the **write side** of memory with a hard gate: `sdd-spec-gate.sh`
RULE A blocks every edit to `specs/memory/**` for any agent other than `product-engineer`
in the CLOSURE phase; `specs doctor` enforces atomicity, link integrity, and image
references. The write side is strong.

The **read side has no enforcement at all.** A gate intercepts writes; it is structurally
incapable of forcing a read. Consumption lives only in soft convention: the
`dadaia-workspace-spec-navigator` skill (opt-in), `AGENTS.md §7`, and a handful of agent
personas that happen to include a memory step.

**Measured blindness (2026-05-30 audit, ai-engineer report):**

| Tier | Count | Agents | Behaviour |
|------|-------|--------|-----------|
| Fully blind | 5 | code-reviewer, design-specialist, project-auditor, researcher, security-reviewer | No `spec-navigator` skill, no memory read step anywhere in persona |
| Partial | 13 | backend-engineer, devops-engineer, qa-engineer, frontend-engineer, software-engineer-python, software-engineer-node, data-engineer, data-analyst, data-architect, game-developer, game-designer, game-tester, ai-engineer | Declare `spec-navigator` in frontmatter but no "Step 0: execute this first" mandate — available, never commanded |
| Genuinely memory-aware | 3 | software-architect, product-engineer, project-manager | Concrete read-architecture/product/tech-stack step explicitly present |

**Write vs read asymmetry:**

| Dimension | Write side | Read / consume side |
|-----------|-----------|---------------------|
| Mechanism | `sdd-spec-gate.sh` RULE A (PreToolUse) + 11 SPEC-DOC + 7 TREE doctor checks | Convention only — skill declared but never commanded |
| Strength | Hard — cannot edit memory outside CLOSURE | None — nothing prevents an agent from starting work without reading memory |
| Coverage | All agents, all runtimes | 3/21 truly; 13/21 "may"; 5/21 blind |

**The live but empty hook.** `ctx-inject.sh` already fires on every Claude Code and
OpenCode prompt (`UserPromptSubmit`) but today emits only ~5 tokens (the active context
name). The injection channel is alive and reaches every agent. We are one payload change
away from universal memory awareness.

**The cost of blindness.** An agent working without product context produces
assumptions, architectural violations, and rework. This is the highest-cost failure mode
in an agentic system — and it is the one currently unguarded by dadaia-workspace, whose
central value proposition is SDD-oriented, context-engineered development.

**Primary sources consumed:**

- Backlog candidate: `specs/backlog/memory-context-enforcement-v1.md`
- Operator decisions: grill-me session 2026-05-30 (4 locked decisions — see §3)
- Specialist analysis (ai-engineer + software-architect, 2026-05-30) — captured in the backlog candidate; the working report HTMLs were ephemeral and are not retained.

---

## 2. Objective

Deliver the foundation that makes **"agents never work blind"** real and universal across
all three runtimes (Claude Code, OpenCode, Codex) by:

1. Payloading the already-firing `ctx-inject.sh` hook so every Claude Code and OpenCode
   session receives architecture + tech-stack + catalog at work-start (~7.3K tokens, once).
2. Generating a machine-readable `catalog.json` as the feature navigation index, with a
   `specs doctor` sync check keeping it consistent with feature HTML files.
3. Adding a mandatory "Step 0 — Memory bootstrap" block to all 21 agent personas, making
   memory consumption commanded rather than optional (covers Codex and standalone sessions
   where the hook does not fire).
4. Creating `specs/memory/AGENTS.md` as the local memory contract co-located with the
   atoms (also closes the TREE-5 `specs doctor` warning on this repo's own specs tree).
5. Creating a universal Codex `memory-ctx` adapter, generalising the existing
   `design-ctx` / `frontend-ctx` pattern to give Codex sessions the same memory bootstrap
   available via `ctx-inject.sh` in Claude Code and OpenCode.

All five deliverables are additive. No breaking changes. No schema migration. No dependency
on any other in-flight release.

---

## 3. Locked operator decisions (grill-me 2026-05-30 — do not re-open)

| # | Decision | Rationale |
|---|----------|-----------|
| D-1 | **Enforcement = soft injection at work-start, not a hard gate / read-receipt.** Guarantees the agent *sees* the memory map; does not prove it *used* it — accepted trade-off. | A hard read-receipt gate requires runtime instrumentation that doesn't exist; the injection channel already fires; correctness improvement is immediate and near-zero cost. |
| D-2 | **North star = "agents never work blind."** Format and tokens are enablers in service of correctness; they are not the primary goal. | If we changed format but left consumption un-commanded, agents would still work blind. Fix the requirement first; format is the mechanism that makes it lean. |
| D-3 | **Decoupled.** This release has no dependency on `spec-context-session-locks-v1`, `spec-context-tree-v2`, `panel-kanban-v1`, or `go-open-source`. It rides the existing always-on `ctx-inject.sh` hook. A later release upgrades injection to per-session bind when `spec-context-session-locks-v1` lands. | Session locks are not yet in production; waiting for them would delay the blindness fix by at least one release cycle. Decoupling is the correct dependency posture. |
| D-4 | **Catalog format = JSON (machine index).** Content stays HTML in this release (stripped of boilerplate at injection time). The YAML source-of-truth migration is the separate Phase-2 candidate `memory-structured-source-v1` — explicitly out of scope here. | JSON is directly addressable by agents without HTML parsing. At ~540 tokens for 18 features it is the cheapest useful index. Converting 23 HTML atoms to YAML is a larger, higher-risk change; sequencing it after the blindness fix avoids blocking correctness behind migration. |

---

## 4. Scope clusters

### C-1 — Payload the live hook

**What this is:** The highest-impact change in this release. `ctx-inject.sh`
(`dadaia_workspace/public/scripts/ctx-inject.sh`) already fires unconditionally on every
`UserPromptSubmit` event in Claude Code and OpenCode but today emits only the active
context name (~5 tokens). The OpenCode counterpart plugin is
`dadaia_workspace/public/plugins/ctx-inject.ts` (calls `ctx-inject.sh` and appends its
stdout to every user message). This cluster extends both assets to inject the full memory
bootstrap at session start.

**Injection payload (Option C from ai-engineer analysis):**

| Layer | What is injected | Tokens (est) |
|-------|-----------------|--------------|
| Catalog index | `specs/memory/product/catalog.json` — all features with slug, title, summary, path, tags, rank | ~540 |
| Architecture | `memory/architecture.html` stripped of `<head>`, `<style>`, Mermaid `<script>` | ~3,410 |
| Tech stack | `memory/tech-stack.html` stripped (same) | ~1,103 |
| **Total injected** | — | **~7,256 (~7.3K)** |

Feature detail files (~32K total for all 18) are **not injected** — the agent self-pulls
only the 1-3 features relevant to its task using the catalog slug → path mapping.

**Stripping helper:** A `strip-memory-html.py` Python helper (approx. 20-30 lines) strips
`<head>`, `<style>`, and Mermaid `<script>` boilerplate from HTML files before injection.
Lives in `dadaia_workspace/public/scripts/` so it is lib-originated and propagated to all
consumer workspaces. Invoked by `ctx-inject.sh` inline.

**First-message-only guard (OpenCode):** The `ctx-inject.ts` OpenCode plugin fires on
every user message (`chat.message`). Without a guard, the 7.3K payload would be paid on
every turn of a multi-turn session (10 turns = 72.5K tokens, ~$0.22 at Sonnet). The
plugin must include a session-scoped guard (via `input.messageID` ordering or an
equivalent mechanism determined by devops-engineer at implementation time) so the payload
is injected only on the first message. Claude Code's `UserPromptSubmit` fires once per
session start, so the guard is only critical for OpenCode.

**Graceful fallback:** When `catalog.json` does not yet exist (consumer repos that have
not yet generated it), the injection skips the catalog block silently and falls back to
injecting `product/index.html` stripped, per the existing spec-navigator fallback
protocol.

**Propagation workflow** (these assets are lib-originated — operator/devops must run
after implementation):
```
dadaia public stage
dadaia public install --target all
dadaia public doctor   # must exit 0
```

**Files changed (lib-originated — edit source, not projections):**

| File | Change |
|------|--------|
| `dadaia_workspace/public/scripts/ctx-inject.sh` | Extend to emit stripped arch + tech-stack + catalog.json; add first-message guard logic |
| `dadaia_workspace/public/plugins/ctx-inject.ts` | Add first-message-only guard for OpenCode multi-turn |
| `dadaia_workspace/public/scripts/strip-memory-html.py` | **NEW** — 20-30 line helper; strips head/style/script boilerplate; invoked by ctx-inject.sh |

**Acceptance criteria:**

- AC-C1-1: `ctx-inject.sh` executed with a valid `DADAIA_CONTEXT` pointing to a context with `specs/memory/` emits a block containing stripped `architecture.html` content, stripped `tech-stack.html` content, and `catalog.json` content (or stripped `product/index.html` if catalog absent).
- AC-C1-2: The injected block is bounded by `=== workspace memory (arch + tech + catalog) ===` … `=== end memory bootstrap ===` markers so agents can locate it deterministically.
- AC-C1-3: `strip-memory-html.py` called on `architecture.html` returns content with `<head>`, `<style>`, and Mermaid `<script>` blocks removed, and all prose/diagram content preserved.
- AC-C1-4: When `catalog.json` is absent, injection silently falls back to injecting stripped `product/index.html` (no error, no empty block).
- AC-C1-5: The OpenCode `ctx-inject.ts` plugin injects the memory payload only on the first message of a session, not on subsequent messages of the same session.
- AC-C1-6: `dadaia public doctor` exits 0 after propagation (no drift, no missing).
- AC-C1-7: Token count of the injected payload with a representative workspace (18 features, `catalog.json` present) is in the range 6,500-8,500 tokens (validates Option C cost).

---

### C-2 — Machine catalog `catalog.json`

**What this is:** A generated (not hand-authored) JSON file at
`specs/memory/product/catalog.json`. It is the machine-readable companion to the
browser-rendered `product/index.html`. The catalog enables agents to navigate to the
1-3 features relevant to their task in O(1) cognitive steps without parsing HTML.

**Schema per entry:**

```json
{
  "generated_at": "<ISO-8601-UTC>",
  "context": "<context-name>",
  "features": [
    {
      "rank": 1,
      "slug": "workspace-init",
      "title": "Workspace Init",
      "summary": "Entry point; creates .dadaia/, .venv, hooks, idempotent structure.",
      "path": "specs/memory/product/workspace-init.html",
      "tags": ["init", "setup", "hooks"],
      "depends_on": []
    }
  ]
}
```

**Field semantics:**

| Field | Type | Agent use |
|-------|------|-----------|
| `rank` | int (1-N) | Daily-relevance order from `index.html` catalog — sort by rank for situational awareness |
| `slug` | string | Primary lookup key; matches the HTML filename stem |
| `title` | string | Human-readable name for report citations |
| `summary` | string (1-2 sentences) | Inline context — agent reads this to decide if it needs to self-pull the full feature HTML |
| `path` | string | Exact filesystem path for self-pull; no path construction needed |
| `tags` | string[] | Keyword search — agent checks task keywords against tags |
| `depends_on` | string[] | Related slugs — informs which other features to pull |

**Generation:** `catalog.json` is generated by a Python CLI command or helper invoked:

1. By `software-engineer-python` as part of this release implementation (initial generation
   for this repo's 18 feature files).
2. Automatically by `dadaia memory product add` when a new feature HTML is created
   (future integration — plumbing the command is in scope; detailed CLI design is
   implementation-led).
3. By `product-engineer` during CLOSURE of any future release that adds/removes/reorders
   features.

`catalog.json` is a committed file in `specs/memory/product/`. It is regenerated, not
hand-edited.

**`specs doctor` sync check:** A new doctor check (`CAT-1`) verifies that the set of
slugs in `catalog.json` matches the set of `*.html` files (excluding `index.html`) in
`specs/memory/product/`. If they diverge, doctor warns (not errors, because `catalog.json`
may simply be stale and needs regeneration). The doctor message must identify the specific
slugs / files that are out of sync.

**Files changed:**

| File | Change |
|------|--------|
| `dadaia_workspace/dadaia_workspace/features/specs/catalog.py` | **NEW** — catalog generator; reads `product/index.html`, extracts catalog entries, writes `catalog.json` |
| `dadaia_workspace/dadaia_workspace/features/specs/doctor.py` | Add CAT-1 sync check |
| `dadaia_workspace/dadaia_workspace/cli/commands/memory.py` | Wire `dadaia memory catalog generate` command (or equivalent plumbing into `memory product add`) |

**Acceptance criteria:**

- AC-C2-1: `catalog.json` exists at `specs/memory/product/catalog.json` in this repo after implementation.
- AC-C2-2: Each entry in `catalog.json` has all required fields: `rank`, `slug`, `title`, `summary`, `path`, `tags`, `depends_on`.
- AC-C2-3: The `path` value for each entry resolves to an existing file on disk.
- AC-C2-4: The `slug` for each entry matches the stem of the corresponding feature HTML filename (e.g., slug `sdd-gate-v3` → file `sdd-gate-v3.html`).
- AC-C2-5: `dadaia specs doctor` emits a CAT-1 warning when `catalog.json` has a slug that does not correspond to any `*.html` file in `product/`, and vice versa.
- AC-C2-6: `dadaia specs doctor` passes (no CAT-1 warning) when catalog slugs and HTML files are in sync.
- AC-C2-7: `catalog.json` is parseable as valid JSON (no syntax errors, no trailing commas).

**Note on `tags` and `depends_on`:** This repo's `specs/memory/product/index.html` has no
`data-tags` or `data-depends` markup on its catalog entries. As a result, the initial
`catalog.json` will have `tags: []` and `depends_on: []` for all entries. Populating these
fields is acceptable future enrichment and does not block the schema (the fields are present,
just empty). T-MCE-01 and T-MCE-04 implementers should expect this and must not treat empty
arrays as a generation error.

---

### C-3 — Universal "Step 0" block in all 21 agent personas

**What this is:** A verbatim "Step 0 — Memory bootstrap (mandatory before any
implementation)" block inserted into the Workflow Protocol section of every agent persona
file in `dadaia_workspace/public/agents/*.md`. This moves `dadaia-workspace-spec-navigator`
from optional to commanded and covers runtimes/sessions where the hook does not fire
(Codex, standalone Claude Code sessions without `ctx-inject.sh` wired).

**Phased rollout:**

| Priority | Agents | Actions |
|----------|--------|---------|
| P0 — Blind (5) | code-reviewer, design-specialist, project-auditor, researcher, security-reviewer | Add `dadaia-workspace-spec-navigator` to skills frontmatter + add Step 0 block |
| P1 — Partial (13) | backend-engineer, devops-engineer, qa-engineer, frontend-engineer, software-engineer-python, software-engineer-node, data-engineer, data-analyst, data-architect, game-developer, game-designer, game-tester, ai-engineer | Add Step 0 block only (spec-navigator already in skills) |
| P2 — Already aware (3) | software-architect, product-engineer, project-manager | Align existing memory-read language to the Step 0 block phrasing (no functional change) |

**Canonical Step 0 block (verbatim — ai-engineer must insert this text exactly):**

```markdown
## Step 0 — Memory bootstrap (mandatory, before any implementation)

If the memory bootstrap was injected at session start via ctx-inject.sh, it is already in
your context. If not (Codex or standalone invocation), execute the dadaia-workspace-spec-navigator
skill now:

  1. Read specs/memory/architecture.html — layer rules, dependency contracts, agent topology.
  2. Read specs/memory/tech-stack.html — approved languages, runtimes, constraints.
  3. Read specs/memory/product/catalog.json (or index.html if catalog.json absent) — feature
     catalog. Identify the 1-3 features most relevant to your task.
  4. Self-pull specs/memory/product/<slug>.html for each relevant feature.

Do NOT begin any implementation, review, or report until Step 0 is complete.
This ensures you are working from the current product state, not from stale context.
```

**Placement:** immediately before or as the first section of the agent's existing
"Workflow Protocol" or equivalent workflow section. If no such section exists, add it at
the top of the agent file's body, after the frontmatter.

**Files changed:**

| Path | Change |
|------|--------|
| `dadaia_workspace/public/agents/*.md` (21 files) | Add Step 0 block (P0: also add spec-navigator to skills) |

These are lib-originated assets. After ai-engineer authors the changes:
```
dadaia public stage && dadaia public install --target all
dadaia public doctor   # must exit 0
```

**Acceptance criteria:**

- AC-C3-1: All 21 agent persona files in `dadaia_workspace/public/agents/` contain a section matching "Step 0 — Memory bootstrap (mandatory" (case-insensitive match sufficient).
- AC-C3-2: All 5 P0 agents (code-reviewer, design-specialist, project-auditor, researcher, security-reviewer) have `dadaia-workspace-spec-navigator` in their frontmatter `skills:` list.
- AC-C3-3: The Step 0 block in every persona contains the clause "Do NOT begin any implementation, review, or report until Step 0 is complete" (verbatim or functionally equivalent).
- AC-C3-4: `dadaia public doctor` exits 0 after propagation.
- AC-C3-5: `grep -l "Step 0" dadaia_workspace/public/agents/*.md | wc -l` outputs `21` (all 21 files).

---

### C-4 — `specs/memory/AGENTS.md`

**What this is:** A local contract file created at `specs/memory/AGENTS.md` (in the
consumer workspace's own specs tree — this repo's `specs/memory/AGENTS.md`). It is the
first file an agent encounters when entering the `specs/memory/` directory. It answers
"what can I do here and how?" before the agent touches any individual atom.

Note: this is distinct from the workspace-level `specs/AGENTS.md` (which is `spec-context-tree-v2`'s
TREE-5 deliverable). These are different files at different paths serving different scopes.

**Content contract:**

1. **Read contract (all agents):** canonical read order: `architecture.html` → `tech-stack.html` → `product/catalog.json` (or `product/index.html` if catalog absent) → self-pull relevant feature HTMLs. Mirrors spec-navigator but is local to the directory.
2. **Write contract (product-engineer only, CLOSURE phase):** states that all `*.html` and `product/*.html` files are write-locked. Cites gate enforcement: RULE A in `sdd-spec-gate.sh`.
3. **Atomicity contract:** memory describes the product as it is now. No Changelog. No History. The delta lives in git.
4. **File manifest:** table mapping each file to its role and the type of content it holds, so agents can confirm whether `catalog.json` exists before choosing fallback behaviour.
5. **Generation note for `catalog.json`:** who generates it, when, and how (`dadaia memory product add` / product-engineer in CLOSURE).

**Max length:** 80 lines (short enough to be read in full without cognitive overhead).

**This file also closes the `specs doctor` TREE-5 warning** on this repo's own specs tree
(TREE-5 warns when `specs/memory/AGENTS.md` is absent in the active context).

**Files changed:**

| File | Change |
|------|--------|
| `repos/dadaia-workspace/specs/memory/AGENTS.md` | **NEW** — authored by ai-engineer |

This file lives in the consumer workspace specs tree (not in `public/`). It is not
lib-originated and does not need to be staged/installed.

**Acceptance criteria:**

- AC-C4-1: `specs/memory/AGENTS.md` exists in this repo.
- AC-C4-2: The file contains all five content sections: read contract, write contract, atomicity contract, file manifest, generation note.
- AC-C4-3: The file is ≤ 80 lines.
- AC-C4-4: `dadaia specs doctor` no longer emits the TREE-5 warning for this repo after the file is created.
- AC-C4-5: The write contract section cites RULE A and `sdd-spec-gate.sh` explicitly.

---

### C-5 — Codex `memory-ctx` universal adapter

**What this is:** A new universal Codex skill adapter at
`dadaia_workspace/public/runtime/codex/memory-ctx/SKILL.md`, generalising the existing
`design-ctx` and `frontend-ctx` role-specific adapters. It provides every Codex session
the same memory bootstrap that Claude Code and OpenCode receive via `ctx-inject.sh`.

**Design (per ai-engineer report §2.3):**

The adapter protocol:
1. Resolve `specs_dir` (from `DADAIA_CONTEXT` env var or `.dadaia/states/primary_context.json`).
2. Read `specs/memory/architecture.html` — strip boilerplate inline (Bash heredoc or Python one-liner).
3. Read `specs/memory/tech-stack.html` — same strip.
4. Read `specs/memory/product/catalog.json` (or `product/index.html` if catalog absent).
5. Emit the context block into the agent's working context.

**Integration with existing adapters:** The existing `design-ctx` and `frontend-ctx`
adapters continue to exist as role supplements (they add release/task/report context).
`memory-ctx` is universal and fires first; role adapters fire after. This mirrors the
existing "this adapter supplements the canonical persona — it does NOT duplicate it"
principle.

**Registration mechanism (ADR-CX-001):** `_install_codex_runtime_adapters` in
`infrastructure/public_assets.py` auto-discovers every
`public/runtime/codex/<slug>/SKILL.md` by directory iteration and copies each to
`.codex/skills/<slug>/SKILL.md`. There is no hardcoded skill list and no per-skill
config registry. `memory-ctx` is registered purely by being a directory with a
`SKILL.md` — exactly as `design-ctx` and `frontend-ctx` are. No `config.toml` edit is
needed or exists for this purpose.

**Files changed:**

| File | Change |
|------|--------|
| `dadaia_workspace/public/runtime/codex/memory-ctx/SKILL.md` | **NEW** — universal memory bootstrap adapter |

After authoring, propagate:
```
dadaia public stage && dadaia public install --target all
dadaia public doctor   # must exit 0
```

`dadaia public doctor` check D-CX-6 validates all `public/runtime/codex/<slug>/SKILL.md`
adapters (leak/missing/drift), including `memory-ctx`.

**Acceptance criteria:**

- AC-C5-1: `dadaia_workspace/public/runtime/codex/memory-ctx/SKILL.md` exists.
- AC-C5-2: The skill file contains a 5-step protocol covering: specs_dir resolution, architecture.html read (with strip instruction), tech-stack.html read (with strip instruction), catalog.json read (with index.html fallback), and context block emission.
- AC-C5-3: After `dadaia public install --target all`, `memory-ctx/SKILL.md` is projected to `.codex/skills/memory-ctx/SKILL.md` (auto-discovered by `_install_codex_runtime_adapters`, ADR-CX-001); `dadaia public doctor` D-CX-6 reports no drift/missing for it.
- AC-C5-4: `dadaia public doctor` exits 0 after propagation.
- AC-C5-5: The skill explicitly states it fires before role-specific adapters (`design-ctx`, `frontend-ctx`).

---

## 5. Out of scope

### 5.1 YAML source-of-truth migration (`memory-structured-source-v1`)

The migration of 23 memory HTML atoms to YAML as the editable source of truth (with HTML
generated by a renderer) is the Phase-2 candidate `memory-structured-source-v1`. It
depends on THIS release being CLOSED (catalog.json and the doctor check must exist before
the YAML schema can reference them). The YAML migration is explicitly NOT in scope for
this release. Content stays HTML; injection strips boilerplate at runtime.

### 5.2 Hard read-receipt gate

A mechanism that proves an agent read and processed the memory (e.g., a read-receipt
stored in a session file) is not in scope. Operator decision D-1 accepted the trade-off:
soft injection guarantees the agent sees the map; it does not prove the agent used it.

### 5.3 Per-session bind injection upgrade

When `spec-context-session-locks-v1` ships, `ctx-inject.sh` could use the bind event
(`DADAIA_SESSION_ID` freshly set) as a cleaner injection trigger instead of
`UserPromptSubmit`. This upgrade and the session-mode emission in the injection payload
(SPEC / IMPLEMENTATION / REVIEW mode) are future work, dependent on the session-locks
release being in production.

### 5.4 Token-tier-aware injection

Injecting only `catalog.json` (~540 tokens, Option D) for Haiku-tier agents (researcher)
while injecting the full Option C payload for Sonnet/Opus agents is a future optimisation.
With 18 features the cost differential is small; the optimisation is premature.

### 5.5 Panel or CLI changes unrelated to memory

No panel tab changes, no new `dadaia context` verbs, no schema migration guards.

---

## 6. Architecture deltas

All changes are additive. No existing public assets are removed.

| Asset type | Path | Change |
|-----------|------|--------|
| Shell script (lib-originated) | `dadaia_workspace/public/scripts/ctx-inject.sh` | Extend payload: stripped arch + tech-stack + catalog |
| TypeScript plugin (lib-originated) | `dadaia_workspace/public/plugins/ctx-inject.ts` | Add first-message-only guard for OpenCode |
| Python helper (lib-originated) | `dadaia_workspace/public/scripts/strip-memory-html.py` | **NEW** — HTML boilerplate stripper; invoked by ctx-inject.sh |
| Agent personas (lib-originated) | `dadaia_workspace/public/agents/*.md` (21 files) | Add Step 0 block; P0 also get spec-navigator in skills |
| Codex adapter (lib-originated) | `dadaia_workspace/public/runtime/codex/memory-ctx/SKILL.md` | **NEW** — universal memory bootstrap adapter (auto-registered by directory iteration, ADR-CX-001; no config edit needed) |
| Python catalog generator | `dadaia_workspace/dadaia_workspace/features/specs/catalog.py` | **NEW** — reads index.html, writes catalog.json |
| Python doctor | `dadaia_workspace/dadaia_workspace/features/specs/doctor.py` | Add CAT-1 slug↔file sync check |
| Python CLI | `dadaia_workspace/dadaia_workspace/cli/commands/memory.py` | Wire catalog generation command |
| Consumer workspace file | `repos/dadaia-workspace/specs/memory/AGENTS.md` | **NEW** — local memory contract (not lib-originated) |
| Generated data file | `repos/dadaia-workspace/specs/memory/product/catalog.json` | **NEW** — generated, committed |
| Manifest | `.dadaia/agentic/manifest.json` | Updated by `dadaia public stage` to track new lib-originated assets |

**No changes to:**
- `public/scaffold/` (scaffold changes belong to `spec-context-tree-v2`)
- `public/templates/` (memory HTML templates unchanged)
- `sdd-spec-gate.sh` (the gate is unchanged; write enforcement is unaffected)
- `spec_contexts.json` schema (no state model changes)
- Any consumer workspace outside `repos/dadaia-workspace/specs/memory/`

---

## 7. Tech-stack deltas

| Item | Delta |
|------|-------|
| Python `html.parser` (stdlib) | Used by `strip-memory-html.py` to strip boilerplate. No new PyPI dependency. |
| Python `json` (stdlib) | Used by `catalog.py` generator. Already available. |
| Shell (bash) | `ctx-inject.sh` extended. No new shell tools required. |
| TypeScript | `ctx-inject.ts` guard added. Uses existing OpenCode plugin API. |
| No new PyPI dependencies | All implementation in Python + Bash + TypeScript (existing stack). |

---

## 8. Security and operations deltas

- **No security surface change.** This release adds injection of read-only memory content
  to the agent prompt; it does not expose any credentials, secrets, or writable paths.
  The injected content is already readable by all agents (memory HTML files have no access
  control).
- **Injection content review.** If `specs/memory/` were to contain sensitive information
  in the future, the injection would expose it universally. This is not a concern for the
  current content (product architecture, tech stack, feature catalog) and is noted for
  future operators who introduce sensitive memory atoms.
- **Catalog.json is a committed file.** It is generated from the HTML index, not from
  external sources; no injection risk.

---

## 9. Memory files affected at CLOSURE

At CLOSURE of this release, the following memory atoms must be updated:

- `specs/memory/architecture.html` — add description of the memory injection subsystem
  (ctx-inject.sh payload, strip-memory-html.py, first-message guard) and the catalog
  generation pipeline.
- `specs/memory/product/index.html` — add `memory-context-enforcement` to the feature
  catalog if a new feature entry for the injection subsystem is warranted; reorder if
  catalog relevance changed.
- `specs/memory/product/catalog.json` — regenerate to reflect any catalog order or
  feature list changes introduced at CLOSURE.
- `specs/memory/tech-stack.html` — note: Python `html.parser` (stdlib) now used for
  memory HTML stripping; no new PyPI dependency (update if different from current state).
- `specs/memory/AGENTS.md` — created as part of C-4 (not updated at CLOSURE; it is the
  deliverable itself).

Files that need no CLOSURE update (unchanged by this release):
- All `specs/memory/product/<feature>.html` atoms (feature descriptions are not changed).

---

## 10. Implementer ownership

| Cluster | Implementer | Work |
|---------|-------------|------|
| C-1 hook payload | **ai-engineer** (EXCLUSIVE owner of `public/` agents/skills/rules/hooks/scripts/plugins) | Extend `ctx-inject.sh` and `ctx-inject.ts`; create `strip-memory-html.py` |
| C-2 catalog generator + doctor check | **software-engineer-python** | `catalog.py` generator; CAT-1 doctor check; CLI wiring; initial `catalog.json` for this repo |
| C-3 Step-0 blocks | **ai-engineer** | Add Step 0 block to 21 personas; add spec-navigator to P0 frontmatter |
| C-4 `specs/memory/AGENTS.md` | **ai-engineer** | Author the local contract file |
| C-5 Codex adapter | **ai-engineer** | Create `memory-ctx/SKILL.md` (auto-registered by `_install_codex_runtime_adapters`, ADR-CX-001 — no config edit) |
| Hook propagation verification | **devops-engineer** | Verify injection wired in Claude Code + OpenCode + Codex settings after `dadaia public install`; confirm `public doctor` exit 0; confirm `ctx-inject.sh` fires and emits expected payload |
| Acceptance validation | **qa-engineer** | Define and run validation plan: 21/21 agent Step-0 check; injection-fires evidence; catalog-sync check; `dadaia public doctor` exit 0 across all three runtimes |

Sequencing note within the release:
- C-2 (catalog generator) must produce `catalog.json` before C-1 (hook payload) can be
  validated end-to-end with a real catalog. The two clusters can be implemented in
  parallel; full integration test requires both.
- C-4 (`AGENTS.md`) can be authored independently and in any order.
- C-3 (Step 0 blocks) and C-5 (Codex adapter) can be authored in parallel.
- devops-engineer's wiring verification runs after all ai-engineer + software-engineer-python
  work is committed and staged.

---

## 11. Dependencies and sequencing

### 11.1 Release dependencies

**None blocking.** This release:

- Rides the existing `ctx-inject.sh` hook (live infrastructure, no changes to the hook
  registration in `.claude/settings.json` needed — only the script payload changes).
- Has no dependency on `spec-context-session-locks-v1` (session binding is not required
  for the first-message injection pattern).
- Has no dependency on `spec-context-tree-v2` (scaffold and tree layout are already
  complete).
- Has no dependency on `go-open-source` or `panel-kanban-v1`.

**Downstream dependency:** `memory-structured-source-v1` (Phase 2, YAML source-of-truth)
explicitly depends on THIS release being CLOSED — specifically, `catalog.json` and the
CAT-1 doctor check must exist before Phase 2 can reference them in its schema design.

### 11.2 Self-applies to this repo AND consumer repos

The lib-originated changes (C-1, C-3, C-5) propagate to all consumer workspaces that run
`dadaia public install --target all`. The injected behaviour is universal. Consumer repos
that do not yet have `specs/memory/product/catalog.json` will gracefully fall back to
injecting stripped `product/index.html` per AC-C1-4.

### 11.3 Concurrency note

This release directory (`specs/releases/memory-context-enforcement-v1/`) is disjoint from
all currently active or in-flight release directories:

- `spec-context-session-locks-v1` — writes to `core/models/`, `infrastructure/`, `features/spec_context/service.py`, `sdd-spec-gate.sh`, `sdd-post-gate.sh`. Zero overlap with this release's write set.
- `go-open-source` — all code complete; pending operator action only. Zero overlap.
- `panel-kanban-v1` — panel frontend assets. Zero overlap with memory injection assets.

The only shared write surface is `dadaia_workspace/dadaia_workspace/features/specs/doctor.py`
(C-2 adds CAT-1; `spec-context-session-locks-v1` adds LOCK-1..LOCK-6; `spec-context-tree-v2`
added TREE-1..TREE-7). These additions are strictly additive and non-conflicting. They
must not be implemented in the same git commit, but they can land in any order because
each adds independent check IDs.

---

## 12. Open questions

### OQ-1 — Claude Code trigger: `UserPromptSubmit` vs `SessionStart`

**Question:** Does Claude Code expose a `SessionStart` (or equivalent once-per-session)
hook event, or is `UserPromptSubmit` the correct trigger for first-message injection?
If Claude Code fires `UserPromptSubmit` on every message (not just the first), a
first-message guard is needed there too (same as OpenCode).

**Working assumption:** `UserPromptSubmit` fires on every user message in Claude Code.
The first-message guard implementation for OpenCode (`ctx-inject.ts`) may need to be
mirrored in `ctx-inject.sh` for Claude Code. devops-engineer must confirm at implementation
time. If `UserPromptSubmit` fires only once per session (session-start behaviour), no guard
is needed for Claude Code.

**Impact if wrong:** Without a guard, the 7.3K payload is paid on every message in a
multi-turn Claude Code session, increasing token cost by ~10x for long sessions. Acceptable
as a Phase-1 interim; the guard should be added if Claude Code behaviour is confirmed
multi-turn.

### OQ-2 — First-message guard mechanism for OpenCode

**Question:** The first-message-only guard for `ctx-inject.ts` can be implemented via
`input.messageID` ordering (check if this is the lowest messageID seen so far in the
session) or via a session-scoped sentinel file in `.dadaia/sessions/`. Which mechanism
is available in the OpenCode plugin API?

**Owner:** devops-engineer at implementation time. If neither mechanism is available,
the guard defaults to a `.dadaia/tmp/ctx-inject-fired-<session-hash>` sentinel file.

### OQ-3 — `strip-memory-html.py` source location

**Question:** Does `strip-memory-html.py` live in `dadaia_workspace/public/scripts/`
(lib-originated, propagated to all consumers) or in `.dadaia/scripts/` (workspace-instance
level, not propagated)?

**Resolution (provisional):** `public/scripts/` is the correct location so all consumer
workspaces receive the helper automatically when they run `dadaia public install`. This is
consistent with `ctx-inject.sh` which already lives in `public/scripts/`. Devops-engineer
confirms at implementation time; if the public path creates any manifest or hook-path
issue, fall back to `.dadaia/scripts/` with a note in C-1's implementation.

### OQ-4 — Codex `memory-ctx` execution trigger

**Question:** In Codex, is a "execute memory-ctx before anything else" instruction in the
Step 0 block sufficient to guarantee the adapter fires, or does Codex require a dedicated
session-start trigger mechanism?

**Working assumption:** The Step 0 block instruction in the agent persona + the adapter's
auto-projection to `.codex/skills/memory-ctx/SKILL.md` (`_install_codex_runtime_adapters`,
ADR-CX-001 — by-directory discovery, no config registration) together are sufficient —
Codex loads the skill and the agent executes it as instructed. devops-engineer confirms at
implementation time.

### OQ-5 — Injection staleness across long sessions

**Observation (not a blocking question):** The first-message-only guard means a session
that runs across a memory update (e.g., product-engineer updates `architecture.html`
during CLOSURE while an implementer session is active) will not see the refreshed memory
until re-bind. This is the accepted trade-off (per analysis §8: "Risks & open
considerations"). Noted for future operators: when memory is updated during CLOSURE, inform
any active implementer sessions to re-start their session to pick up the fresh injection.

---

## 13. Acceptance criteria summary

### 13.1 Coverage (primary operator bar)

- AC-COVER-1: All 21 agent persona files contain a Step 0 memory bootstrap block. `grep -l "Step 0" dadaia_workspace/public/agents/*.md | wc -l` = `21`.
- AC-COVER-2: All 5 P0 agents have `dadaia-workspace-spec-navigator` in frontmatter `skills:`. Zero fully-blind agents remain.
- AC-COVER-3: `ctx-inject.sh` emits the memory payload (arch + tech-stack + catalog) when `DADAIA_CONTEXT` is set and `specs/memory/` exists.
- AC-COVER-4: `catalog.json` exists, is valid JSON, and all slugs map to existing feature HTML files.
- AC-COVER-5: `dadaia specs doctor` CAT-1 check passes (catalog slugs ↔ feature files in sync) for this repo.
- AC-COVER-6: `specs/memory/AGENTS.md` exists (closes TREE-5 `specs doctor` warning).
- AC-COVER-7: `dadaia_workspace/public/runtime/codex/memory-ctx/SKILL.md` exists.
- AC-COVER-8: `dadaia public doctor` exits 0 (no drift, no missing for all propagated assets).

### 13.2 Runtime parity (all three runtimes covered)

- AC-RT-1: Claude Code — injection fires on session start; memory payload present in agent context.
- AC-RT-2: OpenCode — injection fires on first message only; subsequent messages do not re-pay the 7.3K cost.
- AC-RT-3: Codex — `memory-ctx` adapter executes on session start per Step 0 instruction.

### 13.3 Token cost validation

- AC-TOK-1: Injected payload size (catalog.json present, 18 features) measured between 6,500 and 8,500 tokens.
- AC-TOK-2: Cost at Sonnet pricing ($3/MTok): ≤ $0.026 per session-start invocation.

### 13.4 `specs doctor` health

- AC-DOC-1: CAT-1 triggers on a catalog with a mismatched slug (regression fixture).
- AC-DOC-2: CAT-1 triggers on a missing `catalog.json` when feature HTML files exist (warn, not error).
- AC-DOC-3: TREE-5 is resolved for this repo (no warning when `specs/memory/AGENTS.md` exists).

---

*Product Engineer — dadaia-workspace | 2026-05-30*
