---
name: import-linter-contracts-red-but-not-ci-enforced
status: Closed
severity: MEDIUM
reported: 2026-06-27
surface: import-linter contracts / CI (.github) / dadaia ci preflight
session_id: null
---

**Symptom:** `lint-imports` exits non-zero (REAL_EXIT=1) on `feature/v0.1.30` HEAD (and on the
`main` baseline it branched from — none of the offending files are touched by v0.1.30). Three
contract violations:

1. `features must not import infrastructure directly` —
   `features.lifecycle.policy_resolver -> infrastructure.json_workflow_model_policy_store` (l.42)
2. same contract —
   `features.panel.views.workflow_policy -> infrastructure.json_workflow_model_policy_store` (l.54)
3. `features must not import subprocess directly (use ProcessRunner via core.protocols)` —
   `features.backlog.subject_registry -> cli.main -> cli.commands.ci -> subprocess`

**Repro:**
```
/home/marco/workspace/dadaia/.dadaia/.venv/bin/lint-imports ; echo $?   # -> 1
```
(Note: piping `lint-imports | tail` masks the real exit with `tail`'s 0 — read `$?` directly.)

**Expected:** Either the import-linter contracts hold (architecture boundary respected), OR
the contract suite is run in CI so a violation is caught at PR time. Today **neither** is true:
the contracts are red AND no CI job runs `lint-imports` — `.github/` has no import-linter step,
and `dadaia ci preflight` (the pre-push gate) runs only `ruff format --check`, `ruff check`,
`mypy --strict`, `pytest`. So the boundary erodes silently; v0.1.28/v0.1.29 shipped with these
violations because nothing enforces them.

**Impact / scope note:** Pre-existing baseline break, NOT introduced by v0.1.30 Wave A — the
new `infrastructure/headless_adapter_base.py` imports only `core.models.lifecycle` + stdlib
(`subprocess` is permitted in `infrastructure`). Wave A added zero new edges. SPEC acceptance
A5 references "import-linter green"; recorded honestly as: no NEW violation introduced, but the
pre-existing baseline is red. This bug tracks the baseline.

**Suggested fix (separate release — out of v0.1.30 scope):** route the two
`json_workflow_model_policy_store` imports through a `core.protocols` port (the established
pattern — `policy_resolver`/`panel` should depend on a port, not the concrete JSON store), break
the `subject_registry -> cli.main` edge, and add `lint-imports` to both `dadaia ci preflight`
and the GitHub CI workflow so the contracts are enforced going forward.

**Notes:** Surfaced during v0.1.30 Wave A review (foundation refactor). No operator-local
paths/secrets in this record.
