---
name: backlog-doctor-default-alias-map-unresolved-from-repo-subdir
status: Open
severity: MEDIUM
reported: 2026-06-26
surface: dadaia backlog doctor (CLI default --alias-map resolution) / features/backlog
session_id: null
---

**Symptom:** Run standalone from the self-hosting repo subdir
(`repos/dadaia-workspace/`), `dadaia backlog doctor` (no `--alias-map`) reports a
false BL-SCHEMA error for a panel/api subject that DOES have a valid alias:

```
[ERROR] BL-SCHEMA [workflow-model-governance-panel-control-plane] subject ref
'panel:/api/workflow-model-policy' (kind=api) has no alias-map entry; panel/api
subjects bind via the operator alias map only in R1 (no auto-derivation).
```

But the entry exists in the workspace-root alias map
(`<workspace>/.dadaia/states/backlog_subject_aliases.txt`):
`panel:/api/workflow-model-policy -> panel:/api/workflow-model-policy`. Passing the
path explicitly proves the data is correct:

```
$ dadaia backlog doctor --alias-map <workspace>/.dadaia/states/backlog_subject_aliases.txt
backlog doctor: clean.
$ dadaia backlog doctor          # default resolution, same cwd
backlog doctor FAILED: 1 error(s).
```

So the **default `--alias-map` resolution** (`_resolve_backlog_roots` in
`cli/commands/newartifacts.py`) does not locate the workspace-root
`.dadaia/states/backlog_subject_aliases.txt` when the CLI is invoked from within
`repos/<slug>/`. The help text says the default is "workspace .dadaia/states/", but
the resolver appears to anchor on the repo/specs tree rather than walking up to the
workspace root that actually owns `.dadaia/`.

**Repro:**
1. `cd repos/dadaia-workspace`
2. `<ws>/.dadaia/.venv/bin/dadaia backlog doctor` → false UNRESOLVED on a
   panel/api subject that has an alias in the workspace-root alias map.
3. Re-run with `--alias-map <ws>/.dadaia/states/backlog_subject_aliases.txt` → clean.

**Expected:** The default alias-map resolution must find the workspace-root
`.dadaia/states/backlog_subject_aliases.txt` regardless of whether the CLI is run
from the workspace root or a `repos/<slug>/` subdir — the same path the pre-commit
chokepoint uses (commits are NOT falsely blocked, so the hook resolves it
correctly; only the standalone CLI default differs).

**Impact:** LOCAL only. `specs/backlog/` is gitignored in this source repo, so CI's
"Backlog consistency" job checks out no backlog files and is unaffected; the
pre-push gate runs CI preflight + the security verdict, not `backlog doctor`; and a
normal (non-backlog) commit is not blocked (verified: the v0.1.26 closure commit
landed with this false error present). The damage is a misleading standalone
`backlog doctor` result for operators working from the repo subdir.

**Notes:** Surfaced while closing v0.1.26 (R2). Sibling to
`backlog-doctor-bl-schema-vs-spec-doc-031-terminal-status-format-conflict`. Likely
fix: make `_resolve_backlog_roots` walk up to the workspace root (the dir that
contains `.dadaia/`) for the default alias-map, mirroring how the pre-commit
chokepoint resolves it.
