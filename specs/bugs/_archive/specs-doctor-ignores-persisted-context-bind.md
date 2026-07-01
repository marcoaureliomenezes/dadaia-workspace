---
name: specs-doctor-ignores-persisted-context-bind
status: Open
severity: MEDIUM
reported: 2026-06-25
session_id: sess_32d185aa
surface: cli/specs doctor context resolution
---

**Symptom:** After `dadaia context bind dadaia-workspace --print-env` persisted the
bound context/session, `.dadaia/.venv/bin/dadaia specs doctor` failed to resolve
`specs_dir` unless the caller supplied legacy environment variables or passed
`--specs-dir`.

**Observed output:**

```text
Invalid value: Could not resolve specs_dir. Pass --specs-dir or bind a context with `eval $(dadaia context bind <name> --mode read)`.
```

**Expected:** The CLI should honor the bind-driven context contract without requiring
`eval $(...)`, matching the workspace-manager contract that `context bind` persists the
bound context/mode/session and refreshes the incumbent pointer for subsequent workflow
commands.

**Repro:**

1. Run `.dadaia/.venv/bin/dadaia context bind dadaia-workspace --print-env`.
2. Run `.dadaia/.venv/bin/dadaia specs doctor`.
3. The command fails to resolve `specs_dir`.
4. Run `.dadaia/.venv/bin/dadaia specs doctor --specs-dir repos/dadaia-workspace/specs`.
5. The command succeeds, proving the specs tree itself is valid enough to inspect.

**Impact:** Operators can be told the session is bound while core CLI diagnostics still
behave as if only the legacy env/eval path exists. This creates false friction during
audits and can make agents misdiagnose a missing context instead of running the doctor
with the intended active context.

**Notes:** This is not the closed SDD gate bug
`bind-mode-session-record-keyed-by-cli-sid`; this finding is about the specs-doctor CLI
resolution path and its user-facing guidance.
