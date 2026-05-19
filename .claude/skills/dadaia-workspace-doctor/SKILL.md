---
name: dadaia-workspace-doctor
description: >
  Diagnose and repair the dadaia workspace runtime. Checks lib vs .claude/ asset drift
  and assists with JSON schema migration when .dadaia/states/*.json becomes stale after
  a dadaia-workspace library update. Use when the operator mentions "doctor", "drift",
  "schema stale", "fix workspace", or "/dadaia-workspace-doctor".
applyTo: ".dadaia/**"
---

# dadaia-workspace-doctor — Workspace Diagnosis & Repair

## Scope

This skill handles **operational state** only:
1. Lib canonical vs installed `.claude/` drift
2. JSON schema migration in `.dadaia/states/*.json`

Spec↔code drift (feature behavior vs approved SPEC.md) belongs to `product-auditor-agent`.

---

## Phase 0 — Locate workspace and library

```bash
# Find workspace root
ls .dadaia/ 2>/dev/null || echo "Not in a dadaia workspace"

# Find installed library version
dadaia --version 2>/dev/null || pip show dadaia-workspace | grep Version
```

---

## Phase 1 — Lib vs .claude/ drift check

For each asset type (`rules/`, `skills/`, `commands/`, `agents/`):

1. List canonical files in `dadaia_workspace/public/<type>/`
2. List corresponding files in `.claude/<type>/`
3. Compare content — flag any file that differs or is missing in `.claude/`

**CLI shortcut:**
```bash
dadaia doctor
```

**Auto-repair:**
```bash
dadaia doctor --fix
# or
dadaia public stage
dadaia public install --target all --force
```

---

## Phase 2 — JSON schema migration

When `spec_contexts.json` or `academy.json` has a stale schema:

1. Read the current Python frozen dataclasses from the installed library:
   - `dadaia_workspace/core/models/spec_context.py`
   - `dadaia_workspace/core/models/course.py`

2. Read the current JSON file content from `.dadaia/states/`

3. Map old fields to new fields:
   - Fields that disappeared: drop them
   - Fields that are new (non-optional): ask the operator for a default value
   - Fields that were renamed: infer from context if obvious; ask otherwise

4. Rewrite the JSON file atomically (write `.tmp` → `os.replace()`)

5. Report every field change made

**Never** guess required field values silently — always confirm with the operator.

---

## Phase 3 — Report

Write a summary to `.dadaia/reports/<context-name>/dadaia-workspace-doctor/<YYYY-MM-DDTHHMMSSZ>.md` covering:
- Issues found (per category)
- Actions taken (per file)
- Items requiring operator decision

---

## Guardrail

Never edit files under `.agents/`, `.claude/`, `.codex/`, or `.opencode/` directly for
drift repair — use `dadaia public stage` plus `dadaia public install --target all --force`
instead. Manual edits to lib-originated files create new drift rather than resolving it.
