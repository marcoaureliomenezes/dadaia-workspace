# SPEC: 0.1.8 — Cross-Platform OS Compatibility (Linux / macOS / Windows)

**Status:** Aprovado
**Release ID:** 0.1.8
**Segment:** alpha-1 (of alpha-1 / alpha-2 / alpha-3 / rc-1 four-segment release)
**Owner:** product-engineer
**Created:** 2026-06-09

---

## 1. Objective

Close the gap between the false `OS Independent` PyPI classifier dadaia-workspace ships
today and the Linux-only runtime reality. The initiative introduces a **platform-abstraction
seam** (a single `PLATFORM` singleton), a **port/adapter boundary** for every OS-sensitive
domain, and a **3-tier resilience contract** (fail-loud for security controls, degrade-with-log
for non-security features, PlatformCapabilityError at construction for unsupported paths).
The fix is foundation-first: the seam, exceptions, and layer-boundary corrections land before
any surface-level adapter. A phased 3-OS CI matrix grows from an allow-failure
importability-smoke job to a full hard-gate as each surface is fixed.

The outcome of this release is a dadaia-workspace CLI that imports cleanly on Windows and
macOS, enforces its security model correctly on all three platforms, has no bash-dependency
for its governance hooks, and carries an honest classifier that accurately reflects the
remaining Linux-only by-design surface (integration/E2E tests that depend on `/proc` and
`ss`).

---

## 2. Thesis

dadaia-workspace v0.1.7 ships `OS Independent` but is POSIX-Linux-only in practice.
`import fcntl` is unconditional at module top-level in `features/spec_context/locking.py:21`
and `features/telemetry/service.py:25`, both reachable via `container.py`. This is a CLI
crash on every Windows invocation before any command executes. macOS inherits the `/proc`
scan issue and an `os.getuid` AttributeError path. The security model silently no-ops on
Windows (`chmod 0o600/0o700` is a no-op — CWE-732 — while `auth.py` claims OWASP A02
protection). Governance hooks are bash-only and fail-open without Git Bash / WSL. CI is
100% `ubuntu-latest`.

Root cause: absence of a platform-abstraction boundary. The hexagonal port/adapter pattern
already applied to git and JSON stores was never extended to OS-sensitive domains. This
release establishes that foundation.

---

## 3. Findings (FR-01..FR-14) — functional requirements

Each finding from the Pass-1 review is a functional requirement of this release with an
explicit acceptance criterion.

| ID | Severity | Platform | Surface | Evidence | Acceptance criterion |
|----|----------|----------|---------|----------|---------------------|
| **FR-01** | CRITICAL | Windows | `import fcntl` top-level CLI crash | `locking.py:21`, `telemetry/service.py:25` via `container.py:47` | `python -c "import dadaia_workspace"` exits 0 on Windows; fcntl implementation moves to `infrastructure/file_lock_posix.py` behind protocol |
| **FR-02** | CRITICAL | Win+mac | False `OS Independent` classifier | `pyproject.toml:24` | Classifier changed to `Operating System :: POSIX :: Linux`; contract test `test_platform_classifier.py` hard-gates regression; `OS Independent` restored only after Phase-3 CI confirms clean 3-OS run |
| **FR-03** | CRITICAL | Win+mac | No platform boundary (structural root cause) | Zero `sys.platform` / `os.name` / `platform.system` across all `.py` | `core/platform.py` seam exists; `PLATFORM` singleton is the sole authorized `sys.platform` call site; `dadaia doctor` grep check fails the build if `import fcntl`/`import signal`/`os.chmod`/`os.kill` appear in `features/**`; import-linter contract enforced |
| **FR-04** | HIGH | Windows | `OsProcessProbe` (os.kill) in `core/` zero-I/O layer | `core/protocols/process_probe.py:38-65` | Class moved to `infrastructure/process_probe_adapter.py`; `core/` imports zero I/O modules |
| **FR-05** | HIGH | Win+mac | `chmod 0o600/0o700` security no-op (CWE-732) | `features/panel/auth.py:51`, `features/telemetry/service.py:119,126-128`, `features/spec_context/lease.py:108` | `FilePermissionSetter` protocol; `WindowsFilePermissionSetter` via `icacls` raises `PlatformSecurityError` on failure (never a warning); panel MUST NOT start with unprotected token; security-reviewer sign-off required |
| **FR-06** | HIGH | Windows | venv path hardcodes `bin/` (should be `Scripts/` on Windows) | `infrastructure/python_env.py:18,21`, `core/protocols/runtime_env.py:12,15` | `python_env.py` reads `PLATFORM.venv_scripts_dir` and `PLATFORM.venv_exe_suffix`; docstrings platform-agnostic |
| **FR-07** | HIGH | Windows | Bash-only SDD governance hooks fail-open | `sdd-spec-gate.sh`, `root-whitelist-gate.sh`, `ctx-inject.sh`, `pre-push-ci-gate.sh`, `sdd-post-gate.sh` | `dadaia_workspace/hooks/` Python package with parity hooks; `runtime_config.py` emits Python command; `workspace/service.py` recognizes both old `.sh` and new Python command to prevent double-registration; `sdd-gate.ts` + `ctx-inject.ts` updated; security-reviewer sign-off on `gate_policy.py` PROTECTED patch |
| **FR-08** | HIGH | Win+mac | `/proc` scan + `os.getuid()` AttributeError | `features/server_registry/scan.py:115,128,138` | Early-return guard in `scan_unregistered_listeners` on non-Linux; per-function guards in `_read_cmdline`, `_read_cwd`, `_pid_belongs_to_current_user`; INFO log "orphan detection disabled"; `os.getuid` AttributeError guard in `telemetry/service.py` via `getattr` |
| **FR-09** | HIGH | Win+mac | CI 100% ubuntu — no Win/macOS coverage | `ci.yml` (11 jobs), `release.yml` (10 jobs) | Phased 3-OS CI matrix (see §9): importability-smoke allow-fail from Step 4; Phase 2 unit/contract matrix after WS-3+5+6+7 land; Phase 3 hard-gate after all surface fixes |
| **FR-10** | HIGH | Windows | `signal.SIGTERM` registration raises OSError | `features/panel/server.py:85` | `ShutdownHandler` protocol; `WindowsSignalShutdownHandler` registers SIGINT only; INFO log; never attempts `signal.signal(SIGTERM,...)` on Windows |
| **FR-11** | MEDIUM | Windows | Missing `encoding='utf-8'` — cp1252 corruption risk | ~22 call sites across `infrastructure/` and `features/` | All `open()`/`read_text()`/`write_text()` calls in identified files add `encoding='utf-8'`; `_atomic_write_text` chokepoint eliminates 3 `_dump()` duplicates; `test_io_encoding.py` with 7 Unicode roundtrip tests green |
| **FR-12** | MEDIUM | Windows | Hardcoded `/tmp/dadaia-bugs` fallback | `cli/main.py:85` | `tempfile.gettempdir() / 'dadaia-bugs'` or `PLATFORM.tmp_dir / 'dadaia-bugs'`; same fix in bash hooks `sdd-spec-gate.sh:13,27` + `root-whitelist-gate.sh:20,36` is superseded by Python hook migration (FR-07) |
| **FR-13** | LOW | Windows | `os.rename` non-atomic over existing dest on Windows | `features/telemetry/service.py:219` | `os.rename` → `os.replace` at that site; in scope (ADR-6 confirmed) |
| **FR-14** | HIGH | Windows | Test `import fcntl` → pytest collection crash on Windows | `tests/unit/test_spec_context_locking.py:19`, `tests/integration/test_hooks.py:37`, 61 mode-bit assertion sites | `pytest.importorskip('fcntl')` / `skipif win32` markers added to 12+ test files; pytest collection exits 0 on Windows after Step 4 |

---

## 4. Foundation law (must precede all surface work)

### 4.1 Platform seam — `dadaia_workspace/core/platform.py` (NEW)

A single `Capabilities` frozen dataclass with `detect()` classmethod (the sole authorized
`sys.platform` call site in the codebase) and a module-level `PLATFORM` singleton (~35 lines,
stdlib only). Flags: `has_fcntl`, `has_proc_fs`, `has_posix_chmod`, `has_sigterm`,
`venv_scripts_dir`, `venv_exe_suffix`, `tmp_dir` (= `Path(tempfile.gettempdir())`).

No other file may read `sys.platform`, `os.name`, or `platform.system()` directly except
during the transitional window (Steps 0–3) where interim `sys.platform` guards in function
bodies are permitted, each annotated `# TODO: Replace with PLATFORM.has_<flag> once WS-1 lands`.
Module-level `sys.platform` is forbidden everywhere except `core/platform.py` at all times.

**Import convention:** the canonical import form is `from dadaia_workspace.core.platform import PLATFORM`.
All consumer files use this exact form. `detect()` is never called directly — only `PLATFORM`
(the module-level singleton) is accessed. Post-TODO, `features/` files also access it via this
same import.

### 4.2 Layering law (four violations to fix before all other work)

- `core/` — zero I/O. Only stdlib typing + other `core/` modules. `core/platform.py` is the
  single authorized exception.
- `infrastructure/` — all OS adapters. Every `fcntl`, `os.kill`, `os.chmod`, `signal.signal`,
  `subprocess`, `/proc`, `win32security` call lives here behind Protocol interfaces.
- `features/` — business logic only. Zero direct `import fcntl` / `import signal` /
  `os.chmod` / `os.kill`. Receives OS capability via injected Protocol-typed dependency.
- `container.py` — sole composition root. Reads `PLATFORM`, selects adapters, wires them.

Five current violations (atomic prerequisite of all further work):

| # | Violation | Location | Fix |
|---|---|---|---|
| LV-1 | `import fcntl` in `features/` | `locking.py:21` | MOVE to `infrastructure/file_lock_posix.py`; Protocol in `core/protocols/file_lock.py`; `_acquire_flock` is NOT re-exported from `locking.py` — tests import it from `infrastructure/file_lock_posix` directly (or test via the public `workspace_lock`/`context_lock` API) |
| LV-2 | `import fcntl` in `features/` | `telemetry/service.py:25` | MOVE flock block AND the full fd lifecycle (`os.open`/`os.write`/`os.close`/`os.flock(LOCK_UN)`) to `infrastructure/telemetry_lock_posix.py`; `TelemetryRefreshLock` Protocol; `features/` layer calls the protocol and never touches a raw fd |
| LV-3 | `OsProcessProbe` (os.kill) in `core/` | `core/protocols/process_probe.py:38-65` | MOVE to `infrastructure/process_probe_adapter.py`; keep only `ProcessProbe` Protocol in core |
| LV-4 | POSIX path baked in core Protocol docstring | `core/protocols/runtime_env.py:12,15` | Rewrite docstrings platform-agnostic |
| LV-5 | `os.open`/`os.write`/`os.close`/`os.flock(LOCK_UN)` fd lifecycle in `features/` | `features/telemetry/service.py` | MOVE full fd lifecycle into `TelemetryRefreshLock` infrastructure adapters; `features/` layer must not hold a raw fd; `dadaia doctor` grep check extended to also flag `os.open` in `features/**` |

### 4.3 DI convention (three-file pattern per platform-sensitive domain)

1. `core/protocols/<domain>.py` — Protocol only; zero I/O, zero `sys.platform`.
2. `infrastructure/<domain>_posix.py` / `infrastructure/<domain>_windows.py` — one file per
   platform variant; platform-specific module imported at file top.
3. `container.py` — selects adapter by `PLATFORM` flag, wires into builders.

Exception: `infrastructure/python_env.py` reads `PLATFORM.venv_*` directly — a two-line
conditional with no behavioral variation warranting a full protocol.

### 4.4 Enforcement (two layers)

- **import-linter**: `setup.cfg` contract declaring `features` forbidden from importing
  `infrastructure` directly; `core` forbidden from importing I/O modules. Runs in CI `lint` job.
- **`dadaia doctor` check**: greps `features/**/*.py` for `import fcntl`, non-seam
  `import signal`, `os.chmod`, `os.kill`; fails with `[ERROR]` if found.

---

## 5. Resilience contract (3 tiers)

Typed errors in `core/exceptions.py`: `PlatformSecurityError(DadaiaError)`,
`PlatformCapabilityError(DadaiaError)` (attributes: `feature_name: str`, `platform: str`).

**TIER 1 — FAIL LOUD (security controls; silent no-op forbidden).**
- `os.chmod(0o600/0o700)` on Windows → `WindowsFilePermissionSetter` MUST apply TOCTOU
  mitigation option (a): restrict the parent directory to owner-only using
  `icacls <parent_dir> /inheritance:r /grant:r "<user>:(OI)(CI)F"` BEFORE creating the
  token file, so the token inherits a restrictive ACL. Username is obtained via
  `getpass.getuser()` (not `os.environ['USERNAME']`). The `icacls` call MUST use
  `subprocess.run(..., shell=False)`. If the dir-restriction `icacls` call returns non-zero,
  raise `PlatformSecurityError` immediately — do not create the token file. Panel MUST NOT
  start with an unprotected token; there is no warn-and-continue path for `auth.py ensure_token()`.
- `fcntl.flock` on Windows → `WindowsFileLock` uses `msvcrt.locking` (ADR-2 confirmed) or
  raises `PlatformCapabilityError`. A no-op lock is worse than no lock.

**TIER 2 — DEGRADE WITH EXPLICIT INFO LOG (non-security features).**
- `/proc` scan → non-Linux returns `[]` + INFO "orphan detection disabled". Panel shows
  "Scan unavailable on this platform."
- `signal.SIGTERM` on Windows → register SIGINT only; INFO log.
- `TelemetryRefreshLock` on Windows → always-acquire no-op + INFO log. **SQLite WAL
  assumption:** the always-acquire no-op is safe only because SQLite WAL mode serializes
  concurrent writers internally. The `WindowsTelemetryRefreshLock` adapter docstring MUST
  document this assumption explicitly: "safe because SQLite WAL mode provides its own write
  serialization; this no-op is not a correctness risk." If WAL mode is ever disabled, this
  adapter must be revisited.
- Windows permission-setter failure on telemetry/lease dirs → telemetry `None`/503; lease dir
  logs INFO and continues. (Only the panel auth token is Tier 1.)

**TIER 3 — UNSUPPORTED PLATFORM at construction.** Where no degradation exists, raise
`PlatformCapabilityError` / `PlatformSecurityError` at service construction in `container.py`,
not at call time.

**DEAD-PATTERN REMOVAL.** The chmod drift check (`telemetry/service.py:126-128`) fires
false positives on Windows. Guard with `if PLATFORM.has_posix_chmod:` — not a security
regression, removes a false alarm that trains operators to ignore warnings.

---

## 6. Architecture deltas

New files (selected — full 39-file ADD ledger in `specs/backlog/cross-platform-os-compatibility-ledger.md §1`):

- `dadaia_workspace/core/platform.py` — platform seam (NEW)
- `dadaia_workspace/core/exceptions.py` — additions: `PlatformSecurityError`, `PlatformCapabilityError`
- `dadaia_workspace/core/protocols/{file_lock,telemetry_lock,platform_services,shutdown_handler}.py` — 4 new ports
- `dadaia_workspace/infrastructure/{file_lock_posix,file_lock_windows,telemetry_lock_posix,telemetry_lock_windows,file_permission_posix,file_permission_windows,process_probe_adapter,signal_shutdown_posix,signal_shutdown_windows}.py` — 9 new adapters
- `dadaia_workspace/hooks/` — new Python package (6 modules: `__init__`, `_common`, `sdd_gate`, `root_whitelist`, `ctx_inject`, `sdd_post_gate`) replacing bash governance hooks; `pre_push_ci.py` is NOT included (the `.sh` pre-push hook is retained — git-for-Windows ships bash, so it survives on Windows)

Key module verdicts (full 49-module rewrite map in ledger §2):

- `full-module-rearchitecture` (~17): all net-new seam + protocol + adapter + hooks files
  (hooks package is 6 modules, not 7: `pre_push_ci.py` descoped — `.sh` pre-push hook retained)
- `partial-rewrite` (6): `locking.py`, `telemetry/service.py`, `panel/server.py`,
  `infrastructure/runtime_config.py`, `container.py`
- `surgical-change`: remainder (encoding fixes, guard inserts, docstrings, classifier)

MOVE ledger (4 relocations for layer-boundary corrections):

| From | To |
|------|----|
| `core/protocols/process_probe.py::OsProcessProbe` | `infrastructure/process_probe_adapter.py` |
| `features/spec_context/locking.py` fcntl body | `infrastructure/file_lock_posix.py` |
| `features/telemetry/service.py` flock block | `infrastructure/telemetry_lock_posix.py` |
| `features/panel/server.py` shutdown handler | `infrastructure/signal_shutdown_{posix,windows}.py` |

DELETE ledger (8 dead-code units — see ledger §1):

- `OsProcessProbe` from `core/protocols/process_probe.py` (+ dead imports)
- `install_shutdown_handlers()` + `serve_blocking()` from `features/panel/server.py`
- Three `_dump()` duplicates (json_context_store, json_server_registry_store, json_course_store)
- Inline atomic-write block in `json_run_state_store._write_manifest_atomic`
- `workflow_launcher_adapter.is_alive()` inline os.kill body

---

## 7. Architecture Decision Records

**ADR-1 — Injection strategy.** CONFIRMED: lazy module-level default inside
`workspace_lock()` / `context_lock()` / `TelemetryService.__init__()`. Interim
`sys.platform` guard in function/constructor bodies only, each annotated `TODO: Replace with
PLATFORM.has_<flag> once WS-1 lands`. Zero call-site changes.

**ADR-2 — Windows lock strategy.** `msvcrt.locking` (stdlib, zero new PyPI dep).
`WindowsFileLock` raises `PlatformCapabilityError` if `msvcrt` unavailable. A no-op lock is
forbidden (creates false serialization confidence).

**ADR-3 — macOS target level.** Best-effort initially: CI `continue-on-error`,
degradation logged, not a hard-gate. Graduates to hard-gate in CI Phase 3 when both Windows and
macOS legs of the `unit-fast` and `contract-coverage` jobs are green in a named `feature/0.1.8`
CI run. The graduation artifact is an edit to `ci.yml` that removes the `continue-on-error:
true` lines, gated behind an explicit `# GRADUATION-GATE: delete this line when ready to
hard-gate` comment that a human must delete. The CI run reference must be recorded in the
CLOSURE validation evidence.

**ADR-4 — Telemetry tier.** Windows permission-setter failure on telemetry/lease dirs is
Tier 2 (telemetry → None/503; lease dir logs INFO and continues). Only the panel auth token
is Tier 1 (panel MUST NOT start with unprotected token).

**ADR-5 — `dashboard.py` deletion deferred.** `features/server_registry/dashboard.py` is
deprecated but has a live deferred import at `cli/commands/server.py:321`. Do NOT delete
in this release. Deprecation-removal is a follow-up backlog item. Add `encoding='utf-8'`
to its one `read_text()` call as a surgical fix (FR-11 coverage).

**ADR-6 — F-13 in scope.** `os.rename` → `os.replace` at `telemetry/service.py:219`
is included. Safe on Linux; prevents `FileExistsError` on Windows same-second quarantine.

**ADR-7 — OpenCode plugin scope.** Updating `public/plugins/sdd-gate.ts` + `ctx-inject.ts`
to call Python hooks is included. The venv binary resolution (`PLATFORM`-aware path:
`.dadaia/.venv/bin/python` → `.dadaia/.venv/Scripts/python.exe` → bare `python`) is
NON-deferrable and must ship in this release so the TS plugins call Python hooks without
a bash shell dependency. Only the Bun-runtime Windows subprocess env-passing sub-part
(`DADAIA_HOOK_OUTPUT`/`DADAIA_HOOK_EVENT` propagation into a Bun subprocess on Windows)
may be deferred. If deferred, OpenCode-on-Windows hook governance is explicitly **UNGOVERNED**
for that env-passing surface — this limitation must be stated honestly in the CLOSURE
expectations and a tracked backlog item must be registered before `[x]`. Do not characterize
the deferral as "bounded" or "contained" — governance is absent until the backlog item ships.

**ADR-8 — `Capabilities.tmp_dir` included.** `tmp_dir: Path = Path(tempfile.gettempdir())`
is a field on the `PLATFORM` singleton. `cli/main.py` uses `PLATFORM.tmp_dir / 'dadaia-bugs'`
consistently. No dead field.

---

## 8. Scope

### In scope

- All 14 findings (FR-01..FR-14) as described above
- Foundation first: platform seam + exceptions + layer corrections precede all adapters
- `dadaia_workspace/hooks/` Python package (replaces bash governance hooks)
- import-linter + doctor-grep enforcement of layering law
- Phased 3-OS CI matrix (allow-fail importability-smoke → Phase 2 unit/contract → Phase 3 hard-gate)
- `pyproject.toml` classifier correction + removal of hardcoded `/tmp/` cache paths
- `setup.cfg` import-linter contract
- Test markers (`pytest.importorskip`, `skipif win32`) on 12+ test files
- `sdd-gate.ts` + `ctx-inject.ts` Python subprocess migration (ADR-7)
- `core/exceptions.py` additions (two new exception classes)

### Out of scope

- `features/server_registry/dashboard.py` full deletion (deferred — ADR-5; surgical
  `encoding=` fix only)
- Windows-native installation/packaging (no NSIS/WiX installer)
- Windows-native filesystem symlink / junction support
- Integration, E2E-python, E2E-panel CI jobs on Windows/macOS (Linux-only by design:
  they depend on `/proc` and `ss`)
- `psutil` dependency for Windows process liveness (future ADR once `os.kill` behavior
  is documented with INFO log)
- Any new product feature not related to platform portability

---

## 9. Phased 3-OS CI matrix plan

> **Operator exception — CI YAML authorship:** `.github/workflows/ci.yml` and
> `release.yml` editing for this release is authorized for `software-engineer` as a
> recorded operator exception to the `plugin-scope` rule. The operator commissioned the
> CI jobs and named `software-engineer`, not `devops-engineer`, as the responsible
> implementer for this release.


**Phase 1 (Step 4, alpha-1):** ADD `importability-smoke` job in `ci.yml`:
`matrix.os: [windows-latest, macos-latest]` ONLY (ubuntu is already covered by existing
CI jobs). `strategy.fail-fast: false`; each matrix job carries `continue-on-error: true`.
Job env must include `PYTHONIOENCODING: utf-8` and `PYTHONUTF8: 1`.
Runs `python -c "import dadaia_workspace; import dadaia_workspace.cli.main"` and
`dadaia --help`. Allow-failure makes the crash visible without blocking PRs. Also add CI
env vars for tool-cache redirection (`RUFF_CACHE_DIR`, `COVERAGE_FILE`, `MYPY_CACHE_DIR` →
`$RUNNER_TEMP`) and remove the hardcoded `/tmp` paths from `pyproject.toml`
`[tool.ruff]`, `[tool.mypy]`, `[tool.coverage.run]`.

**Phase 2 (alpha-2, after WS-3/5/6/7 land):** Add Windows/macOS matrix legs to `unit-fast`
and `contract-coverage`; Ubuntu hard-gates (unchanged); Windows/macOS legs carry
`continue-on-error: true` and `timeout-minutes: 8` (platform-CI is slower).
Graduate to hard-gate per the ADR-3 machine-verifiable criterion: both Windows+macOS legs
green in a named `feature/0.1.8` CI run; the graduation artifact removes the
`continue-on-error: true` lines (gated behind the `# GRADUATION-GATE:` comment).

**Phase 3 (alpha-3, after all surface fixes):** Replace `runs-on: ubuntu-latest` with
3-OS matrix for lint, typecheck, unit-fast, contract-coverage; hard-gate. Restore
`OS Independent` classifier only after this confirms clean 3-OS runs.

**Linux-only by design (never add Win/macOS):** integration, e2e-python, e2e-panel.
These depend on `/proc` and `ss` — documented in `scan.py` module docstring.

**Windows job env:** set `PYTHONIOENCODING: utf-8` and `PYTHONUTF8: 1` on all
Windows-matrix jobs.

---

## 10. Tech-stack deltas

- `import-linter` (PyPI) — new dev dependency for `setup.cfg` architecture contract.
  Zero runtime impact; lint/CI only.
- No other new PyPI dependencies (Windows lock via stdlib `msvcrt`; Windows ACL via stdlib
  `subprocess icacls`).

---

## 11. Security / operations deltas

- **CWE-732 remediation (F-05):** `WindowsFilePermissionSetter` provides real
  owner-only DACL via `icacls`. `PlatformSecurityError` raised — never a no-op or warning.
  Mandatory security-reviewer sign-off on WS-7 tasks.
- **`gate_policy.py` PROTECTED patch (F-07):** `PROTECTED` class added to
  `PathClass` enum; `.dadaia/sessions/` prefix blocked unconditionally; committed
  atomically with `hooks/sdd_gate.py`. Mandatory security-reviewer sign-off.
- **Panel auth token invariant (ADR-4):** Tier 1 — panel MUST NOT start if token
  cannot be restricted to owner.

---

## 12. Memory files affected at closure

- `specs/memory/product/platform/context-management.md` — locking model updated
  (fcntl behind protocol, Windows adapter)
- `specs/memory/product/platform/workspace-init.md` — hooks registration updated
  (Python hooks, not bash)
- `specs/memory/tech-stack.md` — `import-linter` dev dependency added
- `specs/memory/architecture.md` — layer law section updated (platform seam, layering
  invariant, `container.py` as sole composition root)
- New atom `specs/memory/product/platform/cross-platform-portability.md` — documents
  the platform seam, 3-tier resilience contract, and current portability state

---

## 13. Acceptance criteria

1. `python -c "import dadaia_workspace; import dadaia_workspace.cli.main"` exits 0 on
   Linux, macOS, and (after Step 3) a Windows test runner.
2. `dadaia --help` exits 0 on Linux and macOS (Windows via CI matrix).
3. `tests/contract/test_platform_classifier.py` asserts classifier is
   `Operating System :: POSIX :: Linux` — hard-gates reversion.
4. `dadaia doctor` grep check fails with `[ERROR]` on any `import fcntl` /
   `os.chmod` / `os.kill` / `os.open` (in `features/**/*.py`).
5. import-linter `setup.cfg` contract passes in CI `lint` job: (a) `import-linter` is in
   `[tool.poetry.group.dev.dependencies]`; (b) `features → infrastructure` direct import is
   forbidden; (c) `core → fcntl, signal, subprocess, msvcrt` is forbidden with
   `core.platform` whitelisted for `sys`; (d) `poetry run lint-imports` passes.
6. Panel does not start if `ensure_token()` cannot restrict the token file to owner
   on Windows (Tier 1 invariant).
7. `/proc` scan returns `[]` with INFO log on non-Linux; no `AttributeError` from
   `os.getuid()` on Windows.
8. `dadaia specs doctor` 0 ERROR; `dadaia public doctor` exit 0.
9. Full pytest suite green on Ubuntu (≥ 2291 tests, matching v0.1.7 rc-3 baseline).
10. Windows-adapter behavior tests PASS ON A WINDOWS RUNNER (not merely skip on Linux):
    - `test_file_lock_windows.py`: `msvcrt.locking` acquire → `is_locked` → release + re-entrant
      behavior is not a silent no-op; `msvcrt`-absent → `PlatformCapabilityError`;
      `WindowsFileLock.acquire()` never silently no-ops.
    - `test_file_permission_windows.py`: real `icacls` DACL applied or `PlatformSecurityError`
      on non-zero exit; `icacls` called with `shell=False`; username from `getpass.getuser()`.
11. `runtime_config.py` emits Python hook command (not bash `.sh` path);
    `workspace/service.py` recognizes both to prevent double-registration;
    `test_public_assets.py` asserts the emitted config has the Python command and NOT the
    `.sh` path (projection supersedes, not appends).
12. `sdd-gate.ts` + `ctx-inject.ts` call Python hooks via subprocess.
13. Python hook parity contract — `hooks/sdd_gate.py` and `hooks/ctx_inject.py` must
    preserve the rc-4 behavioral invariants:
    - `hooks/sdd_gate.py` MUST delegate to `gate_policy.evaluate()` /
      `gate_policy.classify_path()` (not re-derive policy); PROTECTED is an enum value in
      `gate_policy.py` that flows through without reimplementation in the hook.
    - Context-slug derivation is PATH-first from the write target: a write under
      `repos/B/...` MUST acquire `repos/B`'s lease, never `repos/A`'s. Parity test:
      monkeypatch `first-ALIVE` to `repos/A`, write target under `repos/B`, assert `repos/B`
      context is acquired.
    - `hooks/ctx_inject.py` preserves the once-per-session sentinel keyed on the harness-native
      session id, guarding the ENTIRE payload; the sentinel path is byte-identical to the shell
      sentinel `.dadaia/tmp/ctx-inject-fired-<sessionId>`. Parity test: second invocation with
      same session id emits nothing.
    - `hooks/sdd_post_gate.py` preserves `os.replace` atomic renewal and `[A-Za-z0-9_-]`
      session-id strip; fail-open parity test: any non-`LockHeldError` → ALLOW; `PROTECTED`
      is the sole fail-closed path.

---

## 14. Dependencies and risks

**Dependencies:**
- ACTIVE.md already points to `release: 0.1.8 / segment: alpha-1 / phase: DEFINITION`.
- `import-linter` must be installable via `poetry add --group dev import-linter`.
- Windows test runner (GitHub Actions `windows-latest`) must be available in CI.

**Risks:**
1. **`container.py` multi-domain edits (Steps 2/5/6)** — three domain concerns touch one
   file; must land sequentially per step ordering to avoid merge conflicts and broken
   intermediate states. Spec-review scrutiny requested: verify the step ordering is
   respected in TASKS.
2. **`gate_policy.py` + `hooks/sdd_gate.py` atomic commit** — these two files are a
   security control; splitting the commit leaves `.dadaia/sessions/` unprotected between
   commits. The TASKS.md must declare them as a single `[ ]` task with one write set.
3. **Bun-runtime Windows subprocess env-passing (ADR-7)** — the `.ts` plugin migration
   may hit a Bun-specific limitation on Windows for the `DADAIA_HOOK_OUTPUT`/
   `DADAIA_HOOK_EVENT` env-passing sub-part. If blocked, OpenCode-on-Windows hook
   governance is explicitly **UNGOVERNED** until a follow-up ships. A backlog item must
   be registered and referenced in CLOSURE. The Python hooks themselves are NOT blocked;
   venv binary resolution is NON-deferrable.
4. **`icacls` availability on Windows Server** — `WindowsFilePermissionSetter` assumes
   `icacls` is on PATH. On Server Core images it may need the full path. Document in the
   adapter's docstring.
5. **macOS green runs** — `continue-on-error` for macOS throughout alpha. If macOS
   reveals unexpected gaps, a follow-up hotfix before Phase-3 graduation is the path.

## rc-1 review record (2026-06-09)

Ship-trio review of the 0.1.8 implementation (feature/0.1.8 HEAD 9a0462c) — **unanimous APPROVE**:
- **security-reviewer — APPROVE.** All 6 mandatory invariants verified with test evidence: CWE-732
  (panel token Tier-1 fail-loud, TOCTOU closed), CWE-78 (icacls shell=False + getpass.getuser),
  SEC-01 PROTECTED (`.dadaia/sessions/**` fail-closed before fail-open, atomic same-commit 73bbb96),
  Windows lock raises (never silent no-op), rc-4 lock-correctness preserved (PATH-first context +
  once-per-session sentinel), no secret/PII leakage (`[ok] public-privacy`). 0 production CVEs.
  Cleared T-018-15, T-018-16, T-018-10 to `[x]`. (Open: devtool CVEs LOW; ctx_inject `.ptr` best-effort INFO.)
- **code-reviewer — APPROVE.** Layering fidelity (import-linter 2 kept/0 broken; core/platform.py sole
  sys.platform site); dead-code kill list confirmed removed (panel server.py dead funcs, _dump
  duplicates, OsProcessProbe moved). One finding (panel auth no-setter `os.chmod` fallback silent
  no-op on Windows, latent CWE-732) FIXED in 9a0462c (raises PlatformSecurityError; +regression test);
  remaining os.chmod sites are Tier-2 (ADR-4) or executability bits — acceptable.
- **qa-engineer — APPROVE.** Full suite 2506 passed / 8 skipped (Windows-runner-only) / 2 xpassed;
  ruff + mypy --strict (213 files) + lint-imports clean; new tests genuine (no slop); CI
  importability-smoke green on windows-latest + macos-latest; Phase-2 matrix present; ubuntu hard-gate intact.

rc-1 is **ship-ready** pending the operator-requested audit + CLOSURE.
