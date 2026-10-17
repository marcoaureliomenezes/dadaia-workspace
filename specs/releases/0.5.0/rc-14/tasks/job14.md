# Job 14 — audit, navigator, cli-library and handoff skills: kernel owners adopted, one git runner, one platform and clock decision, the slug read (FR11, FR13)

**Status:** Draft

Wave 3, after Job 1 (kernel owners, moved schemas) and Job 5 (it edits `verdict.py`'s test and `SKILL.md` of the handoff skill and the clock option of two scripts). Four small skills, one `W:` family each; no radon rank D to F in any of them.

- **audit**: `_audit_check.py` loses `histo_findings`, `finding()` and the JSONL parser; `_audit_store.py` loses `Refusal` and `serialize`; `_audit_verbs.py:101` uses `_clock`; vocabularies from `finding-record-v1`.
- **navigator** (not `_memory_schema.py`, Job 10's): `_memory_drift.py` calls `_git.git` (D1: it does not scrub `GIT_*` today) and loses `Refusal`; `_memory_catalog.py` loses `Refusal`, `serialize`, uses `_clock`; `memory.py` and `_memory_check.py` follow.
- **cli-library**: `registry.py:55` uses `_platform`, `:34-35,154-155` use `_clock`.
- **handoff**: `verdict.py:14` reads the slug pattern from `backlog-v1` through `_ledger.load_schema`, `:64-69` uses `_clock` (the pin of Job 5 stays green).
- Test-side first: T1, T2, T3. Then T4 to T7 in parallel (disjoint `W:`).
- Sweep lines in commit bodies: `git grep -n 'class Refusal\|def serialize\|def finding\|def histo_findings' -- dadaia_workspace/public/skills/dd-audit-project dadaia_workspace/public/skills/dd-spec-navigator` (6 before, 0 after); `git grep -n 'os\.name' -- dadaia_workspace/public/skills` (3 before the kernel, 0 after); `git grep -n 'datetime' -- dadaia_workspace/public/skills/dd-cli-library dadaia_workspace/public/skills/dd-handoff-emitter` (before/after).
- Pre-review checklist: one reader per rule; the only cross-skill edge is the kernel's (plus the backlog schema read for the slug); sweep lines above; platform facts through `_platform.py`; net production lines ≤ 0 (est. −90).

Tasks: 7 (2 jr, 5 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J14.T1 | sr | AC11.2 | `tests/public/skills/dd_spec_navigator/scripts/test__memory_drift.py` | RED, unit: with `GIT_DIR` set to another repo, the drift check run in repo A answers for A. Owner `test__memory_drift.py` |
| J14.T2 | sr | AC13.1 | `tests/public/skills/dd_handoff_emitter/scripts/test_verdict.py` | RED, unit: the verdict slug `a--b` is accepted or refused exactly as the backlog slug pattern says (joins Job 1's cases); the file-name stamp and `produced_at` pin of Job 5 stays. Owner `test_verdict.py` |
| J14.T3 | sr | AC11.4 | `tests/public/skills/dd_cli_library/scripts/test_registry.py` | RED, unit: on a faked Windows platform the registry takes its liveness branch from `_platform`, and `register` stamps through `_clock` (frozen clock). Owner `test_registry.py` |
| J14.T4 | jr | AC11.4 | `dadaia_workspace/public/skills/dd-audit-project/scripts/_audit_check.py`, `dadaia_workspace/public/skills/dd-audit-project/scripts/_audit_store.py`, `dadaia_workspace/public/skills/dd-audit-project/scripts/_audit_verbs.py`, `dadaia_workspace/public/skills/dd-audit-project/scripts/audit.py`, `tests/public/skills/dd_audit_project/scripts/test_audit.py` | adopt the kernel owners as the intro says; delete the copies. Existing audit suite unedited (the test file is listed for its import follow only) |
| J14.T5 | sr | AC11.2, AC11.4 | `dadaia_workspace/public/skills/dd-spec-navigator/scripts/_memory_drift.py`, `dadaia_workspace/public/skills/dd-spec-navigator/scripts/_memory_catalog.py`, `dadaia_workspace/public/skills/dd-spec-navigator/scripts/_memory_check.py`, `dadaia_workspace/public/skills/dd-spec-navigator/scripts/memory.py`, `tests/public/skills/dd_spec_navigator/scripts/test_memory__characterization.py` | adopt the kernel owners; the git calls of `_memory_drift` go through `_git.git`. Owner T1 and the existing suites. After T1. Fix commit of the git-env bug (navigator runner); Phase 0 block `rebuild: the git runner` |
| J14.T6 | jr | AC11.4 | `dadaia_workspace/public/skills/dd-cli-library/scripts/registry.py` | platform and clock from the kernel. Owner T3. After T3 |
| J14.T7 | sr | AC13.1, AC11.4 | `dadaia_workspace/public/skills/dd-handoff-emitter/scripts/verdict.py`, `tests/public/skills/dd_handoff_emitter/scripts/test_verdict__characterization.py` | the slug pattern from the schema, the clock from the kernel; no behaviour change besides `a--b`. Owner T2. After T2 |
