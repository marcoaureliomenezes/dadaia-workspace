# Job 8 — the verdict writer validates its own output (FR8)

**Status:** Draft

Wave 3, after Job 4 (`verdict.py` and the kernel grammar) and Job 6 (Tidy First: owners move before behaviour). Bugs `verdict-writer-emits-a-handoff-the-schema-rejects` and `verdict-validation-stated-three-ways-without-the-reviewed-tree` (its writer and skill legs; the gate's fix line is Job 1). The rule was stated by the gate, its fix line and SKILL.md step 7, and `verdict.py` validated nothing. REBUILD of `main` (5 ledger bugs on the unit; prior fix `fcbbe0850` changed one of three statements).

- **Seams closed.**
  - After writing, `verdict.py` runs `<root>/.dadaia/.venv/<scripts>/dadaia reports validate <target> --reviewed-root <worktree>`, the CLI path from the kernel's `_platform.venv_tool`. On a nonzero exit it unlinks the target and refuses; success prints the path as today.
  - Refusal grammar is the script's own, `[error] <the validator's first failing line>` then one `fix:` line naming the failing key (`Operator action: correct <key> in the stdin body, then rerun verdict.py`); the SPEC's `Error:` reads as this line, because every other refusal of the script and its asserts use `[error]`.
  - An absent CLI refuses with `fix: uvx dadaia-workspace init <root>`; nothing is written.
  - The tests reach the real validator through `patch_cli`: the stub's `reports validate` branch forwards its argv to `python -m dadaia_workspace reports validate` and logs the argv to a file. No helper file is edited. The existing cases and `test_verdict__characterization.py` run against the default stub and stay unedited.
  - Growth reason (G3): about +8 production lines, because validation before acceptance is the bug's expected behaviour.
- **Consumers.** `git grep -n 'reports validate' -- dadaia_workspace/public tests` before and after; step 6 of SKILL.md (report-mode handoffs) keeps its manual run.
- Test-side first: T1. Then T2, T3 (disjoint `W:`).
- Pre-review checklist: the writer is the one statement of the rule; platform facts through `_platform`; sweep line above; net lines +8, stated.

Tasks: 3 (1 jr, 2 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J8.T1 | sr | AC8.1, AC8.2 | `tests/public/skills/dd_handoff_emitter/scripts/test_verdict.py` | RED, integration: (a) a finding lacking `fix_recommendation` exits nonzero with `[error]`, one `fix:` line naming that key, and no handoff file left; (b) a verdict citing a file only the reviewed tree holds is written, and the logged argv is `reports validate <path> --reviewed-root <tree>`. Owner this file |
| J8.T2 | sr | AC8.1, AC8.2 | `dadaia_workspace/public/skills/dd-handoff-emitter/scripts/verdict.py` | the write-validate-or-unlink step of the intro. Owner T1. After T1. Fix commit of both bugs; Phase 0 block `prior diffs read: fcbbe0850`, `rebuild: main` |
| J8.T3 | jr | AC8.4 | `dadaia_workspace/public/skills/dd-handoff-emitter/SKILL.md` | step 7 and the Done-when lose the manual `reports validate` run for a verdict and say the writer validates against the reviewed tree. No test, reviewer sweep |
