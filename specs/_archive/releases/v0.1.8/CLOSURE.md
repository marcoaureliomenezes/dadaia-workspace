# Closure: Release — 0.1.8

**Status:** Aprovado
**Release ID:** 0.1.8
**Owner:** product-engineer
**Closed:** 2026-06-09

---

## Summary

Release 0.1.8 "Cross-Platform OS Compatibility" closes the structural gap between the
`OS Independent` PyPI classifier dadaia-workspace shipped and its true Linux-only runtime
reality. The release established a platform-abstraction foundation — a `core/platform.py`
seam with a `PLATFORM` singleton as the sole authorized `sys.platform` call site, two
typed platform exceptions (`PlatformSecurityError`, `PlatformCapabilityError`), and a
port/adapter boundary covering every OS-sensitive domain: file locks, telemetry locks,
file permissions, process probing, and signal handling.

All 14 functional requirements (FR-01..FR-14) shipped. The critical CLI crash on Windows
(unconditional `import fcntl` at module top-level) is eliminated; the CLI now imports
cleanly on Windows and macOS. CWE-732 (silent `chmod` no-op on Windows) is remediated
with a Tier-1 fail-loud `icacls`-based `WindowsFilePermissionSetter` — the panel will not
start if it cannot restrict its auth token to owner. Governance hooks are now a Python
package (`dadaia_workspace/hooks/`, 6 modules) with no bash dependency; the OpenCode
`.ts` plugins call Python hooks via subprocess; CI has a phased 3-OS matrix with Phase-1
importability-smoke (Windows/macOS, allow-fail) and Phase-2 `unit-fast`/`contract-coverage`
matrix legs confirmed green on both platforms.

The classifier was corrected to `POSIX :: Linux` to reflect the remaining by-design
Linux surface (integration/E2E tests that depend on `/proc` and `ss`). It will be
restored to a broader `OS Independent` classifier after Phase-3 CI graduation (ADR-3),
which requires removing the `# GRADUATION-GATE:` comment lines once both Windows+macOS
legs pass in a named `feature/0.1.8` CI run.

---

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-018-01 | ADD typed platform exceptions to `core/exceptions.py` | feature/0.1.8 |
| T-018-02 | ADD `core/platform.py` platform seam + unit tests | feature/0.1.8 |
| T-018-03 | Layer-boundary correction — OsProcessProbe MOVE, atomic 4-file commit | feature/0.1.8 |
| T-018-04 | ADD file-lock protocols and POSIX/Windows adapters | feature/0.1.8 |
| T-018-05 | UPDATE `locking.py` — remove `import fcntl`, inject via lazy default | feature/0.1.8 |
| T-018-06 | UPDATE `telemetry/service.py` — remove `import fcntl`, fix getuid, chmod guard, DI refresh_lock wiring | feature/0.1.8 |
| T-018-07 | UPDATE `pyproject.toml` classifier + remove hardcoded cache paths; ADD import-linter `setup.cfg` | feature/0.1.8 |
| T-018-08 | ADD `pytest.importorskip`/`skipif` markers to 12 test files; ADD CLI safe_app test + classifier contract test | feature/0.1.8 |
| T-018-09 | UPDATE `cli/main.py` (PLATFORM.tmp_dir + runtime warning); UPDATE CI workflows (importability-smoke Phase 1 + tool-cache env vars + release.yml RUNNER_TEMP) | feature/0.1.8 |
| T-018-10 | ADD `FilePermissionSetter` protocol + POSIX/Windows adapters; UPDATE security consumers [SEC] | feature/0.1.8 (9a0462c) |
| T-018-11 | ADD `ShutdownHandler` protocol + adapters; UPDATE `panel/server.py`; UPDATE `container.py` `build_shutdown_handler()` | feature/0.1.8 |
| T-018-12 | UPDATE `python_env.py` venv paths + `runtime_env.py` docstrings | feature/0.1.8 |
| T-018-13 | UPDATE `scan.py` platform guards + ADD platform guard tests | feature/0.1.8 |
| T-018-14 | I/O encoding + `_dump()` elimination + `_atomic_write_text` consolidation + `os.rename→os.replace` | feature/0.1.8 |
| T-018-15 | UPDATE `gate_policy.py` PROTECTED class [SEC] (atomic with T-018-16) | feature/0.1.8 (73bbb96) |
| T-018-16 | ADD `dadaia_workspace/hooks/` Python package (6 modules) + unit tests [SEC] | feature/0.1.8 (73bbb96) |
| T-018-17 | UPDATE `runtime_config.py` + `workspace/service.py` to emit Python hook commands | feature/0.1.8 |
| T-018-18 | UPDATE `cli/commands/ci.py` pre-push hook; UPDATE `test_cli_ci.py` | feature/0.1.8 |
| T-018-19 | UPDATE `sdd-gate.ts` + `ctx-inject.ts` to call Python hooks [ADR-7] | feature/0.1.8 |
| T-018-20 | UPDATE `tests/integration/test_hooks.py` Linux-only + portable tmp_path | feature/0.1.8 |
| T-018-21 | CI Phase 2 matrix — unit-fast + contract-coverage Windows/macOS allow-fail | feature/0.1.8 |
| T-018-22 | Propagate + verify projections + full suite green | feature/0.1.8 |
| T-018-23 | qa-engineer alpha segment review + commit | feature/0.1.8 |
| T-018-24 | security-reviewer rc-1 review [SEC] | feature/0.1.8 |
| T-018-25 | code-reviewer rc-1 review | feature/0.1.8 |
| T-018-26 | CLOSURE + memory updates | feature/0.1.8 |

---

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full pytest suite green (Linux) | `pytest -p no:cacheprovider -q` | 2506 passed / 8 skipped (Windows-runner-only) / 2 xpassed |
| ruff format check | `ruff format --check dadaia_workspace/` | All checks passed |
| ruff lint | `ruff check dadaia_workspace/ --no-cache` | All checks passed |
| mypy strict (213 files) | `mypy --strict dadaia_workspace` | 0 issues across 213 source files |
| import-linter contracts | `lint-imports` | 2 contracts KEPT / 0 broken |
| dadaia public doctor | `dadaia public doctor` | exit 0; `[ok] public-privacy`; all projections match staging |
| dadaia specs doctor | `dadaia specs doctor` | 0 ERROR |
| CI importability-smoke green | `.github/workflows/ci.yml` `importability-smoke` job | `windows-latest` + `macos-latest` matrix legs GREEN (Phase-1 allow-fail; Phase-2 `continue-on-error` legs present with `# GRADUATION-GATE:` comment for Phase-3 hard-gate) |
| Platform classifier contract test | `pytest tests/contract/test_platform_classifier.py -v` | PASSED — asserts `Operating System :: POSIX :: Linux` |
| Windows lock adapter tests pass on Linux (mocked) | `pytest tests/unit/infrastructure/test_file_lock_windows.py -v` | 4 skipped (Windows-runner-only) / 1 passed (import guard); Windows-runner behavior verified in CI |
| Windows permission adapter tests pass on Linux (mocked) | `pytest tests/unit/infrastructure/test_file_permission_windows.py -v` | 8 passing (mocked `icacls`); `shell=False` + `getpass.getuser` + non-zero exit → `PlatformSecurityError` all verified |
| Hooks parity suite | `pytest tests/unit/hooks/ -v` | 51 passed — includes PATH-first context-slug parity, once-per-session sentinel parity, `os.replace` atomic renewal, fail-open/fail-closed boundary |
| PROTECTED SEC-01 patch atomic commit | `git log --oneline feature/0.1.8 -- dadaia_workspace/features/spec_context/gate_policy.py` | 73bbb96 — committed atomically with `hooks/sdd_gate.py`; security-reviewer APPROVE |
| panel no-no-setter os.chmod fix | `pytest tests/unit/features/panel/test_auth.py -v` | Regression test for `PlatformSecurityError` when no setter wired; PASSED (9a0462c) |
| ship-trio rc-1 unanimous APPROVE | rc-1 review in `specs/releases/0.1.8/SPEC.md §rc-1 review record` | security-reviewer APPROVE + code-reviewer APPROVE + qa-engineer APPROVE (feature/0.1.8 HEAD 9a0462c) |
| Audit PASS | `specs/audits/2026-06-09T075056Z/audit.md` | PASS 9.2/10; 3 LOW drift items (all scheduled for CLOSURE) |

---

## Drifts

### drift-01-public-assets-chmod-guard-missing

**Description:** TASKS.md T-018-14 declared that `dadaia_workspace/infrastructure/public_assets.py`
would have `script.chmod(0o755)` guarded with `PLATFORM.has_posix_chmod`. The guard was not
applied. `public_assets.py:564` still calls `script.chmod(0o755)` unconditionally. This was
discovered in audit DRIFT-01.

**Resolution:** Accepted by the code-reviewer rc-1 APPROVE: "remaining os.chmod sites are Tier-2
(ADR-4) or executability bits — acceptable." `chmod(0o755)` sets script executability, not a
security-sensitive token. On Windows, `Path.chmod()` is a no-op — no crash, no CWE-732 regression.
The guard is a cleanup-quality improvement, not a correctness or security requirement. Registered
as a LOW backlog follow-up item; do NOT reopen T-018-14.

**Memory updates:** No memory atom update required (guard is a code-quality improvement not visible
at the product/feature level).

### drift-02-adr7-opencode-windows-env-passing-confirmed-governed

**Description:** SPEC ADR-7 stated that the Bun-runtime Windows subprocess env-passing sub-part
(`DADAIA_HOOK_OUTPUT`/`DADAIA_HOOK_EVENT` propagation into a Bun subprocess on Windows) _may_ be
deferred, and if deferred, OpenCode-on-Windows hook governance would be "UNGOVERNED" until a backlog
item ships. The TASKS.md T-018-19 done criterion required registering a backlog item before `[x]` if
deferred.

**Resolution:** The OpenCode-on-Windows surface was confirmed GOVERNED during implementation.
The `.ts` plugins use Bun's cross-platform `.env()` API for env-passing, which does propagate
environment variables on Windows without a bash dependency. The raw-stdout read path used by the
`.ts` plugins is platform-neutral. No ungoverned surface exists. No backlog item is needed for
this deferral. The ADR-7 clarification: the "deferrable Bun-env sub-part" was NOT deferred — it
was resolved by Bun's own cross-platform env API, so the concern does not materialize.

**Memory updates:** `specs/memory/product/platform/cross-platform-portability.md` (new atom)
explicitly documents that OpenCode-on-Windows IS governed.

### drift-03-transitional-adr1-import-guards-in-locking-and-telemetry

**Description:** Per ADR-1, interim `sys.platform` guards in function/constructor bodies are
permitted during the transitional window, each annotated `# TODO: Replace with PLATFORM.has_<flag>`.
`features/spec_context/locking.py` and `features/telemetry/service.py` retain such guards. The
import-linter correctly counts 7 `ignore_imports` for the pre-existing
`features-import-infrastructure-direct-debt` (tracked in backlog).

**Resolution:** This is documented transitional debt, not a violation. The full DI container
wiring (removing all `ignore_imports`) is a follow-up release scope. The backlog item
`features-import-infrastructure-direct-debt` tracks this. No action needed in this release.

**Memory updates:** `specs/memory/architecture.md` documents the ADR-1 transitional-debt pattern.

### drift-04-telemetry-os-chmod-tier2-unguarded

**Description:** `features/telemetry/service.py` contains one `os.chmod(db_path, 0o600)` call
(approximately line 316 in post-0.1.8 code) that is not guarded with `PLATFORM.has_posix_chmod`.
This is a Tier-2 degrade scenario: on Windows it is a silent no-op (chmod has no effect on the
SQLite telemetry DB). The security-reviewer noted this is not in the FR-05 evidence list and does
not represent a new security regression (telemetry DB is not a secret token). The audit (DRIFT-03
of the audit report) rated it LOW.

**Resolution:** Accepted as Tier-2 ADR-4 behavior. The telemetry DB is not security-sensitive
in the same way as the panel auth token. The unguarded chmod is a low-priority cleanup. A guard
can be added as a surgical fix in a follow-up. Not a CWE-732 regression because telemetry data
is not a secret credential file.

**Memory updates:** `specs/memory/product/platform/cross-platform-portability.md` (new atom)
documents the Tier-2 degrade list explicitly, including this case.

### drift-05-devtool-cve-dev-only-dependencies

**Description:** The security-reviewer rc-1 APPROVE noted devtool CVEs (poetry, pip, dulwich)
as LOW findings. These are development-only dependencies and do not appear in the wheel's
runtime dep set.

**Resolution:** Accepted LOW. No action for this release. The operator can `poetry update`
to pick up patched versions on their own schedule. These are not runtime CVEs.

**Memory updates:** None.

---

## Memory updates

- `specs/memory/product/platform/context-management.md` — locking model updated: Lock-1
  (workspace) and Lock-2 (per-context git ops) now operate through the `WorkspaceLock` /
  `ContextLock` protocols with POSIX adapters behind `infrastructure/file_lock_posix.py`;
  removed raw `fcntl` references from tldr/summary/body
- `specs/memory/product/platform/workspace-init.md` — hooks registration updated: init
  now configures Python hook commands (`python -m dadaia_workspace.hooks.*`) instead of
  the bash scripts; `ctx-inject.sh` reference updated
- `specs/memory/tech-stack.md` — `import-linter` dev dependency added; `hooks/` Python
  package noted; Bash entry updated to reflect Python governance hooks
- `specs/memory/architecture.md` — layer law section updated: `core/platform.py` seam
  documented as the sole authorized `sys.platform` call site; layering invariant and
  port/adapter boundary documented; `container.py` composition-root role clarified
- `specs/memory/product/platform/cross-platform-portability.md` — NEW atom: documents
  `core/platform.py` seam, PLATFORM singleton, 3-tier resilience contract, 4 new protocol
  ports, 9 new infrastructure adapters, Python hooks package, phased 3-OS CI matrix,
  current portability state, and known Tier-2 degrade behaviors

---

## Backlog returns

The following items were identified during implementation but are out of scope for 0.1.8:

- `specs/backlog/candidates.md` ← `public-assets-chmod-executability-guard` (LOW): add
  `PLATFORM.has_posix_chmod` guard to `infrastructure/public_assets.py:564`
  `script.chmod(0o755)` call for completeness (code-reviewer accepted current state as
  Tier-2 executability bit; guard is a cleanup-quality improvement)
- `specs/backlog/candidates.md` ← `telemetry-db-chmod-posix-guard` (LOW): add
  `PLATFORM.has_posix_chmod` guard to the unguarded `os.chmod(db_path, 0o600)` in
  `features/telemetry/service.py`; Tier-2 degrade, not a security regression
- `specs/backlog/candidates.md` ← `test-process-probe-deferred-delete` (INFO): delete
  `tests/unit/core/test_process_probe.py` once `tests/unit/infrastructure/test_process_probe_adapter.py`
  is confirmed green in a CI run; ledger item-10 tracks this
- `specs/backlog/candidates.md` ← `audit-log-os-open-windows-non-atomicity` (INFO):
  `features/spec_context/locking.py` uses `os.open(O_WRONLY|O_CREAT|O_APPEND, 0o644)`
  for the audit log; `O_APPEND` is non-atomic for multi-process writes on Windows — low
  severity follow-up; SQLite WAL note: this is NOT the telemetry lock path (that path
  uses the `TelemetryRefreshLock` adapter chain)
- `specs/backlog/candidates.md` ← `ci-phase3-graduation` (FOLLOW-UP): Phase-3 CI matrix
  graduation per ADR-3 — delete the `# GRADUATION-GATE:` comment lines from
  `.github/workflows/ci.yml` once both Windows+macOS legs of `unit-fast` and
  `contract-coverage` pass in a named `feature/0.1.8` CI run; at that point restore the
  `OS Independent` classifier and remove `POSIX :: Linux`

---

## rc-2 — Windows Graduation (operator-requested; same 0.1.8 release, no new version)

rc-1 shipped the cross-platform foundation with the Windows unit/contract CI legs on
`continue-on-error` (the GRADUATION-GATE). rc-2 finished the job **inside 0.1.8** — root-caused
every Windows-runner failure, made the legs genuinely green, hard-gated them, exercised the
msvcrt/icacls adapters on a real Windows runner, and broadened the classifier. The
`ci-phase3-graduation` follow-up listed above is now **DONE** (in this release).

### Tasks (T-018-27..31)

- **T-018-27** — 4 cross-platform **product** bugs fixed:
  - FR-RC2-1 `features/specs/catalog.py`: memory-atom `path` slugs emitted via `.as_posix()`
    (POSIX `/` on every OS — they are stable panel/handoff identifiers).
  - FR-RC2-2 `infrastructure/public_assets_common.py::_atomic_write_text`: writes `newline=""`
    so on-disk bytes equal the LF content the installer hashes; Windows CRLF translation was
    breaking the "skip when content matches" contract (every install rewrote every file). Also
    routed the codex `.toml`, opencode-agent, and staged `manifest.json`/`agents.index.json`
    writers through `_atomic_write_text` (`install_helpers.py`, `public_assets.py`).
  - FR-RC2-3 `features/reports_retention/service.py`: absolute-path guard rejects inputs absolute
    under **either** `PurePosixPath` or `PureWindowsPath` (host-independent).
  - FR-RC2-4 `features/import_/service.py`: old workspace-root matched by `as_posix()`, new path
    rebuilt host-native via `workspace_root / rel` (separator-robust import rewrite).
  - **Windows process-liveness** (`core/platform.py` + `infrastructure/process_probe_adapter.py`):
    new `has_os_kill_liveness` capability; Windows uses a non-destructive
    `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)` existence check instead of `os.kill(pid,0)`
    — CPython implements `os.kill` on Windows as `OpenProcess(PROCESS_ALL_ACCESS)` +
    `TerminateProcess`, which would have *killed* the probed process and reported a dead PID as
    alive (ERROR_INVALID_PARAMETER ≠ ESRCH). ctypes `restype`/`argtypes` declared (no HANDLE
    truncation/leak on Win64).
- **T-018-28** — test-only POSIX assumptions corrected (production already right): auth url-safe
  test injects a `FilePermissionSetter` + POSIX-gate the 0o600/atomic test; markdown-store +
  agents-reader unreadable-file tests force `OSError` via monkeypatched `read_text` (chmod 0o000
  is a no-op on Windows) so the branch runs on every OS; scripts-chmod test POSIX-gated; container
  POSIX-adapter-selection test `importorskip("fcntl")` + Windows-selection test branches on fcntl
  availability; host-native assertions in import/launcher/platform tests; NEW
  `tests/contract/test_install_skip_idempotent.py` pins the LF-exact + skip-idempotence invariant;
  deleted the redundant `tests/unit/core/test_process_probe.py` (the infra adapter test is a strict
  superset — completes the deferred T-018-03 migration); +6 mock-based tests covering all four
  branches of the Windows OpenProcess probe (fake kernel32 + `_FORCE_WINDOWS` seam, runs on every OS).
- **T-018-29** — iterated CI to green over 3 fix rounds. The spurious pytest "KeyboardInterrupt"
  artifact on Windows was a side-effect of the real failures and vanished once they cleared.
- **T-018-30** — graduation: deleted the `GRADUATION-GATE` `continue-on-error` from
  `unit-fast-cross` + `contract-coverage-cross` (+ `importability-smoke`); renamed the jobs to drop
  "allow-fail" — now hard gates. Broadened `pyproject.toml` classifier from `POSIX :: Linux` only
  to `POSIX :: Linux` + `MacOS` + `Microsoft :: Windows` (CI-verified; NOT the over-broad
  `OS Independent` — a deliberate revision of the rc-1 follow-up plan). Updated
  `tests/contract/test_platform_classifier.py`. The real msvcrt-lock (`test_file_lock_windows.py`)
  and icacls (`test_file_permission_windows.py::test_restrict_dir_real_icacls_applies_dacl_or_raises`,
  `skipif != win32`) behavior tests run and pass on the windows-latest runner.
- **T-018-31** — reviews + audit + CLOSURE + PR (this section).

### Graduation evidence (machine-verifiable, ADR-3)

- CI run **27211204722** on `feature/0.1.8`: all six cross-leg matrix jobs (`Unit fast`,
  `Contract coverage`, `Importability smoke` × `{windows-latest, macos-latest}`) green as hard
  gates (first run after deleting the GRADUATION-GATE lines).
- CI run **27212134310** on `feature/0.1.8` (after the code-reviewer finding-fixes): all six
  cross-leg jobs green again — final verification.
- Branch protection on `main` now **requires** those six contexts (added via the GitHub API), so
  the Windows + macOS unit/contract/importability legs block merges, not just colour the run.
- Local Linux gate at finalization: 2085 unit+contract passed / 6 Windows-runner-only skips /
  1 xpass; `ruff format --check` + `ruff check` + `mypy --strict` (213 files) + `lint-imports`
  (2 contracts kept) all clean.

### rc-2 reviews

- **code-reviewer — APPROVE** (2 MEDIUM + 2 LOW findings, all fixed: ctypes restype/argtypes,
  `_FORCE_POSIX` on the missed probe test, stale docstring, +6 Windows-branch tests).
- **security-reviewer — APPROVE** (no findings: OpenProcess probe non-destructive + handle closed
  in finally; reports_retention + import guards strengthened, not weakened).
- **qa-engineer — APPROVE** (test-only fixes preserve intent; no coverage lost by the dedupe
  deletion; new contract + Windows-branch tests are genuine).
- **project-auditor — PASS 9.2/10** (findings all LOW/INFO, satisfied by this CLOSURE update).

### Dependabot (operator-flagged during rc-2)

No security alerts. The 4 open Dependabot PRs were folded into 0.1.8 and closed as superseded:
typer 0.26.6→0.26.7, ruff 0.15.15→0.15.16 (`poetry.lock`), actions/setup-node 6.0.0→6.4.0
(`ci.yml` + `release.yml`), actions/download-artifact 4.1.9→8.0.1 (`release.yml`).

---

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/0.1.8/` via
`git mv`. ACTIVE.md will be updated to `release: none` once the move is complete.
PyPI publish remains **operator-gated** at the `release-gate` environment.
