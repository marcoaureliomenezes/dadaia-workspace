# SPEC: v0.1.4.6 — ai-engineer-harness-mastery

**Status:** Aprovado
**Release ID:** v0.1.4.6
**Owner:** product-engineer
**Created:** 2026-06-04

> Staging release-id (4-segment). `pyproject` stays at `0.1.4`; no version bump.
> Goal: deepen ai-engineer into the workspace's true harness specialist and give
> every other agent a shared literacy baseline. Pure AI-entity surface work —
> no Python code, no CI YAML, no test changes, no frontend.

---

## 1. Objective

The dadaia-workspace is the native SDD workspace for AI-agentic development, tailored
to Claude Code and Codex. Today the ai-engineer persona documents good context-engineering
principles, but holds no compiled, reasoned, actionable knowledge of *how the harnesses
actually work* — their primitives, enforcement mechanisms, decision protocols, and dadaia
audit lessons. Every other agent lacks even baseline literacy about what the workspace
harness primitives are.

This release closes that gap in two concentric circles:

- **Inner circle (ai-engineer-exclusive):** three deep skills that compile the academy
  lessons into decision protocols for Claude Code (`ai-harness-claude-code`), Codex
  (`ai-harness-codex`), and harness-agnostic context engineering
  (`ai-context-engineering`), plus persona enrichment and a scope-restriction rule.
- **Outer circle (all agents):** one shared literacy skill (`harness-primitives`) that
  gives every agent a working mental model of what each harness primitive is, how dadaia
  projects them, and when to defer to ai-engineer for depth.

---

## 2. Problem and Context

### Why ai-engineer needs harness mastery

The ai-engineer today can write persona files, but it cannot reason about *why* a
rule fires and a skill does not, *when* a hook pre-empts a tool call, or *what* the
context-window compaction boundary means for skill placement. When harness bugs appear
(e.g. academy audit findings F1–F8), ai-engineer cannot diagnose them without
ad-hoc research. The academy lessons (`.dadaia/academy/06_claude/` and
`.dadaia/academy/07_codex/`) already contain that compiled knowledge — this release
lifts it into three dedicated deep skills so ai-engineer can reason from protocol
rather than from first principles every session.

### Why a shared literacy skill is needed

Eleven other agents (software-engineer-python, qa-engineer, devops-engineer, etc.) are
asked to follow workspace protocols (workspace-protocol.md, tmp-file-guardrail, etc.)
without knowing what the underlying harness mechanisms they reference actually are.
When a new collaborator or a dispatched agent asks "what is a skill?" or "why does
this rule fire?", there is no single place that answers at middle depth. `harness-primitives`
closes that gap without duplicating the deep-mastery content that belongs only to ai-engineer.

---

## 3. Scope (in)

### SCOPE-01 — New skill: `ai-harness-claude-code` (ai-engineer-exclusive)

Compiled mental model + decision protocols for Claude Code. Covers: agentic loop and
harness architecture; context window and compaction mechanics; CLAUDE.md / memory
hierarchy and `@import` scoping; rules (always_on vs path-scoped) and enforcement;
skills and SKILL.md frontmatter (listing budget, name/description/applyTo);
hooks lifecycle (PreToolUse / PostToolUse / Stop / Notification) and matcher semantics;
subagents and dispatch authority; tools and permission model; MCP and tool-search
lifecycle; the composition decision tree (when to use CLAUDE.md vs rule vs skill vs
subagent vs hook vs MCP). Encodes dadaia audit lessons F1–F8 as applied wisdom.
Carries official reference URLs as on-demand links, never as transcribed content.

Write target: `dadaia_workspace/public/skills/ai-harness-claude-code/SKILL.md`

### SCOPE-02 — New skill: `ai-harness-codex` (ai-engineer-exclusive)

Compiled mental model + decision protocols for Codex. Covers: AGENTS.md as scoped
constitution; official Rules (Starlark `.rules`) vs dadaia workflow-protocol naming
collision (disambiguated); skills; subagents and fan-out patterns; config layers
(`~/.codex` vs project `.codex`) and trust model; what must not be project-local;
customization decision table; workflow/SDD phase integration; hooks. Encodes dadaia
Codex audit lessons. Carries official reference URLs as on-demand links.

Write target: `dadaia_workspace/public/skills/ai-harness-codex/SKILL.md`

### SCOPE-03 — New skill: `ai-context-engineering` (ai-engineer-exclusive)

Harness-agnostic context-engineering craft. Covers: token economy principles;
instruction hierarchy and attention ordering; persona-consistency invariants;
model-tier selection decision table; recursive scope-drift detection protocol.
Extracts and expands the principles currently inlined in the ai-engineer persona so
they become a reusable, deeper skill. The persona body will reference this skill
instead of duplicating the content.

Write target: `dadaia_workspace/public/skills/ai-context-engineering/SKILL.md`

### SCOPE-04 — Enrich ai-engineer persona

Add a "Harness mastery" section to `dadaia_workspace/public/agents/ai-engineer.md`
declaring expertise across Claude Code and Codex (opencode = future), referencing the
three new skills, and listing the official doc URLs as the on-demand search surface.
Replace the inlined context-engineering content with a reference to the
`ai-context-engineering` skill (token economy). Set `model: claude-opus-4-8`
(operator-approved upgrade). Modernize the stale `claude-opus-4-7` reference in the
Model-tier selection table to `claude-opus-4-8`. Add the three new skills to the
persona frontmatter `skills:` list.

Write target: `dadaia_workspace/public/agents/ai-engineer.md`

### SCOPE-05 — New restriction rule: `harness-skill-scope` (always_on)

New rule at `dadaia_workspace/public/rules/harness-skill-scope.md` restricting the
**three** deep skills (`ai-harness-claude-code`, `ai-harness-codex`,
`ai-context-engineering`) to `ai-engineer` only. `harness-primitives` (SCOPE-06) is the
open all-agent literacy skill and is explicitly NOT restricted by this rule.
Follows the `plugin-scope.md` idiom: frontmatter with `name`, `description`,
`always_on: true`; body states the restriction and provides a `[SCOPE ERROR]`-style
refusal block for non-authorized agents.

Write target: `dadaia_workspace/public/rules/harness-skill-scope.md`

### SCOPE-06 — New shared skill: `harness-primitives` (all agents)

One unified skill available to all agents. Explains at middle depth: what each
primitive IS (agent, subagent, skill, rule, hook, AGENTS.md, MCP); Claude-Code-vs-Codex
naming and behavior deltas (e.g. rules in Claude Code = always_on Markdown vs Codex
Starlark `.rules`); how dadaia projects and enforces them (public/ source → stage →
install → .claude/.codex/.opencode/.agents; manifest SHA256; SDD and root-whitelist
gates); and when an agent should defer deep harness questions to ai-engineer. This is
literacy, not mastery.

Write target: `dadaia_workspace/public/skills/harness-primitives/SKILL.md`

### SCOPE-07 — Propagation

Run `dadaia public stage && dadaia public install --target all && dadaia public doctor`
to project all new/modified public assets to `.claude/skills/`, `.agents/skills/`,
`.codex/`, and `.opencode/` runtime trees. Verify `dadaia public doctor` exits 0.

---

## 4. Out of Scope

- `ai-harness-opencode` deep skill — deferred to a future release (opencode runtime
  is not yet stable enough for a compiled protocol skill).
- Any verbatim documentation copying — skills must be decision protocols, not doc dumps.
- Python, TypeScript, Go, or test-file changes (`*.py`, `*.ts`, `tests/**`).
- CI YAML changes (`.github/workflows/**`).
- Hand-editing projected runtime files (`.claude/`, `.codex/`, `.opencode/`, `.agents/`);
  propagation happens exclusively through `dadaia public install`.
- Pyproject version bump — stays at `0.1.4`.
- Memory atom updates — forbidden outside CLOSURE.
- Touching v0.1.4.3, v0.1.4.4, or any prior release directory.

---

## 5. Constraints

- **Lib-guardrail:** all authoring targets are `dadaia_workspace/public/...` source files.
  Never edit `.claude/`, `.agents/`, `.codex/`, or `.opencode/` directly. Propagation
  only via `dadaia public stage && dadaia public install --target all`.
- **HARD PRINCIPLE — no doc dumps:** Skills are compiled, reasoned, deep-thought synthesis
  and decision protocols. Official URLs are references to consult on demand, not content
  to transcribe. Every skill-authoring task acceptance criterion must explicitly verify:
  "contains decision protocols + reasoning; cites official refs as links; contains NO
  verbatim doc dumps."
- **SDD gate:** production writes require ACTIVE.md set to `release: v0.1.4.6 / phase:
  IMPLEMENTATION` and the relevant TASKS marker flipped to `[-]` before any write to a
  `dadaia_workspace/public/...` path.
- **Skill listing budget (F5):** adding 5 new skills increases the listing-budget pressure
  on context windows. The `harness-skill-scope` rule must describe the scope boundary
  clearly enough that agents do not attempt to invoke restricted skills, minimizing wasted
  listing budget.
- **Privacy gate:** all public/ assets are shipped in the open-source library. No
  consumer-specific names, hostnames, IPs, private repo slugs, or operator-private
  data may appear in any skill or rule.
- **Model bump authorization:** `claude-opus-4-8` for ai-engineer is operator-approved
  in this release brief. No other model assignments change.

---

## 6. Acceptance Criteria

- **AC-1:** `dadaia_workspace/public/skills/ai-harness-claude-code/SKILL.md` exists,
  contains decision-protocol sections (not doc copies), cites official URLs as links,
  and covers all domains listed in SCOPE-01.
- **AC-2:** `dadaia_workspace/public/skills/ai-harness-codex/SKILL.md` exists, contains
  decision-protocol sections, cites official URLs as links, and covers all domains listed
  in SCOPE-02.
- **AC-3:** `dadaia_workspace/public/skills/ai-context-engineering/SKILL.md` exists,
  extracts and expands the context-engineering content from the persona, and covers all
  domains listed in SCOPE-03.
- **AC-4:** `dadaia_workspace/public/agents/ai-engineer.md` has `model: claude-opus-4-8`,
  a "Harness mastery" section referencing the three deep skills, the stale
  `claude-opus-4-7` reference replaced with `claude-opus-4-8`, and the three new skills
  listed in `skills:` frontmatter. Inlined context-engineering prose is condensed with a
  reference to `ai-context-engineering`.
- **AC-5:** `dadaia_workspace/public/rules/harness-skill-scope.md` exists with
  `always_on: true`, names the three restricted skills (and names `harness-primitives`
  as the open all-agent alternative), provides a `[SCOPE ERROR]`-style
  refusal, and follows the `plugin-scope.md` idiom exactly.
- **AC-6:** `dadaia_workspace/public/skills/harness-primitives/SKILL.md` exists, covers
  middle-depth literacy for all primitive types and dadaia projection mechanics, and does
  not duplicate the deep-mastery content of the ai-engineer-only skills.
- **AC-7:** `dadaia public doctor` exits 0 after propagation. All 5 new skills appear in
  `.claude/skills/` and `.agents/skills/`.
- **AC-8:** No verbatim documentation text is present in any skill file. Security reviewer
  confirms no private data, secrets, consumer-specific names, or doc-copyright violations.
- **AC-9:** Code reviewer confirms persona-consistency invariants hold (frontmatter schema,
  body section order, `[SCOPE ERROR]` format, write-allowlist agreement).
- **AC-10:** `ai-harness-*` and `ai-context-engineering` skills are NOT invocable by
  non-ai-engineer agents per the `harness-skill-scope` rule (advisory enforcement verified
  by qa-engineer spot-check).
