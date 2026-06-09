# TASKS: 0.1.8 — Cross-Platform OS Compatibility (Linux / macOS / Windows)

**Status:** Aprovado
**Release ID:** 0.1.8
**Owner:** product-engineer
**Created:** 2026-06-09

Markers: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.
Maximum one `[-]` per owner at a time unless disjoint write sets are explicitly declared below.
Security-reviewer sign-off is required before `[x]` on tasks flagged `[SEC]`.
ai-engineer owns all tasks touching lib-originated agentic assets (hooks package, TS plugins).
`container.py` is touched in tasks T-018-03, T-018-10, T-018-11 — these are sequenced; only
one may be `[-]` at any time.
Hooks package: 6 modules (`__init__`, `_common`, `sdd_gate`, `root_whitelist`, `ctx_inject`,
`sdd_post_gate`). `pre_push_ci.py` is descoped — the `.sh` pre-push hook is retained.
CI YAML editing (`.github/workflows/ci.yml` + `release.yml`) is authorized for `software-engineer`
as a recorded operator exception to the `plugin-scope` rule for this release.

---

## Segment alpha-1 — Steps 0–4 (platform seam, exceptions, layer corrections, fcntl crash, CI smoke)

### [x] T-018-01 — Step 0: ADD typed platform exceptions to `core/exceptions.py`
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/exceptions.py`
- **Precondition:** none — this is the unconditional first task
- **Done criterion:** `PlatformSecurityError(DadaiaError)` and `PlatformCapabilityError(DadaiaError)`
  added with `feature_name: str` and `platform: str` attributes + docstrings stating their tier;
  mypy --strict passes; pytest green.

### [x] T-018-02 — Step 1: ADD `core/platform.py` platform seam + unit tests
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/platform.py` (NEW),
  `tests/unit/core/test_platform.py` (NEW)
- **Precondition:** T-018-01 `[x]`
- **Done criterion:** `Capabilities` frozen dataclass with all 7 flags (`has_fcntl`,
  `has_proc_fs`, `has_posix_chmod`, `has_sigterm`, `venv_scripts_dir`, `venv_exe_suffix`,
  `tmp_dir`); `detect()` is the sole authorized `sys.platform` call site in the file;
  `PLATFORM` module-level singleton; unit tests monkeypatch `sys.platform` for linux/darwin/win32
  and verify all flags; mypy --strict passes; pytest green.

### [-] T-018-03 — Step 2: Layer-boundary correction (OsProcessProbe MOVE, atomic 4-file commit)
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/core/protocols/process_probe.py` (DELETE OsProcessProbe + dead imports)
  - `dadaia_workspace/infrastructure/process_probe_adapter.py` (NEW — verbatim OsProcessProbe + Windows INFO note)
  - `dadaia_workspace/container.py` (UPDATE import path from core.protocols.process_probe → infrastructure.process_probe_adapter)
  - `tests/unit/core/test_process_probe.py` (UPDATE import path only; add migration comment; do NOT delete yet)
- **Precondition:** T-018-02 `[x]`
- **Parallelism note:** `container.py` is touched here. No other task touching container.py
  may be `[-]` simultaneously.
- **Done criterion:** `core/protocols/process_probe.py` contains only `ProcessProbe` Protocol
  (~7 lines, zero I/O); `OsProcessProbe` lives in `infrastructure/process_probe_adapter.py`;
  `container.py` import updated; `test_process_probe.py` import path updated in this commit
  (file not yet deleted — deferred until `test_process_probe_adapter.py` is green in CI;
  ledger item-10: "import path updated in T-018-03 commit; file deleted in a later task once
  adapter tests are green"); `python -m pytest tests/unit/core/test_process_probe.py` green;
  package imports cleanly.

### [ ] T-018-04 — Step 3a: ADD file-lock protocols and POSIX/Windows adapters
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/core/protocols/file_lock.py` (NEW)
  - `dadaia_workspace/core/protocols/telemetry_lock.py` (NEW)
  - `dadaia_workspace/infrastructure/file_lock_posix.py` (NEW — receives fcntl body + `_acquire_flock`; not re-exported from `locking.py`)
  - `dadaia_workspace/infrastructure/file_lock_windows.py` (NEW — msvcrt.locking, raises PlatformCapabilityError)
  - `dadaia_workspace/infrastructure/telemetry_lock_posix.py` (NEW — receives the FULL fd lifecycle: `os.open`/`os.write`/`os.close`/`os.flock(LOCK_UN)`; `features/` never touches a raw fd after this task)
  - `dadaia_workspace/infrastructure/telemetry_lock_windows.py` (NEW — always-acquire no-op + INFO log; docstring MUST document SQLite WAL safety assumption)
  - `tests/unit/infrastructure/test_file_lock_posix.py` (NEW)
  - `tests/unit/infrastructure/test_file_lock_windows.py` (NEW)
- **Precondition:** T-018-01 `[x]` (typed errors must exist before adapter raises them)
- **Done criterion:** `WorkspaceLock`, `ContextLock`, `TelemetryRefreshLock` Protocols exist
  in `core/protocols/`; four adapters implement them; `test_file_lock_posix.py` has
  `skipif win32`; `test_file_lock_windows.py` has `skipif != win32` for behavior tests;
  Windows adapter behavior tests must PASS ON A WINDOWS RUNNER (not merely skip on Linux):
  `msvcrt.locking` acquire → `is_locked` → release cycle verified; re-entrant acquire is not
  a silent no-op; `msvcrt`-absent → `PlatformCapabilityError`; `WindowsFileLock.acquire()`
  never silently no-ops; `telemetry_lock_posix.py` holds the full fd lifecycle — no `os.open`
  or raw fd access remains in `features/`; importing `file_lock_windows` on non-Windows raises
  `PlatformCapabilityError`; pytest green on Linux.

### [ ] T-018-05 — Step 3b: UPDATE `locking.py` — remove `import fcntl`, inject via lazy default
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/features/spec_context/locking.py`
  - `tests/unit/test_spec_context_locking.py` (ADD `pytest.importorskip('fcntl')` at top; UPDATE any `_acquire_flock` import to come from `dadaia_workspace.infrastructure.file_lock_posix` directly — NOT from `locking.py`, which does not re-export it)
- **Precondition:** T-018-04 `[x]`
- **Done criterion:** `locking.py` contains no `import fcntl`; `locking.py` does NOT
  re-export `_acquire_flock` (import-linter contract must not exempt this path); public API
  (`workspace_lock`, `context_lock`, etc.) preserved exactly; lazy platform default in
  `workspace_lock` and `context_lock` bodies; `pytest.importorskip('fcntl')` at top of
  test file; `_acquire_flock` tested via `infrastructure/file_lock_posix` import or via
  public `workspace_lock`/`context_lock` API only; pytest green on Linux.

### [ ] T-018-06 — Step 3c: UPDATE `telemetry/service.py` — remove `import fcntl`, fix getuid, chmod guard, DI refresh_lock wiring
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/features/telemetry/service.py`
  - `tests/unit/features/telemetry/test_service.py` (ADD importorskip before TelemetryService import; ADD DI injection test for `refresh_lock`)
  - `tests/integration/test_telemetry_corrupt_db.py` (ADD importorskip)
- **Precondition:** T-018-04 `[x]`
- **Note:** `permission_setter` DI wiring is NOT part of this task — it moves to T-018-10
  (Step 5), whose precondition already includes T-018-06. `os.rename → os.replace` is NOT
  part of this task — it is solely T-018-14's write set (SE BLOCKER-2); `telemetry/service.py`
  is in T-018-14's write set for that change.
- **Done criterion:** `telemetry/service.py` has no `import fcntl`; `refresh_lock` DI
  parameter with lazy platform default (transitional `sys.platform` guard, annotated
  `# TODO: Replace with PLATFORM.has_fcntl`); `os.getuid` uses
  `getattr(os, 'getuid', lambda: 1000)`; chmod drift check guarded by
  `if PLATFORM.has_posix_chmod:`; all test importorskip added; pytest green on Linux.

### [ ] T-018-07 — Step 4a: UPDATE `pyproject.toml` classifier + remove hardcoded cache paths; ADD import-linter `setup.cfg`
- **Owner:** software-engineer
- **Write set:**
  - `pyproject.toml`
  - `setup.cfg` (NEW — import-linter contract)
- **Precondition:** T-018-05 `[x]`, T-018-06 `[x]` (classifier change meaningful only after fcntl crash is fixed)
- **Done criterion:**
  - classifier changed from `OS Independent` to `POSIX :: Linux`;
  - `[tool.ruff] cache-dir`, `[tool.mypy] cache_dir`, `[tool.coverage.run] data_file`
    hardcoded `/tmp/` paths removed;
  - `import-linter` added to `[tool.poetry.group.dev.dependencies]` in `pyproject.toml`;
  - `setup.cfg` declares the following import-linter contracts:
    (a) `features → infrastructure` direct import is forbidden;
    (b) `core → fcntl, signal, subprocess, msvcrt` is forbidden;
    (c) `core.platform` is whitelisted for `sys` (sole authorized `sys.platform` call site);
  - `poetry run lint-imports` passes;
  - mypy green.

### [ ] T-018-08 — Step 4b: ADD `pytest.importorskip` / `skipif` markers to 12 test files; ADD CLI safe_app test + classifier contract test
- **Owner:** software-engineer
- **Write set:**
  - `tests/unit/test_spec_context_lock_reclaim.py` (`pytest.importorskip('fcntl')`)
  - `tests/unit/test_container.py` (do NOT `importorskip('fcntl')`; instead monkeypatch `PLATFORM` with `has_fcntl=True`/`False` and assert container selects posix vs windows adapter in each branch — this test runs on Linux)
  - `tests/unit/test_spec_context_service.py` (`pytest.importorskip('fcntl')`)
  - `tests/unit/test_spec_context_doctor.py` (`pytest.importorskip('fcntl')`)
  - `tests/unit/test_spec_context_doctor_root.py` (`pytest.importorskip('fcntl')`)
  - `tests/unit/features/spec_context/test_service.py` (`pytest.importorskip('fcntl')`)
  - `tests/unit/features/spec_context/test_doctor_gc.py` (`pytest.importorskip('fcntl')`)
  - `tests/unit/features/spec_context/test_stable_session_identity.py` (`pytest.importorskip('fcntl')`)
  - `tests/integration/test_telemetry_permissions.py` (`pytest.importorskip('fcntl')` for fcntl-dependent tests; `skipif win32` added here; mode-bit assertions use `skipif win32` per SE MINOR-1; T-018-10 adds the final `skipif win32` pass for that file)
  - `tests/unit/gate/test_post_gate_heartbeat.py` (`pytestmark skipif win32`)
  - `tests/integration/gate/test_protected_sessions.py` (`pytestmark skipif win32`)
  - `tests/contract/test_platform_classifier.py` (NEW)
  - `tests/unit/cli/test_main_safe_app.py` (NEW)
- **Precondition:** T-018-05 `[x]`, T-018-06 `[x]`
- **Note (SE MINOR-1):** `test_telemetry_permissions.py` adds `importorskip` in this task;
  T-018-10 adds `skipif win32` on mode-bit assertions in that same file. The two tasks are
  sequenced (T-018-08 then T-018-10) for this file.
- **Done criterion:** all listed test files have `pytest.importorskip('fcntl')` as first
  executable statement or `pytestmark = pytest.mark.skipif(sys.platform == 'win32', ...)`
  as appropriate; `test_container.py` monkeypatches `PLATFORM` (not `importorskip`) and
  asserts adapter selection for both `has_fcntl=True` and `has_fcntl=False` branches;
  `test_platform_classifier.py` reads `pyproject.toml` via `tomllib` and asserts
  `Operating System :: POSIX :: Linux`; `test_main_safe_app.py` asserts behavior: `_safe_app()`
  fallback uses `PLATFORM.tmp_dir` — the temp path does NOT contain the literal string `/tmp`
  (assert the platform abstraction, not a function name); pytest suite green on Linux with no
  collection errors.

### [ ] T-018-09 — Step 4c: UPDATE `cli/main.py` (PLATFORM.tmp_dir + runtime warning); UPDATE CI workflows (importability-smoke Phase 1 + tool-cache env vars + release.yml RUNNER_TEMP)
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/cli/main.py`
  - `.github/workflows/ci.yml`
  - `.github/workflows/release.yml`
- **Precondition:** T-018-02 `[x]` (PLATFORM available), T-018-07 `[x]`
- **Note (operator exception):** `.github/workflows/ci.yml` and `release.yml` authorship is
  authorized for `software-engineer` as a recorded operator exception to the `plugin-scope`
  rule for this release.
- **Done criterion:**
  - `cli/main.py` uses `PLATFORM.tmp_dir / 'dadaia-bugs'`; emits `warnings.warn` to stderr
    when `sys.platform != 'linux'`;
  - `ci.yml` adds `importability-smoke` job with `matrix.os: [windows-latest, macos-latest]`
    ONLY (ubuntu already covered by existing jobs); `strategy.fail-fast: false`; each matrix
    job has `continue-on-error: true`; job `env:` includes `PYTHONIOENCODING: utf-8` and
    `PYTHONUTF8: 1`;
  - `RUFF_CACHE_DIR`, `COVERAGE_FILE`, `MYPY_CACHE_DIR` set to `$RUNNER_TEMP` paths on all
    relevant jobs;
  - `release.yml` replaces ALL `/tmp/smoke-ws` occurrences (the `mkdir`, the
    `dadaia init --workspace`, AND the `test -f .../spec_contexts.json` assertion) with
    `$RUNNER_TEMP`-based paths;
  - CI YAML lints clean.

---

## Segment alpha-2 — Steps 5–9 (security, signals, venv paths, /proc guard, io-encoding)

### [ ] T-018-10 — Step 5: ADD `FilePermissionSetter` protocol + POSIX/Windows adapters; UPDATE security consumers [SEC]
- **Owner:** software-engineer
- **Security sign-off required:** security-reviewer must approve before `[x]`
- **Write set:**
  - `dadaia_workspace/core/protocols/platform_services.py` (NEW)
  - `dadaia_workspace/infrastructure/file_permission_posix.py` (NEW)
  - `dadaia_workspace/infrastructure/file_permission_windows.py` (NEW — TOCTOU mitigation option (a): restrict parent dir to owner-only via `icacls <parent_dir> /inheritance:r /grant:r "<user>:(OI)(CI)F"` BEFORE token creation; username via `getpass.getuser()` NOT `os.environ['USERNAME']`; `subprocess.run(..., shell=False)`; non-zero exit → `PlatformSecurityError` raised before token creation)
  - `dadaia_workspace/features/panel/auth.py` (inject permission_setter; retain TOCTOU O_EXCL)
  - `dadaia_workspace/features/spec_context/lease.py` (thread permission_setter via None default)
  - `dadaia_workspace/features/telemetry/service.py` (`permission_setter: FilePermissionSetter | None` DI parameter added here — this is the precondition-correct place after T-018-06 `[x]`)
  - `dadaia_workspace/container.py` (ADD `_PERMISSION_SETTER` conditional helper)
  - `dadaia_workspace/cli/commands/panel.py` (ADD import os; catch PlatformSecurityError; Tier 2 telemetry)
  - `tests/unit/infrastructure/test_file_permission_posix.py` (NEW)
  - `tests/unit/infrastructure/test_file_permission_windows.py` (NEW — must PASS ON A WINDOWS RUNNER: real `icacls` DACL applied or `PlatformSecurityError` on non-zero exit; assert `shell=False`; assert username from `getpass.getuser()`)
  - `tests/unit/features/panel/test_auth.py` (skipif + permission setter tests)
  - `tests/fakes.py` (FakeFilePermissionSetter + FakePythonEnvironmentManager venv path fix)
  - `tests/integration/test_telemetry_permissions.py` (ADD `skipif win32` on mode-bit assertions — SE MINOR-1: T-018-08 added `importorskip`, this task adds `skipif win32` for mode-bit tests)
  - `tests/unit/test_try_build_telemetry.py` (AttributeError case)
- **Precondition:** T-018-01 `[x]`, T-018-02 `[x]`, T-018-06 `[x]`. `container.py` edit
  is safe after T-018-03 `[x]` (import path already corrected).
- **Parallelism note:** `container.py` touched here. No other task touching container.py
  simultaneously.
- **Done criterion:** `WindowsFilePermissionSetter.restrict_to_owner()` applies TOCTOU
  mitigation option (a) — restricts parent dir ACL before token creation; on `icacls`
  failure raises `PlatformSecurityError` (never logs and continues); `icacls` called with
  `shell=False`; username from `getpass.getuser()`; panel startup test asserts it does NOT
  start with an unprotected token on a mocked Windows environment; `test_auth.py` skipif on
  mode-bit assertions; Windows adapter test must PASS ON A WINDOWS RUNNER (real `icacls` DACL
  or `PlatformSecurityError` on non-zero exit); security-reviewer handoff approves before `[x]`;
  pytest green on Linux.

### [ ] T-018-11 — Step 6: ADD `ShutdownHandler` protocol + adapters; UPDATE `panel/server.py`; UPDATE `container.py` `build_shutdown_handler()`
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/core/protocols/shutdown_handler.py` (NEW)
  - `dadaia_workspace/infrastructure/signal_shutdown_posix.py` (NEW)
  - `dadaia_workspace/infrastructure/signal_shutdown_windows.py` (NEW — SIGINT only; never calls `signal.signal(SIGTERM,...)`)
  - `dadaia_workspace/features/panel/server.py` (DELETE `install_shutdown_handlers` + `serve_blocking`)
  - `dadaia_workspace/infrastructure/workflow_launcher_adapter.py` (delegate is_alive to injected ProcessProbe)
  - `dadaia_workspace/container.py` (ADD `build_shutdown_handler()` factory in interim form — see done criterion)
  - `dadaia_workspace/cli/commands/panel.py` (replace `install_shutdown_handlers` call with `shutdown_handler.install(server)`)
  - `tests/unit/infrastructure/test_process_probe_adapter.py` (NEW — all 7 migrated tests + 2 new)
  - `tests/unit/infrastructure/test_signal_shutdown.py` (NEW)
  - `tests/unit/core/test_process_probe.py` (UPDATE import path; add skipif fix for geteuid)
  - `tests/unit/features/panel/test_workflow_launcher.py` (probe delegation test; skipif win32 on os.kill tests)
- **Precondition:** T-018-02 `[x]` (PLATFORM), T-018-03 `[x]` (OsProcessProbe in infrastructure).
  `container.py` edit safe after T-018-10 `[x]` (Formal precondition: T-018-10 `[x]`).
- **Parallelism note:** `container.py` touched here. No other task touching container.py
  simultaneously.
- **Done criterion:** `panel/server.py` contains only `build_panel_http_server()`;
  `signal_shutdown_windows.py` never calls `signal.signal(SIGTERM,...)`; `test_signal_shutdown.py`
  passes on all platforms via monkeypatched `signal.signal`; `build_shutdown_handler()` in
  `container.py` takes the expected interim form:
  ```python
  def build_shutdown_handler() -> ShutdownHandler:
      if sys.platform == "win32":  # TODO: replace with PLATFORM.has_sigterm once PLATFORM flag added
          return WindowsSignalShutdownHandler()
      return PosixSignalShutdownHandler()
  ```
  deferred delete of `test_process_probe.py` noted (file-delete task executes only after
  `test_process_probe_adapter.py` is confirmed green in CI); pytest green.

### [ ] T-018-12 — Step 7: UPDATE `python_env.py` venv paths + runtime_env.py docstrings
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/infrastructure/python_env.py`
  - `dadaia_workspace/core/protocols/runtime_env.py`
- **Precondition:** T-018-02 `[x]` (PLATFORM singleton)
- **Parallelism note:** disjoint from T-018-10 and T-018-11 — safe to parallelize if a
  second implementer is available, as write sets are disjoint.
- **Done criterion:** `python_env.py` uses `PLATFORM.venv_scripts_dir` and
  `PLATFORM.venv_exe_suffix`; docstrings in `runtime_env.py` contain no POSIX-specific
  path references; mypy --strict passes.

### [ ] T-018-13 — Step 8: UPDATE `scan.py` platform guards + ADD platform guard tests
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/features/server_registry/scan.py`
  - `tests/unit/features/server_registry/test_scan_platform_guard.py` (NEW)
  - `tests/unit/features/server_registry/test_scan.py` (ADD pytestmark Linux-only)
- **Precondition:** T-018-02 `[x]` (PLATFORM singleton available — guards use `PLATFORM.has_proc_fs`, not raw `sys.platform`)
- **Parallelism note:** disjoint write set — safe to parallelize with T-018-12.
- **Done criterion:** `scan_unregistered_listeners` returns `[]` with INFO log when
  `not PLATFORM.has_proc_fs`; per-function guards in `_read_cmdline`, `_read_cwd`,
  `_pid_belongs_to_current_user` use `PLATFORM.has_proc_fs` (not `sys.platform` directly);
  `test_scan_platform_guard.py` monkeypatches `PLATFORM` with `has_proc_fs=False` (darwin/win32
  equivalent) and asserts empty list + INFO log; existing `test_scan.py` has pytestmark
  Linux-only; pytest green.

### [ ] T-018-14 — Step 9: I/O encoding + `_dump()` elimination + `_atomic_write_text` consolidation + `os.rename→os.replace` [SEC-review encoding only, no sign-off gate]
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/infrastructure/json_context_store.py` (DELETE _dump, +encoding, route to _atomic_write_text)
  - `dadaia_workspace/infrastructure/json_server_registry_store.py` (DELETE _dump, +encoding)
  - `dadaia_workspace/infrastructure/json_course_store.py` (DELETE _dump, +encoding)
  - `dadaia_workspace/infrastructure/json_run_state_store.py` (DELETE inline block, +encoding)
  - `dadaia_workspace/infrastructure/codex_agent_dispatcher.py` (+encoding)
  - `dadaia_workspace/infrastructure/claude_agent_dispatcher.py` (+encoding)
  - `dadaia_workspace/infrastructure/cli_agent_dispatcher.py` (+encoding)
  - `dadaia_workspace/infrastructure/markdown_workflow_store.py` (+encoding)
  - `dadaia_workspace/infrastructure/public_assets.py` (guard `chmod(0o755)` with `has_posix_chmod`)
  - `dadaia_workspace/features/import_/service.py` (+encoding, 4 sites)
  - `dadaia_workspace/features/spec_context/doctor.py` (+encoding, 3 sites)
  - `dadaia_workspace/features/orchestration/service.py` (+encoding)
  - `dadaia_workspace/features/server_registry/dashboard.py` (+encoding — ADR-5 surgical fix; verify the deferred-import read path at `cli/commands/server.py:321` is exercised by an existing test or document in the file docstring that this read path is not directly unit-testable due to deferred import)
  - `dadaia_workspace/cli/commands/context.py` (+encoding, 2 sites)
  - `dadaia_workspace/features/telemetry/service.py` (`os.rename` → `os.replace` at line 219 — sole owner of this change; SE BLOCKER-2)
  - `tests/unit/infrastructure/test_io_encoding.py` (NEW — 7 Unicode roundtrip tests)
  - `tests/unit/test_json_server_registry_store.py` (UPDATE atomic-write temp-suffix assertion)
  - `tests/unit/infrastructure/test_json_context_store.py` (UPDATE atomic-write + encoding coverage)
  - `tests/unit/infrastructure/test_json_course_store.py` (UPDATE atomic-write + encoding coverage)
- **Precondition:** T-018-02 `[x]` (PLATFORM for `has_posix_chmod` in public_assets.py)
- **Done criterion:** no `_dump()` function remaining in the three JSON stores;
  `_atomic_write_text` is the single write path; all 7 Unicode roundtrip tests in
  `test_io_encoding.py` pass; `os.rename` → `os.replace` applied at `telemetry/service.py:219`
  (this is the sole owner — not T-018-06); `dashboard.py` deferred-import read path either
  covered by a test or documented as untestable in the file docstring; mypy --strict green;
  pytest green.

---

## Segment alpha-3 — Step 10 (Python hooks + CI Phase 2/3 graduation)

### [ ] T-018-15 — Step 10a: UPDATE `gate_policy.py` PROTECTED class [SEC] (atomic with T-018-16)
- **Owner:** software-engineer
- **Security sign-off required:** security-reviewer must approve T-018-15 + T-018-16 together before either is `[x]`
- **Write set:**
  - `dadaia_workspace/features/spec_context/gate_policy.py`
- **Precondition:** T-018-05 `[x]` (locking layer clean), T-018-06 `[x]`
- **Execution protocol (atomic same-commit, two owners):**
  1. software-engineer stages `gate_policy.py` changes (does NOT commit);
  2. ai-engineer authors the single commit covering both `gate_policy.py` AND `hooks/sdd_gate.py`;
  3. Neither T-018-15 nor T-018-16 is marked `[x]` until that single commit exists AND
     security-reviewer sign-off is recorded.
- **Done criterion:** `PROTECTED = 'PROTECTED'` in `PathClass` enum; `classify_path` returns
  `PROTECTED` for `.dadaia/sessions/` prefix; `evaluate()` returns `(Decision.BLOCK, SEC-01 message)`
  for PROTECTED; SEC-01 message matches `sdd-spec-gate.sh:122` verbatim; committed atomically
  with `hooks/sdd_gate.py` (neither file alone is a valid commit); security sign-off recorded.

### [ ] T-018-16 — Step 10b: ADD `dadaia_workspace/hooks/` Python package (6 modules) + unit tests [SEC]
- **Owner:** ai-engineer
- **Security sign-off required:** (shared with T-018-15 — same security-reviewer sign-off gate)
- **Note:** `pre_push_ci.py` is NOT included in this package (descoped per orchestrator decision; `.sh` pre-push hook retained). 6 modules: `__init__`, `_common`, `sdd_gate`, `root_whitelist`, `ctx_inject`, `sdd_post_gate`.
- **Write set:**
  - `dadaia_workspace/hooks/__init__.py` (NEW)
  - `dadaia_workspace/hooks/_common.py` (NEW)
  - `dadaia_workspace/hooks/sdd_gate.py` (NEW — atomic with gate_policy.py T-018-15; MUST delegate to `gate_policy.evaluate()` / `gate_policy.classify_path()`, not re-derive policy; context-slug derivation PATH-first from write target)
  - `dadaia_workspace/hooks/root_whitelist.py` (NEW)
  - `dadaia_workspace/hooks/ctx_inject.py` (NEW — handles both SessionStart and UserPromptSubmit events; once-per-session sentinel keyed on harness-native session id, sentinel path byte-identical to shell sentinel `.dadaia/tmp/ctx-inject-fired-<sessionId>`; preserves `DADAIA_HOOK_OUTPUT`/`DADAIA_HOOK_EVENT` env contract)
  - `dadaia_workspace/hooks/sdd_post_gate.py` (NEW — preserves `os.replace` atomic renewal; `[A-Za-z0-9_-]` session-id strip)
  - `tests/unit/hooks/__init__.py` (NEW)
  - `tests/unit/hooks/test_common.py` (NEW)
  - `tests/unit/hooks/test_sdd_gate.py` (NEW — parity tests: (a) write under `repos/B/...` acquires `repos/B`'s context, not first-ALIVE `repos/A`; (b) fail-open: `sdd_gate.py` is fail-open for all non-`PROTECTED` errors)
  - `tests/unit/hooks/test_root_whitelist.py` (NEW)
  - `tests/unit/hooks/test_ctx_inject.py` (NEW — parity test: second invocation with same session id emits nothing)
  - `tests/unit/hooks/test_sdd_post_gate.py` (NEW — parity tests: (a) `os.replace` atomic renewal; (b) `[A-Za-z0-9_-]` session-id strip; (c) fail-open: any non-`LockHeldError` → ALLOW; `PROTECTED` is the sole fail-closed path)
- **Precondition:** T-018-15 committed (same commit); T-018-02 `[x]` (PLATFORM for
  `_default_python_bin`); T-018-05 `[x]` (locking layer clean)
- **Done criterion:** all 5 non-init hook modules have `if __name__ == '__main__': sys.exit(main())`
  entrypoints; `sdd_gate.py` is fail-open (non-`PROTECTED` errors → ALLOW); `sdd_gate.py`
  DELEGATES to `gate_policy.evaluate()` / `gate_policy.classify_path()` — no policy re-derivation
  in the hook; context-slug is derived PATH-first from the write target; `ctx_inject.py`
  handles both SessionStart and UserPromptSubmit; once-per-session sentinel path is byte-identical
  to shell sentinel; `sdd_post_gate.py` uses `os.replace` atomic renewal; all 5 parity tests
  above pass on Linux; `encoding='utf-8'` on all file reads; security-reviewer handoff approves.

### [ ] T-018-17 — Step 10c: UPDATE `runtime_config.py` + `workspace/service.py` to emit Python hook commands
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/infrastructure/runtime_config.py`
  - `dadaia_workspace/features/workspace/service.py`
  - `tests/unit/infrastructure/test_public_assets.py` (UPDATE 8 assertions)
  - `tests/unit/test_workspace_service.py` (UPDATE 2 assertions)
- **Precondition:** T-018-16 `[x]`
- **Done criterion:** `runtime_config.py` emits `python -m dadaia_workspace.hooks.sdd_gate`
  (and other hooks) via `_default_python_bin()`; the projection SUPERSEDES the stale `.sh`
  hook registration (not appends); `workspace/service.py` `_hook_command_present()` recognizes
  both old `.sh` path and new Python command to prevent double-registration;
  `test_public_assets.py` asserts the emitted config has the Python command (e.g. substring
  `dadaia_workspace.hooks.<name>`) AND does NOT contain the `.sh` path (ensuring supersede, not
  append); `test_workspace_service.py` updated; pytest green.

### [ ] T-018-18 — Step 10d: UPDATE `cli/commands/ci.py` pre-push hook; UPDATE `test_cli_ci.py`
- **Owner:** software-engineer
- **Write set:**
  - `dadaia_workspace/cli/commands/ci.py`
  - `tests/contract/cli/test_cli_ci.py`
- **Precondition:** T-018-16 `[x]`
- **Note:** `pre_push_ci.py` is descoped from the hooks Python package. The `install-hook`
  command continues to install the `.sh` pre-push hook (git-for-Windows ships bash; the `.sh`
  hook survives on Windows). Update `ci.py` to ensure the hook install path is correct and
  any Python hook wrapper references are removed if previously planned.
- **Done criterion:** `install-hook` command installs the correct pre-push hook; `test_cli_ci.py`
  hook content assertion reflects the actual hook being installed (`.sh` path — not a `pre_push_ci`
  Python module reference); pytest green.

### [ ] T-018-19 — Step 10e: UPDATE `sdd-gate.ts` + `ctx-inject.ts` to call Python hooks [ADR-7]
- **Owner:** ai-engineer
- **Write set:**
  - `dadaia_workspace/public/plugins/sdd-gate.ts`
  - `dadaia_workspace/public/plugins/ctx-inject.ts`
- **Precondition:** T-018-16 `[x]`
- **Done criterion:**
  - Both `.ts` plugins call Python hook via subprocess. Venv binary resolution is
    NON-deferrable: resolve `.dadaia/.venv/bin/python` → `.dadaia/.venv/Scripts/python.exe`
    → bare `python` (no bash dependency).
  - `sdd-gate.ts` retains fail-open contract.
  - `ctx-inject.ts` preserves the `DADAIA_HOOK_OUTPUT`/`DADAIA_HOOK_EVENT` env contract;
    `runtime_config.codex_hooks()` preserves SessionStart/UserPromptSubmit split.
  - If Bun-runtime Windows subprocess env-passing (`DADAIA_HOOK_OUTPUT`/`DADAIA_HOOK_EVENT`
    propagation into a Bun subprocess on Windows) is confirmed intractable, document the
    limitation explicitly: "OpenCode-on-Windows hook governance is UNGOVERNED for env-passing
    until this backlog item ships." Register a backlog item before marking `[x]`.
  - `dadaia public stage` is run after editing the `.ts` plugins so T-018-22's install sees
    matching SHA256.

### [ ] T-018-20 — Step 10f: UPDATE `tests/integration/test_hooks.py` Linux-only + portable tmp_path
- **Owner:** software-engineer
- **Write set:**
  - `tests/integration/test_hooks.py`
- **Precondition:** T-018-16 `[x]`
- **Done criterion:** module-level `pytestmark` limits to `sys.platform == 'linux'`; all
  `cwd='/tmp'` occurrences replaced with `str(tmp_path)` or portable temp dir; pytest green.

### [ ] T-018-21 — Step 10g: CI Phase 2 matrix — unit-fast + contract-coverage Windows/macOS allow-fail
- **Owner:** software-engineer
- **Write set:**
  - `.github/workflows/ci.yml` (Phase 2 matrix addition)
- **Precondition:** T-018-16 `[x]`, T-018-20 `[x]`, all alpha-2 tasks `[x]`
- **Note (operator exception):** `.github/workflows/ci.yml` authorship is authorized for
  `software-engineer` as a recorded operator exception to the `plugin-scope` rule for this release.
- **Done criterion:** `unit-fast` and `contract-coverage` jobs gain Windows/macOS matrix legs
  with `continue-on-error: true` and `timeout-minutes: 8`; `PYTHONIOENCODING: utf-8` and
  `PYTHONUTF8: 1` set on Windows matrix jobs; Ubuntu remains hard-gate (unchanged);
  each Windows/macOS leg carries a `# GRADUATION-GATE: delete this line when ready to
  hard-gate` comment on the `continue-on-error: true` line — graduation occurs when both
  Windows+macOS legs are green in a named `feature/0.1.8` CI run (reference the run in
  CLOSURE) and a human deletes the comment; CI YAML lints clean.

---

## Segment rc-1 — Ship gate

### [ ] T-018-22 — Propagate + verify projections + full suite green
- **Owner:** software-engineer
- **Write set:** lib-originated projections (`.claude/agents/`, `.codex/agents/`, etc.)
- **Precondition:** T-018-19 `[x]`
- **Done criterion:** `dadaia public stage && dadaia public install --force --target all`;
  `dadaia public doctor` exit 0; `dadaia specs doctor` 0 ERROR; full pytest suite green
  locally on Linux (≥ 2291 tests).

### [ ] T-018-23 — qa-engineer alpha segment review + commit
- **Owner:** qa-engineer
- **Write set:** review report in `.dadaia/reports/dadaia-workspace/qa-engineer/`
- **Precondition:** T-018-22 `[x]`
- **Done criterion:** qa-engineer reviews full `feature/0.1.8` diff; emits handoff JSON;
  commits review on feature branch (no push, no PR — alpha cadence).

### [ ] T-018-24 — security-reviewer rc-1 review [SEC]
- **Owner:** security-reviewer
- **Write set:** review report in `.dadaia/reports/dadaia-workspace/security-reviewer/`
- **Precondition:** T-018-23 `[x]`; operator elects to ship rc-1
- **Done criterion:** security-reviewer APPROVES F-05 CWE-732 remediation, gate_policy.py
  PROTECTED patch, `hooks/sdd_gate.py`, `WindowsFilePermissionSetter` icacls;
  verdict=APPROVED in handoff JSON.

### [ ] T-018-25 — code-reviewer rc-1 review
- **Owner:** code-reviewer
- **Write set:** review report in `.dadaia/reports/dadaia-workspace/code-reviewer/`
- **Precondition:** T-018-23 `[x]`; operator elects to ship rc-1
- **Done criterion:** code-reviewer APPROVES; verdict=APPROVED in handoff JSON.

### [ ] T-018-26 — CLOSURE + memory updates
- **Owner:** product-engineer
- **Write set:**
  - `specs/releases/0.1.8/CLOSURE.md`
  - `specs/memory/product/platform/context-management.md`
  - `specs/memory/product/platform/workspace-init.md`
  - `specs/memory/tech-stack.md`
  - `specs/memory/architecture.md`
  - `specs/memory/product/platform/cross-platform-portability.md` (NEW atom)
  - `specs/releases/ACTIVE.md`
- **Precondition:** T-018-24 `[x]`, T-018-25 `[x]`
- **Done criterion:** CLOSURE.md authored with tasks/validations/memory-updates; all memory
  atoms updated to reflect post-0.1.8 product state (no changelog sections); `dadaia specs
  doctor` 0 ERROR; ACTIVE.md phase updated to ARCHIVED; release dir ready for `git mv`.
