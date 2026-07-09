# CLOSURE — Release v0.1.69 — Context Resolution, Session Observability & CLI Surface

> **Status:** Aprovado
> **Release ID:** v0.1.69
> **Merged:** `3388afde` (PR #132, squash), all CI green post-merge.

## Summary

Four CLI/context bugs (1 CRITICAL) — all live on `main` at HEAD `54e9be0e` — fixed
at root cause, RED-first, no workarounds, plus a bound-context-visible E2E:

| Bug | Fix | Disposition |
|---|---|---|
| `codex-thread-id-bind-resolution-breaks-cli` (CRITICAL) | FR1 — `CODEX_THREAD_ID` recognized at the single source (`session_env.py`) + `lock.py` lease-identity + `ENTRY_SIGNAL_ENV_VARS` safety envelope | resolved |
| `lifecycle-diagnostic-commands-missing-context-options` (HIGH) | FR2 — `--context`/`--release-id` on `preflight` + `specs doctor` (load-bearing only; `status`/`handoffs doctor` stay workspace-global) | resolved |
| `lifecycle-preflight-unusable-resolved-runtime-inputs` (MEDIUM) | FR3 — built `container.build_lifecycle_preflight_input` probe assembly; wired real `service.preflight`; retired the inert stub | resolved |
| `context-bind-success-not-reflected-in-context-show` (MEDIUM) | FR4 — `context show` reads the incumbent pointer | resolved |

FR3 was the meaty one: the architect caught that "wire the stub" was actually a
never-built probe subsystem (its `LifecyclePreflightInput` state classes had zero
producers). It was built honestly from existing readers.

## Validations

| Gate | Result | Evidence |
|---|---|---|
| Full test suite | PASS — 5021 passed / 18 skipped / 0 failed | `pytest -p no:cacheprovider` |
| Mutation-sanity | PASS — 4/4 fixes non-false-positive (incl. CRITICAL FR1 + FR3 subsystem) | qa-engineer handoff `2026-07-09T062212Z` |
| Lint / types / imports | PASS — ruff, mypy --strict (320 files), lint-imports 9/9 | pre-push + CI |
| Architect spec review | REVISE folded (F1a lock.py, F1b safety-envelope, F2 scoping, F3 probe-subsystem) | pre-implementation |
| Code review | APPROVE-WITH-NITS — HIGH (self-hosting `specs doctor --context`) fixed in-release; 1 pre-existing MEDIUM → backlog | code-reviewer handoff `2026-07-09T063300Z` |
| Security push-gate | APPROVED — session/lease identity: no hijack, path-traversal closed at 3 layers, credit-spend hazard closed. Keyed `1302a0dc` | security-reviewer handoffs |
| CI (full matrix) | GREEN — ubuntu + Windows/macOS, PR #132 + post-merge main | GitHub Actions |

## Drifts

- FR3 extended `GitClient`/`GitSubprocessClient` with `upstream_branch`/`unpushed_commit_count`
  (constitution "no subprocess outside infrastructure" — composed, not forked). Reviewed.
- A CI-only test flake surfaced post-push: two FR2 tests were non-hermetic
  (assumed an enclosing workspace) and Rich-box-wrap-fragile on GHA — corrected to
  the CLI-parse contract + ANSI/box normalization (test-only; production unchanged).
- Two non-blocking findings routed to backlog:
  `preflight-block-reasons-missing-operator-command` (MEDIUM, pre-existing, exposed by FR3).
- Registered side-bug `stray-dadaia-tmp-inside-repo` (MEDIUM) — a `code-reviewer`
  sub-agent wrote `.dadaia/tmp/` inside the repo working tree (cleanliness violation);
  the stray dir was removed and the root cause left tracked (open) as an AI-surface item.

## Memory updates

None in this release. Memory consolidation for the whole remediation arc — including
the CLI/context-resolution invariants and the "adapter-validated ≠ workflow-validated"
post-mortem — is done once, after Release C (v0.1.70), per the operator's directive.

## Next

Release C (v0.1.70) — contract/hygiene drift: `specs-doctor-rejects-current-memory-agent-tier-frontmatter`
(HIGH), `remote-bugs-gitignore-blocks-new-intake` (HIGH). Then archival + memory
consolidation + the full post-mortem.
