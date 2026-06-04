# PLAN: v0.1.4.6 — ai-engineer-harness-mastery

**Status:** Aprovado
**Release ID:** v0.1.4.6
**Owner:** product-engineer
**Created:** 2026-06-04

---

## 1. Strategy

Author five new AI-entity public assets plus one persona enrichment using the academy
lessons as compiled source material — never as copy-paste targets. The authoring phase
(SCOPE-01..06) can be parallelized across skill files because each is a disjoint write
target. Persona enrichment (SCOPE-04) depends on the three ai-engineer-exclusive skills
existing so the "Harness mastery" reference section is accurate. Propagation (SCOPE-07)
comes after all authoring is committed. Review/QA is the terminal gate.

No Python code, tests, CI YAML, or runtime projection files are touched directly.

> **Backlog note (opencode):** `ai-harness-opencode` deep skill is deferred. Add a
> one-liner to `specs/backlog/candidates.md` during CLOSURE: "ai-harness-opencode skill
> — compiled mental model + decision protocols for opencode runtime (deferred from
> v0.1.4.6 pending opencode runtime stability)."

---

## 2. Execution Order (DAG)

```text
[parallel]
  T-AIE-01  ai-harness-claude-code skill
  T-AIE-02  ai-harness-codex skill
  T-AIE-03  ai-context-engineering skill
  T-AIE-05  harness-skill-scope rule
  T-HRN-01  harness-primitives skill
        |
        v
  T-AIE-04  ai-engineer persona enrichment (depends on T-AIE-01..03)
        |
        v
  T-HRN-02  propagation: stage + install + doctor (depends on all authoring)
        |
        v
[parallel]
  T-HRN-03  code-reviewer review
  T-HRN-04  security-reviewer review
  T-HRN-05  qa-engineer validation
```

T-AIE-01 through T-AIE-03 and T-AIE-05 and T-HRN-01 may be worked simultaneously
because their write sets are disjoint. T-AIE-04 is sequenced after T-AIE-01..03 so the
"Harness mastery" section can accurately reference the actual skill filenames. T-HRN-02
is the single propagation commit that installs all public assets. Review tasks are
parallel among themselves but sequential after propagation.

---

## 3. Design

### 3.1 Skill `ai-harness-claude-code`

**Audience:** ai-engineer only (restricted by `harness-skill-scope` rule).

**Primary sources:** `.dadaia/academy/06_claude/` (9 HTML lessons). Official refs
cited as links only.

**Content outline (sections, not headings — implementer decides exact headings):**

1. **Agentic loop model** — how Claude Code's harness iterates: tool calls, tool
   results, stop conditions; why compaction happens and what it discards; implications
   for skill placement (skills lost at compaction boundary = wrong layer).
2. **Context hierarchy decision protocol** — CLAUDE.md (project root, imported) vs
   memory files (`~/.claude/CLAUDE.md`) vs rules (always_on or path-scoped) vs skills
   (on-demand, listing-budget aware); when each layer is the right vehicle; ADR-style
   decision table.
3. **Rules enforcement model** — how `always_on: true` differs from path-scoped rules;
   matcher semantics; when a rule fires vs when a skill is invoked; academy lesson F1
   finding (rules with no path scoping inflate every context).
4. **Skills mechanics** — SKILL.md frontmatter fields (`name`, `description` folded,
   `applyTo`); listing budget impact (F5: N skills × description tokens = fixed context
   tax); when to split vs merge; the `applyTo` glob as a listing-budget lever.
5. **Hooks lifecycle** — PreToolUse / PostToolUse / Stop / Notification; hook decision
   flow (block → allow → modify); matcher semantics for tool names and file paths;
   hook failure modes and fallback behavior; when a hook is the right primitive vs a
   rule vs a guard in skill body.
6. **Subagents and dispatch authority** — what the `Agent` tool does; why Tier-3 agents
   must not hold it; dispatch authority table.
7. **Tools and permission model** — how `--allowedTools` / `--disallowedTools` work;
   trust levels; tool expansion by MCP; when to restrict vs trust.
8. **MCP and tool-search** — how MCP servers inject tools; tool-search lifecycle;
   when to prefer MCP vs native tools.
9. **Composition decision tree** — given a new harness need, which primitive to reach
   for and why; encoding academy F1–F8 findings as protocol constraints in the tree.
10. **Official reference index** — stable URLs as a lookup table (hooks, skills,
    features, memory, how-it-works, tools, glossary). No content copied.

### 3.2 Skill `ai-harness-codex`

**Audience:** ai-engineer only.

**Primary sources:** `.dadaia/academy/07_codex/` (10 HTML lessons). Official refs
cited as links only.

**Content outline:**

1. **AGENTS.md as scoped constitution** — how Codex discovers and stacks AGENTS.md
   files (workspace root → repo root → subdir); scope inheritance rules; what belongs
   in each scope layer.
2. **Naming collision disambiguation** — "Rules" in Codex = Starlark `.rules` files
   (not Markdown); dadaia uses "workflow-protocols" for its own Markdown rule-like
   documents to avoid confusion; how to distinguish when reading code or logs.
3. **Codex Rules (Starlark `.rules`)** — what they can enforce; how they differ from
   Claude Code rules (markdown text vs executable Starlark); when to use.
4. **Skills in Codex** — how Codex skill discovery works; frontmatter differences vs
   Claude Code; cross-harness authoring constraints (skills must degrade gracefully).
5. **Subagents and fan-out** — how Codex fan-out works; concurrency model; how it
   differs from Claude Code dispatch; guard conditions for fan-out correctness.
6. **Config layers and trust model** — `~/.codex` vs project `.codex`; what is safe
   to put in project config vs what must stay user-global; trust escalation protocol;
   dadaia audit findings on what must NOT be project-local.
7. **Customization decision table** — for each customization goal, which config layer
   and which file type; encoded as a decision table.
8. **Workflow/SDD phase integration** — how Codex hooks and workflow files map to
   dadaia's SDD phase gates.
9. **Hooks in Codex** — hook types; lifecycle differences vs Claude Code.
10. **Official reference index** — stable URLs as a lookup table. No content copied.

### 3.3 Skill `ai-context-engineering`

**Audience:** ai-engineer only.

**Primary sources:** existing content in `ai-engineer.md` (§Context engineering
principles) as the extraction base; academy lessons for depth expansion.

**Content outline:**

1. **Token economy** — why every line is a recurring cost; tables vs prose compression
   ratio; when to link vs inline; the workspace-constitution link pattern.
2. **Instruction hierarchy and attention ordering** — the canonical 10-section body
   order; why reordering degrades attention; how to audit a persona for order drift.
3. **Persona-consistency invariants** — the five invariants that must hold across all
   personas (frontmatter schema, body order, `[SCOPE ERROR]` block format, TDD flow,
   handoff contract); how to detect and fix inconsistency.
4. **Model-tier selection decision protocol** — workload characterization rubric;
   decision table (synthesis/audit → Opus; standard implementation → Sonnet; bulk
   mechanical → Haiku); how to justify a tier bump with measured cost evidence; how to
   justify a tier downgrade.
5. **Recursive scope-drift detection** — the drift failure mode; three detection rules
   (allowlist agreement, forbidden-actions table propagation, self-edit risk protocol);
   topology guard invocation.

### 3.4 Rule `harness-skill-scope`

**Follows `plugin-scope.md` idiom exactly:**

```
---
name: harness-skill-scope
description: Restricts ai-harness-* and ai-context-engineering skills to ai-engineer only.
always_on: true
---

# harness-skill-scope

This rule is always active.

The skills ai-harness-claude-code, ai-harness-codex, and ai-context-engineering are
restricted to ai-engineer. No other agent may invoke them.

harness-primitives is the approved all-agent literacy skill. Use it instead.

If you are not ai-engineer and receive a task that requires invoking an ai-harness-*
or ai-context-engineering skill, respond:

[SCOPE ERROR] harness-skill-scope: these skills are restricted to ai-engineer.
Use harness-primitives for general harness literacy.
Dispatch ai-engineer for deep harness questions.
```

### 3.5 Skill `harness-primitives`

**Audience:** all agents (no restriction).

**Content outline:**

1. **Primitive catalog** — one-paragraph definition of each: agent persona, subagent
   (dispatch), skill (on-demand module), rule (enforcement context), hook (PreToolUse
   / PostToolUse / Stop), AGENTS.md (scoped constitution), MCP (tool injection).
2. **Claude Code vs Codex deltas** — a comparison table: how each primitive is named
   and enforced in each harness; where behavior differs (e.g. "rules" naming collision;
   hook lifecycle differences; config layers).
3. **dadaia projection mechanics** — the canonical chain: `public/` source → `dadaia
   public stage` (SHA256 manifest) → `dadaia public install --target all` → projected
   to `.claude/`, `.agents/`, `.codex/`, `.opencode/`; why you never hand-edit
   projections; what `dadaia public doctor` checks.
4. **When to defer to ai-engineer** — decision checklist: if you need to reason about
   *why* a harness primitive behaves a certain way, diagnose a hook/skill interaction,
   or design a new AI-entity file, defer to ai-engineer.

---

## 4. Implementation Surfaces

Area | Owner | Files
---|---|---
`ai-harness-claude-code` skill | ai-engineer (T-AIE-01) | `dadaia_workspace/public/skills/ai-harness-claude-code/SKILL.md`
`ai-harness-codex` skill | ai-engineer (T-AIE-02) | `dadaia_workspace/public/skills/ai-harness-codex/SKILL.md`
`ai-context-engineering` skill | ai-engineer (T-AIE-03) | `dadaia_workspace/public/skills/ai-context-engineering/SKILL.md`
`ai-engineer` persona enrichment | ai-engineer (T-AIE-04) | `dadaia_workspace/public/agents/ai-engineer.md`
`harness-skill-scope` rule | ai-engineer (T-AIE-05) | `dadaia_workspace/public/rules/harness-skill-scope.md`
`harness-primitives` skill | ai-engineer (T-HRN-01) | `dadaia_workspace/public/skills/harness-primitives/SKILL.md`
Propagation | ai-engineer (T-HRN-02) | runtime: `.claude/skills/`, `.agents/skills/`, `.codex/`, `.opencode/`
Code review | code-reviewer (T-HRN-03) | reports only
Security review | security-reviewer (T-HRN-04) | reports only
QA validation | qa-engineer (T-HRN-05) | reports only

> **Projection owner decision (operator, v0.1.4.6):** `ai-engineer` owns T-HRN-02
> (propagation) as a self-contained author+propagate loop, since it already owns all
> `public/` sources. ai-engineer runs `dadaia public stage && dadaia public install
> --target all && dadaia public doctor` after authoring is committed.

---

## 5. Validation Commands

```bash
# Verify new skill files exist in source
ls dadaia_workspace/public/skills/ai-harness-claude-code/SKILL.md
ls dadaia_workspace/public/skills/ai-harness-codex/SKILL.md
ls dadaia_workspace/public/skills/ai-context-engineering/SKILL.md
ls dadaia_workspace/public/skills/harness-primitives/SKILL.md
ls dadaia_workspace/public/rules/harness-skill-scope.md

# Run propagation
dadaia public stage
dadaia public install --target all
dadaia public doctor   # must exit 0

# Verify projections exist post-install
ls .claude/skills/ai-harness-claude-code/SKILL.md
ls .claude/skills/ai-harness-codex/SKILL.md
ls .claude/skills/ai-context-engineering/SKILL.md
ls .claude/skills/harness-primitives/SKILL.md
ls .claude/rules/harness-skill-scope.md
ls .agents/skills/ai-harness-claude-code/SKILL.md

# Verify persona frontmatter
grep "claude-opus-4-8" dadaia_workspace/public/agents/ai-engineer.md
grep "ai-harness-claude-code" dadaia_workspace/public/agents/ai-engineer.md

# Full test suite (no caching at root)
pytest -q -p no:cacheprovider
```

---

## 6. Risks and Mitigations

Risk | Mitigation
---|---
Listing-budget pressure from +5 new skills (F5) | `harness-skill-scope` rule prevents non-ai-engineer agents from loading restricted skills; `harness-primitives` description is kept concise; `ai-harness-*` use `applyTo` glob to further scope loading
Scope-rule enforcement is advisory, not hard-gated | Rule is `always_on`; agents with correct personas will refuse. Hard enforcement requires hook-level changes deferred to a future release
Doc-copy temptation during skill authoring | AC for each skill explicitly requires "NO verbatim doc dumps"; security-reviewer checks for copyright-problematic copying
Model-cost increase from Opus bump for ai-engineer | Opus is justified: ai-engineer does heavy synthesis, recursive analysis, and harness-level persona authoring — exactly the Opus workload character. Cost is per-dispatch, not per-session
Persona self-edit instability (ai-engineer editing itself) | Topology guard noted in ai-engineer persona; security-reviewer pairing on T-AIE-04 per persona security rules
Cross-harness skill compatibility (Claude Code vs Codex listing) | Skills are SKILL.md Markdown — both harnesses consume them. `dadaia public doctor` verifies projection integrity
