---
name: pre-push-gate-cannot-locate-workspace-venv
status: Closed
severity: MEDIUM
reported: 2026-06-09
resolved_in: v0.1.10
surface: pre-push-ci-gate.sh (.git/hooks/pre-push runner detection)
session_id: null
---

**Resolution (v0.1.10):** Fixed by T-010-26 — `pre-push-ci-gate.sh` now probes
the runner in order `DADAIA_BIN` → walk-up `<ws>/.dadaia/.venv/bin/dadaia` →
`poetry` → repo-local `.venv`, with a fail-closed clear error when none is found.
This lets the gate actually run in the self-hosting workspace layout instead of
forcing a `--no-verify` bypass. Regression tests (all 7 green):
`tests/unit/public/test_pre_push_gate_venv_probe.py` — including
`::test_branch2_walk_up_to_workspace_venv`,
`::test_none_found_fails_closed`, and the precedence tests
`::test_dadaia_bin_precedes_workspace_venv` / `::test_workspace_venv_precedes_poetry`.


**Symptom:** The mandatory pre-push CI gate (`pre-push-ci-gate.sh`) fails-closed and never runs
its checks in the self-hosting / dadaia-workspace layout. On `git push` it prints:

```
[pre-push] ERROR: neither 'poetry' nor '.venv/bin/dadaia' found to run the gate.
```

and exits 1, blocking the push. It blocks safely, but it can never actually run the
CI-equivalent suite — so the operator is forced to verify manually and bypass with
`git push --no-verify`, which defeats the gate's entire purpose.

**Repro:**
1. In a dadaia-workspace where the venv lives at workspace root `<ws>/.dadaia/.venv` (the
   canonical location) and the package repo is a sub-repo at `<ws>/repos/dadaia-workspace`.
2. `poetry` is not on PATH (venv-only environment — see
   `ci-preflight-raw-traceback-when-poetry-absent`).
3. `git push` from the sub-repo → gate errors and blocks.

**Root cause:** the hook's runner detection only probes two locations:
`command -v poetry` (PATH) and `[ -x ".venv/bin/dadaia" ]` (repo-relative). It does not know
about the workspace-level venv at `<ws>/.dadaia/.venv/bin/dadaia`, which is where the dadaia
CLI actually lives in a generated/self-hosting workspace. The repo is a sub-repo of the
workspace; `.venv/` never exists inside it (forbidden by the repo-cleanliness rule).

**Expected:** the gate locates the dadaia runner in the workspace-level venv (walk up to the
workspace root and probe `.dadaia/.venv/bin/dadaia`), or accept a `DADAIA_PYTHON`/`DADAIA_BIN`
env override, and run the CI-equivalent suite — actually fulfilling its contract ("Runs the
CI-equivalent suite locally and BLOCKS the push if any check fails") instead of hard-erroring.

**Notes:** Related to `ci-preflight-raw-traceback-when-poetry-absent` (same poetry-absent
assumption). For the 0.1.7 close, the full CI-equivalent suite was run manually and is green
(pytest 2365 passed / 2 skipped / 1 xpassed; ruff format+check clean; mypy --strict 193 files
clean), so the push used the documented `--no-verify` bypass with positive not-red evidence —
the gate was not skipped to hide a failure. Candidate fix belongs with the cross-platform /
hooks workstream (WS-8) or a small standalone gate-runner-resolution fix.
