---
name: infrastructure-claude-sdk-imports-features-scope-match
status: Closed
severity: MEDIUM
reported: 2026-06-24
surface: import-linter (lint-imports / CI lint job)
session_id: null
---

**Symptom:** `lint-imports` reports one BROKEN contract on a clean checkout of
`feature/v0.1.16`:

```
infrastructure must not import features/cli/hooks (it depends only on core)
dadaia_workspace.infrastructure.claude_sdk_runtime ->
dadaia_workspace.features.lifecycle.scope_match (l.35)
```

An upward layering edge: `infrastructure/` imports `features/`, which the
`infrastructure-no-upper-layers` forbidden contract (setup.cfg) pins as illegal.

**Repro:**
```
/home/[REDACTED]/workspace/dadaia/.dadaia/.venv/bin/lint-imports
# -> Contracts: 5 kept, 1 broken.
```
Confirmed present on clean HEAD (0fd888d) via `git stash -u` before any WS-6
edit — this is pre-existing, introduced by the WS-4 live Claude SDK adapter
(T-016-10), not by the WS-6 slop-metric work.

**Expected:** `infrastructure/` depends only on `core/`. The scope-match logic the
adapter needs should live behind a `core/protocols` Protocol injected via the
container, or `scope_match` should be relocated to `core/` if it is pure — not
imported upward from `features/`.

**Notes:** `dadaia ci preflight` (ruff format/check, mypy --strict, pytest) is
GREEN — it does not run `lint-imports`; the contract check runs only in the CI
`lint` job, so this break is invisible to the local pre-push preflight. No
operator-local paths/secrets in this record beyond the workspace venv path.

**Resolution (2026-06-24):** `scope_match` is a pure function with no dependencies, so it
was relocated `features/lifecycle/scope_match.py → core/scope_match.py` (the correct layer —
both `features/` and `infrastructure/` may import `core/`). Importers updated
(`infrastructure/claude_sdk_runtime.py`, `features/lifecycle/agent_runner.py`, the test).
`lint-imports` now reports **6 kept, 0 broken**; `dadaia ci preflight` stays green. Fixed
alongside the WS-6 commit on `feature/v0.1.16`.

**Follow-up gap (separate):** `dadaia ci preflight` should also run `lint-imports` so layering
breaks are caught by the local pre-push gate, not only the CI `lint` job. Tracked here as the
reason this slipped past WS-4's local gate.
