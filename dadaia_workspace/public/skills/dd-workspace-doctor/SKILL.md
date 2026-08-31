---
name: dd-workspace-doctor
description: >
  Diagnose and repair the workspace runtime: lib vs projection drift, and
  .dadaia/states/*.json schema migration after a library update. Use when the
  operator mentions "doctor", "drift", "schema stale", or "fix workspace".
---

# dd-workspace-doctor — Workspace Diagnosis & Repair

## 1. When

- The operator mentions "doctor", "drift", "schema stale", "fix workspace", or "/dd-workspace-doctor".
- Operational state only: lib-vs-`.claude/` drift, and `.dadaia/states/*.json` schema migration.
- Spec-vs-code drift (feature behavior vs approved SPEC.md) belongs to `project-auditor` instead.

## 2. Steps

1. Locate the workspace: `ls .dadaia/` (confirm root); locate the library: `dadaia --version` or `pip show dadaia-workspace`.
2. List canonical files in `dadaia_workspace/public/<type>/` for each asset type (`rules/`, `skills/`, `commands/`, `agents/`).
3. List the corresponding files in `.claude/<type>/`.
4. Compare content; flag any file that differs or is missing in `.claude/`.
5. Run `dadaia doctor` as the CLI shortcut for the drift check.
6. Auto-repair with `dadaia doctor --fix`, or `dadaia public stage` then `dadaia public install --target all --force`.
7. For schema migration, read the current frozen dataclasses from the installed library (`core/models/spec_context.py`, `core/models/course.py`).
8. Read the current JSON content: `spec_contexts.json` under `.dadaia/states/`, `academy.json` under `.dadaia/academy/`.
9. Map old fields to new: drop disappeared fields, ask the operator for a default on new required fields, infer or ask on renames.
10. Rewrite the JSON file atomically: write `.tmp` then `os.replace()`.
11. Report every field change made.
12. Never guess a required field value silently — always confirm with the operator.
13. Write a summary report to `.dadaia/reports/<context>/dd-workspace-doctor/<UTC>.html`: issues found, actions taken, operator decisions needed.
14. Never edit `.agents/`, `.claude/`, `.codex/`, `.kimi-code/` directly for drift repair — always `dadaia public stage`/`install --force`.

## 3. Done when

- `dadaia doctor` (or `--fix`) reports drift resolved, or every remaining item is named for operator decision.
- Every JSON schema migration change is reported field-by-field.
- No lib-originated file was hand-edited to fake a fix.

## 4. References

- `dadaia public stage` / `dadaia public install --target all --force` — the only drift-repair path.
- `project-auditor` — spec-vs-code drift, out of this skill's scope.
