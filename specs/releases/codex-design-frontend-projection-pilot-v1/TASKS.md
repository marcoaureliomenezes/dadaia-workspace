# Tasks: codex-design-frontend-projection-pilot-v1

**Status:** Aprovado
**Release ID:** codex-design-frontend-projection-pilot-v1
**Owner:** product-engineer
**Created:** 2026-05-20

---

## Parallelism declaration

Tasks T-01 through T-07 (P1 + P2 + P3) may run concurrently — they have disjoint write
sets. T-08 (P4) depends on T-03 (P3 complete). T-09 through T-13 (P5) may begin once
T-01 through T-08 are all `[x]`. T-14 (P6) begins once T-09 through T-13 are all `[x]`.
T-15 (P7 CLOSURE) begins once T-14 is `[x]`.

---

## Phase P1 — Shared skill SKILL.md files

### T-01

- **ID:** T-01
- **Description:** Create `dadaia_workspace/public/skills/frontend-design/SKILL.md`
- **Owner:** ai-engineer
- **Target files:** `dadaia_workspace/public/skills/frontend-design/SKILL.md`
- **Preconditions:** SPEC Aprovado, PLAN Aprovado
- **Done criterion:** File exists at the target path; contains `# Frontend Design` heading,
  `## Purpose`, `## Protocol` (or equivalent content sections), and `## Guardrails`. AC C2.
- **Parallel note:** Safe to run concurrently with T-02, T-03, T-04, T-05, T-06, T-07.

```
[x] T-01 — Create public/skills/frontend-design/SKILL.md
```

---

### T-02

- **ID:** T-02
- **Description:** Create `dadaia_workspace/public/skills/design-reference-research/SKILL.md`
- **Owner:** ai-engineer
- **Target files:** `dadaia_workspace/public/skills/design-reference-research/SKILL.md`
- **Preconditions:** T-01 started or complete (same parallel batch)
- **Done criterion:** File exists; contains the approved reference whitelist (Dribbble,
  Mobbin, Figma Community, Refactoring UI, Apple HIG, Material 3, W3C WCAG, MDN) and
  citation protocol. AC C1 passes for this skill reference.
- **Parallel note:** Safe to run concurrently with T-01, T-03, T-04, T-05, T-06, T-07.

```
[x] T-02 — Create public/skills/design-reference-research/SKILL.md
```

---

### T-03

- **ID:** T-03
- **Description:** Create `dadaia_workspace/public/skills/design-report-quality-gate/SKILL.md`
- **Owner:** ai-engineer
- **Target files:** `dadaia_workspace/public/skills/design-report-quality-gate/SKILL.md`
- **Preconditions:** T-01 started or complete (same parallel batch)
- **Done criterion:** File exists; covers required sections check (Surface, A11y findings,
  Visual hierarchy, Design spec, ASCII sketches, References, Handoff notes); no Bash or
  Edit invocation in protocol. AC C1 passes for this skill reference.
- **Parallel note:** Safe to run concurrently with T-01, T-02, T-04, T-05, T-06, T-07.

```
[x] T-03 — Create public/skills/design-report-quality-gate/SKILL.md
```

---

### T-04

- **ID:** T-04
- **Description:** Create `dadaia_workspace/public/skills/frontend-implementation-quality/SKILL.md`
- **Owner:** ai-engineer
- **Target files:** `dadaia_workspace/public/skills/frontend-implementation-quality/SKILL.md`
- **Preconditions:** T-01 started or complete (same parallel batch)
- **Done criterion:** File exists; covers TDD protocol, TypeScript strict mode gates,
  component test requirements, WCAG 2.1 AA minimum, responsive breakpoints (360/768/1280),
  performance budget (LCP ≤ 2.5s, CLS ≤ 0.1, INP ≤ 200ms), and OWASP frontend checklist.
  AC C1 and AC C3 pass after T-05 wires it into frontend-engineer.
- **Parallel note:** Safe to run concurrently with T-01, T-02, T-03, T-05, T-06, T-07.

```
[x] T-04 — Create public/skills/frontend-implementation-quality/SKILL.md
```

---

### T-04b

- **ID:** T-04b
- **Description:** Create `dadaia_workspace/public/skills/ux-ui-review/SKILL.md`
- **Owner:** ai-engineer
- **Target files:** `dadaia_workspace/public/skills/ux-ui-review/SKILL.md`
- **Preconditions:** SPEC Aprovado (gap fix — omitted from original PLAN; required by T-05 done criterion and AC C1)
- **Done criterion:** File exists; describes review protocol for screenshots → design-token audit → a11y check → spacing/typography verification. No Bash or Edit in protocol. AC C1 passes for this skill reference.
- **Parallel note:** Safe to run concurrently with T-01 through T-07.

```
[x] T-04b — Create public/skills/ux-ui-review/SKILL.md
```

---

## Phase P2 — Agent frontmatter update

### T-05

- **ID:** T-05
- **Description:** Update `design-specialist.md` frontmatter: set `skills:` to the approved list
- **Owner:** ai-engineer
- **Target files:** `dadaia_workspace/public/agents/design-specialist.md`
- **Preconditions:** SPEC Aprovado. T-01, T-02, T-03 complete (skills must exist before being referenced; or may run in same parallel batch with tests to follow).
- **Done criterion:** `skills:` list in frontmatter equals exactly:
  `[frontend-design, ux-ui-review, design-reference-research, design-report-quality-gate, dadaia-handoff-emitter]`.
  No `Edit`, `Bash`, Playwright, or image-generation tools added. AC C4 boundary test passes.
- **Parallel note:** Safe to run concurrently with T-01, T-02, T-03, T-04, T-06, T-07.

```
[x] T-05 — Update design-specialist.md frontmatter skills list
```

---

### T-06

- **ID:** T-06
- **Description:** Update `frontend-engineer.md` frontmatter: add `dadaia-handoff-emitter` and `frontend-implementation-quality` to `skills:` list
- **Owner:** ai-engineer
- **Target files:** `dadaia_workspace/public/agents/frontend-engineer.md`
- **Preconditions:** SPEC Aprovado. T-04 complete (skill must exist before being referenced; or same parallel batch).
- **Done criterion:** `skills:` list includes `dadaia-handoff-emitter` and
  `frontend-implementation-quality`. Does not include `ux-ui-review`, Playwright, or E2E
  skills. AC C3 and AC C5 boundary tests pass.
- **Parallel note:** Safe to run concurrently with T-01, T-02, T-03, T-04, T-05, T-07.

```
[x] T-06 — Update frontend-engineer.md frontmatter skills list
```

---

## Phase P3 — Codex runtime boundary infrastructure

### T-07

- **ID:** T-07
- **Description:** Create `dadaia_workspace/public/runtime/codex/` directory with README stub
- **Owner:** software-engineer-python
- **Target files:** `dadaia_workspace/public/runtime/codex/README.md`
- **Preconditions:** SPEC Aprovado, PLAN Aprovado
- **Done criterion:** Directory exists. `README.md` exists inside and documents: "Codex-only
  adapters. Source path per ADR-CX-001. Not projected to .claude/ or .opencode/."
- **Parallel note:** Safe to run concurrently with T-01 through T-06.

```
[x] T-07 — Create dadaia_workspace/public/runtime/codex/ with README
```

---

### T-08

- **ID:** T-08
- **Description:** Extend `_install_codex()` in `public_assets.py` with `_install_codex_runtime_adapters()` method
- **Owner:** software-engineer-python
- **Target files:** `dadaia_workspace/infrastructure/public_assets.py`
- **Preconditions:** T-07 complete (directory must exist to validate path assumptions)
- **Done criterion:** New private method `_install_codex_runtime_adapters` exists and is
  called from `_install_codex()`. Method copies `public/runtime/codex/<slug>/SKILL.md` to
  `.codex/skills/<slug>/SKILL.md` for each subdirectory. Method returns early without
  error if source directory does not exist. Existing tests pass.
- **Parallel note:** Must follow T-07. May proceed independently of P1/P2/P4.

```
[x] T-08 — Extend _install_codex() with _install_codex_runtime_adapters()
```

---

### T-09

- **ID:** T-09
- **Description:** Add doctor check for Codex-only asset leak to `.claude/` or `.opencode/`
- **Owner:** software-engineer-python
- **Target files:** `dadaia_workspace/infrastructure/public_assets.py` (or the doctor module)
- **Preconditions:** T-08 complete
- **Done criterion:** Doctor check iterates `public/runtime/codex/` subdirectories and
  verifies no corresponding path exists in `.claude/skills/` or `.opencode/skills/`.
  Emits `[leak] <path>` for each violation. Emits `[missing]` if an installed adapter is
  absent from `.codex/skills/`. Emits `[drift]` if the installed adapter content differs
  from source. AC C8.
- **Parallel note:** Must follow T-08.

```
[x] T-09 — Add doctor leak/missing/drift check for runtime/codex adapters
```

---

## Phase P4 — Codex-only adapter SKILL.md stubs

### T-10

- **ID:** T-10
- **Description:** Create `dadaia_workspace/public/runtime/codex/design-ctx/SKILL.md`
- **Owner:** ai-engineer
- **Target files:** `dadaia_workspace/public/runtime/codex/design-ctx/SKILL.md`
- **Preconditions:** T-07 complete (directory must exist)
- **Done criterion:** File exists; protocol instructs Codex session to locate latest
  design report and QA screenshot report, read active context from
  `.dadaia/states/primary_context.json`, and surface a context summary. No Write, Edit,
  or Bash invocations in the protocol. AC C10.
- **Parallel note:** May run concurrently with T-11 once T-07 is complete.

```
[ ] T-10 — Create public/runtime/codex/design-ctx/SKILL.md
```

---

### T-11

- **ID:** T-11
- **Description:** Create `dadaia_workspace/public/runtime/codex/frontend-ctx/SKILL.md`
- **Owner:** ai-engineer
- **Target files:** `dadaia_workspace/public/runtime/codex/frontend-ctx/SKILL.md`
- **Preconditions:** T-07 complete (directory must exist)
- **Done criterion:** File exists; protocol reads active release from `ACTIVE.md`,
  identifies active task from TASKS.md, reads latest design report path, reads
  dev-server registry state from `.dadaia/states/server_registry.json`. No Write, Edit,
  or Bash invocations. AC C10.
- **Parallel note:** May run concurrently with T-10 once T-07 is complete.

```
[ ] T-11 — Create public/runtime/codex/frontend-ctx/SKILL.md
```

---

## Phase P5 — Tests

### T-12

- **ID:** T-12
- **Description:** Write `test_agent_skill_references_exist` and boundary tests for design-specialist and frontend-engineer
- **Owner:** qa-engineer
- **Target files:** `tests/unit/features/public/test_agent_skill_references.py`, `tests/unit/features/public/test_agent_boundaries.py`
- **Preconditions:** T-01, T-02, T-03, T-04, T-05, T-06 all complete
- **Done criterion:**
  - `test_agent_skill_references_exist`: parses all agent frontmatter `skills:` lists,
    asserts each has a matching `public/skills/<name>/SKILL.md`. Fails on missing skill.
    AC C1.
  - `test_design_specialist_boundary`: asserts no `Edit`/`Bash` in tools, no Playwright
    or image-generation in skills or tools, no non-text paths in write_allowlist. AC C4.
  - `test_frontend_engineer_boundary`: asserts no `ux-ui-review` in skills, no Playwright
    MCP ownership, no E2E ownership, no specs/ paths in write_allowlist. AC C5.
  - All three tests pass with `pytest`.
- **Parallel note:** Must follow T-01 through T-06. May run concurrently with T-13.

```
[ ] T-12 — Write skill-reference integrity and boundary tests
```

---

### T-13

- **ID:** T-13
- **Description:** Write SHA snapshot null-regression test (AC C7) and doctor leak detection tests (AC C8)
- **Owner:** software-engineer-python
- **Target files:** `tests/integration/test_codex_null_regression.py`, `tests/integration/test_codex_doctor_leak.py`
- **Preconditions:** T-08, T-09 complete (runtime adapter install + doctor check implemented)
- **Done criterion:**
  - `test_codex_null_regression`: stage + install all; compute SHA tree for `.claude/**`
    and `.opencode/**`; run `install --target codex`; recompute; assert equality. AC C7.
  - `test_codex_doctor_leak_missing`: remove adapter from `.codex/skills/` post-install;
    run doctor; assert `[missing]` in output. AC C8.
  - `test_codex_doctor_leak_drift`: modify adapter source without reinstalling; run
    doctor; assert `[drift]` in output. AC C8.
  - `test_codex_doctor_leak_opencode`: copy adapter to `.opencode/skills/`; run doctor;
    assert `[leak]` in output. AC C8.
  - All tests pass with `pytest`.
- **Parallel note:** May run concurrently with T-12.

```
[ ] T-13 — Write SHA null-regression and doctor leak detection tests
```

---

## Phase P6 — Stage + install + doctor validation

### T-14

- **ID:** T-14
- **Description:** Run `dadaia public stage && dadaia public install --target all && dadaia public doctor` and verify no drift; verify `config.toml` parses with tomllib
- **Owner:** software-engineer-python
- **Target files:** None (validation only — command output is evidence)
- **Preconditions:** T-12 and T-13 all green
- **Done criterion:**
  - `dadaia public stage` exits 0 with no errors.
  - `dadaia public install --target all` exits 0.
  - `dadaia public doctor` exits 0 with no `[drift]`, `[missing]`, or `[leak]` entries
    for shared assets. AC C6.
  - `.codex/config.toml` parsed by `tomllib.loads()` without exception. `[skills] paths`
    entry present and unchanged (or ADR-approved replacement documented). AC C9.
  - Evidence: stdout snippet or report path captured for CLOSURE.
- **Parallel note:** Sequential after P5.

```
[ ] T-14 — Validate stage + install + doctor pipeline (AC C6, C9)
```

---

## Phase P7 — CLOSURE

### T-15

- **ID:** T-15
- **Description:** Write CLOSURE.md and update memory HTML if needed; archive release
- **Owner:** product-engineer
- **Target files:** `specs/releases/codex-design-frontend-projection-pilot-v1/CLOSURE.md`, `specs/releases/ACTIVE.md`
- **Preconditions:** T-14 `[x]` DONE; all T-01 through T-14 `[x]` DONE
- **Done criterion:** CLOSURE.md written with Summary, Tasks completed table, Validations
  table with AC evidence, Memory updates section. `ACTIVE.md` phase set to `CLOSURE` before
  memory writes; then set to `ARCHIVED`. Release directory moved via `git mv` to
  `specs/_archive/releases/codex-design-frontend-projection-pilot-v1/`.
- **Parallel note:** Sequential; must be last.

```
[ ] T-15 — Write CLOSURE.md and archive release
```
