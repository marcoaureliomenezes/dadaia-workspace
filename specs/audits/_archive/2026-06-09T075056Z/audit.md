---
release: 0.1.8
auditor: project-auditor
audit_date: 2026-06-09T07:50:56Z
branch: feature/0.1.8
head: 7133e3d
verdict: PASS
overall_score: 9.2/10
---

# Audit Report — Release 0.1.8: Cross-Platform OS Compatibility

**Verdict: PASS**  
**Overall score: 9.2 / 10**  
**Branch:** `feature/0.1.8` @ HEAD `7133e3d`  
**Audit date:** 2026-06-09  
**Pre-condition:** ship-trio unanimously APPROVED (security-reviewer, code-reviewer, qa-engineer — recorded in SPEC §rc-1 review record).

---

## 1. Scope

**Audited:**
- Spec↔code fidelity (26 tasks T-018-01..T-018-26)
- Architecture integrity (layering law, import-linter contracts, `sys.platform` isolation)
- Cross-platform completeness (FR-01..FR-14 resolution)
- Dead/stale code (kill list execution)
- Test integrity (pytest suite, Windows-behavior tests, marker sanity)
- Memory/governance consistency (atoms vs. post-0.1.8 implementation state)

**Excluded:**
- Windows-runner-only behavioral tests (require `windows-latest` CI runner — confirmed green per qa-engineer approval)
- Phase-3 CI graduation (ADR-3: `continue-on-error` lines remain; requires a named `feature/0.1.8` CI run reference in CLOSURE)
- T-018-26 CLOSURE itself (currently `[ ]` OPEN — in progress)

---

## 2. Compliance Scorecard

| Dimension          | Score (1–10) | Drift items | Notes |
|--------------------|-------------|-------------|-------|
| Architecture       | 9           | 1 (LOW)     | import-linter 2/2 KEPT; core/platform.py sole sys.platform site; 7 `ignore_imports` are documented transitional debt, not violations |
| Product (spec fidelity) | 9      | 1 (LOW)     | 25/26 tasks [x]; T-018-26 OPEN by design (CLOSURE in progress); T-018-14 missing one done-criterion line (`public_assets.py` chmod guard) |
| Tech stack         | 10          | 0           | `import-linter` added to dev deps; classifier corrected; no new PyPI runtime deps; hardcoded `/tmp` cache paths removed from `pyproject.toml` |
| Security           | 9           | 1 (LOW)     | All CRITICAL/HIGH findings resolved; CWE-732 Tier-1 panel-auth fail-loud confirmed; `icacls shell=False + getpass.getuser`; PROTECTED SEC-01 atomic commit; one residual unguarded `os.chmod(db_path, 0o600)` in telemetry (not in FR-05 evidence list; Tier-2 silent no-op on Windows — not a new security regression) |
| Tests              | 9           | 1 (LOW)     | 2506 passed / 8 skipped / 2 xpassed; skipped = Windows-runner-only (correct pattern); no skip-to-zero; Windows permission tests have 8 genuine passing assertions on Linux via mocked icacls |
| Agent-surface      | 10          | 0           | Python hooks package (6 modules) correct; TS plugins migrated to Python subprocess; runtime_config.py emits Python commands (not .sh); workspace/service.py supersedes stale .sh; projections doctor exit 0 |
| **Overall**        | **9.2**     | **3 total** | Weighted: Arch×0.20 + Prod×0.25 + Tech×0.15 + Sec×0.20 + Test×0.15 + Agent×0.05; floor = min(9,9,10,9,9,10)=9; final = min(9.2, 9+2)=9.2 |

---

## 3. Drift inventory

### DRIFT-01 — T-018-14 done-criterion partially unmet: `public_assets.py` chmod guard missing
- **Dimension:** Product (spec fidelity)
- **Severity:** LOW
- **Description:** TASKS.md T-018-14 write set explicitly includes "`dadaia_workspace/infrastructure/public_assets.py` (guard `chmod(0o755)` with `has_posix_chmod`)". The done criterion states this guard should be added. On inspection `public_assets.py:564` still calls `script.chmod(0o755)` without a `PLATFORM.has_posix_chmod` guard.
- **Spec evidence:** `specs/releases/0.1.8/TASKS.md` T-018-14 write set line: "guard `chmod(0o755)` with `has_posix_chmod`"
- **Code evidence:** `dadaia_workspace/infrastructure/public_assets.py:564` — `script.chmod(0o755)` (no guard); no feature/0.1.8 commits touched this file per `git log feature/0.1.8 -- dadaia_workspace/infrastructure/public_assets.py`
- **Mitigating factor:** The code-reviewer rc-1 APPROVE noted "remaining os.chmod sites are Tier-2 (ADR-4) or executability bits — acceptable." `chmod(0o755)` here sets script executability, not a security-sensitive token. On Windows `Path.chmod()` is a no-op — no crash, no security regression. The ship-trio accepted this state.
- **Action:** Fold into T-018-26 CLOSURE note or register as LOW backlog item for a follow-up cleanup pass. Do NOT block ship.

### DRIFT-02 — `context-management.md` still documents `fcntl Lock-1/Lock-2` without platform abstraction
- **Dimension:** Memory/governance
- **Severity:** LOW (expected pending CLOSURE)
- **Description:** `specs/memory/product/platform/context-management.md` (tldr, summary, and §Locking table) still states "fcntl Lock-1 (workspace)" and "fcntl Lock-2 (per-context git ops)" without mentioning the platform abstraction (Lock-1/Lock-2 now delegate to `infrastructure/file_lock_posix.py` behind the `WorkspaceLock` protocol). SPEC §12 explicitly schedules this update in T-018-26 CLOSURE.
- **Spec evidence:** `specs/releases/0.1.8/SPEC.md §12`: "context-management.md — locking model updated (fcntl behind protocol, Windows adapter)"
- **Code evidence:** `specs/memory/product/platform/context-management.md:6` — tldr still says "fcntl Lock-1/Lock-2 for git ops"
- **Action:** T-018-26 owner (`product-engineer`) must update this atom. Not a blocking finding; CLOSURE is the correct vehicle.

### DRIFT-03 — `workspace-init.md` still references bash hook (`ctx-inject.sh`)
- **Dimension:** Memory/governance
- **Severity:** LOW (expected pending CLOSURE)
- **Description:** `specs/memory/product/platform/workspace-init.md:52` documents `.dadaia/scripts/ctx-inject.sh — hook bash de injeção de contexto`. Post-0.1.8, the hook is a Python module invocation (`python -m dadaia_workspace.hooks.ctx_inject`). SPEC §12 schedules this update in T-018-26.
- **Spec evidence:** `specs/releases/0.1.8/SPEC.md §12`: "workspace-init.md — hooks registration updated (Python hooks, not bash)"
- **Code evidence:** `specs/memory/product/platform/workspace-init.md:52` — references `ctx-inject.sh` as the hook mechanism
- **Action:** T-018-26 owner must update. Not blocking.

---

## 4. Dead / stale code

**Confirmed removed (kill list from SPEC §6 DELETE ledger):**
- `OsProcessProbe` class: removed from `core/protocols/process_probe.py` — file now contains only `ProcessProbe` Protocol (~12 lines, zero I/O). ✓
- `install_shutdown_handlers()` and `serve_blocking()`: `features/panel/server.py` now contains only `build_panel_http_server()` (43 lines). ✓
- Three `_dump()` duplicates: `json_context_store.py`, `json_server_registry_store.py`, `json_course_store.py` — no `def _dump` found. ✓
- Inline atomic-write block in `json_run_state_store._write_manifest_atomic`: consolidated. ✓
- `workflow_launcher_adapter.is_alive()` inline `os.kill` body: delegated to injected `ProcessProbe`. ✓

**No new dead/stale code introduced.** `panel/server.py` is 43 lines (single function). Infrastructure adapters are all referenced by `container.py`. Hooks package 6 modules all have `__main__` entrypoints.

**Observation (INFO):** `tests/unit/core/test_process_probe.py` was noted as "deferred delete" (ledger item-10, T-018-03 done criterion). The file remains, now with updated import path pointing to `infrastructure/process_probe_adapter.py`. This is intentional debt tracked in TASKS, not uncontrolled stale code.

---

## 5. Spec consistency

**All 26 tasks assessed:**
- T-018-01 through T-018-25: `[x]` DONE — implementation confirmed present.
- T-018-26: `[ ]` OPEN — CLOSURE task, correctly not yet done. ACTIVE.md shows `phase: IMPLEMENTATION` (will flip to CLOSURE when T-018-26 begins).

**ACTIVE.md:** points to `release: 0.1.8 / segment: alpha-2 / phase: IMPLEMENTATION`. Correct for a release awaiting CLOSURE.

**SPEC/PLAN/TASKS status:** All `**Status:** Aprovado`. ✓

**CLOSURE.md:** Does not exist yet (expected; T-018-26 authors it). ✓

**Memory atom backlog (pending T-018-26):**
- `context-management.md` — locking model (DRIFT-02)
- `workspace-init.md` — hooks registration (DRIFT-03)
- `architecture.md` — layer law section (platform seam, container.py role)
- `tech-stack.md` — `import-linter` dev dependency entry
- `cross-platform-portability.md` — new atom to be created

**`dadaia specs doctor`:** 0 ERROR, 11 WARN (all WARN are pre-existing token_estimate drift or unknown headings in unrelated atoms — none are 0.1.8 findings). ✓

---

## 6. Dimension analysis

### 6.1 Architecture integrity — Score: 9/10

**import-linter contracts:** 2 contracts, 0 broken (verified via `lint-imports`).
- `features → infrastructure` direct import: KEPT (7 `ignore_imports` documented as transitional ADR-1 debt or pre-existing debt in backlog item `features-import-infrastructure-direct-debt`).
- `core → OS-primitive modules`: KEPT (no fcntl/signal/subprocess/msvcrt in `core/` except via `core.platform` which is correctly whitelisted for `sys`).

**`sys.platform` isolation:** All `sys.platform` usages in `dadaia_workspace/` outside `core/platform.py` are:
- `container.py:134` — interim `if sys.platform == "win32"` function-body guard, annotated `# TODO: Replace with PLATFORM.has_sigterm`. Compliant per SPEC §4.1 ADR-1 transitional window.
- `infrastructure/file_lock_windows.py:27,29,32` — module-level import guard and `platform` attribute passed to exception constructor. Correct: this is an infrastructure adapter module, and passing `sys.platform` to a typed exception attribute is the documented pattern in `core/exceptions.py`.
- `features/panel/auth.py:96` — passes `platform=sys.platform` to `PlatformSecurityError` constructor only. This is correct exception attribution, not a platform-dispatch decision.
- `features/server_registry/scan.py` — docstring only (no code reads). ✓
- `features/telemetry/service.py:57,60` — interim in-body guard, annotated `# TODO: Replace with PLATFORM.has_fcntl`. Compliant per ADR-1.
- `features/spec_context/locking.py:70,76,88,94` — interim in-body guards, annotated `# TODO: replace with PLATFORM.has_fcntl once stable`. Compliant per ADR-1.

**Layer violations (LV-1..LV-5):** All five violations corrected:
- LV-1: `import fcntl` moved to `infrastructure/file_lock_posix.py`. ✓
- LV-2: Full fd lifecycle (`os.open`/`os.write`/`os.close`/`os.flock`) moved to `infrastructure/telemetry_lock_posix.py`. ✓
- LV-3: `OsProcessProbe` moved to `infrastructure/process_probe_adapter.py`. ✓
- LV-4: `runtime_env.py` docstrings rewritten platform-agnostic. ✓
- LV-5: No `os.open`/raw fd in `features/telemetry/service.py`. ✓

**Note (INFO):** `features/spec_context/locking.py:208` still has `os.open(O_WRONLY|O_CREAT|O_APPEND, 0o644)` for the audit log. This is NOT a layer violation (it's not an OS-primitive that the SPEC tracked) and was not in the FR-05 evidence list or the LV violations list. `os.open` with O_APPEND on Windows has non-atomic multi-process behavior, which is a low-severity follow-up item, not a blocking finding for this release.

### 6.2 Cross-platform completeness — embedded in Architecture and Security dimensions

**FR-01:** `import fcntl` removed from features. `python -c "import dadaia_workspace"` exits 0 on Linux. ✓  
**FR-02:** Classifier changed to `POSIX :: Linux`; `test_platform_classifier.py` contract test passes. ✓  
**FR-03:** `core/platform.py` seam exists; sole `sys.platform` call site. ✓  
**FR-04:** `OsProcessProbe` moved to infrastructure. ✓  
**FR-05:** `FilePermissionSetter` protocol + POSIX/Windows adapters; `icacls shell=False + getpass.getuser`; panel Tier-1 fail-loud. ✓  
**FR-06:** `python_env.py` uses `PLATFORM.venv_scripts_dir` and `PLATFORM.venv_exe_suffix`. ✓  
**FR-07:** `dadaia_workspace/hooks/` Python package (6 modules); `runtime_config.py` emits Python commands; `.ts` plugins call Python subprocess. ✓  
**FR-08:** `scan_unregistered_listeners` early-return guard on `not PLATFORM.has_proc_fs`; `os.getuid` via `getattr` guard. ✓  
**FR-09:** Phase-1 importability-smoke job (Windows/macOS allow-fail); Phase-2 unit-fast/contract-coverage matrix with `continue-on-error`. ✓  
**FR-10:** `ShutdownHandler` protocol; `WindowsSignalShutdownHandler` never calls `signal.signal(SIGTERM,...)`. ✓  
**FR-11:** `encoding='utf-8'` on all `open()`/`read_text()`/`write_text()`; `_atomic_write_text` consolidation; `test_io_encoding.py` 7 roundtrip tests. ✓  
**FR-12:** `PLATFORM.tmp_dir / 'dadaia-bugs'` in `cli/main.py`. ✓ (bash hooks superseded by Python hooks).  
**FR-13:** `os.rename` → `os.replace` at `telemetry/service.py:268`. ✓  
**FR-14:** `pytest.importorskip('fcntl')` / `skipif win32` markers on 12+ test files; pytest collection exits 0. ✓

### 6.3 Test integrity — Score: 9/10

**Suite result:** 2506 passed / 8 skipped / 2 xpassed in 52.90s. ✓  
**Skips are correct:** All 8 skips are Windows-runner-only behavior tests (correctly deferred to `windows-latest` CI runner). No skip-to-zero pattern.  
**Windows test genuineness:** `test_file_permission_windows.py` has 8 passing assertions on Linux via mocked `subprocess.run` (verifies `shell=False`, `getpass.getuser`, non-zero exit → `PlatformSecurityError`). `test_file_lock_windows.py` has 4 Windows-runner-skips and 1 Linux-passing import-guard test.  
**mypy --strict:** 0 issues across 213 source files. ✓  
**ruff:** All checks passed. ✓  
**lint-imports:** 2 contracts KEPT, 0 broken. ✓

---

## 7. Memory / governance consistency

**Memory atoms that NOW contradict post-0.1.8 reality (all correctly deferred to T-018-26):**
1. `context-management.md` — still says "fcntl Lock-1/Lock-2" (DRIFT-02)
2. `workspace-init.md` — still says bash hook (DRIFT-03)
3. `architecture.md` — layer law section has no mention of `core/platform.py` seam
4. `tech-stack.md` — no `import-linter` dev dependency entry
5. Missing: `cross-platform-portability.md` atom (not yet created)

These are ALL scheduled in T-018-26 and are NOT blocking. They are the expected pre-CLOSURE state.

**`dadaia specs doctor`:** 0 ERROR. ✓  
**`dadaia public doctor`:** All `[ok]` (verified). ✓

---

## 8. Recommended actions

Priority 1 — **Complete T-018-26 (CLOSURE)** — owner: `product-engineer`
- Author `CLOSURE.md` with task validations and GRADUATION-GATE CI run reference (ADR-3)
- Update 5 memory atoms (DRIFT-02, DRIFT-03, architecture.md, tech-stack.md, new portability atom)
- Flip `ACTIVE.md` phase to ARCHIVED
- Register backlog item for audit-log `os.open(O_APPEND)` Windows non-atomicity (INFO finding)

Priority 2 — **CLOSURE backlog notes** — owner: `product-engineer` (fold into CLOSURE §Drifts)
- `public_assets.py:564` `script.chmod(0o755)` without `PLATFORM.has_posix_chmod` guard (DRIFT-01, LOW). Accepted by code-reviewer as "executability bits — acceptable." Register as LOW backlog follow-up, do NOT re-open T-018-14.
- ADR-7 Bun-runtime Windows env-passing (`DADAIA_HOOK_OUTPUT`/`DADAIA_HOOK_EVENT`) confirmed UNGOVERNED on OpenCode-Windows — must have a registered backlog item referenced in CLOSURE per SPEC ADR-7 deferral contract.
- ADR-3 Phase-3 `continue-on-error` graduation: CLOSURE must record the `feature/0.1.8` CI run reference that confirms both Windows+macOS legs green. Until then, hard-gate upgrade is blocked.
- `test_process_probe.py` deferred-delete (ledger item-10): still present per spec intent; CLOSURE should note the follow-up action.

---

## 9. Evidence sources

All evidence gathered directly by this auditor (no sub-agent dispatch — operator-instructed single-agent mode):

| Evidence | Command / path | Key result |
|---|---|---|
| Test suite | `pytest -p no:cacheprovider -q` | 2506 passed / 8 skipped / 2 xpassed |
| mypy strict | `mypy --strict dadaia_workspace` | 0 issues, 213 files |
| ruff | `ruff check dadaia_workspace/ --no-cache` | All checks passed |
| import-linter | `lint-imports` | 2 contracts KEPT, 0 broken |
| dadaia specs doctor | `dadaia specs doctor` | 0 ERROR, 11 WARN (pre-existing) |
| dadaia public doctor | `dadaia public doctor` | All [ok] |
| sys.platform audit | `grep -rn "sys\.platform" dadaia_workspace/ | grep -v core/platform.py` | Only transitional guards + exception constructors |
| import fcntl in features | `grep -rn "^import fcntl" dadaia_workspace/features/` | 0 matches |
| os.chmod in features | `grep -rn "os\.chmod" dadaia_workspace/features/` | auth.py:86 (POSIX fallback path, guarded), telemetry:175 (Tier-2), telemetry:316 (Tier-2, unguarded — LOW) |
| Dead code kill list | Checked panel/server.py, _dump(), OsProcessProbe | All confirmed removed |
| Classifier test | `tests/contract/test_platform_classifier.py` | PASSED |
| Windows tests | `tests/unit/infrastructure/test_file_{lock,permission}_windows.py` | 9 pass (Linux-safe assertions) / 5 skip (Windows-runner-only) |
| Hooks parity tests | `tests/unit/hooks/` (5 test files) | 51 passed |
| TASKS.md | `specs/releases/0.1.8/TASKS.md` | T-018-01..T-018-25 [x]; T-018-26 [ ] |
| public_assets.py chmod | `dadaia_workspace/infrastructure/public_assets.py:564` | `script.chmod(0o755)` unguarded — LOW, accepted by code-reviewer |
| Memory atoms | `specs/memory/product/platform/{context-management,workspace-init}.md` | Pre-CLOSURE state; fcntl/bash refs pending T-018-26 |
