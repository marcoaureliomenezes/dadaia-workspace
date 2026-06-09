# PLAN: 0.1.8 — Cross-Platform OS Compatibility (Linux / macOS / Windows)

**Status:** Aprovado
**Release ID:** 0.1.8
**Segment:** alpha-1 (PLAN covers the full four-segment arc; segment-level TASKS break it down)
**Owner:** product-engineer
**Created:** 2026-06-09

---

## Strategy

Foundation-first. No surface fix before the platform seam, exception types, and
layer-boundary corrections exist. Each step is a dependency node: later steps import
types/singletons/protocols introduced by earlier ones. The Step 0..10 sequence from the
blueprint is the execution order for all production work.

All production edits run on branch `feature/0.1.8` under the SDD gate (`[-]` task
reservation per TASKS.md). Review cadence: qa-engineer commits after each alpha-N segment;
the full ship trio (qa + security + code-reviewer) gates rc-1.

---

## Layers affected

| Layer | Scope |
|-------|-------|
| `core/` | ADD `platform.py` seam + 4 new Protocol ports; surgical changes to `exceptions.py`, `process_probe.py`, `runtime_env.py` |
| `infrastructure/` | ADD 9 adapters; partial-rewrite `runtime_config.py`; surgical changes to `python_env.py`, `workflow_launcher_adapter.py`, 9 JSON/dispatcher stores |
| `features/` | Partial-rewrite `locking.py`, `telemetry/service.py`, `panel/server.py`; surgical changes to `auth.py`, `lease.py`, `scan.py`, `gate_policy.py`, `workspace/service.py`, `import_/service.py`, `spec_context/doctor.py`, `orchestration/service.py`, `server_registry/dashboard.py` |
| `hooks/` | ADD `dadaia_workspace/hooks/` Python package (6 modules, net-new; `pre_push_ci.py` descoped) |
| `cli/` | Surgical: `main.py` (tmp_dir + runtime warning), `commands/panel.py` (PlatformSecurityError), `commands/ci.py` (Python hook wrapper) |
| `container.py` | Partial-rewrite: fix OsProcessProbe import, add PLATFORM + permission setter + shutdown handler factory |
| `public/plugins/` | Surgical: `sdd-gate.ts`, `ctx-inject.ts` (Python subprocess) |
| `ci/` | Phased: `ci.yml`, `release.yml`, `pyproject.toml`, `setup.cfg` (import-linter) |
| `tests/` | ADD ~20 new test files; UPDATE 30+ existing (importorskip, skipif, import paths, assertion updates) |

---

## Execution sequence (Step 0..10 — authoritative ordering)

Each step's dependency rationale is the point. Never swap the order.

### alpha-1: Steps 0–4 (platform seam, exceptions, layer corrections, fcntl crash, CI smoke)

**Step 0 — `core/exceptions.py` additions**
Why first: every subsequent adapter imports `PlatformSecurityError` / `PlatformCapabilityError`.
Nothing can raise typed platform errors until these two classes exist.
Write set: `dadaia_workspace/core/exceptions.py`

**Step 1 — `core/platform.py` platform seam (NEW)**
Why: creates the `PLATFORM` singleton every adapter reads from. Must precede any file that
uses `PLATFORM.has_<flag>`.
Write set: `dadaia_workspace/core/platform.py` + `tests/unit/core/test_platform.py`

**Step 2 — Foundation layer-boundary correction (atomic 4-file commit)**
Why: MOVE `OsProcessProbe` core→infrastructure + UPDATE `container.py:11` import + UPDATE
`test_process_probe.py` import path + ADD `infrastructure/process_probe_adapter.py`. All four
changes are coupled — any one alone leaves the package unimportable. Must precede all later
`container.py` edits.

Deferred-delete protocol for `test_process_probe.py`: the import-path UPDATE (to point at
`infrastructure.process_probe_adapter`) is included in this commit. The full FILE DELETE of
`test_process_probe.py` is a separate later task, deferred until `test_process_probe_adapter.py`
is confirmed green in CI. The ledger item-10 language reflects this: "import path updated in
T-018-03 commit; file deleted in a later task once adapter tests are green."

Write set: `core/protocols/process_probe.py` (shrink), `infrastructure/process_probe_adapter.py`
(NEW), `container.py` (import path), `tests/unit/core/test_process_probe.py` (import path update)

**Step 3 — fcntl crash elimination (WS-3, highest blast radius)**
Why: eliminates the two CLI-killing import crashes. Must precede any CI matrix expansion and
any test that imports `container`. This is the prerequisite of the importability-smoke job
becoming useful.

Step 3 is split into two sub-tasks (3a and 3b/3c):
- **3a (T-018-04):** ADD protocols + all four lock adapters. Full fd lifecycle
  (`os.open`/`os.write`/`os.close`/`os.flock(LOCK_UN)`) moves into `telemetry_lock_posix.py`
  (LV-5). `_acquire_flock` is NOT re-exported from `locking.py`; tests import it from
  `infrastructure/file_lock_posix` directly or via the public API.
- **3b (T-018-05):** UPDATE `locking.py` — remove `import fcntl`, inject via lazy default.
  `test_spec_context_locking.py` imports `_acquire_flock` from `infrastructure/file_lock_posix`
  directly (not from `locking.py` — no re-export).
- **3c (T-018-06):** UPDATE `telemetry/service.py` — remove `import fcntl`, inject
  `refresh_lock` via lazy DI; fix `os.getuid` guard; guard chmod drift check with
  `PLATFORM.has_posix_chmod`. `permission_setter` DI wiring is NOT included here — it moves
  to T-018-10 (Step 5) whose precondition already includes T-018-06. `os.rename → os.replace`
  is NOT included here — it belongs solely to T-018-14 (Step 9, io-encoding); `telemetry/service.py`
  is in T-018-14's write set.

Write set (3a):
- ADD `core/protocols/file_lock.py`, `core/protocols/telemetry_lock.py`
- ADD `infrastructure/file_lock_posix.py`, `infrastructure/file_lock_windows.py`,
  `infrastructure/telemetry_lock_posix.py` (full fd lifecycle), `infrastructure/telemetry_lock_windows.py`
- ADD `tests/unit/infrastructure/test_file_lock_posix.py`, `test_file_lock_windows.py`

Write set (3b):
- UPDATE `features/spec_context/locking.py` (remove `import fcntl`, lazy default)
- UPDATE `tests/unit/test_spec_context_locking.py` (importorskip + import from
  `infrastructure/file_lock_posix` for `_acquire_flock`)

Write set (3c):
- UPDATE `features/telemetry/service.py` (remove `import fcntl`, DI `refresh_lock` only,
  getuid guard, chmod drift check guard)
- UPDATE `tests/unit/features/telemetry/test_service.py` (importorskip + DI injection test)
- UPDATE `tests/integration/test_telemetry_corrupt_db.py` (importorskip)

**Step 4 — CI classifier + collection-crash markers (WS-1/2)**
Why: must follow Step 3 (the importorskip guards reflect the post-fix reality); must precede
enabling any Windows CI matrix job.
Write set:
- UPDATE `pyproject.toml` (classifier, remove hardcoded cache paths)
- UPDATE `.github/workflows/ci.yml` (importability-smoke job Phase 1, tool-cache env vars)
- UPDATE `.github/workflows/release.yml` (replace `/tmp/smoke-ws` with `$RUNNER_TEMP/smoke-ws`)
- UPDATE `dadaia_workspace/cli/main.py` (PLATFORM.tmp_dir, runtime warning)
- ADD `tests/contract/test_platform_classifier.py`
- ADD `tests/unit/cli/test_main_safe_app.py`
- ADD `setup.cfg` (import-linter contract — initial baseline)
- ADD `pytest.importorskip('fcntl')` to 12 test files (see TASKS.md T-018-08 write set)
- ADD `pytestmark skipif win32` to `tests/unit/gate/test_post_gate_heartbeat.py`,
  `tests/integration/gate/test_protected_sessions.py`

---

### alpha-2: Steps 5–9 (security, signals, venv paths, /proc guard, io-encoding)

**Step 5 — File-permission security (WS-7)**
Precondition: T-018-01 `[x]`, T-018-02 `[x]`, T-018-06 `[x]`. `container.py` edit is safe
after T-018-03 `[x]` (import path already corrected). Typed errors exist; `PLATFORM` usable;
`container.py` importable.
Write set:
- ADD `core/protocols/platform_services.py`
- ADD `infrastructure/file_permission_posix.py`, `infrastructure/file_permission_windows.py`
- UPDATE `features/panel/auth.py` (inject `permission_setter`, retain TOCTOU O_EXCL)
- UPDATE `features/spec_context/lease.py` (thread `permission_setter`)
- UPDATE `dadaia_workspace/container.py` (`_PERMISSION_SETTER` helper)
- UPDATE `dadaia_workspace/cli/commands/panel.py` (`PlatformSecurityError` catch, Tier 2)
- ADD `tests/unit/infrastructure/test_file_permission_posix.py`, `test_file_permission_windows.py`
- UPDATE `tests/unit/features/panel/test_auth.py` (skipif + permission setter tests)
- UPDATE `tests/fakes.py` (`FakeFilePermissionSetter`, venv path fix)
- UPDATE `tests/integration/test_telemetry_permissions.py` (importorskip + skipif)
- UPDATE `tests/unit/test_try_build_telemetry.py` (AttributeError parametrize case)

**Step 6 — Process liveness + signals (WS-5)**
Depends on Steps 1, 2. `container.py` edit is safe only after T-018-10 `[x]`
(Precondition: T-018-02 `[x]`, T-018-03 `[x]`, T-018-10 `[x]`).

`build_shutdown_handler()` expected interim form in `container.py`:
```python
def build_shutdown_handler() -> ShutdownHandler:
    if sys.platform == "win32":  # TODO: replace with PLATFORM.has_sigterm once PLATFORM flag added
        return WindowsSignalShutdownHandler()
    return PosixSignalShutdownHandler()
```

Write set:
- ADD `core/protocols/shutdown_handler.py`
- ADD `infrastructure/signal_shutdown_posix.py`, `infrastructure/signal_shutdown_windows.py`
- UPDATE `features/panel/server.py` (DELETE dead functions, leave only `build_panel_http_server`)
- UPDATE `infrastructure/workflow_launcher_adapter.py` (delegate is_alive to injected ProcessProbe)
- UPDATE `dadaia_workspace/container.py` (`build_shutdown_handler()` factory as above)
- UPDATE `dadaia_workspace/cli/commands/panel.py` (`shutdown_handler.install(server)`)
- ADD `tests/unit/infrastructure/test_process_probe_adapter.py`
- ADD `tests/unit/infrastructure/test_signal_shutdown.py`
- UPDATE `tests/unit/core/test_process_probe.py` (import path, skipif fix)
- UPDATE `tests/unit/features/panel/test_workflow_launcher.py` (probe delegation + skipif)

**Step 7 — Venv exec paths + temp dir (WS-6)**
Depends on Step 1 (`PLATFORM` singleton).
Write set:
- UPDATE `infrastructure/python_env.py` (`PLATFORM.venv_scripts_dir`, `PLATFORM.venv_exe_suffix`)
- UPDATE `core/protocols/runtime_env.py` (platform-agnostic docstrings)
- UPDATE `tests/fakes.py` (already covered in Step 5 write set — `FakePythonEnvironmentManager`)

**Step 8 — `/proc` scan guard (WS-4)**
Self-contained; may land any time after Step 0. Sequenced here to group cross-platform surface
fixes in one segment.
Write set:
- UPDATE `features/server_registry/scan.py` (early-return guard + per-function guards)
- ADD `tests/unit/features/server_registry/test_scan_platform_guard.py`
- UPDATE `tests/unit/features/server_registry/test_scan.py` (pytestmark Linux-only)

**Step 9 — I/O encoding + atomic-write consolidation + os.rename→os.replace (WS-F11/F13)**
Zero dependency on platform seam; sequenced last in alpha-2 to minimize review blast radius.
Write set:
- DELETE `_dump()` from `json_context_store.py`, `json_server_registry_store.py`,
  `json_course_store.py`; DELETE inline atomic-write block from `json_run_state_store.py`
- ADD `encoding='utf-8'` to ~22 call sites across `infrastructure/` + `features/`
- UPDATE `features/server_registry/dashboard.py` (`encoding='utf-8'` — ADR-5 surgical fix)
- UPDATE `infrastructure/public_assets.py` (guard `script.chmod(0o755)` with `has_posix_chmod`)
- UPDATE `features/telemetry/service.py`: `os.rename` → `os.replace` at line 219 (sole
  owner of this change — removed from T-018-06 per SE BLOCKER-2)
- ADD `tests/unit/infrastructure/test_io_encoding.py`
- UPDATE `tests/unit/test_json_server_registry_store.py` (assertion update)
- UPDATE `tests/unit/infrastructure/test_json_context_store.py` (atomic-write + encoding coverage)
- UPDATE `tests/unit/infrastructure/test_json_course_store.py` (atomic-write + encoding coverage)

---

### alpha-3: Step 10 (Python hooks + CI Phase 2/3 graduation)

**Step 10 — Python hook entrypoints (WS-8)**
Depends on Steps 1, 3 (`PLATFORM` for `_default_python_bin`, importable container).
`gate_policy.py` PROTECTED patch is an atomic prerequisite of `sdd_gate.py`.

`pre_push_ci.py` is **NOT included** in the hooks package. The `.sh` pre-push hook is
retained (git-for-Windows ships bash). The hooks package has 6 modules:
`__init__`, `_common`, `sdd_gate`, `root_whitelist`, `ctx_inject`, `sdd_post_gate`.

**T-018-15/16 execution protocol (atomic same-commit, two owners):**
software-engineer stages `gate_policy.py` (no commit); ai-engineer authors the single commit
covering both `gate_policy.py` and `hooks/sdd_gate.py`; neither task is marked `[x]` until
that single commit exists AND security-reviewer sign-off is recorded.

Write set (10a — T-018-15, software-engineer):
- STAGE `dadaia_workspace/features/spec_context/gate_policy.py` (do not commit alone)

Write set (10b — T-018-16, ai-engineer):
- COMMIT (with gate_policy.py staged by SE): `dadaia_workspace/hooks/__init__.py`,
  `_common.py`, `sdd_gate.py`, `root_whitelist.py`, `ctx_inject.py`, `sdd_post_gate.py`
- ADD `tests/unit/hooks/` package + 5 test modules (test_common, test_sdd_gate,
  test_root_whitelist, test_ctx_inject, test_sdd_post_gate)

Write set (10c — T-018-17, software-engineer):
- UPDATE `infrastructure/runtime_config.py` (_default_python_bin, Python hook commands)
- UPDATE `features/workspace/service.py` (Python hook command, double-registration guard)
- UPDATE `tests/unit/infrastructure/test_public_assets.py` (assertions: Python command present,
  `.sh` path NOT present — projection supersedes, not appends)
- UPDATE `tests/unit/test_workspace_service.py`

Write set (10d — T-018-18, software-engineer):
- UPDATE `cli/commands/ci.py` (Python hook wrapper — references `pre_push_ci` via `.sh` hook,
  NOT via the Python hooks package)
- UPDATE `tests/contract/cli/test_cli_ci.py`

Write set (10e — T-018-19, ai-engineer):
- UPDATE `public/plugins/sdd-gate.ts`, `ctx-inject.ts` (Python subprocess — ADR-7; venv
  binary resolution: `.dadaia/.venv/bin/python` → `.dadaia/.venv/Scripts/python.exe` → `python`;
  `DADAIA_HOOK_OUTPUT`/`DADAIA_HOOK_EVENT` env contract preserved)
- RUN `dadaia public stage` after editing the `.ts` plugins so T-018-22's install sees matching SHA

Write set (10f — T-018-20, software-engineer):
- UPDATE `tests/integration/test_hooks.py` (Linux-only pytestmark, portable tmp_path)

Write set (10g — T-018-21, software-engineer):
- UPDATE `.github/workflows/ci.yml` (Phase 2 matrix; `continue-on-error` + `timeout-minutes: 8`
  for Windows/macOS; `PYTHONIOENCODING: utf-8` + `PYTHONUTF8: 1` on Windows jobs)

---

### rc-1: ship gate

Ship trio (qa-engineer + security-reviewer + code-reviewer) review the full `feature/0.1.8`
branch. All must approve before push + PR. After merge: CLOSURE.md, memory updates, archive.

---

## Technical risks and mitigations

| Risk | Mitigation |
|------|-----------|
| `container.py` touched in T-018-03, T-018-10, T-018-11 | Formal `Precondition:` lines in each task enforce sequential ordering; only one may be `[-]` at a time |
| `gate_policy.py` + `sdd_gate.py` must be atomic | T-018-15/16 execution protocol: SE stages gate_policy.py, ai-engineer authors the single commit; neither `[x]` until commit + security sign-off exist |
| `telemetry/service.py` split across T-018-06 and T-018-14 | T-018-06: `import fcntl` removal + getuid + chmod guard only; `os.rename→os.replace` is solely T-018-14's write set; `permission_setter` DI is solely T-018-10. Precondition chain prevents out-of-order edits |
| Bun/Windows TS subprocess env-passing (ADR-7) | Venv binary resolution is NON-deferrable. Only `DADAIA_HOOK_OUTPUT`/`DADAIA_HOOK_EVENT` env-passing may defer; if deferred, OpenCode-on-Windows governance is explicitly UNGOVERNED — backlog item required |
| macOS CI flakiness | `continue-on-error` throughout alpha; graduation to hard-gate follows ADR-3 machine-verifiable criterion |

---

## Validation plan

- After each Step (alpha task): `ruff format --check`, `ruff check --no-cache`, `mypy --strict`,
  `pytest -p no:cacheprovider` green locally before committing.
- After Step 3: `python -c "import dadaia_workspace"` exits 0 locally.
- After Step 4: CI importability-smoke job runs and is visible (allow-failure).
- After Step 10: CI Phase 2 matrix added; `dadaia public doctor` exit 0;
  `dadaia specs doctor` 0 ERROR.
- rc-1 gate: full ship trio + `dadaia public doctor` + `dadaia specs doctor` both exit 0.
- `tests/contract/test_platform_classifier.py` asserts correct classifier throughout.
- import-linter `setup.cfg` contract passes in every CI `lint` run from Step 4 onward.
