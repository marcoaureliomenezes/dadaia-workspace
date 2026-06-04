# TASKS: v0.1.4.6 — ai-engineer-harness-mastery

**Status:** Aprovado

parallel_tasks: T-AIE-01, T-AIE-02, T-AIE-03, T-AIE-05, T-HRN-01 (disjoint write sets)

Markers: `[ ]` open → `[-]` in progress → `[x]` done.
At most one `[-]` per owner at a time unless the task header declares disjoint write
sets. T-AIE-01 through T-AIE-03, T-AIE-05, and T-HRN-01 have disjoint write sets
and may be worked in parallel by ai-engineer (each targets a distinct file path).

---

### T-AIE-01 — Skill: `ai-harness-claude-code`
- **Owner:** ai-engineer
- **Status:** [x]
- **Write set:** `dadaia_workspace/public/skills/ai-harness-claude-code/SKILL.md` (new file)
- **Preconditions:** TASKS.md Aprovado; ACTIVE.md phase = IMPLEMENTATION; marker `[-]` committed.
- **Inputs:** `.dadaia/academy/06_claude/` (9 HTML lessons); official Claude Code docs as
  linked references only (hooks, skills, features, memory, how-it-works, tools, glossary).
- **Description:** Author a new deep skill for ai-engineer containing compiled mental model
  and decision protocols for the Claude Code harness. Cover: agentic loop and compaction;
  context hierarchy decision protocol (CLAUDE.md vs rule vs skill vs subagent vs hook vs MCP);
  rules enforcement model (always_on vs path-scoped, academy lesson F1); skills mechanics
  (frontmatter, listing budget F5, applyTo lever); hooks lifecycle (PreToolUse/PostToolUse/Stop/
  Notification, matcher semantics); subagents and dispatch authority; tools and permission model;
  MCP and tool-search; composition decision tree encoding findings F1–F8; official reference index
  (URLs as links, no transcribed text).
- **Done criterion:** File exists; frontmatter has `name: ai-harness-claude-code` and `description`
  (folded `>`); body contains decision-protocol sections (not doc copies); all composition
  decision-tree nodes are covered; official refs cited as links only; no verbatim doc text;
  code-reviewer + security-reviewer approve same commit.

---

### T-AIE-02 — Skill: `ai-harness-codex`
- **Owner:** ai-engineer
- **Status:** [x]
- **Write set:** `dadaia_workspace/public/skills/ai-harness-codex/SKILL.md` (new file)
- **Preconditions:** Same as T-AIE-01. May run in parallel with T-AIE-01, T-AIE-03, T-AIE-05, T-HRN-01.
- **Inputs:** `.dadaia/academy/07_codex/` (10 HTML lessons); official Codex docs as linked
  references only (agents-md, rules, skills, subagents, config-advanced, customization).
- **Description:** Author a new deep skill for ai-engineer containing compiled mental model
  and decision protocols for the Codex harness. Cover: AGENTS.md as scoped constitution;
  naming-collision disambiguation (Codex Rules = Starlark vs dadaia workflow-protocols naming);
  Codex Rules (.rules); skills in Codex (frontmatter deltas vs Claude Code); subagents and
  fan-out; config layers and trust model (what must NOT be project-local); customization decision
  table; workflow/SDD phase integration; hooks in Codex; official reference index (URLs as links).
- **Done criterion:** File exists; frontmatter valid; body contains decision-protocol sections;
  naming collision is explicitly disambiguated; config trust model is explicit; official refs cited
  as links only; no verbatim doc text; code-reviewer + security-reviewer approve same commit.

---

### T-AIE-03 — Skill: `ai-context-engineering`
- **Owner:** ai-engineer
- **Status:** [x]
- **Write set:** `dadaia_workspace/public/skills/ai-context-engineering/SKILL.md` (new file)
- **Preconditions:** Same as T-AIE-01. May run in parallel with T-AIE-01, T-AIE-02, T-AIE-05, T-HRN-01.
- **Inputs:** Existing §"Context engineering principles" in `dadaia_workspace/public/agents/ai-engineer.md`
  (extraction source); academy lessons for depth expansion.
- **Description:** Extract and expand the context-engineering principles currently inlined in the
  ai-engineer persona into a dedicated deep skill. Cover: token economy (cost per line, tables vs
  prose compression, link vs inline decision); instruction hierarchy and attention ordering (the
  10-section order, audit protocol for order drift); persona-consistency invariants (5 invariants,
  detection, fix protocol); model-tier selection decision protocol (workload rubric, decision table,
  cost-justification discipline); recursive scope-drift detection (failure mode, 3 detection rules,
  topology guard protocol).
- **Done criterion:** File exists; frontmatter valid; content is deeper and more protocol-oriented
  than the inline version it replaces; all five topic areas covered; code-reviewer + security-reviewer
  approve same commit.

---

### T-AIE-04 — Persona enrichment: `ai-engineer`
- **Owner:** ai-engineer
- **Status:** [x]
- **Write set:** `dadaia_workspace/public/agents/ai-engineer.md` (modify existing)
- **Preconditions:** T-AIE-01, T-AIE-02, T-AIE-03 must be complete (skills must exist before
  the persona references them); ACTIVE.md phase = IMPLEMENTATION; marker `[-]` committed.
- **Description:** Enrich the ai-engineer persona with the following changes:
  1. Set `model: claude-opus-4-8` in frontmatter (operator-approved in v0.1.4.6 brief).
  2. Add `ai-harness-claude-code`, `ai-harness-codex`, `ai-context-engineering` to frontmatter `skills:` list.
  3. Add a "Harness mastery" section (after the existing "Scope" section and before "Boundary with
     product-engineer") declaring expertise across Claude Code and Codex (opencode = future),
     referencing the three deep skills by name, and listing the official doc URLs as on-demand
     search surface.
  4. Replace the inline §"Context engineering principles" body content with a concise reference
     to the `ai-context-engineering` skill (retain a one-paragraph summary for orientation, remove
     duplicated depth).
  5. In the Model-tier selection table: replace `claude-opus-4-7` with `claude-opus-4-8`.
- **Done criterion:** Frontmatter has `model: claude-opus-4-8` and all three new skills listed;
  "Harness mastery" section exists; `claude-opus-4-7` does not appear anywhere in the file;
  persona-consistency invariants hold (frontmatter schema, body section order, `[SCOPE ERROR]`
  block, write-allowlist); code-reviewer + security-reviewer approve same commit.

---

### T-AIE-05 — Rule: `harness-skill-scope`
- **Owner:** ai-engineer
- **Status:** [x]
- **Write set:** `dadaia_workspace/public/rules/harness-skill-scope.md` (new file)
- **Preconditions:** Same as T-AIE-01. May run in parallel with T-AIE-01, T-AIE-02, T-AIE-03, T-HRN-01.
- **Description:** Author a new always_on restriction rule following the `plugin-scope.md` idiom
  exactly. Frontmatter: `name: harness-skill-scope`, `description` (folded), `always_on: true`.
  Body: state that `ai-harness-claude-code`, `ai-harness-codex`, and `ai-context-engineering` are
  restricted to `ai-engineer`; name `harness-primitives` as the approved all-agent literacy skill;
  provide a `[SCOPE ERROR]`-style refusal block for non-authorized agents.
- **Done criterion:** File exists; `always_on: true` in frontmatter; names all three restricted
  skills; provides `[SCOPE ERROR]` refusal block; follows plugin-scope.md idiom exactly (same
  frontmatter structure, same block format); code-reviewer + security-reviewer approve same commit.

---

### T-HRN-01 — Skill: `harness-primitives`
- **Owner:** ai-engineer
- **Status:** [x]
- **Write set:** `dadaia_workspace/public/skills/harness-primitives/SKILL.md` (new file)
- **Preconditions:** Same as T-AIE-01. May run in parallel with T-AIE-01 through T-AIE-05.
- **Description:** Author a shared middle-depth literacy skill available to all agents (no
  restriction). Cover: primitive catalog (one-paragraph definition each: agent persona, subagent,
  skill, rule, hook, AGENTS.md, MCP); Claude Code vs Codex primitive deltas (comparison table);
  dadaia projection mechanics (public/ → stage → install → projected trees; manifest SHA256;
  why projections are never hand-edited; what dadaia public doctor checks); when to defer to
  ai-engineer (decision checklist). Content must be literacy-depth — do not replicate the
  decision protocols that belong in the ai-engineer-only skills.
- **Done criterion:** File exists; frontmatter valid; all four content areas covered; no
  deep-mastery duplication of ai-engineer-only skill content; code-reviewer + security-reviewer
  approve same commit.

---

### T-FIX-01 — Codex model-map support for claude-opus-4-8 (scope amendment)
- **Owner:** software-engineer-python
- **Status:** [x]
- **Authorization:** Operator-approved scope amendment (2026-06-04). SPEC §4 "no Python
  changes" is amended for this single transform: the AC-4 opus-4-8 bump cannot propagate
  to Codex (AC-7 `--target all`) without a `MODEL_MAP` entry. Minimal, bounded change.
- **Write set:** `dadaia_workspace/infrastructure/runtime_transforms/model_mapping.py`,
  `tests/unit/infrastructure/runtime_transforms/test_model_mapping.py`,
  `dadaia_workspace/features/telemetry/pricing.py`
- **Description:** Add `"claude-opus-4-8": "gpt-5.5"` to `MODEL_MAP`. Update the
  "exactly 3 entries" guard test to 4 and add `assert map_model("claude-opus-4-8") ==
  "gpt-5.5"`. Add a `claude-opus-4-8` row to `PRICING_TABLE` (mirror opus-4-7 pricing).
- **Done criterion:** `pytest -q -p no:cacheprovider tests/unit/infrastructure/runtime_transforms/test_model_mapping.py tests/unit/features/telemetry/` passes; `map_model("claude-opus-4-8")` returns `"gpt-5.5"`.

---

### T-HRN-02 — Propagation: stage + install + doctor
- **Owner:** ai-engineer
- **Status:** [x]
- **Write set:** `.claude/skills/`, `.agents/skills/`, `.codex/`, `.opencode/` (via dadaia public install)
- **Preconditions:** T-AIE-01, T-AIE-02, T-AIE-03, T-AIE-04, T-AIE-05, T-HRN-01 all complete.
- **Description:** Run the full propagation chain:
  ```bash
  dadaia public stage
  dadaia public install --target all
  dadaia public doctor
  ```
  Verify `dadaia public doctor` exits 0. Verify the 5 new skills appear in `.claude/skills/`
  and `.agents/skills/`. Verify the new rule appears in `.claude/rules/`. Commit the propagation
  result with a conventional-commit message referencing T-HRN-02.
- **Done criterion:** `dadaia public doctor` exits 0; all 5 new skill directories present in
  `.claude/skills/` and `.agents/skills/`; `harness-skill-scope.md` present in `.claude/rules/`;
  ai-engineer.md in `.claude/agents/` reflects `claude-opus-4-8` model; no lib-originated path
  was hand-edited (all changes via install chain); commit SHA captured.

---

### T-HRN-03 — Code review
- **Owner:** code-reviewer
- **Status:** [x]
- **Write set:** `.dadaia/reports/dadaia-workspace/code-reviewer/` and `.dadaia/handoff/dadaia-workspace/` (reports only)
- **Preconditions:** T-HRN-02 complete (review the propagated commit, not pre-propagation).
- **Pre-agreed review criteria:**
  - Frontmatter schema consistency across all 5 new SKILL.md files and the modified ai-engineer.md
    (name, description folded, optional applyTo; agent persona has full frontmatter schema).
  - Body section order follows the canonical 10-section instruction hierarchy (where applicable).
  - `[SCOPE ERROR]` block format consistent with workspace idiom.
  - Write-allowlist in ai-engineer.md frontmatter and body are in agreement.
  - `harness-skill-scope.md` follows the plugin-scope.md idiom exactly.
  - `harness-primitives` does not duplicate deep-mastery content.
  - No dead sections, no stale model references (zero occurrences of `claude-opus-4-7`).
- **Done criterion:** Handoff JSON emitted with `verdict: APPROVED` (or `REQUEST_CHANGES` sent
  back to ai-engineer for rework). Task stays `[-]` until APPROVED.

---

### T-HRN-04 — Security review
- **Owner:** security-reviewer
- **Status:** [x]
- **Write set:** `.dadaia/reports/dadaia-workspace/security-reviewer/` and `.dadaia/handoff/dadaia-workspace/` (reports only)
- **Preconditions:** T-HRN-02 complete.
- **Pre-agreed security checks:**
  - No consumer-specific names, hostnames, IPs, private repo slugs, or operator-private data in
    any new skill or rule (public/ assets ship open-source).
  - No verbatim transcription of copyrighted documentation text.
  - No secrets, tokens, or auth credentials embedded in any skill body.
  - No prompt-injection vectors (e.g. skill body instructing agents to bypass other rules).
  - ai-engineer.md `paths.write_allowlist` not widened beyond what SPEC authorizes.
  - `harness-skill-scope` rule does not inadvertently restrict agents beyond the stated scope.
  - Privacy gate: spot-check that official URL references are to public documentation, not
    internal or login-gated pages.
- **Done criterion:** Handoff JSON emitted with `verdict: APPROVED` (or `REQUEST_CHANGES` sent
  back to ai-engineer for rework). Task stays `[-]` until APPROVED.

---

### T-HRN-05 — QA validation
- **Owner:** qa-engineer
- **Status:** [x]
- **Write set:** `.dadaia/reports/dadaia-workspace/qa-engineer/` and `.dadaia/handoff/dadaia-workspace/` (reports only)
- **Preconditions:** T-HRN-02 complete; T-HRN-03 and T-HRN-04 APPROVED.
- **Validation plan:**
  - `dadaia public doctor` exits 0 (evidence: command output).
  - All 5 new skills listed in `.claude/skills/` directory.
  - `harness-skill-scope.md` listed in `.claude/rules/` directory.
  - ai-engineer persona in `.claude/agents/` has `model: claude-opus-4-8`.
  - Spot-check: a simulated non-ai-engineer agent prompt referencing `ai-harness-claude-code`
    produces the `[SCOPE ERROR]` refusal (advisory enforcement check — documented as advisory
    per PLAN §6 risks).
  - `pytest -q -p no:cacheprovider` passes (no regression from public asset authoring).
  - No cache or output artifacts created inside any repo working tree or at workspace root.
- **Done criterion:** All validation checks pass with evidence captured; handoff JSON emitted
  with `verdict: APPROVED`. Task stays `[-]` until APPROVED.
