# Plan: codex-design-frontend-projection-pilot-v1

**Status:** Aprovado
**Release ID:** codex-design-frontend-projection-pilot-v1
**Owner:** product-engineer
**Created:** 2026-05-20

---

## Strategy

This release has three independent work streams that converge in Phase P5 (tests):

1. **Shared skill authoring (P1)** — create the SKILL.md files that close the gap
   between what agent frontmatter references and what exists on disk.
2. **Agent frontmatter update (P2)** — wire the new skills into `design-specialist`
   and `frontend-engineer` frontmatter, respecting the plugin-scope rule boundaries
   from the SPEC (FR4, ADR-CX-005).
3. **Codex-only runtime boundary (P3 + P4)** — establish `public/runtime/codex/` as
   the canonical source for Codex-exclusive adapters, extend `_install_codex()` to read
   from that path, add a doctor check for boundary violations, and author two adapter
   stubs.

P1 and P2 may run in parallel. P3 must complete before P4. P5 (tests) may begin once
P1, P2, and P3 are all done. P6 (stage + install + doctor validation) follows P5. P7
(CLOSURE) is the product-engineer gate after P6 passes.

---

## Layers affected

| Layer | Files touched |
|---|---|
| `public/skills/` | 4 new SKILL.md files (1 already exists: `ux-ui-review`) |
| `public/agents/` | `design-specialist.md`, `frontend-engineer.md` |
| `public/runtime/codex/` | new directory; 2 adapter SKILL.md stubs |
| `infrastructure/public_assets.py` | `_install_codex()` extended; doctor check added |
| `tests/unit/features/public/` | new test file for skill-reference integrity |
| `tests/integration/` | SHA snapshot null-regression; boundary; leak-detection tests |

---

## Phase P1 — Shared skill SKILL.md files

**Owner:** ai-engineer
**Parallelism:** Safe to run concurrently with P2 (disjoint file sets).

Four of the five skills named in the SPEC §6 need new SKILL.md files. One
(`ux-ui-review`) already exists and is checked off in the acceptance criteria via C2.

### Skills to create

| Skill slug | Path | Purpose |
|---|---|---|
| `frontend-design` | `public/skills/frontend-design/SKILL.md` | Workspace surface catalogue, token naming, typography scale, spacing system, component handoff conventions. Used by both `design-specialist` and `frontend-engineer` (read-only context). |
| `design-reference-research` | `public/skills/design-reference-research/SKILL.md` | Approved reference whitelist and citation protocol for design decisions. Centralises the source-whitelist logic currently embedded in the design-specialist agent body. |
| `design-report-quality-gate` | `public/skills/design-report-quality-gate/SKILL.md` | Validates design report completeness (required sections, token presence, handoff notes, WCAG evidence). Does not require Bash or Edit. |
| `frontend-implementation-quality` | `public/skills/frontend-implementation-quality/SKILL.md` | Objective frontend implementation gates: TDD protocol, TypeScript strictness, component tests, accessibility checks, responsive breakpoints, performance budget, OWASP frontend checklist. |

`ux-ui-review` already exists at `public/skills/ux-ui-review/SKILL.md`; no change
needed.

### Content requirements (applies to each new SKILL.md)

Each file must open with a `# <Skill Name>` heading, followed by:

- `## Purpose` — one paragraph on what the skill provides.
- `## Protocol` (or named sections relevant to the skill's domain) — the actionable
  content implementers follow.
- `## Guardrails` — what is out of scope for this skill.

Each file is plain Markdown. No frontmatter is required (skills are referenced by
path, not parsed as YAML).

### Validation

- AC C1: `test_agent_skill_references_exist` must pass (written in P5).
- AC C2: `frontend-design/SKILL.md` must exist before P5 starts.

---

## Phase P2 — Agent frontmatter update

**Owner:** ai-engineer
**Parallelism:** Safe to run concurrently with P1 (disjoint file sets).

### design-specialist.md

Add to the `skills:` YAML list:

```yaml
skills:
  - frontend-design
  - ux-ui-review
  - design-reference-research
  - design-report-quality-gate
  - dadaia-handoff-emitter
```

The body of the agent file already references these skills in the "Skills consumed"
table (lines 91–94). The frontmatter `skills:` key must match that table so that
`test_agent_skill_references_exist` (AC C1) can detect missing SKILL.md files.

Do NOT add `Edit`, `Bash`, Playwright, or image-generation tools. FR4 prohibits this.

### frontend-engineer.md

Add to the `skills:` YAML list:

```yaml
skills:
  - dadaia-workspace-spec-navigator
  - dadaia-task-manager
  - dev-server-registry
  - frontend-implementation-quality
  - dadaia-handoff-emitter
```

Do NOT add `ux-ui-review`, Playwright, or E2E skills. FR4 prohibits this.

### Validation

- AC C3: `frontend-engineer` frontmatter includes `dadaia-handoff-emitter` and
  `frontend-implementation-quality`.
- AC C4 / C5: boundary tests (P5) will assert the absence of forbidden skills/tools.

---

## Phase P3 — Codex runtime boundary infrastructure

**Owner:** software-engineer-python
**Depends on:** nothing (can start immediately).
**Must complete before P4.**

### P3.1 — Create `public/runtime/codex/` source directory

Create the directory with a README stub:

```
dadaia_workspace/public/runtime/codex/
    README.md       ← brief note: "Codex-only adapters. Not projected to .claude/ or .opencode/."
```

This is the ADR-CX-001 canonical source path for Codex-exclusive adapters.

### P3.2 — Extend `_install_codex()` in `public_assets.py`

Add a new private method `_install_codex_runtime_adapters(agentic_dir, workspace_root,
force, installed)` that:

1. Resolves `source = agentic_dir.parent / "runtime" / "codex"` (i.e. the path
   relative to `public/`).
2. Iterates over subdirectories of `source/`; for each subdirectory, if it contains
   a `SKILL.md`, copies it to `.codex/skills/<subdir-name>/SKILL.md`.
3. Appends `[ok]` / `[skip]` entries to `installed` list (consistent with existing
   copy helpers).
4. Returns early (no error) if `source` does not exist — the directory is optional
   from the runtime's perspective; doctor handles presence validation.

Call `_install_codex_runtime_adapters` from `_install_codex()` after the existing
`_install_codex_agents` call.

### P3.3 — Doctor check: Codex-only asset leak detection

Extend the doctor (locate the `doctor` method or the relevant doctor class) with a
check that iterates over `runtime/codex/` subdirectories and verifies that no
corresponding file exists in `.claude/skills/` or `.opencode/skills/`. If a leak is
detected, emit a `[leak]` entry with the offending path. AC C8.

### Validation

- AC C8: doctor detects a missing adapter, a stale adapter, and an accidental OpenCode
  leak.
- AC C7: SHA snapshot null-regression in P5 must confirm `.claude/**` and
  `.opencode/**` are byte-identical before and after `install --target codex`.

---

## Phase P4 — Codex-only adapter SKILL.md stubs

**Owner:** ai-engineer
**Depends on:** P3 (directory must exist before files are placed inside it).

Create two SKILL.md files in `public/runtime/codex/`:

### design-ctx/SKILL.md

Purpose: read-only context injection for `design-specialist`. When invoked at the
start of a Codex session, this adapter instructs the agent to:

1. Locate the latest design report in `.dadaia/reports/<context>/design-specialist/`.
2. Locate the latest QA screenshot report in `.dadaia/reports/<context>/qa-engineer/`.
3. Read the active Spec Context Project from `.dadaia/states/primary_context.json`.
4. Surface a concise context summary (surface name, last design report date, last QA
   report path).

This adapter is read-only (no Write, no Edit, no Bash). It enriches the Codex runtime
without duplicating the canonical persona.

### frontend-ctx/SKILL.md

Purpose: context injection for `frontend-engineer`. When invoked, this adapter:

1. Reads the active release from `specs/releases/ACTIVE.md`.
2. Identifies the active task (first `[-]` in TASKS.md).
3. Reads the latest design report from `.dadaia/reports/<context>/design-specialist/`.
4. Reads the dev-server registry state from `.dadaia/states/server_registry.json`
   (if it exists).
5. Surfaces a structured context block: active release, active task ID, design report
   path, dev-server URL (if registered).

This adapter is also read-only. It does not duplicate the `frontend-engineer` agent
body.

### Validation

- AC C10: both adapter candidates are named and sourced from `public/runtime/codex/`
  before implementation.
- AC C7: adding these adapters changes only `.codex/skills/design-ctx/` and
  `.codex/skills/frontend-ctx/`; `.claude/**` and `.opencode/**` remain byte-identical.

---

## Phase P5 — Tests

**Owner:** qa-engineer (boundary tests, C4/C5); software-engineer-python (C1, C7, C8)
**Depends on:** P1, P2, P3 all complete.

### T-05a — `test_agent_skill_references_exist` (AC C1)

Location: `tests/unit/features/public/test_agent_skill_references.py`

Reads every agent `.md` in `dadaia_workspace/public/agents/`, parses the `skills:`
YAML list from frontmatter, and asserts that each listed skill has a corresponding
`dadaia_workspace/public/skills/<name>/SKILL.md`. Fails loudly when a skill is
referenced but not on disk.

### T-05b — Boundary tests `design-specialist` (AC C4)

Location: `tests/unit/features/public/test_agent_boundaries.py`

Assert that `design-specialist` frontmatter:
- Has no `Edit` in `tools:`.
- Has no `Bash` in `tools:`.
- Has no `playwright` or `image-generation` in `skills:` or `tools:`.
- Has no non-textual paths in `paths.write_allowlist` (allowed: `.html`, `.md`,
  `.json`, `.txt`).

### T-05c — Boundary tests `frontend-engineer` (AC C5)

Same file as T-05b.

Assert that `frontend-engineer` frontmatter:
- Has no `ux-ui-review` in `skills:`.
- Has no Playwright MCP ownership declaration.
- Has no E2E ownership declaration.
- Has no `specs/releases` or `specs/memory` in `paths.write_allowlist`.

### T-05d — SHA snapshot null-regression (AC C7, ADR-CX-004)

Location: `tests/integration/test_codex_null_regression.py`

1. Stage and install to all targets; compute SHA hash of every file under `.claude/**`
   and `.opencode/**`.
2. Run `install --target codex` again (idempotent).
3. Recompute hashes. Assert equality — no file under `.claude/` or `.opencode/`
   changed.

### T-05e — Doctor leak detection (AC C8)

Location: `tests/integration/test_codex_doctor_leak.py`

Three sub-tests:

1. **Missing adapter:** remove a `runtime/codex/<adapter>/SKILL.md` after install;
   run doctor; assert `[missing]` entry appears in output.
2. **Stale adapter:** modify a `runtime/codex/<adapter>/SKILL.md` without re-running
   install; run doctor; assert `[drift]` entry appears.
3. **Leak to OpenCode:** manually copy a `runtime/codex/<adapter>/SKILL.md` to
   `.opencode/skills/<adapter>/SKILL.md`; run doctor; assert `[leak]` entry appears.

---

## Phase P6 — Stage + install + doctor validation

**Owner:** software-engineer-python
**Depends on:** P5 all green.

Run the full pipeline in a real workspace fixture (or integration test):

```bash
dadaia public stage
dadaia public install --target all
dadaia public doctor
```

Assert:
- AC C6: no drift reported for shared assets.
- AC C9: `.codex/config.toml` parses cleanly with `tomllib` and `[skills] paths`
  behavior is preserved (or ADR-approved replacement is documented).

This phase produces the final green evidence needed for CLOSURE validations.

---

## Phase P7 — CLOSURE

**Owner:** product-engineer

After all tasks are `[x]` DONE:

1. Write `CLOSURE.md` for this release.
2. Update memory HTML if any agent boundary definition changed visibly (product
   feature catalog); otherwise document "no change" with reason.
3. Set `ACTIVE.md` phase to `ARCHIVED`.
4. Move release directory: `git mv specs/releases/codex-design-frontend-projection-pilot-v1 specs/_archive/releases/codex-design-frontend-projection-pilot-v1`.

---

## Technical risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| `_install_codex()` extension breaks existing codex install | Medium | SHA snapshot test (T-05d) catches regressions before merge |
| `design-specialist` frontmatter `skills:` already references skills not yet on disk | Low | C1 test will fail and surface this before merge |
| Doctor leak check false-positives on shared skills | Low | Doctor checks only `runtime/codex/` names, not all skills |
| Adapter stubs (P4) too minimal to be useful | Low | Stubs can be enriched in follow-up; pilot only requires candidates named per C10 |

---

## Parallelism summary

```
P1 (ai-engineer)     ─────────────────┐
P2 (ai-engineer)     ─────────────────┤
P3 (sweng-python)    ─────────────────┤
                                      ├──► P5 (qa-eng + sweng-python) ──► P6 ──► P7
P4 (ai-engineer)     depends on P3   ─┘
```

Maximum one `[-]` active per owner at any time unless TASKS.md declares disjoint safe
parallel tasks.
