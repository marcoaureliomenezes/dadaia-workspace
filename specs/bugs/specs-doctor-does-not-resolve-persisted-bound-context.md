---
name: specs-doctor-does-not-resolve-persisted-bound-context
status: Closed
severity: MEDIUM
reported: 2026-06-18
surface: dadaia specs doctor / context resolution
session_id: null
release: null
---

**Symptom:** `dadaia specs doctor` run from the workspace root fails to resolve
the active specs directory even after the session has been bound to the
`dadaia-workspace` context. The same command succeeds when `--specs-dir
repos/dadaia-workspace/specs` is passed explicitly.

**Repro:**
1. Bind the session to `dadaia-workspace`.
2. From `<workspace-root>`, run `.dadaia/.venv/bin/dadaia specs doctor`.
3. Observe:

```text
Invalid value: Could not resolve specs_dir. Pass --specs-dir or bind a context
with `eval $(dadaia context bind <name> --mode read)`.
```

4. Run `.dadaia/.venv/bin/dadaia specs doctor --specs-dir repos/dadaia-workspace/specs`.
5. Observe the doctor resolves and completes.

**Expected:** The command should either resolve the persisted bound context
consistently or state that only shell-exported `eval $(dadaia context bind ...)`
environment is supported. The current message is misleading in a workspace where
`dadaia context bind` also writes persistent context/session state.

**Notes:** This blocked normal release-definition validation until the explicit
`--specs-dir` workaround was used.
