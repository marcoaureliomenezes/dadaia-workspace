---
name: telemetry-tier2-chmod-unguarded-on-windows
status: candidate
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/telemetry/service.py#TelemetryService" }
    change: "route the telemetry state-dir/DB chmod through the injected FilePermissionSetter (or guard with PLATFORM.has_posix_chmod), removing the Windows silent-no-op while preserving the Tier-2 degrade"
  - subject: { kind: code, ref: "dadaia_workspace/core/protocols/platform_services.py#FilePermissionSetter" }
    change: "use the injected port for telemetry dir/DB restriction, catching PlatformSecurityError -> Tier-2 degrade with an INFO log"
---

# BACKLOG — telemetry Tier-2 os.chmod unguarded on Windows (silent no-op)

**Reported:** 2026-06-09 (0.1.8 rc-1 audit, scorecard `specs/audits/2026-06-09T075056Z/`).
**Severity:** LOW (Tier-2 operational state, not a credential store; accepted degrade per ADR-4).
**Owner:** project-manager (curates) → product-engineer (release definition when picked).
**Status:** CANDIDATE — not picked. Deliberately deferred from 0.1.8 (non-blocking, ship-trio + audit APPROVE).

## Problem

`features/telemetry/service.py` still calls `os.chmod(self._state_dir, 0o700)` (~line 175) and
`os.chmod(db_path, 0o600)` (~line 316) directly. On Windows `os.chmod` is a no-op (CWE-732), so the
telemetry state dir / DB are not actually restricted there. This is **accepted Tier-2 behavior** per
0.1.8 ADR-4 (telemetry is operational state, not a credential store — it degrades, the panel auth
token is the sole Tier-1 control and IS protected via the `FilePermissionSetter`/icacls path). But the
two direct calls are not routed through the injected `FilePermissionSetter` nor guarded with
`PLATFORM.has_posix_chmod`, so they read as inconsistent with the new port/adapter convention.

## Scope when picked

Route the telemetry dir/DB restriction through the injected `FilePermissionSetter` (catching
`PlatformSecurityError` → Tier-2 degrade to telemetry-disabled with an INFO log), OR guard the direct
`os.chmod` calls with `if PLATFORM.has_posix_chmod:`. Either removes the silent-no-op inconsistency
while preserving the Tier-2 degrade contract.

## Evidence

- `dadaia_workspace/features/telemetry/service.py:175,316` (direct `os.chmod`).
- `specs/audits/2026-06-09T075056Z/audit.md` (LOW finding, Security dimension 9/10).
- 0.1.8 SPEC §5 (3-tier resilience) + ADR-4 (telemetry = Tier-2).
