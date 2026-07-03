---
slug: cross-platform-portability
title: cross-platform-portability
category: product
tldr: dadaia-workspace runs on Linux/macOS/Windows via a core/platform.py seam + port/adapter boundary + 3-tier resilience; governance hooks are Python (no bash).
summary: Establishes the cross-platform foundation for dadaia-workspace v0.1.8 — a
  PLATFORM singleton (sole sys.platform call site), typed platform exceptions, 4 protocol
  ports, 9 infrastructure adapters, a Python governance hooks package, and a hard-gated
  3-OS CI matrix. Defines the 3-tier resilience contract (fail-loud for security,
  degrade-with-log for non-security, unsupported-platform at construction). As of 0.1.8
  rc-2 the Windows + macOS CI legs are GREEN and HARD-GATED (no continue-on-error;
  branch-protection required); classifier is POSIX::Linux + MacOS + Microsoft::Windows.
tags:
- platform
- cross-platform
- portability
- windows
- macos
- linux
- hooks
- security
token_estimate: 1750
last_updated: '2026-07-02'
release_origin: v0.1.48
---

## Purpose

Documents the platform-portability model of dadaia-workspace. Release 0.1.8 closed
the gap between the PyPI classifier `OS Independent` and the Linux-only reality, establishing a
port/adapter boundary for all OS-sensitive domains and a 3-tier resilience
contract that governs behavior on non-Linux platforms.

The foundation is the `core/platform.py` seam: a `PLATFORM` singleton that is the only authorized site
for the `sys.platform` call in the entire codebase. No other file may read `sys.platform`
directly (except during transitional guards in function bodies, per ADR-1, each annotated
with `# TODO: Replace with PLATFORM.has_<flag>`).

## Usage flow

  1. `container.py` reads `PLATFORM` at startup and selects the concrete adapters for each
     OS-sensitive domain (file lock, telemetry lock, file permissions, process probe, signal handling).
  2. `features/` receive the adapters injected via Protocol — zero direct `import fcntl` / `import signal`
     / `os.chmod` in features.
  3. On a Windows runner: `python -c "import dadaia_workspace"` exits 0. `dadaia --help` exits 0.
  4. Governance hooks run as `python -m dadaia_workspace.hooks.<name>` — no bash
     dependency. The registered PreToolUse is the MERGED `pre_gate` entrypoint (root-whitelist →
     venv-guard → SDD gate, first-block-wins); `ctx_inject` and `sdd_post_gate` run as
     their own entrypoints.
  5. The CI importability-smoke job (Windows/macOS) confirms portability on every push.

## Typical trigger

When a new platform (Windows or macOS) needs to run dadaia-workspace, or when an
agent needs to verify that an OS-sensitive capability degrades correctly instead of crashing.

## Differentiator

Without the platform seam, the CLI crashed on Windows before executing any command (top-level
`import fcntl`, `ModuleNotFoundError`). With the seam, the CLI imports and runs on all three OSes. The
port/adapter model guarantees that future additions of Windows support follow a clear pattern
without scattering `sys.platform` checks across the codebase.

## Platform seam — `core/platform.py`

`Capabilities` frozen dataclass with a `detect()` classmethod. Flags:

| Flag | Linux | macOS | Windows |
|------|-------|-------|---------|
| `has_fcntl` | True | True | False |
| `has_proc_fs` | True | False | False |
| `has_posix_chmod` | True | True | False |
| `has_sigterm` | True | True | False |
| `venv_scripts_dir` | `bin` | `bin` | `Scripts` |
| `venv_exe_suffix` | `""` | `""` | `.exe` |
| `tmp_dir` | `Path(tempfile.gettempdir())` | idem | idem |

The `PLATFORM` singleton is accessed via `from dadaia_workspace.core.platform import PLATFORM`.
`detect()` is never called directly — only `PLATFORM` is consumed.

## Resilience contract — 3 tiers

**TIER 1 — FAIL LOUD (security controls; silent no-op forbidden):**
- `WindowsFilePermissionSetter.restrict_to_owner()` — applies the ACL via `icacls <parent_dir> /inheritance:r /grant:r "<user>:(OI)(CI)F"` BEFORE creating the protected file. `icacls` with `shell=False`. Username via `getpass.getuser()`. Failure → `PlatformSecurityError` (never warn-and-continue). (The original consumer — the panel auth token — was removed with the panel's no-auth model; the `panel.token` residue in telemetry is tracked in the `hygiene-and-dead-code-cleanup` backlog.)
- `WindowsFileLock.acquire()` — uses `msvcrt.locking` (stdlib). If `msvcrt` is absent → `PlatformCapabilityError`. Silent no-op is forbidden (it creates false confidence of serialization).

**TIER 2 — DEGRADE WITH INFO LOG (non-security features):**
- `/proc` scan → non-Linux returns `[]` + INFO "orphan detection disabled". Panel shows "Scan unavailable on this platform."
- `signal.SIGTERM` on Windows → registers SIGINT only + INFO log.
- `WindowsTelemetryRefreshLock` → always-acquire no-op + INFO log. Safe because SQLite WAL mode provides its own write serialization. If WAL is ever disabled, this adapter must be revisited.
- `WindowsFilePermissionSetter` on telemetry/lease dirs → Tier 2 (INFO log + continue).
- `os.chmod(db_path, 0o600)` in `features/telemetry/service.py` (1 site) — no `PLATFORM.has_posix_chmod` guard; silent no-op on Windows. Tier-2 acceptable (the telemetry DB is not a security credential). Guard is a low-priority follow-up.
- `script.chmod(0o755)` in `infrastructure/public_assets.py` (1 site) — executability bit; no guard; silent no-op on Windows. Tier-2 acceptable. Guard is a low-priority follow-up.

**TIER 3 — UNSUPPORTED PLATFORM at construction.** Where no degradation exists, `PlatformCapabilityError` / `PlatformSecurityError` is raised in `container.py` at service construction, not at call time.

## Ports and adapters (4 + 9)

**Protocol ports in `core/protocols/`:**
- `file_lock.py` — `WorkspaceLock`, `ContextLock`
- `telemetry_lock.py` — `TelemetryRefreshLock`
- `platform_services.py` — `FilePermissionSetter`
- `shutdown_handler.py` — `ShutdownHandler`

**Adapters in `infrastructure/`:**
- `file_lock_posix.py`, `file_lock_windows.py`
- `telemetry_lock_posix.py`, `telemetry_lock_windows.py`
- `file_permission_posix.py`, `file_permission_windows.py`
- `process_probe_adapter.py` (POSIX; `OsProcessProbe` moved from `core/`)
- `signal_shutdown_posix.py`, `signal_shutdown_windows.py`

## Python governance hooks package

`dadaia_workspace/hooks/` — 8 modules: `__init__`, `_common`, `pre_gate`, `sdd_gate`,
`root_whitelist`, `venv_guard`, `ctx_inject`, `sdd_post_gate`.

PreToolUse wiring: the harness registers **a single** entrypoint, the MERGED `pre_gate`
(`python -m dadaia_workspace.hooks.pre_gate`), which runs the stages root-whitelist →
venv-guard → SDD gate in sequence, first-block-wins. `sdd_gate.py` and `root_whitelist.py`
remain POLICY modules exposing `evaluate_payload()`, consumed by `pre_gate`
(the legacy standalone `main()`s still exist; removal tracked in the
`hygiene-and-dead-code-cleanup` backlog). `ctx_inject` and `sdd_post_gate` have their own entrypoints
(`if __name__ == '__main__': sys.exit(main())`).

Parity invariants (parity contract with the previous bash hooks):
- `sdd_gate.py` delegates to `gate_policy.evaluate()` / `gate_policy.classify_path()` — it does not re-derive policy. `.dadaia/sessions/**` is PROTECTED (fail-closed, SEC-01).
- Context-slug is derived PATH-first from the write target: a write under `repos/B/...` acquires the context of `repos/B`, never of `repos/A` (first-ALIVE).
- `ctx_inject.py` preserves the once-per-session sentinel keyed on the harness-native session id. Sentinel path byte-identical to the bash sentinel (`.dadaia/tmp/ctx-inject-fired-<sessionId>`).
- `sdd_post_gate.py` uses `os.replace` atomic renewal + `[A-Za-z0-9_-]` session-id strip.
- Fail-open: any non-PROTECTED error → ALLOW. PROTECTED is the only fail-closed path.

`runtime_config.py` emits the Python command for `.claude/settings.json`; for Codex, it
emits executable wrappers at `.dadaia/hooks/codex-*` — the platform angle is that each
wrapper resolves the venv Python **relative to its own path**, cross-platform; the
registration/matcher mechanics are owned by [[public-asset-distribution]].
`workspace/service.py` recognizes both the
old `.sh` path and the new Python command to avoid double registration in
migrated workspaces.

PI (`.pi/extensions/dadaia-sdd-gate.ts`, post-trust Ring-1) calls the Python hooks via
subprocess. Venv binary resolution: `.dadaia/.venv/bin/python` →
`.dadaia/.venv/Scripts/python.exe` → bare `python` — cross-platform on Windows.

`pre_push_ci.py` is NOT in the package. The `.sh` pre-push hook is retained (git-for-Windows ships bash).

## CI matrix 3-OS (graduated — hard-gated)

The 3-OS matrix has been **HARD-GATED** since rc-2 (0.1.8). All `continue-on-error` entries were
removed and the `# GRADUATION-GATE:` comment was eliminated. The Windows and macOS legs are
now required checks in branch-protection (6 contexts added via API).

The PyPI classifier was widened from `POSIX :: Linux` to
`POSIX :: Linux + MacOS + Microsoft :: Windows` (no longer the provisional "OS Independent").

**Jobs with 3-OS coverage (Linux/macOS/Windows):** `importability-smoke`, `unit-fast`,
`contract-coverage` — all hard-gated. Any failure on Windows or macOS blocks the merge.

**Linux-only by design (never add Win/macOS):** `integration`, `e2e-python`, `e2e-panel`.
They depend on `/proc` and `ss` — documented in the `scan.py` docstring.

## Runtime state touched

- `dadaia_workspace/core/platform.py` — `PLATFORM` singleton instantiated at module load
- `dadaia_workspace/hooks/` — Python package; executed as a subprocess by the harness
- `.dadaia/scripts/*.sh` — legacy bash scripts; still present but no longer the registered hooks
  (except `pre-push-ci-gate.sh`, which remains active)
- `.claude/settings.json` + `.codex/hooks.json` — hook entries with the Python command

## Dependencies

- Depends on [[workspace-init]] (creates `.venv`, registers the hooks, provisions the Python package)
- [[context-management]] uses the `WorkspaceLock`/`ContextLock` protocols for Lock-1/Lock-2
- [[sdd-gate-v3]] describes the gate's behavior; the Python policy is `hooks/sdd_gate.py`
  (`evaluate_payload()`), consumed by the wired entrypoint `hooks/pre_gate.py`
- [[architecture]] describes the layering invariant and the layer contracts the enforcement depends on
