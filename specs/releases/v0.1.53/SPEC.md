# SPEC — v0.1.53 — Legacy Purge

**Status:** Aprovado
**Branch:** `feature/v0.1.53` (base: `8627fdec`, v0.1.52 closure)
**Origin:** R5 — the FINAL release of the operator's R1→R5 mandate (grill 2026-07-02; definition-time inspection 2026-07-03). Dual definition review 2026-07-03: software-architect REJECT (dead launcher chain; rewire contract; agent_tier additionalProperties trap; agreement-test design; archival invariants) + qa-engineer REJECT (redaction probe false-green on /home/ubuntu; decidable AC-1; corrected counts 12/3; AC-8 inventory; chmod test seams; import-linter probe) — ALL amendments folded in.
**Consumes:** legacy-surface-retirement, hygiene-and-dead-code-cleanup,
centralize-release-semver-canon, telemetry-tier2-chmod-unguarded-on-windows

## 1. Problem

The operator's no-legacy-code law has a verified violation inventory (all anchors
re-checked 2026-07-03):

1. **Legacy CLI surfaces:** `dadaia bug new` (Markdown scaffolder,
   `newartifacts.py:152-184` + `bug_app` in `cli/main.py` + `spec_artifacts`
   backing) superseded by the v0.1.46 JSONL canon; `dadaia server dashboard`
   (`server.py:296-339`) — "removed next release" promised at deprecation, overdue
   since v0.1.48; `features/orchestration` — `start_run`/`resume_run` are honest
   no-ops, only read-only `list/show` survive (consumed by
   `cli/commands/orchestrate.py`); the dead exception pair
   `ReviewBlockedByImplementationError`/`ImplementationBlockedByReviewError`
   (`core/exceptions.py:137-148`, zero raisers/catchers);
   `workflows/_deferred.py` (an EMPTY tuple wrapped in ceremony, 2 consumers).
2. **Audit-C dead code:** legacy `main()`s in `hooks/sdd_gate.py:360` +
   `hooks/root_whitelist.py:96` (one-release promise from v0.1.14);
   `lease.LEASE_TTL_SECONDS` re-export (test-only importers, 6 sites);
   `library_workflow_catalog()` (test-only, 5 modules); `views/_assets.py` shim;
   stale `core.js` router comments; the dead `TelemetryService.list_workflows()`
   (`service.py:444` — calls a method the aggregator does not have) + the
   structurally unreachable `handler.py:736-739` fallback that calls it; the
   aggregator's legacy shared-`dao` mode (v0.1.52 INFO-2) if still present;
   `.import_linter_cache` at the repo root (repo-cleanliness law); the 90s
   wall-clock perf ceiling (`test_lifecycle_hygiene_scan.py:22` — load-sensitive);
   `agent_tier` frontmatter on all atoms with ZERO runtime consumers.
3. **SemVer canon triplicated:** identical `^v\d+\.\d+\.\d+$` literals in
   `scaffolder.py:18`, `doctor.py:135`, `new_artifacts.py:28`; no shared constant,
   no agreement test. (The backlog's "persona prose copy" claim is STALE — no
   regex exists in the persona; recorded as a no-op.)
4. **Windows chmod silent no-op (CWE-732, accepted Tier-2):** direct
   `os.chmod` at `telemetry/service.py:177` (state-dir fallback) and `:318` (DB,
   every refresh) bypass the injected `FilePermissionSetter`/`has_posix_chmod`
   convention.
5. **Redaction debt (CWE-532, security LOW):** 12 tracked `specs/bugs/**` files
   carry `/home/<user>/` literals; the store's `redact()` already masks
   `/home|/Users` usernames (`core/models/bugs.py:75-80`) — the backstop
   evaluation is DONE; only the historical files need the sweep.

Already consumed elsewhere (verified GONE; no work): academy.js mermaid branch,
kanban CSS, panel.token drift-check, connection factory (all v0.1.52);
`repos/*/.dadaia` doctor WARN — NOT implemented and intent superseded: the
root-whitelist/hygiene laws + the v0.1.47 skill fix cover it; dispositioned as
REJECTED-stale in this SPEC (recorded, not silently dropped).

## 2. Goals

1. Every inventoried legacy/dead surface above is DELETED (or re-tuned/centralized
   where stated), with caller-verified safety: zero functional grep hits remain
   for each deleted name.
2. `dadaia orchestrate list/show` keep working, backed by `features/workflows` —
   the orchestration package dies without breaking the read-only CLI.
3. One shared `RELEASE_SEMVER_RE`/`is_release_semver()` in `core/specs_version.py`
   with an agreement test that fails on any reintroduced literal copy.
4. The two telemetry chmods route through the injected `FilePermissionSetter`
   (PlatformSecurityError → Tier-2 INFO degrade), `os.chmod` fallback guarded by
   `PLATFORM.has_posix_chmod` — no Windows silent no-op.
5. The 12 tracked bug files are redacted (`/home/<user>` → `/home/[REDACTED]`),
   matching the live `redact()` semantics.
6. `agent_tier` is REMOVED from `memory-frontmatter-v1` (zero runtime consumers;
   operator YAGNI law): implementation makes schema/lint/catalog tolerate-then-drop
   the field; the atom strip is a CLOSURE-phase MEMORY edit (gate law).
7. Deprecation-expiry law recorded in memory at closure: every future deprecation
   carries a release-stamped expiry honored by the disposing release.

## 3. Functional requirements

### FR1 — Legacy CLI + package retirement

- DELETE `bug new`: the `bug_app` command (`newartifacts.py`), its `cli/main.py`
  registration, the `spec_artifacts.new_artifacts.bug_new` backing + its tests.
  The `context-management` atom's "dadaia bug new is LEGACY" lines update at
  closure (MEMORY).
- DELETE `server dashboard` (`server.py:296-339`) + its tests.
- RETIRE `features/orchestration`: delete the package +
  `container.py#build_orchestration_service`; rewire
  `cli/commands/orchestrate.py` `list/show` via a `features/workflows` accessor
  over the shared `MarkdownWorkflowStore` that returns `WorkflowDefinition`
  (preserving `stage.gate.kind` and `WorkflowInput` — the existing
  `WorkflowDetailDTO.gate: bool` DISCARDS the gate kind, so a naive `get_detail`
  rewire is NOT contract-preserving); AC-2 asserts byte-identical `--json`
  output for `list` and `show` (incl. `gate=<kind>`) against a golden fixture.
  `run/status/resume` verbs are REMOVED (honest no-ops; their tests die).
- DELETE the DEAD panel workflow-launcher chain (definition-review discovery —
  live-wired but UNREACHABLE: no panel route or JS maps to `run_workflow`, yet it
  spawns `["…","orchestrate","run",…]` as a subprocess):
  `PanelService.run_workflow` (`panel/service.py:366-399`),
  `SubprocessWorkflowLauncher` (`infrastructure/workflow_launcher_adapter.py`),
  `core/protocols/workflow_launcher.py`, the `container.py:483`
  `workflow_launcher=` wiring + `PanelService` param, the `workflow_state_store`
  running-workflow registry IF orphaned (confirm), and the 4 launcher test
  modules (`test_workflow_launcher.py`, `test_service_di_workflows.py`, the
  `run_workflow` block in `test_service.py`, the launcher case in
  `test_process_probe_adapter.py`).
- DELETE the two dead exceptions; inline the empty `DEFERRED_WORKFLOWS` concept
  into its 2 consumers and DELETE `_deferred.py` (tests updated).
- `features/migrate` audit RESULT (recorded): both registry steps (`tree-v2`,
  `bugs-jsonl`) are reachable from `dadaia specs upgrade` supported paths — KEEP
  both; no migration deletions this release.

### FR2 — Dead-code sweep (hooks / panel / telemetry / tests-support)

- DELETE the legacy `main()`s in `hooks/sdd_gate.py` + `hooks/root_whitelist.py`
  (verify no harness wiring references them — `pre_gate` is the single
  entrypoint).
- DELETE the `lease.LEASE_TTL_SECONDS` re-export: repoint lease.py's OWN internal
  uses (~:458/490/809) to `kernel_tunables.LEASE_TTL_SECONDS`, drop the `__all__`
  entry, and update the **12** test import sites (corrected count) — of which
  `test_kernel_tunables.py` DELETES its re-export-existence assertion and
  `test_stable_session_identity.py` REPOINTS its surviving `== 120` assertion.
- `library_workflow_catalog()`: relocate to ONE tests-owned helper
  (`tests/unit/features/lifecycle/_workflow_catalog.py`), update the **3**
  consuming test modules, ZERO production shim left in `policy_resolver.py`
  (fix its dangling `:func:` docstring refs).
- DELETE `views/_assets.py` (zero code importers verified) + refresh the stale
  comment references in `views/static.py`, `views/assets/__init__.py`,
  `views/assets/css/tokens.py`.
- DELETE `TelemetryService.list_workflows` + the unreachable `handler.py:736-739`
  fallback (the `api_workflows` view is always container-wired); DELETE the
  aggregator's legacy shared-`dao` mode if present (v0.1.52 INFO-2 — verify).
- Refresh the stale `core.js` router comments (comment-only edit).

### FR3 — Canon + config + test-budget hygiene

- `core/specs_version.py` gains `RELEASE_SEMVER_RE` + `is_release_semver()`; the
  three modules import it. Agreement-test design (decidable, no false positives):
  (a) IDENTITY assertion — all three call sites resolve to the SAME compiled
  object; (b) a scan restricted to `re.compile(...)` ASSIGNMENTS of the pattern
  outside the canon module (message strings/docstrings — e.g. the surviving
  `new_artifacts.py:178` help text — excluded by construction). AC-7(a) plants a
  competing `re.compile`, not message text.
- DELETE the existing `.import_linter_cache/` at the repo root (live hygiene
  violation) + redirect the cache via config (under `.dadaia/tmp/` or
  `--no-cache`); the probe RUNS `lint-imports` with the new config and THEN
  asserts the cache is absent from the tree.
- Re-tune the perf test from the 90s wall-clock ceiling to an op-count/CPU-time
  budget (deterministic under load).
- `agent_tier` removal, implementation half — the exact sequence (the schema has
  `additionalProperties:false`, so removal-from-properties before the atom strip
  would fail ALL atoms): drop `agent_tier` from `required` but RETAIN it in
  `properties` (optional); BOTH catalog renderers stop emitting it in lockstep —
  `public/scripts/generate-memory-catalog.py` AND its byte-identical production
  twin `features/specs/catalog.py` (pinned by
  `test_memory_catalog_render_contract.py`, updated together); `catalog.json`
  regenerated. CLOSURE: strip the field from the 25 atoms (MEMORY edit) AND from
  the `public/scaffold/memory/*.md` templates + AGENTS.md tri-copy (PUBLIC-ASSET
  edits via `dadaia public stage/install`, NOT MEMORY). A later release may then
  drop it from `properties`.

### FR4 — Windows chmod + redaction sweep

- Route the state-dir and DB chmods through the injected `FilePermissionSetter`
  (catch `PlatformSecurityError` → INFO + Tier-2 degrade); direct-`os.chmod`
  fallback only under `PLATFORM.has_posix_chmod`. Unit tests for the
  Windows-path (setter raises / posix absent) behavior.
- Redact the 12 tracked `specs/bugs/**` files (`/home/<user>` and `/Users/<user>`
  → `[REDACTED]` form matching `core/models/bugs.py` semantics); `_archive` files
  edited via Bash (FROZEN class). Backstop evaluation recorded: `redact()`
  already strips these — no code change.

## 4. Non-goals

- NO migration deletions (audit says both steps live). NO `agent_tier`
  replacement wiring (removal is the decision). NO backtrack-transition
  reconciliation (`lifecycle-verb-governance-uniformity` owns it). NO touching
  the surviving frozen no-steal suite. NO persona edits (the regex claim was
  stale). NO new deprecations without a release-stamped expiry.

## 5. Acceptance criteria

- **AC-1 (deletions, per-symbol decidable):** for each deleted symbol, BOTH:
  (a) un-importability — `python -c "from <module> import <symbol>"` raises
  ImportError/AttributeError; (b) the exact `path#symbol` definition line is
  gone. Exclusions defined: comments/docstrings, `specs/_archive/**`, and the
  surviving canonical definitions (`kernel_tunables.LEASE_TTL_SECONDS`, the
  `dadaia orchestrate` CLI itself, `features/workflows`). For the launcher chain:
  the literal `"orchestrate", "run"` subprocess argv is gone from production.
- **AC-2 (orchestrate CLI):** `list/show` `--json` output byte-identical to a
  golden fixture captured pre-rewire (incl. `gate=<kind>` — never degraded to a
  boolean); `run/status/resume` gone from `--help`.
- **AC-3 (canon):** the identity+scan agreement test passes; three modules import
  the canon.
- **AC-4 (chmod):** a source-scan contract test proves no bare `os.chmod(` in
  `telemetry/service.py` outside the guarded block; DI-fake tests prove the INFO
  Tier-2 degrade on PlatformSecurityError and the `has_posix_chmod=False` path
  (via the module-level PLATFORM name or capability injection — NEVER setattr on
  the frozen `Capabilities` instance).
- **AC-5 (redaction, redact()-shaped + sentinel-aware):**
  `grep -rEn "/home/[^/[:space:]]+|/Users/[^/[:space:]]+" specs/bugs/ | grep -vF
  '[REDACTED]'` → empty (this catches the `/home/ubuntu` leak the narrow pattern
  missed — 22× marco + 6× ubuntu across the files); every JSONL line re-parses
  (`json.loads` per line) and `dadaia specs doctor` stays clean (SPEC-DOC-033
  validates the events; `_archive` .md edits touch only SPEC-DOC-032 WARN
  territory). This grep IS the redaction falsifiability probe.
- **AC-6 (gates):** ruff/mypy/full pytest (unpiped, real exit) green locally and
  in CI; `dadaia public doctor` exit 0 after the W3 projection updates.
- **AC-7 (mutation-sanity):** (a) plant a competing `re.compile` semver copy →
  agreement test FAILS; (b) restore a bare unguarded `os.chmod(` → the
  source-scan contract test FAILS. Captured on task lines, reverted.
- **AC-8 (behavior inventory):** each deletion wave records a two-column ledger
  on its task line — surviving behaviors (with the test now asserting them) vs
  intentionally-dead behaviors — so a green suite cannot mask collateral deletion
  of surviving assertions (e.g. `test_cli_orchestrate.py` list/show survives;
  run/status/resume dies).

## 6. Risks

- **Hidden orchestration consumers** — full inventory (definition-review
  corrected): production = `orchestrate.py`, `container.py` (build + import +
  `:483` launcher wiring), `workflow_launcher_adapter.py`, `panel/service.py`
  (`run_workflow`), `core/protocols/workflow_launcher.py`; tests = 8+ modules.
  AC-2's golden fixture guards the surviving CLI contract.
- **Load-bearing W5-archival invariants (verified at definition):** (i) NO
  W1-W4 commit stages any `specs/backlog/**` path — the pre-commit BL gate is
  staged-scope-only, so source-only commits pass with dead anchors; (ii) exactly
  ONE push, at W5, AFTER the atomic archival commit (all 4 entries + ledger in
  one commit). No surviving backlog entry references a to-be-deleted anchor
  (verified). If either invariant breaks, the affected entry's archival moves to
  the wave that first deletes one of its anchors (legacy→W1, hygiene→W2,
  semver→W3).
- **Hook main() external invocation** — verify no projected harness config or
  script invokes `python -m dadaia_workspace.hooks.sdd_gate` directly before
  deleting (grep public/ + .claude/ + .codex/ projections).
- **Redaction breaking JSONL schema** — AC-5 requires parse validation post-edit.
- **agent_tier transition** — lint must tolerate the field until closure strips
  it, else the memory lint gate would fail mid-release.
- **Backlog dead anchors (R4 discovery applies from the start):** this release
  deletes anchors of its OWN consuming entries — the consumed-backlog archival
  (durable copies + ledger ×4) happens AT SHIP in W5, before the push.
