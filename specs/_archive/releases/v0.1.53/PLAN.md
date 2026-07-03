# PLAN — v0.1.53 — Legacy Purge

**Status:** Aprovado

## Wave map

- **W0 — definition**: SPEC/PLAN/TASKS from the 2026-07-03 inspection (every target
  caller-verified; consumed-by-R4 items recorded); dual definition review;
  `Aprovado`; definition commit.
- **W1 — FR1 legacy CLI + package retirement**: bug-new chain, server dashboard,
  orchestration retirement (orchestrate.py rewired onto features/workflows),
  dead exceptions, `_deferred.py` inline+delete, the DEAD panel workflow-launcher chain (run_workflow/SubprocessWorkflowLauncher/protocol/container wiring + 4 test modules), migrate-audit result recorded. AC-8 ledger on the task line.
- **W2 — FR2 dead-code sweep**: hook `main()`s (after projection-wiring grep),
  LEASE_TTL_SECONDS re-export, library_workflow_catalog relocation, `_assets.py`,
  TelemetryService.list_workflows + handler fallback, shared-`dao` mode check,
  core.js comment refresh.
- **W3 — FR3 canon + config + budgets**: semver canon + agreement test
  (+ AC-7a sabotage), `.import_linter_cache` relocation, perf-budget re-tune,
  `agent_tier` schema-side removal (tolerate-then-strip transition).
- **W4 — FR4 chmod + redaction**: FilePermissionSetter routing + posix guards
  (+ AC-7b sabotage), the 12-file redaction sweep (Bash for `_archive`, JSONL
  parse validation).
- **W5 — gates + ship**: full local gates; **consumed-backlog archival at SHIP**
  (all four entries — durable copies + `consumed_backlog.json`; the release
  deletes its own anchors, per the R4 process discovery); QA review commit;
  security push-gate APPROVE keyed to the pushed sha; push; CI green; PR; merge.
- **W6 — closure** (CLOSURE phase): CLOSURE.md (Validations + Drifts); atom strip
  of `agent_tier` (25 atoms, MEMORY-phase edit) + `context-management` bug-new
  line update + the deprecation-expiry law recorded in the appropriate memory
  atom (`sdd-bug-backlog-governance` or `architecture`); catalog + lint; archive;
  ACTIVE → none; candidates R5 row marked shipped — **mandate complete**.

## Write sets (disjoint per wave)

| Wave | Files |
|---|---|
| W1 | `cli/commands/newartifacts.py`, `cli/main.py`, `features/spec_artifacts/new_artifacts.py`, `cli/commands/server.py`, `features/orchestration/**` (delete), `cli/commands/orchestrate.py`, `dadaia_workspace/container.py`, `infrastructure/workflow_launcher_adapter.py` (delete), `core/protocols/workflow_launcher.py` (delete), `features/panel/service.py` (run_workflow + launcher param), `features/workflows/**` (accessor), `core/exceptions.py`, `features/lifecycle/workflows/{_deferred.py,__init__.py}`, `features/workflows/dadaia_catalog.py`, their tests |
| W2 | `hooks/sdd_gate.py`, `hooks/root_whitelist.py`, `features/spec_context/lease.py`, `features/lifecycle/policy_resolver.py`, `features/panel/views/_assets.py` (delete), `features/telemetry/service.py` (list_workflows), `features/telemetry/aggregator/queries.py` (dao mode), `features/panel/handler.py` (fallback), `views/assets/js/core.js`, their tests (incl. the 6 LEASE_TTL import sites + 5 catalog-helper modules) |
| W3 | `core/specs_version.py`, `features/specs/scaffolder.py`, `features/specs/doctor.py`, `features/spec_artifacts/new_artifacts.py` (regex only — W1 owner finishes first; sequential), `setup.cfg`/lint config (cache dir), `tests/performance/test_lifecycle_hygiene_scan.py`, memory-frontmatter schema/lint/catalog scripts (`public/scripts/*`), `features/specs/catalog.py` (byte-identical twin, lockstep), `tests/contract/test_memory_catalog_render_contract.py`, regenerated `catalog.json`, staging via `dadaia public stage/install`, new contract test |
| W4 | `features/telemetry/service.py` (chmod sites — sequential after W2, disjoint lines), `core/protocols/platform_services.py` (only if signature work needed), the 12 tracked `specs/bugs/**` files, their tests |
| W5/W6 | `specs/**` per the ritual |

`features/telemetry/service.py` is shared W2/W4 — sequential, disjoint ranges.
`new_artifacts.py` is shared W1/W3 — sequential. `dadaia public stage/install`
runs after the W3 script edits (lib-originated assets law) with
`dadaia public doctor` exit 0.

## Test strategy

- Deletion waves are grep-contract driven: each wave's tests assert the CLI/help
  surface (AC-2) and the greps (AC-1); collateral test updates ride the wave.
- W3: the agreement test is the canon's regression lock; perf budget asserted on
  op-count, not seconds.
- W4: DI-fake FilePermissionSetter (raises PlatformSecurityError) for the degrade path; the posix-absent branch via module-level PLATFORM name patch or capability injection (the Capabilities dataclass is frozen — never setattr); AC-7(b) as a source-scan contract test; redacted JSONL re-parsed per line + doctor SPEC-DOC-033 clean.
- Per deletion wave: the AC-8 surviving/dead behavior ledger is a deliverable.
- W1-W4 commits stage NO specs/backlog paths (archival invariant i).
- Full-suite + lint + mypy locally before push; `dadaia public doctor` exit 0
  after the W3 projection updates.

## Rollback

Single feature branch `feature/v0.1.53`; RED commits where a contract is being
established (agreement test, chmod contract); revert = drop the branch. Deletions
are single-commit-per-wave recoverable via git.
