---
name: pid-probe-seam-consolidation
status: candidate
intents:
  - subject: { kind: code, ref: "dadaia_workspace/hooks/sdd_gate.py#_build_pid_probe" }
    change: "stop exporting the private hook-layer pid-probe builder as a de-facto shared seam; hooks/CLI/doctor consume one public composition-root builder instead"
  - subject: { kind: code, ref: "dadaia_workspace/container.py#_build_pid_probe" }
    change: "promote to the single public composition-root pid-probe builder (container.build_pid_probe); preserve None=>TTL-only degrade and the no-steal invariant"
---

# PID-PROBE-SEAM — Consolidate `_build_pid_probe` into one public composition-root builder (LOW)

**Status:** OPEN — candidate. Target: v0.1.12. Nothing here authorizes work; needs
operator pick + grill per release-governance.
**Reported:** 2026-06-11, as a v0.1.11 CLOSURE backlog return (rc-1 code-review finding
LOW-2; PM-curation pre-approved by the release coordinator).

## Problem

The pid-liveness probe builder lives at `hooks.sdd_gate._build_pid_probe` (a private
function of the hook layer) but is now imported from **4 sites**: the sdd_gate hook
itself, `cli/commands/specs.py` (SpecsDoctor seam, v0.1.11 T-011-03),
`container.py::_build_pid_probe` (DoctorService LOCK-GC wiring, v0.1.11 fix `62e8db5`),
and the lock CLI path. A privately-named hook function acting as a de-facto shared
composition-root seam is a layering smell: the hook layer is not a library surface, and
each new consumer repeats the lazy-import dance.

## Direction

Promote the builder to ONE public composition-root home (`container.build_pid_probe()`
or a `core/protocols`-adjacent factory wired in `container.py`), have hooks/CLI/doctor
all consume that single seam, and keep the existing guarantees:

- `features/**` never imports the infrastructure adapter (`OsProcessProbe`) directly —
  import-linter contract unchanged.
- Default `None` ⇒ TTL-only degradation (Windows/legacy-record safe) preserved.
- The no-steal invariant tests (`test_doctor_lock_gc.py`, lock-steal probe gating,
  `lease._main`) stay green unchanged.

## Acceptance seed

- Exactly one production definition of the probe builder; grep shows zero imports of
  `hooks.sdd_gate._build_pid_probe` outside `hooks/sdd_gate.py`.
- `mypy --strict`, import-linter, and the full suite green.
