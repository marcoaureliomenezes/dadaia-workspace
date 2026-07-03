# TASKS — v0.1.53 — Legacy Purge

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. Shared files (PLAN §Write
sets) are sequential — one owner, no parallel `[-]`.

## W0 — definition

- [x] T-53-01 SPEC/PLAN/TASKS authored from the 2026-07-03 inspection (all targets
  caller-verified; GONE items recorded: academy.js mermaid / kanban CSS /
  drift-check / factory / repos-.dadaia WARN-intent REJECTED-stale; persona regex
  claim stale = no-op; migrate audit = keep both steps); dual definition review REJECT×2 — architect (dead launcher chain caught; rewire seam named w/ golden fixture; agent_tier required-vs-properties sequence; identity+scan agreement test; archival invariants stated) + QA (AC-5 probe generalized — /home/ubuntu leak; per-symbol AC-1; counts 12/3 + two mixed-assertion test files enumerated; AC-8 ledger; chmod seams; import-linter delete+run probe) — ALL folded; `Aprovado`; definition commit. Owner: product-engineer
  (orchestrated).

## W1 — FR1 legacy CLI + package retirement

- [x] T-53-10 DONE `9d537d69` (28 files, 8 deletions; affected scope 150 passed; unit+integration 4,080 passed/16 skipped exit 0; ruff/mypy clean). 14/14 AC-1 per-symbol probes OK; golden fixtures byte-identical (3 SHA256 matches; gate=<kind> preserved via new WorkflowsService.list_definitions/get_definition over MarkdownWorkflowStore); launcher argv gone; workflow_state_store CONFIRMED orphaned → JsonWorkflowStateStore deleted too; AC-8 ledger in the W1 handoff (2026-07-03T030549Z). Migrate audit: keep both steps. Findings routed to W2: orphaned run-state infra (WorkflowStore protocol, JsonRunStateStore+model, OrchestrationUnsupportedError) + orphaned server_registry/dashboard.py + SKILL.md doc drift. Original scope: DELETE bug-new chain (command + cli/main.py registration +
  spec_artifacts backing + tests); DELETE `server dashboard` (+tests); RETIRE
  COLLATERAL FIX `3811dde7`: `test_dashboard_deprecation_warning_visible`
  (e2e, asserts the deleted `server dashboard` banner) was missed by the
  "+tests" sweep — caught at the W3/W4 full-suite run, deleted pre-ship.
  `features/orchestration` (package + `build_orchestration_service`;
  `orchestrate.py list/show` rewired onto `features/workflows` with the same
  output contract — CLI tests updated; `run/status/resume` verbs REMOVED);
  DELETE the two dead exceptions; inline `DEFERRED_WORKFLOWS` into its 2 consumers and DELETE `_deferred.py`; DELETE the dead panel launcher chain (SPEC FR1 enumeration; confirm workflow_state_store orphan status and record). Record the migrate-audit no-deletion result + the AC-8 ledger on this line. Golden fixture for list/show --json captured BEFORE the rewire. NO specs/backlog paths staged. Owner: software-engineer.

## W2 — FR2 dead-code sweep

- [x] T-53-11 DONE `5984a79c` (44 files, +223/−773; scope 4,223 passed/16 skipped exit 0; ruff/mypy clean). 13/13 AC-1 probes OK (incl. the W1-routed run-state infra + dashboard.py + RunNotFoundError collateral); hook-wiring pre-check: zero live invocations of the deleted main()s (pre_gate is the sole wired entrypoint); shared-dao mode was present+production-dead → removed, 6 test sites converted via a non-closing shared_connection_factory fake (zero assertion loss); AC-8 ledger in the W2 handoff (2026-07-03T035654Z); harness_env fixture gained isolated policy drivers. Recorded not fixed: dev-server-registry SKILL.md drift (lib-originated → CLOSURE). COLLATERAL FIX `3811dde7`: the FROZEN lease e2e (`test_two_actor_lease.py` hook DRIVER) hand-rolled `-m hooks.sdd_gate` — silent no-op after the main() deletion (regression vs merge-base, missed because the wiring pre-check grepped projections only, not tests) — repointed to `-m hooks.pre_gate` (production entrypoint, same contract); frozen-suite modification flagged for QA ship-gate adjudication. Original scope: Pre-check: grep projections/public for direct
  `hooks.sdd_gate`/`hooks.root_whitelist` invocations (record result); DELETE the
  two legacy `main()`s; DELETE the `LEASE_TTL_SECONDS` re-export (lease.py internal uses repointed; __all__ entry dropped; 12 test files — kernel_tunables contract assertion deleted, ==120 assertion repointed); relocate `library_workflow_catalog` to `tests/unit/features/lifecycle/_workflow_catalog.py` (3 modules updated, zero production shim); DELETE `views/_assets.py` (verify zero importers); DELETE
  `TelemetryService.list_workflows` + the unreachable handler fallback; check +
  delete the aggregator shared-`dao` mode (v0.1.52 INFO-2); refresh core.js stale comments + the _assets.py comment refs (static.py, assets/__init__.py, tokens.py). AC-8 ledger on this line. NO specs/backlog paths staged. Owner: software-engineer.

## W3 — FR3 canon + config + budgets

- [x] T-53-12 DONE RED `71e187a5` → feat `0cc3cc53`. Canon in `core/specs_version.py`
  (`RELEASE_SEMVER_RE` + `is_release_semver`); 3 consumers repointed (scaffolder,
  doctor, new_artifacts — `_RELEASE_SEMVER_RE` un-importable from all 3, identity
  holds); RED tail captured (4 failed: offending sites scaffolder:18/doctor:135/
  new_artifacts:29). AC-7(a): planted `_SABOTAGE_SEMVER_RE` in scaffolder ⇒ scan
  FAILED (site scaffolder:20); reverted ⇒ 1 passed. `agent_tier`: dropped from
  schema `required`, RETAINED in `properties` (tolerate-then-strip); BOTH renderers
  lockstep incl. features/specs/catalog.py; render-contract test; catalog.json
  regenerated. `.import_linter_cache` relocated/disabled + hygiene contract test;
  perf test re-tuned to op-count/CPU budget (90s wall-clock ceiling dead).
  Collateral: 2 stale `workflow_launcher_adapter` ignore_imports edges removed
  (W1 deletion residue; lint-imports errored on them), ignore-cap 17→15.
  Projection: `public stage && install --target all && public doctor` exit 0.
  AC-8 ledger in the W3/W4 handoff (2026-07-03T044006Z). NO specs/backlog staged.
  Owner: software-engineer.
  Original scope: `RELEASE_SEMVER_RE` + `is_release_semver()` in
  `core/specs_version.py`; three modules import it; agreement/contract test (RED
  commit first: the test must FAIL against the current triplication — it asserts
  zero literal copies outside the canon). AC-7(a) sabotage: plant a literal copy
  ⇒ test FAILS (captured; reverted). Relocate `.import_linter_cache` (config →
  under `.dadaia/tmp/` or disabled; tree clean after a lint run). Re-tune the
  perf test to an op-count/CPU budget. `agent_tier` schema-side removal per the SPEC sequence (required-list drop, properties RETAINED; BOTH renderers lockstep incl. features/specs/catalog.py + render-contract test; catalog.json regen; `dadaia public stage && install --target all && public doctor` exit 0). NO specs/backlog paths staged.

## W4 — FR4 chmod + redaction

- [x] T-53-13 DONE `6d6d7891`. Both telemetry chmods routed through the injected
  `FilePermissionSetter` (PlatformSecurityError → INFO Tier-2 degrade; 18 existing
  telemetry tests green); single posix-guarded `os.chmod` fallback remains
  (service.py:205 under `PLATFORM.has_posix_chmod`); Windows-path unit tests added
  (frozen Capabilities respected — injection, not setattr). AC-7(b): restored a
  bare `os.chmod(db_path, 0o600)` in the refresh path ⇒ source-scan contract test
  FAILED (line 343); reverted ⇒ 2 passed. Redaction: 28 leaks masked (22 marco +
  6 ubuntu) across the 12 tracked `specs/bugs/**` files → `/home/[REDACTED]`;
  `_archive` .md via Bash (FROZEN class); every JSONL line re-parsed OK; AC-5 grep
  (generalized /home|/Users probe minus [REDACTED]) → EMPTY (exit 1); `specs
  doctor` 0 errors exit 0. Backstop recorded: `redact_text()` already masks — no
  code change. AC-8 ledger in the W3/W4 handoff (2026-07-03T044006Z). NO
  specs/backlog staged. Owner: software-engineer.
  Original scope: Route both telemetry chmods through the injected
  `FilePermissionSetter` (PlatformSecurityError → INFO Tier-2 degrade); direct
  `os.chmod` only under `PLATFORM.has_posix_chmod`; unit tests for the
  Windows paths. AC-7(b) sabotage: restore an unguarded direct chmod ⇒ the
  contract test FAILS (captured; reverted). Redact the 12 tracked
  `specs/bugs/**` files (JSONL notes/repro + `_archive` .md via Bash — FROZEN
  class); JSONL lines re-parsed post-edit; record the backstop evaluation
  (redact() already masks — no code change).

## W5 — gates + ship (flat release: single ship gate)

- [x] T-53-20 DONE. Archival commit `6c08dd25` (single atomic: 4 R100 renames
  backlog→`_archive/v0.1.53/consumed-backlog/` + `consumed_backlog.json`; backlog
  doctor clean; no W1-W4 commit staged specs/backlog — invariants i+ii verified).
  QA ship gate: **APPROVE** (handoff 2026-07-03T051502Z-qa-engineer-v0153-ship-gate,
  validated exit 0). 7/7 checks: AC-1 16/16 symbols zero LIVE refs (tree+tests+
  public); AC-2 CLI contract (bug group + server dashboard + run/status/resume
  absent; orchestrate list/show --json exit 0); AC-3/AC-7 RED `71e187a5` ancestor
  of feat + both contract tests green + single guarded chmod service.py:205;
  AC-5 grep EMPTY + 220/220 JSONL lines parse; AC-6 unpiped 4322 passed/17
  skipped exit 0 + ruff/mypy/public doctor all exit 0. FROZEN-SUITE ADJUDICATED
  PASS: no-steal invariant 100% intact (identical assertions/TTL 120/pid-veto);
  3 paths zero-diff; 4 paths value-identical kernel_tunables repoint (forced by
  FR2); test_two_actor_lease.py pre_gate repoint restores the exercise (was
  silently no-opping); 1 §5 path stale (absent at merge-base too); dashboard-test
  deletion legitimate (asserted a deleted command). Routed to W6: MEDIUM record
  §4↔FR2 freeze tension + stale test_lock_liveness_session.py ref in CLOSURE
  Drifts; LOW dev-server-registry SKILL.md:69,89 still documents server dashboard
  (lib-originated public asset — MUST land in W6). Owner: qa-engineer +
  orchestrator.
- [ ] T-53-21 Security review (push gate — attention: redaction completeness,
  deleted CLI surfaces, hook-entrypoint wiring, public-asset projection
  integrity): APPROVE handoff `metrics.commit_sha` = pushed sha; push; CI green;
  PR; merge. Owner: security-reviewer + orchestrator.

## W6 — closure (CLOSURE phase)

- [ ] T-53-30 CLOSURE.md (Validations + Drifts — SPEC-DOC-006); MEMORY edits:
  strip `agent_tier` from all atoms (+ catalog regenerate + lint),
  `context-management` bug-new legacy lines updated, the deprecation-expiry law
  recorded; archive; ACTIVE → none; candidates R5 row marked shipped —
  **the R1→R5 mandate is complete**. Owner: product-engineer.
