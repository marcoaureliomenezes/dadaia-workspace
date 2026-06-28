---
name: codex-lifecycle-workspace-root-requires-skip-git-repo-check
status: Open
severity: HIGH
reported: 2026-06-27
surface: lifecycle Codex Layer-2 runtime adapter / backlog-definition workflow
session_id: sess_2687aa9b
---

**Symptom:** After fixing Codex's writable runtime home and allowing network access, a
live Codex Layer-2 workflow still blocked at the first model step:

```json
{
  "status": "BLOCKED",
  "blocked": {
    "blocked_at_step": "intake_grill",
    "reason": "Not inside a trusted directory and --skip-git-repo-check was not specified."
  },
  "steps": [
    {"label": "intake_grill", "runtime": "codex_exec", "accepted": false}
  ]
}
```

**Root cause:** The lifecycle container starts workflow workers with `cwd` set to the
dadaia workspace root (`/home/marco/workspace/dadaia`). That root is intentionally not a
Git repository; the actual source repo is under `repos/dadaia-workspace`. `codex exec`
requires either a Git repo/trusted project or the explicit `--skip-git-repo-check` flag.
The adapter did not pass that flag, so Codex refused to start before the worker prompt
could run.

**Expected:** Lifecycle Codex workers must be able to run from the dadaia workspace root
because workflow artifact paths such as `.dadaia/handoff/<context>/**` are
workspace-relative. The adapter should pass the supported `--skip-git-repo-check` flag
for non-interactive lifecycle execution while the SDD gates and git chokepoints remain the
source of write-safety enforcement.

**Impact:** Codex Layer-2 workflows are blocked in the standard dadaia workspace layout
even when the Codex CLI, auth, model, network, and writable runtime home are otherwise
correct.

**Acceptance:** Add `--skip-git-repo-check` to the Codex exec adapter command and pin it
in command-construction tests; rerun a Codex-backed workflow smoke past this startup
guard.
